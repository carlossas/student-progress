import pytest

from tests.gate.helpers import FIXTURES, ai_findings, by_rule, requires_gemini

pytestmark = [pytest.mark.ai, requires_gemini]


def test_r20_docs_accuracy_ai():
    violation = by_rule(ai_findings(FIXTURES / "r20-ai" / "violation"), "AGENTS#20")
    assert {f.severity for f in violation} & {"medium"}, violation
    assert any(f.file == "docs/API-AND-BUSINESS-RULES.md" for f in violation)
    compliant = by_rule(ai_findings(FIXTURES / "r20-ai" / "compliant"), "AGENTS#20")
    assert compliant == [], compliant
