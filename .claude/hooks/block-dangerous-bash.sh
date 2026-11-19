#!/usr/bin/env bash
# PreToolUse (Bash) — the rules of AGENTS.md that a shell command can break.
# What lives in AGENTS.md is read by the model; this is run by code.
#
# It reads the text of the command: it stops what an assistant would run in the
# normal course of work, not a command built to slip past it (ADR 0031).
# Every rule that rejects runs before any rule that asks.
set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

INPUT=$(cat)
COMMAND=$(field "$INPUT" '.tool_input.command')
[[ -n "$COMMAND" ]] || exit 0

matches() { printf '%s' "$COMMAND" | grep -qE -e "$1"; }

# Git is read in a normalized copy of the command:
#   - quoted text becomes Q, so a commit message that mentions "-n" or "--force"
#     is not taken for the flag itself;
#   - the global options between git and its subcommand (-C <dir>, -c <k=v>,
#     --git-dir=…, --no-pager…) are dropped, so "git -C . push" is a push.
GIT=$(printf '%s' "$COMMAND" | sed -E "s/\"[^\"]*\"/Q/g; s/'[^']*'/Q/g")
while :; do
  NEXT=$(printf '%s' "$GIT" | sed -E \
    's/(^|[^[:alnum:]_-])git[[:space:]]+(-[Cc][[:space:]]+[^[:space:]]+|--[a-z-]+(=[^[:space:]]+)?|-P)/\1git/g')
  [[ "$NEXT" == "$GIT" ]] && break
  GIT=$NEXT
done
git_matches() { printf '%s' "$GIT" | grep -qE -e "$1"; }

# Start of a command: beginning of the line or after a separator.
S='(^|[;&|(][[:space:]]*|[[:space:]])'

# A test file: backend/tests/, frontend/e2e/ or a *.test.ts(x) of the dashboard.
TEST_PATH='(backend/tests/|frontend/e2e/|[^[:space:]]*\.test\.tsx?([[:space:]]|$))'

# ── Rejected ─────────────────────────────────────────────────────────────────

# 1. Recursive deletion, device destruction and wide-open permissions.
#    Deleting one file with rm or rm -f is not mass deletion.
if matches "${S}rm[[:space:]]+(-[^[:space:]]+[[:space:]]+)*(-[a-zA-Z]*[rR]|--recursive)|${S}mkfs|${S}dd[[:space:]]+if=|:\(\)\{.*\};:"; then
  deny "Comando destructivo bloqueado: $COMMAND"
fi
if matches "${S}chmod[[:space:]]+(-R[[:space:]]+)?777"; then
  deny "chmod 777 bloqueado: abre el archivo a cualquier usuario del sistema."
fi

# 2. Reading a secrets file through the shell (the Read tool has its own hook).
#    The same rule as the Read hook, on every word that looks like a file: it has
#    a dot or a slash, so a bare word like "credentials" in a grep stays free.
if matches "${S}(cat|less|more|head|tail|grep|rg|bat|nl|awk|sed|xxd|strings|base64|cp|scp|diff|source|\.)[[:space:]]"; then
  while IFS= read -r token; do
    if [[ "$token" == *[./]* ]] && is_secret_path "$token"; then
      deny "Lectura bloqueada: $token tiene secretos o credenciales y no se carga en el contexto del modelo (AGENTS.md § 7). Si necesitás saber qué variables existen, leé .env.example."
    fi
  done < <(printf '%s' "$COMMAND" | grep -oE "[^[:space:]\"';|&<>()]+")
fi

# 3. History rewriting and force push, in any of its forms.
if git_matches "${S}git[[:space:]]+push([[:space:]].*)?[[:space:]](--force|-f([[:space:]]|$)|\+[^[:space:]])"; then
  deny "El push forzado (--force, --force-with-lease, -f o +rama) no está permitido: lo hace una persona o no se hace."
fi
if git_matches "${S}git[[:space:]]+filter-branch"; then
  deny "git filter-branch reescribe la historia: lo hace una persona o no se hace."
fi

# 4. Skipping the pre-commit hook, and merging.
if git_matches "${S}git[[:space:]]+commit([[:space:]].*)?[[:space:]](--no-verify|-n)([[:space:]]|$)"; then
  deny "git commit --no-verify saltea el hook de pre-commit, que corre los tres verificadores (AGENTS.md § 11). Saltearlo lo decide una persona, a mano."
fi
if matches "${S}gh[[:space:]]+pr[[:space:]]+merge" || matches "${S}gh[[:space:]]+api[[:space:]].*/merge([^[:alnum:]_-]|$)"; then
  deny "Un asistente nunca hace merge: la aprobación final de un pull request es de una persona (AGENTS.md § 13)."
fi

# 5. Production and deploys. Naming the word, as in a grep, is not operating on it:
#    what counts is an environment set to it (APP_ENV=production, --env production).
if matches '(ENV|env)(=|[[:space:]]+)production([^[:alnum:]_-]|$)' \
  || matches "${S}render[[:space:]]+deploys?([[:space:]]|$)"; then
  deny "Ningún asistente opera contra production ni despliega: lo aprueba y lo hace una persona."
fi

# ── Asked ────────────────────────────────────────────────────────────────────

# 6. Deleting or rewriting a test from the shell: the same rule as the edit hook.
if matches "${S}(rm|unlink|mv)[[:space:]].*${TEST_PATH}" \
  || matches "${S}(sed|perl)[[:space:]](.*[[:space:]])?-[a-zA-Z]*i.*${TEST_PATH}" \
  || matches ">[[:space:]]*${TEST_PATH}" \
  || git_matches "${S}git[[:space:]]+(checkout|restore|rm)[[:space:]].*${TEST_PATH}"; then
  ask "Este comando borra o cambia un test. Un test no se modifica, no se deshabilita y no se borra sin la aprobación de una persona (ADR 0024, punto 6). Confirmá solo si la persona lo decidió."
fi

# 7. Discarding local work.
if git_matches "${S}git[[:space:]]+(reset[[:space:]]+--hard|clean[[:space:]]+-[a-zA-Z]*f)"; then
  ask "Este comando descarta trabajo local sin vuelta atrás. Confirmalo a mano."
fi

# 8. Commits and pushes belong to the person (AGENTS.md § 13).
if git_matches "${S}git[[:space:]]+commit([[:space:]]|$)" && ! matches '--dry-run'; then
  ask "Un asistente hace commit solo cuando una persona se lo pide (AGENTS.md § 13). Confirmá que te lo pidieron."
fi
if git_matches "${S}git[[:space:]]+push([[:space:]]|$)" && ! matches '--dry-run'; then
  ask "Un asistente hace push solo cuando una persona se lo pide (AGENTS.md § 13). Confirmá que te lo pidieron."
fi

# 9. The classification evals call the real model and cost money (AGENTS.md § 11).
if matches 'evals\.classification\.run.*[[:space:]]--run([[:space:]]|$)'; then
  ask "El set de regresión con --run llama al modelo real, cuesta plata y usa la clave del demo (AGENTS.md § 11). Antes de correrlo se dice cuántas llamadas son y se espera el ok: corré primero sin --run."
fi

# 10. New dependencies (AGENTS.md § 9). Installing from a requirements file stays free.
if { matches "${S}pip3?[[:space:]]+install([[:space:]]|$)" && ! matches '[[:space:]](-r|--requirement)[[:space:]]'; } \
  || matches "${S}(npm|pnpm|yarn|bun)[[:space:]]+(i|add|install)([[:space:]]+-[^[:space:]]+)*[[:space:]]+[^-[:space:]]"; then
  ask "Vas a instalar una dependencia. Verificá en el registro oficial que el paquete existe y es el correcto, y justificá por qué no alcanza lo instalado (AGENTS.md § 9). En el backend se agrega al .in y se corre scripts/lock_backend_dependencies.sh."
fi

exit 0
