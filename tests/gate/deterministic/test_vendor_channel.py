"""A18 (AGENTS#2): scaffolding for a third-party channel that handles personal data."""

from gate.deterministic import vendor_channel
from gate.deterministic.runner import FAST
from gate.diff import DiffContext

SCAFFOLD = (
    "import logging\n\n"
    "logger = logging.getLogger(__name__)\n"
    'SENDGRID_FROM = "reminders@openenglish.com"\n\n\n'
    "def send_inactivity_reminder(email: str, days_inactive: int) -> None:\n"
    '    logger.info("queued %s", days_inactive)\n'
)


def ctx_for(tmp_path, source, body=""):
    (tmp_path / "app").mkdir(exist_ok=True)
    (tmp_path / "app" / "notifications.py").write_text(source, encoding="utf-8")
    return DiffContext(tmp_path, {"app/notifications.py": None}, "fixture", pr_body=body)


def test_vendor_scaffold_with_personal_field_is_high(tmp_path):
    findings = vendor_channel.check(ctx_for(tmp_path, SCAFFOLD))
    assert [(f.rule, f.severity, f.check, f.line) for f in findings] == [("AGENTS#2", "high", "A18", 7)]
    assert "sendgrid" in findings[0].message and "`email`" in findings[0].message
    assert "vendor_channel" in FAST


def test_documented_legal_basis_minimized_data_or_real_calls_pass(tmp_path):
    assert vendor_channel.check(ctx_for(tmp_path, SCAFFOLD, "Legal basis: parental consent, OE-42")) == []
    only_id = SCAFFOLD.replace("email: str", "student_id: str")
    assert vendor_channel.check(ctx_for(tmp_path, only_id)) == []
    # A real call is pii_flow's job (it follows the data to the call): no duplicate here.
    calling = SCAFFOLD + "    sendgrid.send(to=email)\n"
    assert vendor_channel.check(ctx_for(tmp_path, calling)) == []
    no_vendor = SCAFFOLD.replace("SENDGRID_FROM", "REMINDER_FROM")
    assert vendor_channel.check(ctx_for(tmp_path, no_vendor)) == []
