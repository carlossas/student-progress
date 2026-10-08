"""Gemini settings (AGENTS#8: key from the environment only; AGENTS#14: stable output).

| Env var                    | Where it lives in GitHub | Default            |
|----------------------------|--------------------------|--------------------|
| GEMINI_API_KEY             | secret                   | (required)         |
| GEMINI_MODEL               | repo variable            | gemini-3.8-flash   |
| GEMINI_THINKING_LEVEL      | repo variable            | LOW                |
| GEMINI_FALLBACK_MODELS     | repo variable (csv)      | see FALLBACK       |
| GEMINI_MAX_OUTPUT_TOKENS   | repo variable            | 4096               |
| GEMINI_MAX_INPUT_TOKENS    | repo variable            | 30000              |
"""

from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_MODEL = "gemini-3.8-flash"

# Tried in order after GEMINI_MODEL when it is out of quota (429) or congested (503).
# Every model here needs a rate in pricing.RATES or the cost line says "approximate".
FALLBACK = ("gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.6-flash")

# A review is "map a diff onto a fixed rule set", not open-ended reasoning: LOW thinking
# keeps cost down and, with temperature 0, keeps findings stable run to run (AGENTS#14).
DEFAULT_THINKING_LEVEL = "LOW"
TEMPERATURE = 0.0
# Fixed sampling seed: temperature alone did not make 3.8 Flash repeat its High findings (R14-B).
SEED = 20261007

# Output (and thinking) bills at 5x the input rate, so the cap is the main cost lever.
# 4096 (raised from 2048 after the R02 AI test truncated in CI, 2026-10-08). The cap only bills
# what the model actually writes, so a higher cap costs nothing on normal PRs. A review that hits
# it is retried with the cap doubled, up to OUTPUT_ESCALATION x the cap (16384); only a review
# that still truncates at the ceiling fails, loudly.
DEFAULT_MAX_OUTPUT_TOKENS = 4096
OUTPUT_ESCALATION = 4
# Input budget per request. A larger PR is split into several requests (one output cap each),
# so cost grows with the PR instead of one huge call that truncates. Typical PRs use ~4k.
DEFAULT_MAX_INPUT_TOKENS = 30_000
REQUEST_TIMEOUT_MS = 120_000


class MissingApiKey(RuntimeError):
    pass


@dataclass(frozen=True)
class GeminiSettings:
    api_key: str
    models: tuple[str, ...]
    thinking_level: str
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS
    max_input_tokens: int = DEFAULT_MAX_INPUT_TOKENS

    @classmethod
    def from_env(cls, require_key: bool = True) -> GeminiSettings:
        api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if require_key and not api_key:
            raise MissingApiKey("GEMINI_API_KEY is not set: add it as a repository secret (never commit it).")
        primary = os.environ.get("GEMINI_MODEL", "").strip() or DEFAULT_MODEL
        extra = [m.strip() for m in os.environ.get("GEMINI_FALLBACK_MODELS", "").split(",") if m.strip()]
        models = tuple(dict.fromkeys([primary, *(extra or FALLBACK)]))
        level = (os.environ.get("GEMINI_THINKING_LEVEL", "").strip() or DEFAULT_THINKING_LEVEL).upper()
        max_out = int(os.environ.get("GEMINI_MAX_OUTPUT_TOKENS", "").strip() or DEFAULT_MAX_OUTPUT_TOKENS)
        max_in = int(os.environ.get("GEMINI_MAX_INPUT_TOKENS", "").strip() or DEFAULT_MAX_INPUT_TOKENS)
        return cls(api_key, models, level, max_output_tokens=max_out, max_input_tokens=max_in)
