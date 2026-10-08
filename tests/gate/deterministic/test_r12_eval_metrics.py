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


def test_r12_verdicts_count_unscored_rules():
    # PR #12: a process rule (AGENTS#20, outside scope_rules) blocked a sound PR. Precision and
    # recall can't see it; the merge verdict must.
    from gate.eval.run_eval import verdicts

    truth = {
        "prs": [
            {"branch": "sound", "verdict": "sound"},
            {"branch": "noted", "verdict": "comment"},
            {"branch": "bad", "verdict": "block"},
        ]
    }
    found = {
        "sound": [f("AGENTS#20", "high", "app/main.py", None)],
        "noted": [f("AGENTS#5", "medium", "app/main.py", 52)],
        "bad": [f("AGENTS#7", "medium", "app/x.py", 1)],
    }
    v = verdicts(truth, found)
    assert (v["correct"], v["false_blocks"], v["missed_blocks"]) == (1, 1, 1)

    found["sound"] = [f("AGENTS#20", "medium", "app/main.py", None)]
    found["bad"].append(f("AGENTS#1", "critical", "app/x.py", 3))
    assert verdicts(truth, found)["correct"] == 3


def test_r12_golden_prs_are_pinned(tmp_path):
    # PR #10's branch got develop merged in; the eval must keep scoring the original commit.
    from gate.eval.run_eval import pr_head
    from tests.gate.helpers import commit, git_repo, run_git

    repo = git_repo(tmp_path / "repo", {"a.txt": "1\n"})
    original = run_git(repo, "rev-parse", "HEAD").strip()
    commit(repo, {"a.txt": "2\n"}, "moved on")
    assert pr_head(repo, {"branch": "main", "head": original}) == original
    assert pr_head(repo, {"branch": "main"}) == "main"


def test_r12_stability_across_prompt_variants():
    # A PR whose verdict depends on the prompt variant is flagged, even if one run got it right.
    from gate.eval.run_eval import permuted, stability

    truth = {"prs": [{"branch": "steady", "verdict": "block"}, {"branch": "flaky", "verdict": "comment"}]}
    critical = f("AGENTS#1", "critical", "app/main.py", 3)
    high = f("AGENTS#6", "high", "tests/t.py", 18)
    runs = [
        {"steady": [critical], "flaky": []},
        {"steady": [critical], "flaky": [high]},
        {"steady": [critical], "flaky": []},
    ]
    st = stability(truth, runs)
    assert st["flipped"] == 1 and st["correct_per_variant"] == [2, 1, 2]
    assert [r["stable"] for r in st["rows"]] == [True, False]

    # Variants reorder the same content, reproducibly.
    items = list(range(10))
    assert sorted(permuted(items, 1)) == items and permuted(items, 1) == permuted(items, 1) != items
