### AGENTS#4 — collect and copy only what you need (B6) · critical when the data can belong to minors

Flag code that gathers name, email, birthdate or `is_minor` when `student_id` (or an aggregate) would serve the stated purpose: support contexts, analytics payloads, debug helpers, caches. Point at the line that adds the unnecessary field and suggest the minimal version.
