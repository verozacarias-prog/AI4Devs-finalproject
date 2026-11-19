#!/usr/bin/env bash
# Stop — the turn does not close with the backend or the dashboard tests in the red.
#
# Each half runs only when it has uncommitted changes, new files included. A half
# whose only changes are tests is in the red phase of ADR 0024 and is let through.
# Integration tests, e2e, lint and types stay in the pre-commit hook and in CI.
#
# It blocks once. On the second attempt (stop_hook_active) it runs the suite again
# and, if it is still red, lets the turn close but tells the person: blocking again
# could leave the assistant in a loop on a test it cannot fix. When a half cannot
# run because its runner is missing, the turn closes with a warning too.
#
# Escape for a local exploration, never inside a delivery: PLATITA_PERMITIR_ROJO=1
# in the "env" of .claude/settings.local.json.
set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

INPUT=$(cat)
SECOND_ATTEMPT=$(field "$INPUT" '.stop_hook_active')
[[ "${PLATITA_PERMITIR_ROJO:-}" == "1" ]] && exit 0
git -C "$PROJECT_DIR" rev-parse --git-dir >/dev/null 2>&1 || exit 0

# changed <path>... → the uncommitted files under those paths, one per line.
changed() {
  git -C "$PROJECT_DIR" status --porcelain --untracked-files=all -- "$@" 2>/dev/null \
    | cut -c4- | sed 's/.* -> //'
}

# needs_run <files> <test pattern> → success when some file is not a test.
needs_run() {
  [[ -n "$1" ]] || return 1
  printf '%s\n' "$1" | grep -qvE "$2"
}

FAILURES=""
NOT_RUN=""

BACKEND=$(changed backend/app backend/tests)
if needs_run "$BACKEND" '^backend/tests/'; then
  PYTHON="$PROJECT_DIR/backend/.venv/bin/python"
  if [[ -x "$PYTHON" ]]; then
    if ! OUT=$(cd "$PROJECT_DIR/backend" && "$PYTHON" -m pytest -m "not integration" -q 2>&1); then
      FAILURES+=$'\n\nBackend, `pytest -m "not integration" -q`:\n'"$(printf '%s' "$OUT" | tail -30)"
    fi
  else
    NOT_RUN+=" No se corrieron los tests del backend: falta backend/.venv."
  fi
fi

FRONTEND=$(changed frontend/src)
if needs_run "$FRONTEND" '\.test\.tsx?$'; then
  VITEST="$PROJECT_DIR/frontend/node_modules/.bin/vitest"
  if [[ -x "$VITEST" ]]; then
    if ! OUT=$(cd "$PROJECT_DIR/frontend" && "$VITEST" run 2>&1); then
      FAILURES+=$'\n\nDashboard, `vitest run`:\n'"$(printf '%s' "$OUT" | tail -30)"
    fi
  else
    NOT_RUN+=" No se corrieron los tests del dashboard: falta frontend/node_modules (npm ci)."
  fi
fi

if [[ -n "$FAILURES" && "$SECOND_ATTEMPT" == "true" ]]; then
  warn "El turno cerró con la suite en rojo: el asistente no la pudo poner en verde después del primer aviso. Revisalo antes de seguir.${NOT_RUN}${FAILURES}"
fi
if [[ -n "$FAILURES" ]]; then
  block "La suite falla y el turno todavía no se cierra. Implementá lo mínimo para que pase; nunca modifiques, deshabilites ni borres un test para lograrlo (AGENTS.md § 13).${NOT_RUN}${FAILURES}"
fi
if [[ -n "$NOT_RUN" ]]; then
  warn "${NOT_RUN# }"
fi

exit 0
