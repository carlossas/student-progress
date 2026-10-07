"""`python -m gate all`: one command, one verdict; AI skipped without a usable key."""

import gate.ai.client
from gate.local import run_all
from tests.gate.helpers import git_repo

BASE = {
    "README.md": "x\n",
    "app/__init__.py": "",
    "DECISIONS.md": "# Decisions\n\n## ADR-1\n\nWhy.\n",
    "AI-USAGE.md": "# AI usage\n\n## Tools\n\nClaude.\n",
    "docs/ARCHITECTURE.md": "# Architecture\n",
    "docs/API-AND-BUSINESS-RULES.md": "# API\n",
}
LEAKY = (
    "import logging\n\nlogger = logging.getLogger(__name__)\n\n\ndef log(student):\n    logger.info(student.email)\n"
)
COMPLIANT = {
    "app/calc.py": "def add(a, b):\n    return a + b\n",
    "tests/test_calc.py": "from app.calc import add\n\n\ndef test_add():\n    assert add(2, 3) == 5\n",
    "docs/ARCHITECTURE.md": "# Architecture\n\n`app/calc.py`: arithmetic helpers.\n",
    "docs/API-AND-BUSINESS-RULES.md": "# API\n\nBR-1: add() sums two numbers.\n",
}


def test_check_all(tmp_path, capsys, monkeypatch):
    repo = git_repo(tmp_path / "repo", BASE)

    # Uncommitted, untracked leak + no key: blocked by the deterministic checks, AI skipped.
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    (repo / "app" / "leaky.py").write_text(LEAKY, encoding="utf-8")
    assert run_all(repo, "main") == 1
    out = capsys.readouterr().out
    assert "AGENTS#1" in out and "RESULT: BLOCKED" in out
    assert "GEMINI_API_KEY is not set (deterministic checks only)" in out

    # Compliant change (logic + tests + docs) + invalid key: the free probe fails, so AI is skipped, not failed.
    monkeypatch.setenv("GEMINI_API_KEY", "invalid")
    monkeypatch.setattr(gate.ai.client, "probe", lambda settings: (False, "HTTP 400 API key not valid"))
    (repo / "app" / "leaky.py").unlink()
    for name, text in COMPLIANT.items():
        (repo / name).parent.mkdir(parents=True, exist_ok=True)
        (repo / name).write_text(text, encoding="utf-8")
    assert run_all(repo, "main") == 0, capsys.readouterr().out
    out = capsys.readouterr().out
    assert "API key not valid (deterministic checks only)" in out
    assert "RESULT: READY (AI skipped)" in out
