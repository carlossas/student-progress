# TEAM-STANDARDS — Open English LMS

Reglas del equipo. Todo PR se revisa contra este documento.

## 1. Calidad de código
- Código simple y legible; sin dead code ni TODOs sin ticket.
- Errores manejados explícitamente; nada de `except: pass`.
- Input externo siempre validado.

## 2. Testing
- Todo cambio de lógica trae tests que **fallan si la lógica se rompe**.
- Tests decorativos (asserts triviales, todo mockeado, no cubren el caso de negocio) cuentan como ausencia de tests.
- Los tests documentan el comportamiento esperado, incluidos casos borde.

## 3. PII y logging
- Clasificación: `pii` (datos personales de cualquier usuario) y `pii-minor` (datos de menores de 18 — tratamiento más estricto). En este servicio: `full_name`, `email`, `birthdate` son PII; si `is_minor=True`, son `pii-minor`.
- **Prohibido loguear PII**, directa o indirectamente (a través de helpers, `extra`, serialización de objetos). Usar `app.privacy.redact()`.
- Los datos de menores nunca salen del servicio hacia destinos no aprobados (analytics, soporte, terceros) sin minimización y base legal documentada.

## 4. Retención de datos
- Todo dataset persistido o copiado declara su categoría de retención (`app.privacy.RETENTION_DAYS`).
- Datos de menores: máximo 90 días salvo base legal documentada en el PR.
- Prohibido crear copias secundarias de datos personales "por las dudas" o "para siempre": minimización de datos siempre.

## 5. Secrets
- Solo por variables de entorno. Un secret commiteado es incidente de seguridad, aunque sea de sandbox.

## 6. Severidades para review
- **S1 — bloquea merge:** exposición de PII (agravado si `pii-minor`), secrets commiteados, violación de retención/minimización de datos de menores.
- **S2 — bloquea merge:** bugs de lógica que entregan datos incorrectos, lógica core sin tests reales o con tests decorativos.
- **S3 — comenta, no bloquea:** estilo, naming, oportunidades de refactor.
