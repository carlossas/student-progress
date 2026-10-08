from gate.deterministic import change_policy, tests_runner
from gate.diff import DiffContext
from tests.gate.helpers import commit, git_repo, run_git

CALC = "def add(a, b):\n    return a + b\n"
SUB = "\n\ndef sub(a, b):\n" "    if a < b:\n" "        return -(b - a)\n" "    return a - b\n"
TEST_ADD = "from app.calc import add\n\n\ndef test_add():\n    assert add(2, 3) == 5\n"
TEST_BROKEN = "\n\ndef test_add_broken():\n    assert add(1, 1) == 3\n"
TEST_SUB = (
    "from app.calc import sub\n\n\n"
    "def test_sub_positive():\n    assert sub(5, 3) == 2\n\n\n"
    "def test_sub_negative():\n    assert sub(3, 5) == -2\n"
)


def findings_for(repo):
    ctx = DiffContext.from_refs(repo, "main", "HEAD")
    return tests_runner.run(ctx) + change_policy.tests_touched(ctx)


def test_r06_tests_coverage(tmp_path):
    # Violation: untested branchy code, no test changes, and a failing test already on main.
    bad = git_repo(
        tmp_path / "bad", {"app/__init__.py": "", "app/calc.py": CALC, "tests/test_calc.py": TEST_ADD + TEST_BROKEN}
    )
    run_git(bad, "checkout", "-q", "-b", "feature")
    commit(bad, {"app/calc.py": CALC + SUB}, "add sub")
    findings = findings_for(bad)
    assert sorted(f.check for f in findings) == ["A10", "A8", "A9"]
    assert {(f.rule, f.severity) for f in findings} == {("AGENTS#6", "high")}

    # Compliant: the logic ships with tests covering every changed line, all green.
    good = git_repo(tmp_path / "good", {"app/__init__.py": "", "app/calc.py": CALC, "tests/test_calc.py": TEST_ADD})
    run_git(good, "checkout", "-q", "-b", "feature")
    commit(good, {"app/calc.py": CALC + SUB, "tests/test_sub.py": TEST_SUB}, "add sub with tests")
    assert findings_for(good) == []
