"""B8 severity: High only when tests cannot fail; tests that could be stronger are Medium.

Found by the CI eval (2026-10-08): a fresh run on score-validation returned High AGENTS#6 for
"doesn't assert the 200, no non-numeric case" and blocked a PR whose truth is "comment".
"""

import pytest

from tests.gate.helpers import FIXTURES, ai_findings, by_rule, requires_gemini

pytestmark = [pytest.mark.ai, requires_gemini]


def test_r06_test_severity_ai():
    # Tests that assert exact rejections but miss a case: at most Medium, never blocking.
    stronger = by_rule(ai_findings(FIXTURES / "r06-ai-medium"), "AGENTS#6")
    assert not [f for f in stronger if f.severity in ("critical", "high")], stronger

    # Tests that cannot fail (isinstance, assert True, mocking the function under test): High.
    cannot_fail = by_rule(ai_findings(FIXTURES / "r06-ai" / "violation"), "AGENTS#6")
    assert any(f.severity == "high" for f in cannot_fail), cannot_fail
