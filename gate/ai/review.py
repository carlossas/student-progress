"""Pipeline B: Gemini reviews the PR for every AI check (B1-B12).

One request per batch of files: a typical PR is a single request; a large PR is split so each
request stays under GEMINI_MAX_INPUT_TOKENS (prompt_builder.plan_batches).

Each request's result is cached by a hash of everything that shapes it: the files in the
batch (with their changed lines), the PR title/description, the deterministic findings, the
system prompt and the model settings. A re-run on an unchanged PR costs nothing; any change
gives a new key, so a stale answer is never reused.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from gate.ai.client import GeminiClient
from gate.ai.config import GeminiSettings, MissingApiKey
from gate.ai.pricing import Usage
from gate.ai.prompt_builder import plan_batches, response_schema, system_prompt, user_prompt
from gate.ai.validate import validate_ai_output
from gate.config import valid_rules
from gate.diff import DiffContext
from gate.report.finding import Finding, Signal
from gate.report.merge import dedupe

log = logging.getLogger("gate.ai")
CACHE_FORMAT = 1
SUMMED = ("prompt_tokens", "cached_tokens", "output_tokens", "thinking_tokens", "calls")
SUMMED_USD = ("input_usd", "output_usd", "thinking_usd", "total_usd", "cache_savings_usd", "original_total_usd")


@dataclass
class AIResult:
    findings: list[Finding]
    dropped: list[tuple[dict, str]] = field(default_factory=list)
    cost: dict = field(default_factory=dict)
    model: str = ""
    cached: bool = False
    cache_key: str = ""
    requests: int = 1


def cache_key(settings: GeminiSettings, system: str, user: str, schema: dict) -> str:
    payload = {
        "format": CACHE_FORMAT,
        "models": settings.models,
        "thinking": settings.thinking_level,
        "max_output_tokens": settings.max_output_tokens,
        "schema": schema,
        "system": system,
        "user": user,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def build_requests(ctx: DiffContext, deterministic: list[Finding], signals: list[Signal], settings: GeminiSettings):
    """(system, [user prompt per batch], schema)."""
    batches = plan_batches(ctx, deterministic, signals, settings.max_input_tokens)
    if len(batches) == 1:  # the common case: byte-identical to an unbatched request
        users = [user_prompt(ctx, deterministic, signals, narrow=batches[0][1])]
    else:
        users = [user_prompt(ctx, deterministic, signals, batch=b, narrow=n) for b, n in batches]
    return system_prompt(), users, response_schema()


def review_key(ctx: DiffContext, deterministic=None, signals=None, settings: GeminiSettings | None = None) -> str:
    """One key for the whole review, computable without an API key (CI uses it to restore the cache)."""
    settings = settings or GeminiSettings.from_env(require_key=False)
    system, users, schema = build_requests(ctx, deterministic or [], signals or [], settings)
    keys = [cache_key(settings, system, user, schema) for user in users]
    return keys[0] if len(keys) == 1 else hashlib.sha256("".join(keys).encode()).hexdigest()


def _merge_costs(costs: list[dict]) -> dict:
    merged = dict(costs[-1])
    for key in SUMMED:
        merged[key] = sum(c.get(key, 0) for c in costs)
    for key in SUMMED_USD:
        merged[key] = round(sum(c.get(key, 0.0) for c in costs), 6)
    merged["rate_known"] = all(c.get("rate_known", True) for c in costs)
    return merged


def _review_one(ctx, system, user, schema, settings, client, cache_dir) -> tuple[AIResult, object]:
    key = cache_key(settings, system, user, schema)
    cache_file = Path(cache_dir) / f"{key}.json" if cache_dir is not None else None
    if cache_file is not None and cache_file.exists():
        entry = json.loads(cache_file.read_text(encoding="utf-8"))
        findings, dropped = validate_ai_output(entry["raw"], ctx, valid_rules())
        log.info("AI review served from cache %s (model %s)", key[:12], entry["model"])
        cost = {**Usage(model=entry["model"]).cost(), "original_total_usd": entry.get("total_usd", 0.0)}
        return AIResult(findings, dropped, cost, entry["model"], cached=True, cache_key=key), client
    if client is None:
        if not settings.api_key:
            raise MissingApiKey("GEMINI_API_KEY is not set: add it as a repository secret (never commit it).")
        client = GeminiClient(settings)
    raw, model, usage = client.generate_json(system, user, schema)
    findings, dropped = validate_ai_output(raw, ctx, valid_rules())  # raises on malformed output: never cached
    cost = usage.cost()
    if cache_file is not None:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(
            json.dumps({"model": model, "raw": raw, "total_usd": cost["total_usd"]}), encoding="utf-8"
        )
    return AIResult(findings, dropped, cost, model, cached=False, cache_key=key), client


def review(
    ctx: DiffContext,
    deterministic: list[Finding] | None = None,
    signals: list[Signal] | None = None,
    client=None,
    cache_dir: Path | None = None,
    settings: GeminiSettings | None = None,
) -> AIResult:
    settings = settings or GeminiSettings.from_env(require_key=False)
    system, users, schema = build_requests(ctx, deterministic or [], signals or [], settings)
    if len(users) > 1:
        log.warning("large PR: AI review split into %d requests (GEMINI_MAX_INPUT_TOKENS)", len(users))
    parts = []
    for user in users:
        part, client = _review_one(ctx, system, user, schema, settings, client, cache_dir)
        parts.append(part)
    if len(parts) == 1:
        return parts[0]
    return AIResult(
        findings=dedupe([f for p in parts for f in p.findings]),
        dropped=[d for p in parts for d in p.dropped],
        cost=_merge_costs([p.cost for p in parts]),
        model=parts[-1].model,
        cached=all(p.cached for p in parts),
        cache_key=review_key(ctx, deterministic, signals, settings),
        requests=len(parts),
    )
