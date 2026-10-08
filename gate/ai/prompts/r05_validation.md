### AGENTS#5 — business-level input validation (B7) · high

Type checks are not enough. Use the business rules (context section) as the contract. Flag changed code that accepts:
- IDs that must exist but are not checked (for example a `lesson_id` not in the catalog);
- values outside their valid range (for example `score` outside 0–100);
- inputs that still crash with a 500 instead of a 4xx (non-numeric strings, missing keys).
