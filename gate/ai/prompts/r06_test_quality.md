### AGENTS#6 — tests must be able to fail (B8)

Judge whether the tests in the diff would fail if the behavior they cover broke. The severity depends on that question, not on how complete the tests are.

**high** (blocks): the tests **cannot fail** when the behavior breaks. Report on the weak test:
- trivial assertions (`assert True`, `isinstance(...)`, `>= 0`, a status code checked against a set of values);
- mocking the very function under test;
- asserting on implementation details instead of behavior;
- tests that lock in a wrong behavior;
- core logic added with no effective test at all.

**medium** (comment): the tests **would fail** if the behavior broke, but could be stronger:
- a missing edge case (empty input, zero, duplicates, boundaries, non-numeric input);
- a status code or a field not asserted next to assertions that do check behavior;
- one more case worth adding.

Example: tests that assert exact rejections (422) for bad input but don't check the 200 of the valid case, or skip non-numeric input, are **medium**. Tests that only assert `isinstance(result, int)` are **high**.

Coverage is already measured by a script; high coverage with assertions that can't fail is still high.
