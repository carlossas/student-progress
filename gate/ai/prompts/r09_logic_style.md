### AGENTS#9 — logic bugs (B11) · high, and style (B12) · low

- **B11** Logic that produces incorrect data: wrong formulas, truncation where rounding is expected, double counting, off-by-one, wrong defaults for edge cases, behavior that contradicts the docstring or the business rules in the context section. Explain the input that produces the wrong output.
- **B12** Style, naming, readability, refactoring ideas. Always `low`. Report at most two, only on changed lines.
