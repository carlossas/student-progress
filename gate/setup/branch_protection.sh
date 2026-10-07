#!/usr/bin/env bash
# Protects develop and main with the quality gate (AGENTS#15). Run once, as a repo admin:
#   bash gate/setup/branch_protection.sh [owner/repo] [required approvals, default 1]
# Requires an authenticated gh CLI. Branches that don't exist yet are skipped with a warning.
# Admins are not forced (enforce_admins=false) so a solo maintainer can still merge.
# Check names carry the base branch: a commit that heads PRs into develop and main gets one
# pair of checks per PR instead of sharing (and overwriting) one pair.
set -euo pipefail

REPO="${1:-$(gh repo view --json nameWithOwner -q .nameWithOwner)}"
APPROVALS="${2:-1}"

for BRANCH in develop main; do
  if ! gh api "repos/$REPO/branches/$BRANCH" >/dev/null 2>&1; then
    echo "skip: $REPO has no '$BRANCH' branch yet (create it, then re-run)" >&2
    continue
  fi
  gh api --method PUT "repos/$REPO/branches/$BRANCH/protection" --input - <<JSON
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["quality-gate/$BRANCH/critical", "quality-gate/$BRANCH/high"]
  },
  "enforce_admins": false,
  "required_pull_request_reviews": {
    "dismiss_stale_reviews": true,
    "required_approving_review_count": $APPROVALS
  },
  "restrictions": null
}
JSON
  echo "protected: $REPO@$BRANCH requires quality-gate/$BRANCH/critical, quality-gate/$BRANCH/high and $APPROVALS approval(s)"
done
