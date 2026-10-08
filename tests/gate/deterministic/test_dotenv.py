"""gate/env.py: local `.env` for the developer's Gemini key; real env vars always win."""

import os

from gate.env import load_dotenv


def test_dotenv_sets_missing_vars_only(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("GATE_T_KEY", raising=False)
    monkeypatch.delenv("GATE_T_QUOTED", raising=False)
    monkeypatch.delenv("GATE_T_EMPTY", raising=False)
    monkeypatch.setenv("GATE_T_REAL", "from-env")
    env = tmp_path / ".env"
    env.write_text(
        '# comment\n\nGATE_T_KEY=abc\nexport GATE_T_QUOTED = "q v"\nGATE_T_EMPTY=\nGATE_T_REAL=from-file\nnot a line\n',
        encoding="utf-8",
    )
    assert load_dotenv(env) == ["GATE_T_KEY", "GATE_T_QUOTED"]
    assert (os.environ["GATE_T_KEY"], os.environ["GATE_T_QUOTED"]) == ("abc", "q v")
    assert os.environ["GATE_T_REAL"] == "from-env"  # CI secrets beat a stray .env
    assert "GATE_T_EMPTY" not in os.environ  # the blank template line sets nothing
    assert ".env:7: ignored" in capsys.readouterr().err  # malformed lines are reported, not swallowed


def test_no_dotenv_is_fine(tmp_path):
    assert load_dotenv(tmp_path / ".env") == []
