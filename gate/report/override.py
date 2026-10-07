"""R14-A (AGENTS#14): a production-level approver can override a blocked PR, and it is logged.

Trigger: a PR comment `/gate-override <reason>`. Authorization, in order:
1. `GATE_OVERRIDE_TEAM=org/team-slug` set: the commenter must be an active member
   (needs `GATE_ORG_TOKEN`, a token with `read:org`).
2. Otherwise: the commenter's repository permission must be `admin` or `maintain`
   (configurable with `GATE_OVERRIDE_PERMISSIONS`).
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import UTC, datetime

from gate.config import STATUS_CRITICAL, STATUS_HIGH
from gate.report.github import STICKY_MARKER, blocking_fingerprints

COMMAND = re.compile(r"^/gate-override\b[ \t]*(.*)$", re.M)


@dataclass
class OverrideResult:
    accepted: bool
    message: str
    record: dict | None = None


def parse(body: str) -> str | None:
    """The reason, '' when missing, None when the comment is not an override."""
    match = COMMAND.search(body or "")
    return match.group(1).strip() if match else None


def authorized(gh, user: str) -> tuple[bool, str]:
    team = os.environ.get("GATE_OVERRIDE_TEAM", "").strip()
    if team:
        org, _, slug = team.partition("/")
        ok = gh.team_member(org, slug, user, token=os.environ.get("GATE_ORG_TOKEN") or None)
        return ok, f"member of @{team}" if ok else f"not a member of @{team}"
    allowed = {p.strip() for p in os.environ.get("GATE_OVERRIDE_PERMISSIONS", "admin,maintain").split(",") if p.strip()}
    permission = gh.collaborator_permission(user)
    return permission in allowed, f"repository permission `{permission}`"


def handle(gh, number: int, user: str, body: str, run_url: str | None = None) -> OverrideResult:
    reason = parse(body)
    if reason is None:
        return OverrideResult(False, "not an override command")
    ok, why = authorized(gh, user)
    if not ok:
        message = f"❌ Override rejected: @{user} is not a production approver ({why})."
        gh.comment(number, message)
        return OverrideResult(False, message)
    if not reason:
        message = (
            "❌ Override rejected: a reason is required, e.g. `/gate-override incident INC-42, fix in follow-up PR`."
        )
        gh.comment(number, message)
        return OverrideResult(False, message)

    pr = gh.pr(number)
    sha = pr["head"]["sha"]
    sticky = next((c["body"] for c in gh.issue_comments(number) if STICKY_MARKER in (c.get("body") or "")), "")
    record = {
        "user": user,
        "authorization": why,
        "timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
        "reason": reason,
        "commit": sha,
        "findings": blocking_fingerprints(sticky),
    }
    description = f"Overridden by @{user}: {reason}"
    for context in (STATUS_CRITICAL, STATUS_HIGH):
        gh.set_status(sha, context, "success", description, run_url)
    message = (
        f"⚠️ **Quality gate overridden** by @{user} ({why}) at {record['timestamp']} for commit `{sha[:8]}`.\n\n"
        f"Reason: {reason}\n\nOverridden blocking findings: {', '.join(record['findings']) or 'none recorded'}\n\n"
        "A new push re-runs the gate; the override applies to this commit only."
    )
    gh.comment(number, message)
    print(f"::warning::{message}")
    return OverrideResult(True, message, record)
