from gate.report.actions import decide
from gate.report.finding import Finding
from gate.report.github import STICKY_MARKER
from gate.report.override import handle


class FakeGitHub:
    """Records what the override would do; `admins` have repository permission `admin`."""

    def __init__(self, admins):
        self.admins = admins
        self.statuses, self.comments = [], []

    def collaborator_permission(self, user):
        return "admin" if user in self.admins else "write"

    def pr(self, number):
        return {"head": {"sha": "abc1234def"}, "base": {"ref": "develop"}}

    def issue_comments(self, number):
        return [{"body": f'{STICKY_MARKER}\nsummary\n<!-- qg:findings ["f00d", "beef"] -->'}]

    def set_status(self, sha, context, state, description, target_url=None):
        self.statuses.append((sha, context, state, description))

    def comment(self, number, body):
        self.comments.append(body)


CRITICAL = Finding("AGENTS#8", "critical", "deterministic:secrets", "app/notifications.py", "Key.", "Rotate.", 7, "A1")


def test_r14_critical_block_override(monkeypatch):
    monkeypatch.delenv("GATE_OVERRIDE_TEAM", raising=False)

    # Violation: a Critical in enforce mode blocks.
    blocked = decide([CRITICAL], mode="enforce")
    assert blocked.exit_code == 1 and blocked.statuses["quality-gate/develop/critical"][0] == "failure"

    gh = FakeGitHub(admins={"lead"})
    rejected = [handle(gh, 7, "dev", "/gate-override hotfix"), handle(gh, 7, "lead", "/gate-override")]
    assert [r.accepted for r in rejected] == [False, False]
    assert gh.statuses == []  # still blocked

    ok = handle(gh, 7, "lead", "/gate-override incident INC-42")
    assert ok.accepted
    assert {(c, s) for _, c, s, _ in gh.statuses} == {
        ("quality-gate/develop/critical", "success"),
        ("quality-gate/develop/high", "success"),
    }
    assert ok.record["user"] == "lead" and ok.record["reason"] == "incident INC-42"
    assert ok.record["findings"] == ["f00d", "beef"] and ok.record["timestamp"]
    assert "overridden" in gh.comments[-1]

    # Compliant: shadow mode posts the finding but never blocks.
    shadow = decide([CRITICAL], mode="shadow")
    assert shadow.exit_code == 0 and shadow.statuses["quality-gate/develop/critical"][0] == "success"
    assert "[shadow]" in shadow.statuses["quality-gate/develop/critical"][1]
