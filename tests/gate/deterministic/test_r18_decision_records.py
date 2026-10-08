from gate.deterministic.change_policy import records
from gate.diff import DiffContext


def test_r18_decision_records(tmp_path):
    (tmp_path / "DECISIONS.md").write_text("# Decisions\n", encoding="utf-8")
    findings = records(DiffContext(tmp_path, {}, "fixture"))
    assert {(f.file, f.severity, f.rule) for f in findings} == {
        ("DECISIONS.md", "low", "AGENTS#18"),
        ("AI-USAGE.md", "low", "AGENTS#18"),
    }

    (tmp_path / "DECISIONS.md").write_text("# Decisions\n\n## ADR-1\n\nWhy.\n", encoding="utf-8")
    (tmp_path / "AI-USAGE.md").write_text("# AI usage\n\n## Tools\n\nClaude.\n", encoding="utf-8")
    assert records(DiffContext(tmp_path, {}, "fixture")) == []
