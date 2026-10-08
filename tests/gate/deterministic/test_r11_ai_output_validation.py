import json
import logging

from gate.ai.validate import validate_ai_output
from gate.config import valid_rules
from gate.diff import DiffContext


def ai_item(**overrides):
    item = {
        "rule": "AGENTS#1",
        "severity": "critical",
        "check": "B1",
        "file": "app/main.py",
        "line": 12,
        "message": "Email reaches a log through a renamed local.",
        "suggestion": "Log student.id instead.",
    }
    item.update(overrides)
    return {k: v for k, v in item.items() if v is not ...}


def test_r11_ai_output_validation(tmp_path, caplog):
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "main.py").write_text("x = 1\n" * 30, encoding="utf-8")
    ctx = DiffContext(tmp_path, {"app/main.py": {10, 11, 12}}, "fixture")
    rules = valid_rules()

    # Violation input: one valid item and three that must be dropped with a reason.
    raw = json.dumps(
        {
            "findings": [
                ai_item(),
                ai_item(file=...),
                ai_item(severity="urgent"),
                ai_item(file="app/other.py"),
            ]
        }
    )
    with caplog.at_level(logging.WARNING, logger="gate.ai"):
        kept, dropped = validate_ai_output(raw, ctx, rules)
    assert [f.check for f in kept] == ["B1"]
    assert kept[0].source == "ai:gemini"
    reasons = [reason for _, reason in dropped]
    assert reasons == ["missing file", "unknown severity 'urgent'", "file 'app/other.py' is not part of the diff"]
    assert len([r for r in caplog.records if "dropped AI finding" in r.getMessage()]) == 3

    # Compliant input: two valid items survive, nothing is dropped.
    raw = json.dumps({"findings": [ai_item(), ai_item(rule="AGENTS#4", line=10, check="B6")]})
    kept, dropped = validate_ai_output(raw, ctx, rules)
    assert len(kept) == 2 and dropped == []
