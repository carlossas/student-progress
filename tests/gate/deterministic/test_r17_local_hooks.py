import os
import subprocess
import sys
import time

from gate.config import GATE_ROOT
from gate.tools import bash
from tests.gate.helpers import git_repo, run_git

HOOK = (GATE_ROOT / "gate" / "hooks" / "run.sh").as_posix()
LEAKY = (
    "import logging\n\nlogger = logging.getLogger(__name__)\n"
    'API_KEY = "AIza' + "Sy" + "Q" * 33 + '"\n\n\n'
    "def log(student):\n    logger.info(student.email)\n"
)
CLEAN = "def add(a, b):\n    return a + b\n"


def precommit(repo):
    env = {**os.environ, "GATE_PYTHON": sys.executable}
    return subprocess.run(
        [bash(), HOOK, "precommit"], cwd=repo, capture_output=True, text=True, env=env, encoding="utf-8"
    )


def test_r17_local_hooks(tmp_path):
    repo = git_repo(tmp_path / "repo", {"README.md": "x\n"})

    (repo / "app").mkdir()
    (repo / "app" / "leaky.py").write_text(LEAKY, encoding="utf-8")
    run_git(repo, "add", "app/leaky.py")
    blocked = precommit(repo)
    assert blocked.returncode != 0
    assert "AGENTS#8" in blocked.stdout and "AGENTS#1" in blocked.stdout

    run_git(repo, "reset", "-q", "app/leaky.py")
    (repo / "app" / "calc.py").write_text(CLEAN, encoding="utf-8")
    run_git(repo, "add", "app/calc.py")
    start = time.monotonic()
    clean = precommit(repo)
    assert clean.returncode == 0, clean.stdout + clean.stderr
    assert time.monotonic() - start < 10
