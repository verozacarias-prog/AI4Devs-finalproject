#!/usr/bin/env bash
# Stop — the turn does not close with the backend or the dashboard tests in the red.
#
# Each half runs only when it has uncommitted changes, new files included. A half
# whose only changes are tests is in the red phase of ADR 0024 and is let through.
# Integration tests, e2e, lint and types stay in the pre-commit hook and in CI.
#
# Escape for a local exploration, never inside a delivery: PLATITA_PERMITIR_ROJO=1
# in the "env" of .claude/settings.local.json.
set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

INPUT=$(cat)
[[ "$(field "$INPUT" '.stop_hook_active')" == "true" ]] && exit 0
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

BACKEND=$(changed backend/app backend/tests)
if needs_run "$BACKEND" '^backend/tests/'; then
  PYTHON="$PROJECT_DIR/backend/.venv/bin/python"
  if [[ -x "$PYTHON" ]]; then
    if ! OUT=$(cd "$PROJECT_DIR/backend" && "$PYTHON" -m pytest -m "not integration" -q 2>&1); then
      FAILURES+=$'\n\nBackend, `pytest -m "not integration" -q`:\n'"$(printf '%s' "$OUT" | tail -30)"
    fi
  fi
fi

FRONTEND=$(changed frontend/src)
if needs_run "$FRONTEND" '\.test\.tsx?$'; then
  VITEST="$PROJECT_DIR/frontend/node_modules/.bin/vitest"
  if [[ -x "$VITEST" ]]; then
    if ! OUT=$(cd "$PROJECT_DIR/frontend" && "$VITEST" run 2>&1); then
      FAILURES+=$'\n\nDashboard, `vitest run`:\n'"$(printf '%s' "$OUT" | tail -30)"
    fi
  fi
fi

if [[ -n "$FAILURES" ]]; then
  block "La suite falla y el turno todavía no se cierra. Implementá lo mínimo para que pase; nunca modifiques, deshabilites ni borres un test para lograrlo (AGENTS.md § 13).${FAILURES}"
fi

exit 0
