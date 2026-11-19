#!/usr/bin/env bash
# Common helpers for the Claude Code hooks of this repository.
#
# Every hook sources this file. A hook must never break the session: when
# something it needs is missing (jq, git, a test runner), it lets the action
# through instead of failing on every turn.
#
# Adapted from the SDD Harness Kit (github.com/DisTinta/sdd-harness-kit, MIT).

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"

# Without jq the hooks cannot read their input: they turn themselves off.
command -v jq >/dev/null 2>&1 || exit 0

# field <json> <jq path> → the value, or an empty string.
field() {
  printf '%s' "$1" | jq -r "$2 // empty" 2>/dev/null
}

# relative <path> → the path relative to the project root.
relative() {
  local path=$1
  case "$path" in
    "$PROJECT_DIR"/*) path=${path#"$PROJECT_DIR"/} ;;
  esac
  printf '%s' "$path"
}

# absolute <path> → the path anchored at the project root.
absolute() {
  case "$1" in
    /*) printf '%s' "$1" ;;
    *) printf '%s/%s' "$PROJECT_DIR" "$1" ;;
  esac
}

# ── PreToolUse decisions ─────────────────────────────────────────────────────

_decide() {
  jq -n --arg decision "$1" --arg reason "$2" '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: $decision,
      permissionDecisionReason: $reason
    }
  }'
  exit 0
}

deny() { _decide deny "$1"; }
ask() { _decide ask "$1"; }

# ── Stop decision ────────────────────────────────────────────────────────────

block() {
  jq -n --arg reason "$1" '{decision: "block", reason: $reason}'
  exit 0
}

# warn <message> → let the turn close, and show the message to the person.
warn() {
  jq -n --arg message "$1" '{systemMessage: $message}'
  exit 0
}

# ── Rules shared by more than one hook ───────────────────────────────────────

# is_secret_path <path> → success when the file holds secrets or credentials.
# .env.example is the documented, secret-free template and stays readable, and so
# does frontend/e2e/compose.env: versioned, with invented values for the e2e stack.
is_secret_path() {
  local name
  [[ "$(relative "$1")" == "frontend/e2e/compose.env" ]] && return 1
  name=$(basename "$1")
  case "$name" in
    .env.example) return 1 ;;
    .env | .env.* | *.env) return 0 ;;
    credentials* | id_rsa | id_ed25519 | *.pem | *.key | service-account*.json) return 0 ;;
  esac
  return 1
}
