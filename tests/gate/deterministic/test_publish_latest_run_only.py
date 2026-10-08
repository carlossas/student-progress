"""Re-runs leave the PR showing only the latest run (PRs #13 and #18, 2026-10-08)."""

from gate.report.actions import comment_body, decide
from gate.report.finding import Finding
from gate.report.github import STICKY_MARKER, SUPERSEDED, publish


class FakeGitHub:
    """In-memory PR: inline comments and reviews, enough for publish()."""

    def __init__(self):
        self.comments, self.reviews_, self.dismissed, self.next_id = [], [], [], 1

    def _id(self):
        self.next_id += 1
        return self.next_id

    def set_status(self, *args, **kwargs):
        pass

    def upsert_sticky(self, number, body):
        pass

    def pr_files(self, number):
        patch = "@@ -1,0 +1,60 @@\n" + "\n".join("+x" for _ in range(60))
        return [{"filename": "app/main.py", "patch": patch}]

    def review_comments(self, number):
        return list(self.comments)

    def delete_review_comment(self, comment_id):
        self.comments = [c for c in self.comments if c["id"] != comment_id]

    def reviews(self, number):
        return list(self.reviews_)

    def create_review(self, number, sha, event, body, comments):
        review = {"id": self._id(), "state": "CHANGES_REQUESTED" if event == "REQUEST_CHANGES" else "COMMENTED"}
        self.reviews_.append({**review, "body": body})
        self.comments += [{"id": self._id(), "body": c["body"], "line": c["line"]} for c in comments]
        return review

    def update_review(self, number, review_id, body):
        for r in self.reviews_:
            if r["id"] == review_id:
                r["body"] = body

    def dismiss_review(self, number, review_id, message):
        self.dismissed.append(review_id)
        for r in self.reviews_:
            if r["id"] == review_id:
                r["state"] = "DISMISSED"


def bug(severity, message="Truncates the percentage."):
    return Finding("AGENTS#9", severity, "ai:gemini", "app/main.py", message, "Use round().", 38, "B11")


def run(gh, findings):
    publish(gh, 18, "abc", findings, decide(findings, mode="enforce"), "summary", None)


def test_rerun_with_reworded_ai_message_does_not_repost():
    gh = FakeGitHub()
    run(gh, [bug("high")])
    run(gh, [bug("high", "Percentage is truncated by int().")])  # same finding, new wording
    assert len(gh.comments) == 1 and len(gh.reviews_) == 1


def test_regraded_or_fixed_findings_leave_no_stale_comments():
    gh = FakeGitHub()
    # An old-format comment from before this change, for a finding that is still there.
    old_body = comment_body(bug("high")).replace(bug("high").fingerprint(), "0123456789ab")
    gh.comments.append({"id": 1, "body": old_body, "line": 38})
    gh.reviews_.append({"id": 1, "state": "CHANGES_REQUESTED", "body": f"{STICKY_MARKER}\nold run"})

    run(gh, [bug("high")])
    assert len(gh.comments) == 1 and "0123456789ab" not in gh.comments[0]["body"]
    assert gh.reviews_[0]["body"] == SUPERSEDED and gh.reviews_[0]["state"] == "DISMISSED"
    assert gh.reviews_[-1]["state"] == "CHANGES_REQUESTED"  # the PR is still blocked, by the new review

    # Re-graded to Medium (#13): the HIGH comment goes, a MEDIUM one replaces it, nothing blocks.
    run(gh, [bug("medium")])
    assert ["MEDIUM" in c["body"] for c in gh.comments] == [True]
    assert all(r["state"] != "CHANGES_REQUESTED" for r in gh.reviews_)

    # Fixed: no inline comments left, older reviews blanked.
    run(gh, [])
    assert gh.comments == []
    assert all(r["body"] == SUPERSEDED for r in gh.reviews_)
