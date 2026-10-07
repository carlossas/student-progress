from gate.deterministic import secrets_scan
from gate.diff import DiffContext
from tests.gate.helpers import FIXTURES


def test_r08_secrets():
    # The fixture is scanned as its own root, so the repo-level allowlist does not apply.
    findings = secrets_scan.check(DiffContext.from_fixture(FIXTURES / "r08" / "violation"))
    assert {(f.file, f.line) for f in findings} == {("config.py", 2), (".env", None)}
    assert {(f.rule, f.severity) for f in findings} == {("AGENTS#8", "critical")}
    key = next(f for f in findings if f.file == "config.py")
    assert "FAKEFAKE" not in key.message  # the secret itself is never echoed
    assert 'os.environ["GEMINI_API_KEY"]' in key.suggestion

    assert secrets_scan.check(DiffContext.from_fixture(FIXTURES / "r08" / "compliant")) == []
