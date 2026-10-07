from pathlib import Path

import yaml

from gate.config import GATE_ROOT
from gate.deterministic.workflow_policy import GATE_WORKFLOW, problems
from tests.gate.helpers import FIXTURES


def test_r15_triggers():
    found = problems((FIXTURES / "r15" / "violation.yml").read_text(encoding="utf-8"))
    assert any("paths-ignore" in p for p in found)
    assert any("skip condition" in p for p in found)
    assert any("`ai` job" in p for p in found)

    real = Path(GATE_ROOT / GATE_WORKFLOW).read_text(encoding="utf-8")
    assert problems(real) == []
    jobs = yaml.safe_load(real)["jobs"]
    assert "if" not in jobs["deterministic"]
    assert "github.base_ref == 'main' || github.base_ref == 'develop'" in jobs["ai"]["if"]
