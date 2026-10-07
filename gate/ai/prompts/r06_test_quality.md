### AGENTS#6 — tests must be able to fail (B8) · high

Judge whether the tests in the diff would fail if the behavior they cover broke. Flag (on the weak test):
- trivial assertions (`assert True`, `isinstance(...)`, `>= 0`, status code in a set of values);
- mocking the very function under test;
- asserting on implementation details instead of behavior;
- missing edge cases the code obviously has (empty input, zero, duplicates, boundaries);
- tests that lock in a wrong behavior.

Coverage is already measured by a script; high coverage with weak assertions is still a finding.
