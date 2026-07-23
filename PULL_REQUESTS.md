# Pull Requests abiertos

Estos son los 8 PRs pendientes de review. Cada branch parte de `main`.
Tu AI Quality Gate debe revisarlos contra `TEAM-STANDARDS.md`.

| # | Branch | Título | Descripción del autor |
|---|--------|--------|----------------------|
| 1 | `feature/lessons-pagination` | Add pagination to lessons list | "El catálogo va a crecer a cientos de lecciones; agrego limit/offset con validación y tests." |
| 2 | `feature/score-validation` | Validate lesson and score on progress recording | "Estábamos aceptando cualquier lesson_id y scores fuera de rango. Agrego validación + tests." |
| 3 | `fix/mobile-sync-visibility` | Add sync visibility for mobile progress bug | "Soporte reporta progreso que no aparece tras usar la app mobile. Agrego logging para poder rastrear los casos reportados." |
| 4 | `feature/support-context` | Support tooling: context on progress lookups | "Soporte pierde 20 min por ticket juntando datos de 3 sistemas. Este helper loguea un contexto compacto en cada lookup." |
| 5 | `feature/email-reminders` | Scaffolding for inactivity email reminders | "Primer paso de recordatorios por email. Solo scaffolding, todavía no se envía nada real." |
| 6 | `feature/streaks` | Lesson streak calculation | "Cálculo de racha de días consecutivos para gamification. Con tests." |
| 7 | `feature/analytics-archive` | Archive progress events for cohort analytics | "Analytics necesita cortar cohortes sin joins. Archivo cada evento de progreso con atributos del estudiante." |
| 8 | `fix/progress-percentage` | Fix percentage rounding inconsistencies | "La app reporta porcentajes inconsistentes con el backend. Unifico el cálculo y cubro el edge case sin lecciones." |
