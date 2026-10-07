from gate.eval.run_eval import metrics
from gate.report.finding import Finding

TRUTH = {
    "scope_rules": ["AGENTS#1", "AGENTS#6", "AGENTS#8", "AGENTS#9"],
    "line_window": 3,
    "acceptable_everywhere": [],
    "prs": [
        {
            "branch": "pr-a",
            "verdict": "block",
            "expected": [
                {"id": "a-log", "rule": "AGENTS#1", "severity": "critical", "file": "app/main.py", "lines": [10, 10]},
                {"id": "a-key", "rule": "AGENTS#8", "severity": "critical", "file": "app/n.py", "lines": [7, 7]},
            ],
        },
        {
            "branch": "pr-b",
            "verdict": "block",
            "expected": [
                {"id": "b-bug", "rule": "AGENTS#9", "severity": "high", "file": "app/s.py", "lines": [5, 14]},
                {"id": "b-tests", "rule": "AGENTS#6", "severity": "high"},
            ],
        },
    ],
}


def f(rule, severity, file, line):
    return Finding(rule, severity, "deterministic:test", file, "m", "s", line, "X")


def test_r12_eval_metrics():
    # 3 true positives, 1 false positive (line 30 is beyond the +/-3 window), 1 miss (b-tests).
    found = {
        "pr-a": [f("AGENTS#1", "critical", "app/main.py", 12), f("AGENTS#8", "critical", "app/n.py", 7)],
        "pr-b": [f("AGENTS#9", "high", "app/s.py", 9), f("AGENTS#9", "high", "app/s.py", 30)],
    }
    m = metrics(TRUTH, found)
    assert (m["precision"], m["recall"]) == (0.75, 0.75)
    assert (m["tp"], m["fp"], m["fn"]) == (3, 1, 1)
    assert m["per_severity"]["critical"] == {"findings": 2, "precision": 1.0, "expected": 2, "recall": 1.0}
    assert m["per_severity"]["high"] == {"findings": 2, "precision": 0.5, "expected": 2, "recall": 0.5}

    perfect = {
        "pr-a": [f("AGENTS#1", "critical", "app/main.py", 10), f("AGENTS#8", "critical", "app/n.py", 7)],
        "pr-b": [f("AGENTS#9", "high", "app/s.py", 5), f("AGENTS#6", "high", "app/s.py", None)],
    }
    m = metrics(TRUTH, perfect)
    assert (m["precision"], m["recall"], m["severity_agreement"]) == (1.0, 1.0, 1.0)
