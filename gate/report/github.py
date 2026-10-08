"""Minimal GitHub REST client (stdlib only) and the PR publisher.

Publishing is idempotent across re-runs: one sticky summary comment updated in place,
inline comments posted once per finding fingerprint, statuses overwritten. The PR only shows
the latest run: inline comments for findings that are gone (fixed, re-graded) are deleted, and
older gate reviews are hidden as outdated (GitHub can't delete a submitted review).
"""

from __future__ import annotations

import json
import logging
import os
import re
import urllib.error
import urllib.request

from gate.report.actions import Decision, comment_body
from gate.report.finding import Finding

log = logging.getLogger("gate.github")
STICKY_MARKER = "<!-- quality-gate:summary -->"
FINDINGS_MARKER = re.compile(r"<!-- qg:findings (.*?) -->", re.S)
INLINE_MARKER = re.compile(r"<!-- qg:(\w+) -->")
# Body of a hidden old review: renders as nothing, and marks it as already handled.
SUPERSEDED = f"{STICKY_MARKER}<!-- quality-gate:superseded -->"


class GitHubError(RuntimeError):
    pass


class GitHub:
    def __init__(self, token: str | None = None, repo: str | None = None, api: str | None = None):
        self.token = token or os.environ.get("GITHUB_TOKEN", "")
        self.repo = repo or os.environ.get("GITHUB_REPOSITORY", "")
        self.api = (api or os.environ.get("GITHUB_API_URL") or "https://api.github.com").rstrip("/")
        if not self.token or not self.repo:
            raise GitHubError("GITHUB_TOKEN and GITHUB_REPOSITORY are required to publish")

    def request(self, method: str, path: str, body: dict | None = None, token: str | None = None):
        url = path if path.startswith("http") else f"{self.api}{path}"
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", f"Bearer {token or self.token}")
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("X-GitHub-Api-Version", "2022-11-28")
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=30) as res:
                text = res.read().decode()
                return json.loads(text) if text else None
        except urllib.error.HTTPError as e:
            raise GitHubError(f"{method} {path}: HTTP {e.code} {e.read().decode()[:300]}") from e

    def paginate(self, path: str) -> list:
        items, page = [], 1
        while True:
            sep = "&" if "?" in path else "?"
            batch = self.request("GET", f"{path}{sep}per_page=100&page={page}") or []
            items += batch
            if len(batch) < 100:
                return items
            page += 1

    # --- endpoints used by the gate --------------------------------------------------

    def pr(self, number: int) -> dict:
        return self.request("GET", f"/repos/{self.repo}/pulls/{number}")

    def pr_files(self, number: int) -> list[dict]:
        return self.paginate(f"/repos/{self.repo}/pulls/{number}/files")

    def set_status(self, sha: str, context: str, state: str, description: str, target_url: str | None = None) -> None:
        body = {"state": state, "context": context, "description": description[:140]}
        if target_url:
            body["target_url"] = target_url
        self.request("POST", f"/repos/{self.repo}/statuses/{sha}", body)

    def issue_comments(self, number: int) -> list[dict]:
        return self.paginate(f"/repos/{self.repo}/issues/{number}/comments")

    def upsert_sticky(self, number: int, body: str) -> None:
        existing = next((c for c in self.issue_comments(number) if STICKY_MARKER in (c.get("body") or "")), None)
        if existing:
            self.request("PATCH", f"/repos/{self.repo}/issues/comments/{existing['id']}", {"body": body})
        else:
            self.request("POST", f"/repos/{self.repo}/issues/{number}/comments", {"body": body})

    def comment(self, number: int, body: str) -> None:
        self.request("POST", f"/repos/{self.repo}/issues/{number}/comments", {"body": body})

    def review_comments(self, number: int) -> list[dict]:
        return self.paginate(f"/repos/{self.repo}/pulls/{number}/comments")

    def reviews(self, number: int) -> list[dict]:
        return self.paginate(f"/repos/{self.repo}/pulls/{number}/reviews")

    def create_review(self, number: int, sha: str, event: str, body: str, comments: list[dict]) -> dict:
        return self.request(
            "POST",
            f"/repos/{self.repo}/pulls/{number}/reviews",
            {"commit_id": sha, "event": event, "body": body, "comments": comments},
        )

    def dismiss_review(self, number: int, review_id: int, message: str) -> None:
        self.request("PUT", f"/repos/{self.repo}/pulls/{number}/reviews/{review_id}/dismissals", {"message": message})

    def update_review(self, number: int, review_id: int, body: str) -> None:
        self.request("PUT", f"/repos/{self.repo}/pulls/{number}/reviews/{review_id}", {"body": body})

    def delete_review_comment(self, comment_id: int) -> None:
        self.request("DELETE", f"/repos/{self.repo}/pulls/comments/{comment_id}")

    def hide_as_outdated(self, node_id: str) -> None:
        """Collapse a review or comment in the PR, like GitHub's "Hide > Outdated"."""
        api = self.api[: -len("/v3")] if self.api.endswith("/v3") else self.api  # GHES: /api/v3 -> /api
        query = (
            "mutation($id: ID!) { minimizeComment(input: {subjectId: $id, classifier: OUTDATED}) { clientMutationId } }"
        )
        res = self.request("POST", f"{api}/graphql", {"query": query, "variables": {"id": node_id}})
        if (res or {}).get("errors"):
            raise GitHubError(f"minimizeComment {node_id}: {res['errors']}")

    def collaborator_permission(self, user: str) -> str:
        return self.request("GET", f"/repos/{self.repo}/collaborators/{user}/permission").get("permission", "none")

    def team_member(self, org: str, team: str, user: str, token: str | None = None) -> bool:
        try:
            data = self.request("GET", f"/orgs/{org}/teams/{team}/memberships/{user}", token=token)
        except GitHubError as e:
            if "HTTP 404" in str(e):
                return False
            raise
        return (data or {}).get("state") == "active"


def commentable_lines(files: list[dict]) -> dict[str, set[int]]:
    """Lines on the RIGHT side of the PR diff, where GitHub accepts inline comments."""
    result: dict[str, set[int]] = {}
    for f in files:
        lines, current = set(), 0
        for row in (f.get("patch") or "").splitlines():
            match = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)", row)
            if match:
                current = int(match.group(1))
            elif row.startswith("-"):
                continue
            else:
                lines.add(current)
                current += 1
        result[f["filename"]] = lines
    return result


def publish(
    gh: GitHub, number: int, sha: str, findings: list[Finding], decision: Decision, summary: str, run_url: str | None
) -> None:
    """Statuses, sticky summary, review with new inline comments, stale gate reviews dismissed."""
    for context, (state, description) in decision.statuses.items():
        gh.set_status(sha, context, state, description, run_url)

    payload = json.dumps([f.fingerprint() for f in findings if f.severity in ("critical", "high")])
    gh.upsert_sticky(number, f"{STICKY_MARKER}\n{summary}\n<!-- qg:findings {payload} -->")

    if decision.review_event != "REQUEST_CHANGES":
        for review in gh.reviews(number):
            if review.get("state") == "CHANGES_REQUESTED" and STICKY_MARKER in (review.get("body") or ""):
                try:
                    gh.dismiss_review(number, review["id"], "Quality gate: no blocking findings on the latest commit.")
                except GitHubError as e:
                    log.warning("could not dismiss stale gate review %s: %s", review["id"], e)

    # Keep one inline comment per current finding; delete repeats and findings that are gone.
    current = {f.fingerprint() for f in decision.inline}
    posted = set()
    for c in gh.review_comments(number):
        marks = INLINE_MARKER.findall(c.get("body") or "")
        if not marks:
            continue
        if marks[0] in current and marks[0] not in posted:
            posted.add(marks[0])
            continue
        try:
            gh.delete_review_comment(c["id"])
        except GitHubError as e:
            log.warning("could not delete stale gate comment %s: %s", c["id"], e)

    # Gate reviews still showing a run's findings; only one that matches this run may stay.
    live = [r for r in gh.reviews(number) if STICKY_MARKER in (r.get("body") or "") and SUPERSEDED not in r["body"]]
    if decision.review_event is None:
        supersede_reviews(gh, number, live, dismiss=False)
        return
    valid = commentable_lines(gh.pr_files(number))
    comments, not_inline = [], []
    for f in decision.inline:
        if f.fingerprint() in posted:
            continue
        if f.line in valid.get(f.file, set()):
            comments.append({"path": f.file, "line": f.line, "side": "RIGHT", "body": comment_body(f)})
        else:
            not_inline.append(f)
    lines = [STICKY_MARKER, "Quality gate review. Full summary in the pinned gate comment."]
    for f in not_inline + [f for f in decision.summary_only if f.severity != "low"]:
        lines += ["", comment_body(f).replace(STICKY_MARKER, ""), f"<sub>at `{f.location}`</sub>"]
    body = "\n".join(lines)
    state = "CHANGES_REQUESTED" if decision.review_event == "REQUEST_CHANGES" else "COMMENTED"
    latest = live[-1] if live else None
    if not comments and latest and latest.get("state") == state and latest.get("body") == body:
        supersede_reviews(gh, number, live[:-1], dismiss=True)
        return  # nothing changed since the last run
    gh.create_review(number, sha, decision.review_event, body, comments)
    supersede_reviews(gh, number, live, dismiss=True)


def supersede_reviews(gh: GitHub, number: int, reviews: list[dict], dismiss: bool) -> None:
    """Older gate reviews list findings from older runs: dismiss their request for changes, blank and hide them."""
    for review in reviews:
        try:
            if dismiss and review.get("state") == "CHANGES_REQUESTED":
                gh.dismiss_review(number, review["id"], "Superseded by a newer gate run.")
            gh.update_review(number, review["id"], SUPERSEDED)
            gh.hide_as_outdated(review["node_id"])
        except GitHubError as e:
            log.warning("could not supersede gate review %s: %s", review["id"], e)


def blocking_fingerprints(sticky_body: str) -> list[str]:
    match = FINDINGS_MARKER.search(sticky_body or "")
    return json.loads(match.group(1)) if match else []
