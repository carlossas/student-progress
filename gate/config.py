"""Gate-wide configuration.

Everything here is read from the gate's own checkout (the base branch in CI), never from
the PR under review, so a PR cannot loosen the rules it is judged by.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

GATE_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = GATE_ROOT / "gate" / "config"

SEVERITIES = ("critical", "high", "medium", "low")

# Service code: the only place personal data lives today.
SOURCE_DIRS = ("app",)
TEST_DIR = "tests"
DOC_FILES = ("docs/ARCHITECTURE.md", "docs/API-AND-BUSINESS-RULES.md")
RECORD_FILES = ("DECISIONS.md", "AI-USAGE.md")

# Gate test fixtures contain deliberate violations; they are never analyzed as PR code.
EXCLUDED_PREFIXES = ("tests/gate/fixtures/",)
# Not service code: PII flow and input-validation checks skip these.
NON_SERVICE_PREFIXES = ("tests/", "gate/")

# Always treated as personal data, even if the PR's app/privacy.py forgets one (AGENTS.md table).
DEFAULT_PII_FIELDS = frozenset({"full_name", "email", "birthdate", "is_minor"})

COVERAGE_THRESHOLD = 85.0
COVERAGE_PACKAGES = ("app",)
MINOR_RETENTION_MAX_DAYS = 90

RUFF_CONFIG = CONFIG_DIR / "ruff.toml"
SECRET_ALLOWLIST = CONFIG_DIR / "secret-allowlist.txt"
RULE_MAP = CONFIG_DIR / "rule_map.yml"
AGENTS_MD = GATE_ROOT / "AGENTS.md"

STATUS_CRITICAL = "quality-gate/critical"
STATUS_HIGH = "quality-gate/high"


def valid_rules(agents_md: Path = AGENTS_MD) -> frozenset[str]:
    """`AGENTS#n` for every numbered golden rule in AGENTS.md."""
    numbers = re.findall(r"^\s*(\d+)\.\s+\*\*", agents_md.read_text(encoding="utf-8"), flags=re.M)
    return frozenset(f"AGENTS#{n}" for n in numbers)


def is_excluded(path: str) -> bool:
    return path.startswith(EXCLUDED_PREFIXES)


def is_service_python(path: str) -> bool:
    return path.endswith(".py") and not path.startswith(NON_SERVICE_PREFIXES) and not is_excluded(path)


def is_source(path: str) -> bool:
    return path.endswith(".py") and path.split("/", 1)[0] in SOURCE_DIRS


def module_assignment(source: str, name: str) -> tuple[ast.expr, int, int] | None:
    """Module-level `name = <expr>` (or annotated) as (value node, first line, last line)."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    for node in tree.body:
        targets = (
            node.targets if isinstance(node, ast.Assign) else [node.target] if isinstance(node, ast.AnnAssign) else []
        )
        if any(isinstance(t, ast.Name) and t.id == name for t in targets) and node.value is not None:
            return node.value, node.lineno, node.end_lineno or node.lineno
    return None


def literal_assignment(source: str, name: str):
    """Literal value of a module-level assignment, or None when absent or not a literal."""
    found = module_assignment(source, name)
    if found is None:
        return None
    try:
        return ast.literal_eval(found[0])
    except ValueError:
        return None


def pii_fields(privacy_source: str | None) -> frozenset[str]:
    """Personal-data field names: the AGENTS.md defaults plus the PR's `PII_FIELDS`."""
    declared = literal_assignment(privacy_source, "PII_FIELDS") if privacy_source else None
    return DEFAULT_PII_FIELDS | frozenset(declared or ())
