from gate.deterministic.readme_smoke import run

README = """# demo

## Running locally

```bash
{first}
{second}
```

## Endpoints
"""


def write(tmp_path, first, second):
    (tmp_path / "README.md").write_text(README.format(first=first, second=second), encoding="utf-8")
    return tmp_path


def test_r16_readme_smoke(tmp_path):
    findings = run(write(tmp_path, "true", "pip-install-typo -r requirement.txt"))
    assert [(f.rule, f.severity, f.file, f.line) for f in findings] == [("AGENTS#16", "medium", "README.md", 7)]
    assert "pip-install-typo -r requirement.txt" in findings[0].message

    assert run(write(tmp_path, "true", "echo ready")) == []

    slow = run(write(tmp_path, "true", "sleep 5"), time_limit=1)
    assert [f.severity for f in slow] == ["medium"] and "longer than" in slow[0].message
