#!/usr/bin/env bash
# Protects develop and main with the quality gate (AGENTS#15). Run once, as a repo admin:
#   bash gate/setup/branch_protection.sh [owner/repo]
# Requires an authenticated gh CLI. Branches that don't exist yet are skipped with a warning.
set -euo pipefail

REPO="${1:-$(gh repo view --json nameWithOwner -q .nameWithOwner)}"

for BRANCH in develop main; do
  if ! gh api "repos/$REPO/branches/$BRANCH" >/dev/null 2>&1; then
    echo "skip: $REPO has no '$BRANCH' branch yet (create it, then re-run)" >&2
    continue
  fi
  gh api --method PUT "repos/$REPO/branches/$BRANCH/protection" --input - <<JSON
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["quality-gate/critical", "quality-gate/high"]
  },
  "enforce_admins": false,
  "required_pull_request_reviews": {
    "dismiss_stale_reviews": true,
    "required_approving_review_count": 0
  },
  "restrictions": null
}
JSON
  echo "protected: $REPO@$BRANCH requires quality-gate/critical and quality-gate/high"
done
