from gate.deterministic.change_policy import docs_touched
from gate.diff import DiffContext

FILES = ["app/main.py", "tests/test_progress.py", "docs/ARCHITECTURE.md", "docs/API-AND-BUSINESS-RULES.md"]


def ctx_for(tmp_path, changed):
    for name in FILES:
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text("x\n", encoding="utf-8")
    return DiffContext(tmp_path, {p: None for p in changed}, "fixture")


def test_r20_docs_updated(tmp_path):
    findings = docs_touched(ctx_for(tmp_path, ["app/main.py", "tests/test_progress.py"]))
    assert [(f.rule, f.severity, f.check) for f in findings] == [("AGENTS#20", "medium", "A14")]
    assert "ARCHITECTURE.md" in findings[0].message and "API-AND-BUSINESS-RULES.md" in findings[0].message

    assert docs_touched(ctx_for(tmp_path, FILES)) == []
    assert docs_touched(ctx_for(tmp_path, ["docs/ARCHITECTURE.md"])) == []  # docs-only change
