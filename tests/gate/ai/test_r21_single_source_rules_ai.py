import pytest

from tests.gate.helpers import FIXTURES, ai_findings, by_rule, requires_gemini

pytestmark = [pytest.mark.ai, requires_gemini]


def test_r21_single_source_rules_ai():
    violation = by_rule(ai_findings(FIXTURES / "r21-ai" / "violation"), "AGENTS#21")
    assert {f.severity for f in violation} & {"low"}, violation
    assert {f.file for f in violation} == {"CONTRIBUTING.md"}
    compliant = by_rule(ai_findings(FIXTURES / "r21-ai" / "compliant"), "AGENTS#21")
    assert compliant == [], compliant
