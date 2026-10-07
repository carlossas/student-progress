import yaml

from gate.ai.prompt_builder import user_prompt
from gate.config import GATE_ROOT
from gate.diff import DiffContext
from gate.report.finding import Finding, Signal
from gate.report.merge import dedupe


def test_r10_orchestration(tmp_path):
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "main.py").write_text("x = 1\n" * 60, encoding="utf-8")
    ctx = DiffContext(tmp_path, {"app/main.py": None}, "fixture")
    a = Finding(
        "AGENTS#1", "critical", "deterministic:pii_flow", "app/main.py", "Email logged.", "Use redact().", 58, "P2"
    )
    b = Finding("AGENTS#1", "critical", "ai:gemini", "app/main.py", "Email logged (AI).", "Use redact().", 58, "B1")
    signal = Signal("P4", "app/main.py", 12, "`contact` may hold personal data (contact)")

    # The AI receives what Pipeline A already found, plus its hints.
    prompt = user_prompt(ctx, [a], [signal])
    assert "app/main.py:58: Email logged." in prompt
    assert "`contact` may hold personal data" in prompt

    # Same rule and location from both pipelines: one finding, the deterministic one.
    assert dedupe([b, a]) == [a]

    # The AI job always runs after A, even when A failed.
    jobs = yaml.safe_load((GATE_ROOT / ".github/workflows/quality-gate.yml").read_text(encoding="utf-8"))["jobs"]
    assert jobs["ai"]["needs"] == "deterministic"
    assert jobs["ai"]["if"].replace("${{", "").strip().startswith("always()")
    assert set(jobs["report"]["needs"]) == {"deterministic", "smoke", "ai"}
