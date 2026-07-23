#!/usr/bin/env bash
# Uso (evaluador): crear un repo privado en GitHub, luego:
#   git remote add origin git@github.com:TU-ORG/student-progress.git
#   git push -u origin main
#   ./open_prs.sh
# Requiere gh CLI autenticado. Crea un PR por branch con título y descripción.
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
  ["feature/lessons-pagination"]="El catálogo va a crecer a cientos de lecciones; agrego limit/offset con validación y tests."
  ["feature/score-validation"]="Estábamos aceptando cualquier lesson_id y scores fuera de rango. Agrego validación + tests."
  ["fix/mobile-sync-visibility"]="Soporte reporta progreso que no aparece tras usar la app mobile. Agrego logging para poder rastrear los casos reportados."
  ["feature/support-context"]="Soporte pierde 20 min por ticket juntando datos de 3 sistemas. Este helper loguea un contexto compacto en cada lookup."
  ["feature/email-reminders"]="Primer paso de recordatorios por email. Solo scaffolding, todavía no se envía nada real."
  ["feature/streaks"]="Cálculo de racha de días consecutivos para gamification. Con tests."
  ["feature/analytics-archive"]="Analytics necesita cortar cohortes sin joins. Archivo cada evento de progreso con atributos del estudiante."
  ["fix/progress-percentage"]="La app reporta porcentajes inconsistentes con el backend. Unifico el cálculo y cubro el edge case sin lecciones."
)

for branch in "${!TITLES[@]}"; do
  git push -u origin "$branch"
  gh pr create --base main --head "$branch" --title "${TITLES[$branch]}" --body "${BODIES[$branch]}"
done
