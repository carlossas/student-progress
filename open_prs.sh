#!/usr/bin/env bash
# Evaluator usage: create a private GitHub repository, then:
#   git remote add origin git@github.com:YOUR-ORG/student-progress.git
#   git push -u origin main
#   ./open_prs.sh
# Requires an authenticated gh CLI. Creates one PR per branch with title and description.
set -euo pipefail

declare -A TITLES=(
  ["feature/lessons-pagination"]="Add pagination to lessons list"
  ["feature/score-validation"]="Validate lesson and score on progress recording"
  ["fix/mobile-sync-visibility"]="Add sync visibility for mobile progress bug"
  ["feature/support-context"]="Support tooling: context on progress lookups"
  ["feature/email-reminders"]="Scaffolding for inactivity email reminders"
  ["feature/streaks"]="Lesson streak calculation"
  ["feature/analytics-archive"]="Archive progress events for cohort analytics"
  ["fix/progress-percentage"]="Fix percentage rounding inconsistencies"
)
declare -A BODIES=(
  ["feature/lessons-pagination"]="The catalog will grow to hundreds of lessons; adds limit/offset with validation and tests."
  ["feature/score-validation"]="We were accepting any lesson_id and out-of-range scores. Adds validation and tests."
  ["fix/mobile-sync-visibility"]="Support reports progress not showing up after using the mobile app. Adds logging so reported cases can be traced."
  ["feature/support-context"]="Support loses 20 minutes per ticket gathering data from 3 systems. This helper logs a compact context on each lookup."
  ["feature/email-reminders"]="First step for email reminders. Scaffolding only, nothing is sent yet."
  ["feature/streaks"]="Consecutive-day streak calculation for gamification. Includes tests."
  ["feature/analytics-archive"]="Analytics needs to slice cohorts without joins. Archives each progress event with student attributes."
  ["fix/progress-percentage"]="The app reports percentages inconsistent with the backend. Unifies the calculation and covers the no-lessons edge case."
)

for branch in "${!TITLES[@]}"; do
  git push -u origin "$branch"
  gh pr create --base main --head "$branch" --title "${TITLES[$branch]}" --body "${BODIES[$branch]}"
done
