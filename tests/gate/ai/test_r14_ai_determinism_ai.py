import pytest

from gate.ai.config import GeminiSettings
from tests.gate.helpers import FIXTURES, ai_findings, requires_gemini

pytestmark = [pytest.mark.ai, requires_gemini]


def signature(findings):
    return {(f.rule, f.severity, f.file) for f in findings}


def test_r14_ai_determinism():
    settings = GeminiSettings.from_env()
    assert settings.thinking_level == "LOW"

    runs = [signature(ai_findings(FIXTURES / "r01-ai" / "violation")) for _ in range(3)]
    assert runs[0] == runs[1] == runs[2], runs
    assert ("AGENTS#1", "critical") in {(rule, severity) for rule, severity, _ in runs[0]}

    for _ in range(3):
        assert not [f for f in ai_findings(FIXTURES / "r01-ai" / "compliant") if f.severity == "critical"]
