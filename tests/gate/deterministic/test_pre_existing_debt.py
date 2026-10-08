"""Pre-existing debt policy (gate/report/baseline.py): moved lines don't block on code-quality rules."""

import subprocess

from gate.diff import DiffContext
from gate.report.baseline import demote_preexisting
from gate.report.finding import Finding
from tests.gate.helpers import commit, git_repo

BASE = "def record(payload):\n" "    return Record(\n" '        score=int(payload.get("score", 0)),\n' "    )\n"
HEAD = (
    "def record(payload):\n"
    '    score = int(payload.get("score", 0))\n'  # line 2: moved, not new
    '    lesson = int(payload.get("lesson", 0))\n'  # line 3: new
    "    return Record(score=score)\n"
)


def repo_with_move(tmp_path):
    repo = git_repo(tmp_path / "repo", {"app/main.py": BASE})
    subprocess.run(["git", "checkout", "-q", "-b", "pr"], cwd=repo, check=True)
    commit(repo, {"app/main.py": HEAD}, "move the score conversion")
    return DiffContext.from_refs(repo, "main", "HEAD")


def high(rule, line):
    return Finding(
        rule, "high", "ai:gemini", "app/main.py", "non-numeric input returns a 500", "catch ValueError", line
    )


def test_moved_line_is_demoted_new_line_is_not(tmp_path):
    ctx = repo_with_move(tmp_path)
    moved, new = demote_preexisting([high("AGENTS#5", 2), high("AGENTS#5", 3)], ctx)
    assert moved.severity == "medium" and "Pre-existing" in moved.message
    assert new.severity == "high" and new.message == high("AGENTS#5", 3).message


def test_privacy_secrets_and_tests_are_never_demoted(tmp_path):
    ctx = repo_with_move(tmp_path)
    for rule in ("AGENTS#1", "AGENTS#2", "AGENTS#3", "AGENTS#4", "AGENTS#6", "AGENTS#8"):
        assert demote_preexisting([high(rule, 2)], ctx)[0].severity == "high", rule
    critical = Finding("AGENTS#9", "critical", "ai:gemini", "app/main.py", "m", "s", 2)
    assert demote_preexisting([critical], ctx) == [critical]


def test_short_lines_and_other_modes_are_left_alone(tmp_path):
    ctx = repo_with_move(tmp_path)
    assert demote_preexisting([high("AGENTS#9", 4)], ctx)[0].severity == "high"  # new line
    assert demote_preexisting([high("AGENTS#9", 1)], ctx)[0].severity == "medium"  # `def record(payload):` existed
    assert demote_preexisting([high("AGENTS#9", None)], ctx)[0].severity == "high"  # file-level
    fixture = DiffContext(ctx.repo, {"app/main.py": None}, "fixture")
    assert demote_preexisting([high("AGENTS#5", 2)], fixture)[0].severity == "high"
