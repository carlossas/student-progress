from gate.deterministic import lint, todo_ticket
from gate.diff import DiffContext
from gate.report.merge import dedupe
from tests.gate.helpers import FIXTURES, by_rule


def run(root):
    ctx = DiffContext.from_fixture(root)
    return by_rule(dedupe(lint.check(ctx) + todo_ticket.check(ctx)), "AGENTS#7")


def test_r07_simplicity():
    findings = run(FIXTURES / "r07" / "violation")
    assert {(f.line, f.severity, f.check) for f in findings} == {
        (1, "medium", "A11"),  # unused import
        (5, "medium", "A11"),  # unused variable
        (6, "medium", "A12"),  # to-do marker without a ticket
        (10, "low", "A13"),  # not formatted
    }

    assert run(FIXTURES / "r07" / "compliant") == []
