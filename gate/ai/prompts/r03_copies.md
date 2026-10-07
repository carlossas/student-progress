### AGENTS#3 — no secondary copies without purpose and retention (B5) · critical when minors' data is involved, otherwise high

Detect copies of personal data: archives, caches, denormalized or "enriched" events, exports, snapshots. Each needs a declared purpose and a retention category in `RETENTION_DAYS` (minors' data: at most 90 days). Copies kept "indefinitely", or with no category, are violations. A copy that only holds `student_id` and non-personal facts, with a declared category, is fine.
