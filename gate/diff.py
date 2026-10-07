"""What changed in a PR (or in the staged index), as files and line numbers.

Three sources, one interface:
- `from_refs`: a git range, used in CI and by the eval harness.
- `from_staged`: the index, used by the pre-commit hook.
- `from_fixture`: a directory, used by gate tests (every file is "new" unless
  a `changes.json` says otherwise).
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from gate.config import is_excluded

HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")
FIXTURE_META = {"changes.json", "pr.json"}


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def parse_unified_diff(text: str) -> dict[str, set[int]]:
    """Added/modified line numbers (new side) per file from `git diff -U0` output."""
    changed: dict[str, set[int]] = {}
    current: str | None = None
    for line in text.splitlines():
        if line.startswith("+++ "):
            target = line[4:].strip()
            current = None if target == "/dev/null" else target.removeprefix("b/")
            if current is not None:
                changed.setdefault(current, set())
            continue
        match = HUNK.match(line)
        if match and current is not None:
            start, count = int(match.group(1)), int(match.group(2) or 1)
            changed[current].update(range(start, start + count))
    return changed


@dataclass
class DiffContext:
    repo: Path
    changed: dict[str, set[int] | None]  # None: the whole file counts as changed
    mode: str
    base: str | None = None
    head: str = "HEAD"
    pr_title: str = ""
    pr_body: str = ""
    _cache: dict[str, str | None] = field(default_factory=dict, repr=False)

    # --- constructors -------------------------------------------------------------

    @classmethod
    def from_refs(cls, repo: Path, base: str, head: str = "HEAD", **meta) -> DiffContext:
        repo = Path(repo).resolve()
        text = git(repo, "diff", "--unified=0", "--no-color", "--no-ext-diff", "--diff-filter=ACMR", f"{base}...{head}")
        return cls(repo, dict(parse_unified_diff(text)), "refs", base, head, **meta)

    @classmethod
    def from_worktree(cls, repo: Path, base: str) -> DiffContext:
        """Everything not yet on `base`: commits, staged and unstaged edits, and untracked files."""
        repo = Path(repo).resolve()
        merge_base = git(repo, "merge-base", base, "HEAD").strip()
        text = git(repo, "diff", "--unified=0", "--no-color", "--no-ext-diff", "--diff-filter=ACMR", merge_base)
        changed: dict[str, set[int] | None] = dict(parse_unified_diff(text))
        for path in git(repo, "ls-files", "--others", "--exclude-standard").splitlines():
            changed[path] = None
        return cls(repo, changed, "worktree", merge_base, "WORKTREE")

    @classmethod
    def from_staged(cls, repo: Path) -> DiffContext:
        repo = Path(repo).resolve()
        text = git(repo, "diff", "--cached", "--unified=0", "--no-color", "--no-ext-diff", "--diff-filter=ACMR")
        return cls(repo, dict(parse_unified_diff(text)), "staged")

    @classmethod
    def from_fixture(cls, root: Path) -> DiffContext:
        root = Path(root).resolve()
        meta = json.loads((root / "pr.json").read_text(encoding="utf-8")) if (root / "pr.json").exists() else {}
        if (root / "changes.json").exists():
            spec = json.loads((root / "changes.json").read_text(encoding="utf-8"))
            changed = {path: (None if lines is None else set(lines)) for path, lines in spec.items()}
        else:
            changed = {
                p.relative_to(root).as_posix(): None
                for p in sorted(root.rglob("*"))
                if p.is_file() and p.name not in FIXTURE_META and "__pycache__" not in p.parts
            }
        return cls(root, changed, "fixture", pr_title=meta.get("title", ""), pr_body=meta.get("body", ""))

    # --- queries ------------------------------------------------------------------

    def files(self) -> list[str]:
        """Changed files that exist in the analyzed tree, minus gate fixtures."""
        return sorted(p for p in self.changed if not is_excluded(p) and self.read(p) is not None)

    def read(self, path: str) -> str | None:
        if path not in self._cache:
            self._cache[path] = self._read(path)
        return self._cache[path]

    def _read(self, path: str) -> str | None:
        if self.mode == "staged":
            try:
                return git(self.repo, "show", f":{path}")
            except RuntimeError:
                return None
        file = self.repo / path
        if not file.is_file():
            return None
        return file.read_text(encoding="utf-8", errors="replace")

    def lines(self, path: str) -> set[int]:
        """Changed line numbers of `path` (all lines when the whole file is new)."""
        if path not in self.changed:
            return set()
        lines = self.changed[path]
        if lines is None:
            text = self.read(path) or ""
            return set(range(1, text.count("\n") + 2))
        return lines

    def is_changed(self, path: str, first: int, last: int | None = None) -> bool:
        lines = self.lines(path)
        return any(n in lines for n in range(first, (last or first) + 1))

    def touches(self, prefix: str) -> bool:
        return any(p.startswith(prefix) for p in self.files())

    def history_added_lines(self) -> list[tuple[str, str, str]]:
        """(commit, path, text) for every line added by any commit in the range (refs mode only)."""
        if self.mode != "refs" or not self.base:
            return []
        out = git(
            self.repo, "log", "-p", "--unified=0", "--no-color", "--format=commit:%H", f"{self.base}..{self.head}"
        )
        added, commit, path = [], "", ""
        for line in out.splitlines():
            if line.startswith("commit:"):
                commit = line[7:]
            elif line.startswith("+++ "):
                path = line[4:].strip().removeprefix("b/")
            elif line.startswith("+") and not line.startswith("+++"):
                added.append((commit, path, line[1:]))
        return added


def default_base(repo: Path) -> str:
    """The branch a PR would target: origin/develop, else origin/main, else main."""
    for candidate in ("origin/develop", "origin/main", "main"):
        try:
            git(repo, "rev-parse", "--verify", "--quiet", candidate)
            return candidate
        except RuntimeError:
            continue
    raise RuntimeError("no base branch found (origin/develop, origin/main or main); pass --base")
