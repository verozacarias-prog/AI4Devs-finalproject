#!/usr/bin/env bash
# PreToolUse (Bash) — the rules of AGENTS.md that a shell command can break.
# What lives in AGENTS.md is read by the model; this is run by code.
set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

INPUT=$(cat)
COMMAND=$(field "$INPUT" '.tool_input.command')
[[ -n "$COMMAND" ]] || exit 0

matches() { printf '%s' "$COMMAND" | grep -qE -e "$1"; }

# Start of a command: beginning of the line or after a separator.
S='(^|[;&|(][[:space:]]*|[[:space:]])'

# 1. Mass deletion, device destruction and wide-open permissions.
if matches "${S}rm[[:space:]]+(-[a-zA-Z]*[rf][a-zA-Z]*[[:space:]]+)+|${S}mkfs|${S}dd[[:space:]]+if=|:\(\)\{.*\};:"; then
  deny "Comando destructivo bloqueado: $COMMAND"
fi
if matches "${S}chmod[[:space:]]+(-R[[:space:]]+)?777"; then
  deny "chmod 777 bloqueado: abre el archivo a cualquier usuario del sistema."
fi

# 2. Reading a secrets file through the shell (the Read tool has its own hook).
if matches "${S}(cat|less|more|head|tail|grep|rg|bat|nl|awk|sed|xxd|strings|base64|source|\.)[[:space:]]"; then
  while IFS= read -r token; do
    if [[ -n "$token" ]] && is_secret_path "$token"; then
      deny "Lectura bloqueada: $token tiene secretos y no se carga en el contexto del modelo (AGENTS.md § 7). Si necesitás saber qué variables existen, leé .env.example."
    fi
  done < <(printf '%s' "$COMMAND" | grep -oE "[^[:space:]\"';|&<>()]*\.env[^[:space:]\"';|&<>()]*")
fi

# 3. History rewriting and force push.
if matches "${S}git[[:space:]]+push.*(--force([^-]|$)|[[:space:]]-f([[:space:]]|$))"; then
  deny "git push --force no está permitido: un push forzado lo hace una persona o no se hace."
fi
if matches "${S}git[[:space:]]+filter-branch"; then
  deny "git filter-branch reescribe la historia: lo hace una persona o no se hace."
fi
if matches "${S}git[[:space:]]+(reset[[:space:]]+--hard|clean[[:space:]]+-[a-zA-Z]*f)"; then
  ask "Este comando descarta trabajo local sin vuelta atrás. Confirmalo a mano."
fi

# 4. Commits, pushes and merges belong to the person (AGENTS.md § 13).
if matches "${S}git[[:space:]]+commit([[:space:]].*)?[[:space:]](--no-verify|-n)([[:space:]]|$)"; then
  deny "git commit --no-verify saltea el hook de pre-commit, que corre los tres verificadores (AGENTS.md § 11). Saltearlo lo decide una persona, a mano."
fi
if matches "${S}gh[[:space:]]+pr[[:space:]]+merge"; then
  deny "Un asistente nunca hace merge: la aprobación final de un pull request es de una persona (AGENTS.md § 13)."
fi
if matches "${S}git[[:space:]]+commit([[:space:]]|$)" && ! matches '--dry-run'; then
  ask "Un asistente hace commit solo cuando una persona se lo pide (AGENTS.md § 13). Confirmá que te lo pidieron."
fi
if matches "${S}git[[:space:]]+push([[:space:]]|$)" && ! matches '--dry-run'; then
  ask "Un asistente hace push solo cuando una persona se lo pide (AGENTS.md § 13). Confirmá que te lo pidieron."
fi

# 5. Production and deploys.
if matches 'APP_ENV=production' || matches "${S}render[[:space:]]+deploys?([[:space:]]|$)"; then
  deny "Ningún asistente opera contra production ni despliega: lo aprueba y lo hace una persona."
fi

# 6. The classification evals call the real model and cost money (AGENTS.md § 11).
if matches 'evals\.classification\.run.*[[:space:]]--run([[:space:]]|$)'; then
  ask "El set de regresión con --run llama al modelo real, cuesta plata y usa la clave del demo (AGENTS.md § 11). Antes de correrlo se dice cuántas llamadas son y se espera el ok: corré primero sin --run."
fi

# 7. New dependencies (AGENTS.md § 9). Installing from a requirements file stays free.
if { matches "${S}pip3?[[:space:]]+install([[:space:]]|$)" && ! matches '[[:space:]](-r|--requirement)[[:space:]]'; } \
  || matches "${S}(npm|pnpm|yarn|bun)[[:space:]]+(i|add|install)([[:space:]]+-[^[:space:]]+)*[[:space:]]+[^-[:space:]]"; then
  ask "Vas a instalar una dependencia. Verificá en el registro oficial que el paquete existe y es el correcto, y justificá por qué no alcanza lo instalado (AGENTS.md § 9). En el backend se agrega al .in y se corre scripts/lock_backend_dependencies.sh."
fi

exit 0
