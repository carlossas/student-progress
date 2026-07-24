# Open pull requests

These are the 8 pull requests pending review. Each branch is based on `main`.
Your AI Quality Gate must review them against `TEAM-STANDARDS.md`.

| # | Branch | Title | Author's description |
|---|--------|-------|---------------------|
| 1 | `feature/lessons-pagination` | Add pagination to lessons list | "The catalog will grow to hundreds of lessons; adds limit/offset with validation and tests." |
| 2 | `feature/score-validation` | Validate lesson and score on progress recording | "We were accepting any lesson_id and out-of-range scores. Adds validation and tests." |
| 3 | `fix/mobile-sync-visibility` | Add sync visibility for mobile progress bug | "Support reports progress not showing up after using the mobile app. Adds logging so reported cases can be traced." |
| 4 | `feature/support-context` | Support tooling: context on progress lookups | "Support loses 20 minutes per ticket gathering data from 3 systems. This helper logs a compact context on each lookup." |
| 5 | `feature/email-reminders` | Scaffolding for inactivity email reminders | "First step for email reminders. Scaffolding only, nothing is sent yet." |
| 6 | `feature/streaks` | Lesson streak calculation | "Consecutive-day streak calculation for gamification. Includes tests." |
| 7 | `feature/analytics-archive` | Archive progress events for cohort analytics | "Analytics needs to slice cohorts without joins. Archives each progress event with student attributes." |
| 8 | `fix/progress-percentage` | Fix percentage rounding inconsistencies | "The app reports percentages inconsistent with the backend. Unifies the calculation and covers the no-lessons edge case." |
