#!/usr/bin/env bash
# PreToolUse (Read) — no secret or credential file enters the model's context.
# AGENTS.md § 7: secrets only through environment variables.
set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

INPUT=$(cat)
FILE=$(field "$INPUT" '.tool_input.file_path')
[[ -n "$FILE" ]] || exit 0

if is_secret_path "$FILE"; then
  deny "Lectura bloqueada: $(relative "$FILE") tiene secretos o credenciales, y no se cargan en el contexto del modelo (AGENTS.md § 7). Si necesitás saber qué variables existen, leé .env.example."
fi

exit 0
