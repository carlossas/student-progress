"""Gemini settings (AGENTS#8: key from the environment only; AGENTS#14: stable output).

| Env var                 | Where it lives in GitHub | Default            |
|-------------------------|--------------------------|--------------------|
| GEMINI_API_KEY          | secret                   | (required)         |
| GEMINI_MODEL            | repo variable            | gemini-3.8-flash   |
| GEMINI_THINKING_LEVEL   | repo variable            | LOW                |
| GEMINI_FALLBACK_MODELS  | repo variable (csv)      | see FALLBACK       |
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
MAX_OUTPUT_TOKENS = 8192
REQUEST_TIMEOUT_MS = 120_000


class MissingApiKey(RuntimeError):
    pass


@dataclass(frozen=True)
class GeminiSettings:
    api_key: str
    models: tuple[str, ...]
    thinking_level: str

    @classmethod
    def from_env(cls) -> GeminiSettings:
        api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not api_key:
            raise MissingApiKey("GEMINI_API_KEY is not set: add it as a repository secret (never commit it).")
        primary = os.environ.get("GEMINI_MODEL", "").strip() or DEFAULT_MODEL
        extra = [m.strip() for m in os.environ.get("GEMINI_FALLBACK_MODELS", "").split(",") if m.strip()]
        models = tuple(dict.fromkeys([primary, *(extra or FALLBACK)]))
        level = (os.environ.get("GEMINI_THINKING_LEVEL", "").strip() or DEFAULT_THINKING_LEVEL).upper()
        return cls(api_key=api_key, models=models, thinking_level=level)
