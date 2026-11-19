#!/usr/bin/env bash
# PreToolUse (Edit|MultiEdit|Write) — what the assistant must not rewrite on its own:
#   1. Environment files.
#   2. The approval line of a feature spec, which only the person writes.
#   3. Existing tests: adding to them is the red phase; changing them asks.
#   4. Migrations already in git.
# AGENTS.md § 8 and § 13; ADR 0024.
set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

INPUT=$(cat)
TOOL=$(field "$INPUT" '.tool_name')
FILE=$(field "$INPUT" '.tool_input.file_path')
[[ -n "$FILE" ]] || exit 0

case "$FILE" in
  *..*) deny "Ruta con '..' rechazada: $FILE" ;;
esac

if is_secret_path "$FILE"; then
  deny "Los archivos de entorno no se editan desde el asistente: $(relative "$FILE"). Los cambia una persona (AGENTS.md § 7)."
fi

REL=$(relative "$FILE")
ABS=$(absolute "$FILE")

# The text the edit removes and the text it leaves, joined across edits.
case "$TOOL" in
  MultiEdit)
    REMOVED=$(printf '%s' "$INPUT" | jq -r '[.tool_input.edits[]?.old_string] | join("\n")')
    ADDED=$(printf '%s' "$INPUT" | jq -r '[.tool_input.edits[]?.new_string] | join("\n")')
    ONLY_ADDS=$(printf '%s' "$INPUT" | jq -r \
      '[.tool_input.edits[]? | .new_string as $n | .old_string as $o | $n | contains($o)] | all')
    ;;
  Write)
    REMOVED=$([[ -f "$ABS" ]] && cat "$ABS")
    ADDED=$(field "$INPUT" '.tool_input.content')
    ONLY_ADDS=$([[ -f "$ABS" ]] && echo false || echo true)
    ;;
  *)
    REMOVED=$(field "$INPUT" '.tool_input.old_string')
    ADDED=$(field "$INPUT" '.tool_input.new_string')
    ONLY_ADDS=$(printf '%s' "$INPUT" | jq -r \
      '.tool_input.new_string as $n | .tool_input.old_string as $o | $n | contains($o)')
    ;;
esac

# 2. The approval line of a spec. The template keeps a placeholder, not an approval.
approvals() {
  printf '%s\n' "$1" | grep -E '\*\*Aprobado por:\*\*' \
    | grep -cvE '\*\*Aprobado por:\*\*[[:space:]]*pendiente[[:space:]]*$'
}
case "$REL" in
  docs/features/TEMPLATE/*) ;;
  docs/features/*/spec.md)
    if (( $(approvals "$ADDED") > $(approvals "$REMOVED") )); then
      deny "La línea «Aprobado por» de $REL la completa la persona que aprueba los casos, nunca un asistente (AGENTS.md § 13). Dejala en «pendiente» y pedí la aprobación."
    fi
    ;;
esac

# 3. Existing tests.
is_test=false
case "$REL" in
  backend/tests/* | frontend/e2e/*) is_test=true ;;
  frontend/src/*.test.ts | frontend/src/*.test.tsx) is_test=true ;;
esac
if $is_test && [[ -f "$ABS" && "$ONLY_ADDS" != "true" ]]; then
  ask "Vas a cambiar o borrar algo de un test existente ($REL). Nunca se modifica un test para que la suite pase (AGENTS.md § 13): si el test está mal, frená y mostralo. Confirmá solo si la persona lo decidió."
fi

# 4. Migrations already in git.
case "$REL" in
  backend/migrations/versions/*)
    if [[ -f "$ABS" ]] && git -C "$PROJECT_DIR" ls-files --error-unmatch "$REL" >/dev/null 2>&1; then
      ask "$REL es una migración ya versionada, y una migración aplicada no se edita (AGENTS.md § 8): el cambio va en una migración nueva. Confirmá solo si nunca se aplicó."
    fi
    ;;
esac

exit 0
