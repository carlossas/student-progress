import os
import subprocess
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"

requires_gemini = pytest.mark.skipif(not os.environ.get("GEMINI_API_KEY"), reason="GEMINI_API_KEY not set")


def by_rule(findings, rule):
    return [f for f in findings if f.rule == rule]


def expected(root: Path, tag: str = "") -> set[tuple[str, int]]:
    """(file, line) of every `# expect: <tag>` marker in a fixture tree."""
    marks = set()
    for path in root.rglob("*.py"):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if "# expect:" in line and tag in line.split("# expect:", 1)[1]:
                marks.add((path.relative_to(root).as_posix(), number))
    return marks


def located(findings) -> set[tuple[str, int]]:
    return {(f.file, f.line) for f in findings}


def git_repo(path: Path, files: dict[str, str]) -> Path:
    """Throwaway repo with one commit on `main` holding `files`."""
    path.mkdir(parents=True, exist_ok=True)
    run_git(path, "init", "-q", "-b", "main")
    commit(path, files, "base")
    return path


def commit(path: Path, files: dict[str, str], message: str) -> None:
    for name, text in files.items():
        target = path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    run_git(path, "add", "-A")
    run_git(path, "-c", "user.name=gate-test", "-c", "user.email=gate-test@example.com", "commit", "-q", "-m", message)


def run_git(path: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=path, check=True, capture_output=True, text=True).stdout


def ai_findings(fixture: Path):
    """Runs the real Gemini review on a fixture tree (only from @pytest.mark.ai tests)."""
    from gate.ai.review import review
    from gate.diff import DiffContext

    return review(DiffContext.from_fixture(fixture)).findings
