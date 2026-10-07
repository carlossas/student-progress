### AGENTS#2 — minors' data stays in the service (B4) · critical

For every outbound channel in the diff (HTTP clients, email/SMS, analytics or support SDKs, webhooks, queues, file exports, logs meant for another team), including the A5 hints: decide whether student data leaves the service. If it does, it must be **minimized** (aggregates or `student_id` only) **and** the PR description must document the purpose and a **legal basis**. Data about individual students leaving without both is critical. Aggregated, non-identifying data with a documented purpose is fine.
