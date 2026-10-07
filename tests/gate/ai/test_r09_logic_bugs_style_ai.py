import pytest

from tests.gate.helpers import FIXTURES, ai_findings, by_rule, requires_gemini

pytestmark = [pytest.mark.ai, requires_gemini]


def test_r09_logic_bugs_style_ai():
    violation = by_rule(ai_findings(FIXTURES / "r09-ai" / "violation"), "AGENTS#9")
    # B11: the double-counting bug (line 3) is a blocking High.
    assert any(f.severity == "high" and f.check == "B11" and f.line in (3, 4, 5, 6) for f in violation), violation
    # B12 style notes are optional ("at most two", never blocking): if present, they are Low.
    assert all(f.severity in ("high", "low") for f in violation), violation
    assert all(f.severity == "low" for f in violation if f.check == "B12"), violation
    compliant = by_rule(ai_findings(FIXTURES / "r09-ai" / "compliant"), "AGENTS#9")
    assert not [f for f in compliant if f.severity in ("critical", "high")], compliant
