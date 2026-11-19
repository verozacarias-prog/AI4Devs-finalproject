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

# adds_lines($o; $n): $n keeps $o whole and only puts complete lines around it.
# Text added inside a line of $o, like "or True" after an assertion, is a change.
ADDS_LINES='def adds_lines($o; $n):
  ($n | split($o)) as $parts
  | if ($parts | length) < 2 then false
    else ($parts[0]) as $before | ($parts[1:] | join($o)) as $after
      | ($before == "" or ($before | endswith("\n")) or ($o | startswith("\n")))
        and ($after == "" or ($after | startswith("\n")) or ($o | endswith("\n")))
    end;'

# The text the edit removes and the text it leaves, joined across edits.
case "$TOOL" in
  MultiEdit)
    REMOVED=$(printf '%s' "$INPUT" | jq -r '[.tool_input.edits[]?.old_string] | join("\n")')
    ADDED=$(printf '%s' "$INPUT" | jq -r '[.tool_input.edits[]?.new_string] | join("\n")')
    ONLY_ADDS=$(printf '%s' "$INPUT" | jq -r \
      "$ADDS_LINES"' [.tool_input.edits[]? | adds_lines(.old_string; .new_string)] | all')
    ;;
  Write)
    REMOVED=$([[ -f "$ABS" ]] && cat "$ABS")
    ADDED=$(field "$INPUT" '.tool_input.content')
    if [[ -f "$ABS" ]]; then
      ONLY_ADDS=$(printf '%s' "$INPUT" | jq -r --rawfile current "$ABS" \
        "$ADDS_LINES"' adds_lines($current | sub("\n+$"; ""); .tool_input.content)')
    else
      ONLY_ADDS=true
    fi
    ;;
  *)
    REMOVED=$(field "$INPUT" '.tool_input.old_string')
    ADDED=$(field "$INPUT" '.tool_input.new_string')
    ONLY_ADDS=$(printf '%s' "$INPUT" | jq -r \
      "$ADDS_LINES"' adds_lines(.tool_input.old_string; .tool_input.new_string)')
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
# Lines that skip, expect to fail or single out a test: adding one disables others.
disablers() {
  printf '%s\n' "$1" | grep -cE \
    '@pytest\.mark\.(skip|skipif|xfail)|pytest\.(skip|xfail)\(|unittest\.skip|(^|[^[:alnum:]_])(it|test|describe)\.(skip|only|todo|fixme)|(^|[^[:alnum:]_])x(it|test|describe)\('
}
if $is_test && [[ -f "$ABS" ]]; then
  if (( $(disablers "$ADDED") > $(disablers "$REMOVED") )); then
    ask "Vas a deshabilitar un test de $REL (skip, xfail u only). Un test no se deshabilita sin la aprobación de una persona (ADR 0024, punto 6). Confirmá solo si la persona lo decidió."
  fi
  if [[ "$ONLY_ADDS" != "true" ]]; then
    ask "Vas a cambiar o borrar algo de un test existente ($REL). Nunca se modifica un test para que la suite pase (AGENTS.md § 13): si el test está mal, frená y mostralo. Confirmá solo si la persona lo decidió."
  fi
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
