"""Gemini client with a model fallback chain, ported from the reporting-spike agent.

Two failures, opposite handling: 503 is transient congestion, so retry the same model with
backoff; 429 is spent quota, so move to the next model immediately. Every model's outcome is
recorded, so a failure tells the operator whether it is quota, billing or Google.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass

from google import genai
from google.genai import errors, types

from gate.ai.config import REQUEST_TIMEOUT_MS, SEED, TEMPERATURE, GeminiSettings
from gate.ai.pricing import Usage

log = logging.getLogger("gate.ai")


@dataclass
class ModelStatus:
    model: str
    code: int | str
    status: str
    message: str = ""
    quota: str = ""
    retry_after: str = ""


class GeminiUnavailable(RuntimeError):
    """Every model in the chain failed. The review did not run; the gate must not pass silently."""

    def __init__(self, message: str, detail: list[ModelStatus]):
        super().__init__(message)
        self.detail = detail


class OutputTruncated(GeminiUnavailable):
    """The review was cut by the output cap: a gate error, never a partial (silently passing) review."""


def describe(model: str, e: Exception) -> ModelStatus:
    code = getattr(e, "code", 0) or 0
    status = ModelStatus(model=model, code=code, status=str(getattr(e, "status", "") or "UNKNOWN"))
    status.message = str(getattr(e, "message", "") or e)[:160]
    details = getattr(e, "details", None) or {}
    if isinstance(details, str):
        try:
            details = json.loads(details)
        except ValueError:
            details = {}
    for d in (details.get("error", {}) if isinstance(details, dict) else {}).get("details", []) or []:
        kind = str(d.get("@type", ""))
        if "QuotaFailure" in kind and d.get("violations"):
            v = d["violations"][0]
            status.quota = f"{v.get('quotaMetric', '')} = {v.get('quotaValue', '')} ({v.get('quotaId', '')})"
        if "RetryInfo" in kind:
            status.retry_after = str(d.get("retryDelay", ""))
    return status


def classify_limit(results: list[ModelStatus]) -> str:
    text = " ".join(f"{r.message} {r.quota}" for r in results).lower()
    if "prepayment credits" in text:
        return "prepaid_depleted"
    if "freetier" in text or "free_tier" in text:
        return "free_tier"
    if any(r.code == 429 for r in results):
        return "rate_limit"
    return "none"


BILLING_HINT = {
    "prepaid_depleted": "AI Studio PREPAID CREDITS are exhausted (not free tier, not congestion): top up at aistudio.google.com/apikey.",
    "free_tier": "The API key is on the FREE TIER. A Google AI Pro subscription does not apply to API keys.",
    "rate_limit": "Rate limit reached. A retryDelay in seconds means a per-minute limit; re-run the job later.",
    "none": "",
}


class GeminiClient:
    def __init__(self, settings: GeminiSettings):
        self.settings = settings
        self._client = genai.Client(
            api_key=settings.api_key, http_options=types.HttpOptions(timeout=REQUEST_TIMEOUT_MS)
        )

    def generate_json(self, system: str, prompt: str, schema: dict) -> tuple[str, str, Usage]:
        """One structured review call. Returns (raw JSON text, model that served it, usage)."""
        config = types.GenerateContentConfig(
            system_instruction=system,
            temperature=TEMPERATURE,
            seed=SEED,
            max_output_tokens=self.settings.max_output_tokens,
            thinking_config=types.ThinkingConfig(thinking_level=self.settings.thinking_level),
            response_mime_type="application/json",
            response_json_schema=schema,
            # No tools: a single structured answer. Also silences the SDK's AFC warning.
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )
        results: list[ModelStatus] = []
        for model in self.settings.models:
            last = None
            for attempt in range(3):
                try:
                    res = self._client.models.generate_content(model=model, contents=prompt, config=config)
                    usage = Usage(model=model).add(res.usage_metadata, model)
                    finish = str(res.candidates[0].finish_reason) if res.candidates else ""
                    if "MAX_TOKENS" in finish:
                        raise OutputTruncated(
                            f"{model} hit the output cap ({self.settings.max_output_tokens} tokens) before finishing "
                            "the review. Raise the GEMINI_MAX_OUTPUT_TOKENS repo variable and re-run.",
                            results,
                        )
                    if not res.text:
                        reason = res.candidates[0].finish_reason if res.candidates else "no candidates"
                        raise GeminiUnavailable(
                            f"{model} returned an empty response (finish_reason={reason}).", results
                        )
                    return res.text, model, usage
                except errors.APIError as e:
                    last = describe(model, e)
                    log.warning("gemini %s attempt %d: HTTP %s %s", model, attempt + 1, last.code, last.status)
                    if last.code == 429:
                        break  # quota: next model
                    if last.code not in (500, 503, 504):
                        results.append(last)
                        raise GeminiUnavailable(
                            f"{model}: HTTP {last.code} {last.status} {last.message}", results
                        ) from e
                    time.sleep(2 * (attempt + 1))
            if last:
                results.append(last)
        lines = "\n".join(f"  {r.model}: HTTP {r.code} {r.status} {r.quota} {r.retry_after}".rstrip() for r in results)
        raise GeminiUnavailable(
            f"Every Gemini model failed.\n{lines}\n{BILLING_HINT[classify_limit(results)]}".strip(), results
        )


def probe(settings: GeminiSettings) -> tuple[bool, str]:
    """(usable, reason). Reads the model's metadata: checks key and model without spending tokens."""
    if not settings.api_key:
        return False, "GEMINI_API_KEY is not set"
    model = settings.models[0]
    try:
        # Keep a reference: google-genai closes a client when it is garbage-collected,
        # which would make the probe report "unreachable" for a perfectly valid key.
        client = genai.Client(api_key=settings.api_key, http_options=types.HttpOptions(timeout=15_000))
        client.models.get(model=model)
    except errors.APIError as e:
        status = describe(model, e)
        return False, f"{model}: HTTP {status.code} {status.status} {status.message}".strip()
    except Exception as e:  # noqa: BLE001 - network/DNS problems mean "skip the AI step", reported to the user
        return False, f"cannot reach Gemini: {e}"
    return True, ""
