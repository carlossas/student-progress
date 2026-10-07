import pytest

from gate.config import STATUS_CRITICAL, STATUS_HIGH
from gate.report.actions import decide
from gate.report.finding import Finding


def finding(severity, line=10):
    return Finding("AGENTS#1", severity, "deterministic:test", "app/main.py", "msg", "fix", line, "P2")


EXPECTED = {
    # severity: (exit code, critical status, high status, review event, inline?)
    "critical": (1, "failure", "success", "REQUEST_CHANGES", True),
    "high": (0, "success", "failure", "REQUEST_CHANGES", True),
    "medium": (0, "success", "success", "COMMENT", True),
    "low": (0, "success", "success", "COMMENT", False),
}


@pytest.mark.parametrize("severity", list(EXPECTED))
def test_r09_severity_actions(severity):
    exit_code, critical, high, event, inline = EXPECTED[severity]

    # Violation input: one finding of this severity.
    decision = decide([finding(severity)], mode="enforce")
    assert decision.exit_code == exit_code
    assert decision.statuses[STATUS_CRITICAL][0] == critical
    assert decision.statuses[STATUS_HIGH][0] == high
    assert decision.review_event == event
    assert (decision.inline != []) is inline
    assert (decision.summary_only != []) is (not inline)

    # Findings without a line are never inline: they go to the review body / summary.
    assert decide([finding(severity, line=None)]).inline == []

    # Compliant input: nothing found -> pass, no review.
    clean = decide([], mode="enforce")
    assert clean.exit_code == 0
    assert {state for state, _ in clean.statuses.values()} == {"success"}
    assert clean.review_event is None
