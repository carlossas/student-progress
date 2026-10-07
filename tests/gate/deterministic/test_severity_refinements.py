"""Severity refinements approved after reviewing the live PRs (#15, #17)."""

from gate.deterministic import pii_flow
from gate.diff import DiffContext
from gate.report.finding import Finding
from gate.report.merge import dedupe

ARCHIVE = (
    "ARCHIVE: list[dict] = []\n\n\n"
    "def archive(student, record) -> None:\n"
    '    ARCHIVE.append({"student_id": student.id, "birthdate": student.birthdate})\n'
)


def test_copy_of_personal_data_is_critical(tmp_path):
    # PR #17: minors' personal data copied into a collection with no retention is S1, not S2.
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "archive.py").write_text(ARCHIVE, encoding="utf-8")
    findings = pii_flow.check(DiffContext(tmp_path, {"app/archive.py": None}, "fixture"))
    assert [(f.rule, f.severity, f.line) for f in findings] == [("AGENTS#3", "critical", 5)]

    # A copy holding only the pseudonymous id is not personal data.
    (tmp_path / "app" / "archive.py").write_text(
        ARCHIVE.replace(', "birthdate": student.birthdate', ""), encoding="utf-8"
    )
    assert pii_flow.check(DiffContext(tmp_path, {"app/archive.py": None}, "fixture")) == []


def finding(check, line=None):
    return Finding("AGENTS#6", "high", "deterministic:test", "app/notifications.py", check, "fix", line, check)


def test_untested_change_is_reported_once():
    # PR #15: "no tests touched" (A9) and "0% changed-line coverage" (A10) share one root cause.
    assert [f.check for f in dedupe([finding("A9"), finding("A10", 2)])] == ["A9"]
    # With tests touched but too little coverage, A10 alone still reports it.
    assert [f.check for f in dedupe([finding("A10", 2)])] == ["A10"]
