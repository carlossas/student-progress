"""Cost controls of the AI pipeline, tested offline (no Gemini calls)."""

import json
from types import SimpleNamespace

import pytest

from gate.ai.client import GeminiClient, OutputTruncated
from gate.ai.config import DEFAULT_MAX_OUTPUT_TOKENS, GeminiSettings
from gate.ai.pricing import Usage
from gate.ai.prompt_builder import agents_excerpt, system_prompt, user_prompt
from gate.ai.review import review
from gate.ai.validate import AIOutputError
from gate.config import AGENTS_MD
from gate.diff import DiffContext

SETTINGS = GeminiSettings(api_key="test", models=("gemini-3.8-flash",), thinking_level="LOW")
FINDING = {
    "rule": "AGENTS#1",
    "severity": "critical",
    "check": "B1",
    "file": "app/main.py",
    "line": 2,
    "message": "Email logged.",
    "suggestion": "Log student.id.",
}


class FakeClient:
    def __init__(self, raw):
        self.raw, self.calls = raw, 0

    def generate_json(self, system, prompt, schema):
        self.calls += 1
        return self.raw, "gemini-3.8-flash", Usage("gemini-3.8-flash", prompt_tokens=4000, output_tokens=500, calls=1)


def repo(tmp_path, body):
    (tmp_path / "app").mkdir(parents=True, exist_ok=True)
    (tmp_path / "app" / "main.py").write_text(body, encoding="utf-8")
    return DiffContext(tmp_path, {"app/main.py": None}, "fixture", pr_title="t", pr_body="b")


def test_ai_result_cache_keyed_by_the_request(tmp_path):
    cache = tmp_path / "cache"
    client = FakeClient(json.dumps({"findings": [FINDING]}))
    ctx = repo(tmp_path / "r", "import logging\nlogging.info(student.email)\n")

    first = review(ctx, client=client, cache_dir=cache, settings=SETTINGS)
    again = review(ctx, client=client, cache_dir=cache, settings=SETTINGS)
    assert client.calls == 1 and not first.cached and again.cached
    assert again.findings == first.findings
    assert again.cost["total_usd"] == 0 and again.cost["original_total_usd"] == first.cost["total_usd"]

    # A different diff, different settings or different PR text: new key, new call.
    review(
        repo(tmp_path / "r", "import logging\nlogging.info(student.id)\n"),
        client=client,
        cache_dir=cache,
        settings=SETTINGS,
    )
    review(ctx, client=client, cache_dir=cache, settings=GeminiSettings("test", SETTINGS.models, "MEDIUM"))
    ctx.pr_body = "now with a legal basis"
    review(ctx, client=client, cache_dir=cache, settings=SETTINGS)
    assert client.calls == 4

    # A malformed answer is a gate error and is never cached.
    with pytest.raises(AIOutputError):
        review(
            repo(tmp_path / "s", "x = 1\n"), client=FakeClient("not json"), cache_dir=tmp_path / "c2", settings=SETTINGS
        )
    assert not (tmp_path / "c2").exists() or not list((tmp_path / "c2").iterdir())


def test_output_cap_is_configurable_and_truncation_fails_loudly(monkeypatch):
    monkeypatch.delenv("GEMINI_MAX_OUTPUT_TOKENS", raising=False)
    assert GeminiSettings.from_env(require_key=False).max_output_tokens == DEFAULT_MAX_OUTPUT_TOKENS == 4096
    monkeypatch.setenv("GEMINI_MAX_OUTPUT_TOKENS", "8192")
    assert GeminiSettings.from_env(require_key=False).max_output_tokens == 8192

    client = GeminiClient(SETTINGS)
    truncated = SimpleNamespace(
        text='{"findings": [',
        usage_metadata=None,
        candidates=[SimpleNamespace(finish_reason="FinishReason.MAX_TOKENS")],
    )
    caps = []

    def always_truncated(model, contents, config):
        caps.append(config.max_output_tokens)
        return truncated

    # Doubles the cap up to 4x before giving up, then fails loudly (never a truncated pass).
    monkeypatch.setattr(client._client.models, "generate_content", always_truncated)
    with pytest.raises(OutputTruncated, match="GEMINI_MAX_OUTPUT_TOKENS"):
        client.generate_json("system", "prompt", {"type": "object"})
    assert caps == [4096, 8192, 16384]


def test_truncated_review_is_retried_with_a_bigger_cap(monkeypatch):
    # R02 AI test, 2026-10-08: a PR with many real problems hit 2048 and failed the gate.
    client = GeminiClient(SETTINGS)
    meta = SimpleNamespace(
        prompt_token_count=4000, cached_content_token_count=0, candidates_token_count=4096, thoughts_token_count=0
    )
    truncated = SimpleNamespace(
        text='{"findings": [', usage_metadata=meta, candidates=[SimpleNamespace(finish_reason="MAX_TOKENS")]
    )
    complete = SimpleNamespace(
        text='{"findings": []}', usage_metadata=meta, candidates=[SimpleNamespace(finish_reason="STOP")]
    )
    caps = []

    def truncated_once(model, contents, config):
        caps.append(config.max_output_tokens)
        return truncated if len(caps) == 1 else complete

    monkeypatch.setattr(client._client.models, "generate_content", truncated_once)
    text, model, usage = client.generate_json("system", "prompt", {"type": "object"})
    assert (text, caps) == ('{"findings": []}', [4096, 8192])
    assert (usage.calls, usage.output_tokens) == (2, 8192)  # the truncated try is billed too


def test_system_prompt_is_stable_and_shrunk(tmp_path):
    full = AGENTS_MD.read_text(encoding="utf-8")
    excerpt = agents_excerpt(full)
    assert "**Personal data fields**" in excerpt and "`is_minor`" in excerpt
    numbers = {int(line.split(".")[0]) for line in excerpt.splitlines() if line[:1].isdigit()}
    assert numbers == {1, 2, 3, 4, 5, 6, 20, 21}
    assert len(excerpt) < len(full) * 0.75

    # Byte-identical for every PR, so Gemini's prompt cache can serve it.
    a, b = repo(tmp_path / "a", "x = 1\n"), repo(tmp_path / "b", "y = 2\n")
    assert system_prompt() == system_prompt()
    assert "x = 1" not in system_prompt()
    # Repository context comes before the PR so the cacheable prefix is longer.
    (tmp_path / "a" / "app" / "privacy.py").write_text('PII_FIELDS = {"email"}\n', encoding="utf-8")
    prompt = user_prompt(a, [], [])
    assert prompt.index("<repository_context>") < prompt.index("<pull_request>") < prompt.index("x = 1")
    assert user_prompt(b, [], []) != prompt


def test_cached_input_is_priced_at_the_cache_rate():
    cold = Usage("gemini-3.8-flash", prompt_tokens=1_000_000, cached_tokens=0).cost()
    warm = Usage("gemini-3.8-flash", prompt_tokens=1_000_000, cached_tokens=600_000).cost()
    assert warm["input_usd"] == pytest.approx(cold["input_usd"] * (0.4 + 0.6 * 0.1))
    assert warm["cache_savings_usd"] == pytest.approx(cold["input_usd"] * 0.6 * 0.9)


def test_large_pr_is_trimmed_excluded_and_batched(tmp_path):
    from gate.ai.prompt_builder import estimate_tokens, numbered, plan_batches, reviewable_files

    # Big files: only the changed hunk (+/- context) is sent, with the gaps marked.
    big = "\n".join(f"x{n} = {n}" for n in range(1, 1001))
    excerpt = numbered(big, {500})
    assert "+  500 | x500 = 500" in excerpt and "x1 = 1\n" not in excerpt
    assert "... lines 1-469 unchanged, not shown" in excerpt and "... lines 531-1000 unchanged" in excerpt

    # Generated files are never sent; 8 code files of ~2k tokens each.
    files = {f"app/m{i}.py": f"# module {i}\n" + "value = 'abcdefghij' * 3\n" * 250 for i in range(8)}
    files |= {"eval/results/pr.ai.json": "{}", "package-lock.json": "{}"}
    root = tmp_path / "big"
    for name, text in files.items():
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_text(text, encoding="utf-8")
    ctx = DiffContext(root, {name: None for name in files}, "fixture")
    assert reviewable_files(ctx) == sorted(f for f in files if f.startswith("app/"))

    # A 9k-token input budget splits the PR into several requests, each under budget.
    settings = GeminiSettings("test", SETTINGS.models, "LOW", max_input_tokens=9_000)
    batches = plan_batches(ctx, [], [], settings.max_input_tokens)
    assert len(batches) > 1 and sorted(p for b, _ in batches for p in b) == reviewable_files(ctx)
    assert all(
        estimate_tokens(user_prompt(ctx, [], [], batch=b)) + estimate_tokens(system_prompt()) <= 9_000
        for b, _ in batches
    )

    finding = {**FINDING, "file": "app/m0.py", "line": 2}
    client = FakeClient(json.dumps({"findings": [finding]}))
    result = review(ctx, client=client, cache_dir=tmp_path / "cache", settings=settings)
    assert client.calls == result.requests == len(batches)
    assert len(result.findings) == 1  # the same finding from every batch is merged
    assert result.cost["prompt_tokens"] == 4000 * len(batches)

    again = review(ctx, client=client, cache_dir=tmp_path / "cache", settings=settings)
    assert again.cached and client.calls == len(batches)  # every batch served from cache

    # A typical PR is one request, byte-identical to the unbatched prompt (keeps old cache keys valid).
    small = repo(tmp_path / "small", "x = 1\n")
    assert plan_batches(small, [], [], SETTINGS.max_input_tokens) == [(["app/main.py"], frozenset())]
