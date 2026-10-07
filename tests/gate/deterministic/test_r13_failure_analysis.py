from gate.eval.run_eval import failure_ids, missing_analysis
from tests.gate.deterministic.test_r12_eval_metrics import TRUTH, f

FOUND = {
    "pr-a": [f("AGENTS#1", "critical", "app/main.py", 12), f("AGENTS#8", "critical", "app/n.py", 7)],
    "pr-b": [f("AGENTS#9", "high", "app/s.py", 9), f("AGENTS#9", "high", "app/s.py", 30)],
}

ANALYSIS = """
## Failure analysis

### fp-pr-b-9-s-30
**Why:** the model flagged a second, valid branch as a bug.
**Change:** add the edge case to the prompt's business rules.

### fn-b-tests
**Why:** {why}
**Change:** {change}
"""


def test_r13_failure_analysis():
    failures = failure_ids(TRUTH, FOUND)
    assert [(x["id"], x["kind"], x["rule"], x["location"]) for x in failures] == [
        ("fp-pr-b-9-s-30", "FP", "AGENTS#9", "app/s.py:30"),
        ("fn-b-tests", "FN", "AGENTS#6", "(any file)"),
    ]
    ids = [x["id"] for x in failures]

    # Violation: the FN has no written analysis -> the completeness check names it.
    assert missing_analysis(ANALYSIS.format(why="", change=""), ids) == ["fn-b-tests"]

    # Compliant: both analyses written.
    filled = ANALYSIS.format(why="no test-quality check ran.", change="enable B8 for test files.")
    assert missing_analysis(filled, ids) == []
