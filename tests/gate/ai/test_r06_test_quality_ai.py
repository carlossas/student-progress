import pytest

from tests.gate.helpers import FIXTURES, ai_findings, by_rule, requires_gemini

pytestmark = [pytest.mark.ai, requires_gemini]


def test_r06_test_quality_ai():
    violation = by_rule(ai_findings(FIXTURES / "r06-ai" / "violation"), "AGENTS#6")
    assert {f.severity for f in violation} & {"high"}, violation
    assert any(f.file == "tests/test_progress_calc.py" for f in violation)
    compliant = by_rule(ai_findings(FIXTURES / "r06-ai" / "compliant"), "AGENTS#6")
    assert compliant == [], compliant
