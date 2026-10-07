"""Cost accounting for a review, ported from the reporting-spike agent.

TOKEN COUNTS ARE REAL: every figure comes from `usage_metadata` in the Gemini response.
PRICES ARE A TABLE: Google publishes no pricing API, so the rates below are transcribed by
hand from ai.google.dev/gemini-api/docs/pricing (verified 2026-10-07) and go stale when
Google changes them. Thinking tokens bill at the OUTPUT rate. Input tokens served from
Gemini's implicit cache (the stable system prompt) bill at 10% of the input rate.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import date

# USD per 1M tokens. (input, output, promo end, (input, output) after promo)
RATES: dict[str, tuple[float, float, str | None, tuple[float, float] | None]] = {
    "gemini-3.8-flash": (0.75, 3.75, "2027-01-01", (1.50, 7.50)),
    "gemini-3.7-flash": (0.75, 3.75, "2027-01-01", (1.50, 7.50)),
    "gemini-3.6-flash": (0.75, 3.75, "2027-01-01", (1.50, 7.50)),
    "gemini-3.5-flash": (1.50, 9.00, None, None),
    "gemini-3.5-flash-lite": (0.30, 2.50, None, None),
    "gemini-2.5-flash": (0.30, 2.50, None, None),
}
FALLBACK_RATE = (0.75, 3.75)
# Context-caching price as a fraction of the input rate (0.075 vs 0.75 on 3.x Flash).
CACHED_INPUT_FACTOR = 0.10


def rate_for(model: str, on: date | None = None) -> tuple[float, float, bool]:
    """(input, output, known) USD per 1M tokens."""
    if model not in RATES:
        return (*FALLBACK_RATE, False)
    inp, out, until, after = RATES[model]
    if until and after and (on or date.today()) >= date.fromisoformat(until):
        return (*after, True)
    return (inp, out, True)


@dataclass(frozen=True)
class Usage:
    model: str
    prompt_tokens: int = 0
    cached_tokens: int = 0
    output_tokens: int = 0
    thinking_tokens: int = 0
    calls: int = 0

    def add(self, meta, model: str) -> Usage:
        """Folds one response's usage_metadata into the running total."""
        if meta is None:
            return replace(self, model=model, calls=self.calls + 1)
        return Usage(
            model=model,
            prompt_tokens=self.prompt_tokens + (meta.prompt_token_count or 0),
            cached_tokens=self.cached_tokens + (meta.cached_content_token_count or 0),
            output_tokens=self.output_tokens + (meta.candidates_token_count or 0),
            thinking_tokens=self.thinking_tokens + (meta.thoughts_token_count or 0),
            calls=self.calls + 1,
        )

    def cost(self, on: date | None = None) -> dict:
        inp, out, known = rate_for(self.model, on)
        uncached = max(self.prompt_tokens - self.cached_tokens, 0)
        input_usd = (uncached + self.cached_tokens * CACHED_INPUT_FACTOR) / 1e6 * inp
        output_usd = self.output_tokens / 1e6 * out
        thinking_usd = self.thinking_tokens / 1e6 * out
        return {
            **asdict(self),
            "input_usd": round(input_usd, 6),
            "output_usd": round(output_usd, 6),
            "thinking_usd": round(thinking_usd, 6),
            "total_usd": round(input_usd + output_usd + thinking_usd, 6),
            "cache_savings_usd": round(self.cached_tokens * (1 - CACHED_INPUT_FACTOR) / 1e6 * inp, 6),
            "rate_known": known,
        }
