#!/usr/bin/env bash
# Tests for the Claude Code hooks in .claude/hooks/.
#
# Each case feeds a hook the JSON that Claude Code would send it and checks the
# decision: allow, ask, deny (PreToolUse) or block (Stop). The hooks run against
# a throwaway git repository, so nothing here touches the real project.
#
# Usage: scripts/test_assistant_hooks.sh
set -uo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
HOOKS="$ROOT/.claude/hooks"
PASSED=0
FAILED=0

command -v jq >/dev/null 2>&1 || { echo "test_assistant_hooks: jq is required"; exit 1; }
command -v git >/dev/null 2>&1 || { echo "test_assistant_hooks: git is required"; exit 1; }

SANDBOX=$(mktemp -d)
trap 'rm -rf "$SANDBOX"' EXIT
export CLAUDE_PROJECT_DIR="$SANDBOX"
unset PLATITA_PERMITIR_ROJO

# ── Helpers ──────────────────────────────────────────────────────────────────

# decision <hook file> <json> → allow | ask | deny | block | error-<status>
decision() {
  local out status d
  out=$(printf '%s' "$2" | bash "$HOOKS/$1" 2>/dev/null)
  status=$?
  if [[ $status -ne 0 ]]; then
    echo "error-$status"
    return
  fi
  d=$(printf '%s' "$out" | jq -r '.hookSpecificOutput.permissionDecision // .decision // empty' 2>/dev/null)
  echo "${d:-allow}"
}

expect() {
  local name=$1 want=$2 got=$3
  if [[ "$got" == "$want" ]]; then
    PASSED=$((PASSED + 1))
  else
    FAILED=$((FAILED + 1))
    echo "FAIL $name: expected $want, got $got"
  fi
}

read_json() { jq -n --arg p "$1" '{tool_name: "Read", tool_input: {file_path: $p}}'; }
edit_json() {
  jq -n --arg p "$1" --arg o "$2" --arg n "$3" \
    '{tool_name: "Edit", tool_input: {file_path: $p, old_string: $o, new_string: $n}}'
}
write_json() {
  jq -n --arg p "$1" --arg c "$2" '{tool_name: "Write", tool_input: {file_path: $p, content: $c}}'
}
bash_json() { jq -n --arg c "$1" '{tool_name: "Bash", tool_input: {command: $c}}'; }
stop_json() { jq -n --argjson a "${1:-false}" '{hook_event_name: "Stop", stop_hook_active: $a}'; }

# Suite stubs: each one leaves a mark when it runs and fails if its red flag exists.
reset_marks() { rm -f "$SANDBOX"/.backend-ran "$SANDBOX"/.frontend-ran "$SANDBOX"/.backend-red "$SANDBOX"/.frontend-red; }
ran() { [[ -f "$SANDBOX/.$1-ran" ]] && echo yes || echo no; }
restore_tree() { git -C "$SANDBOX" checkout -q -- . && git -C "$SANDBOX" clean -qfd -e '.backend-*' -e '.frontend-*'; }

# ── Sandbox ──────────────────────────────────────────────────────────────────

S="$SANDBOX"
mkdir -p "$S/backend/app" "$S/backend/tests/unit" "$S/backend/migrations/versions" \
  "$S/backend/.venv/bin" "$S/docs/features/FEAT-003" "$S/frontend/src" "$S/frontend/node_modules/.bin"

printf 'def service() -> int:\n    return 1\n' > "$S/backend/app/service.py"
printf 'def test_a() -> None:\n    assert 1 == 1\n' > "$S/backend/tests/unit/test_service.py"
printf 'revision = "0001"\n' > "$S/backend/migrations/versions/0001_init.py"
printf '# FEAT-003\n\n- C1-01: un caso\n- **Aprobado por:** pendiente\n' > "$S/docs/features/FEAT-003/spec.md"
printf 'export const Page = () => null;\n' > "$S/frontend/src/Page.tsx"
printf 'it("renders", () => {});\n' > "$S/frontend/src/Page.test.tsx"
printf 'APP_ENV=local\n' > "$S/.env.example"
printf 'APP_ENV=local\n' > "$S/backend/app/constants.py"

cat > "$S/backend/.venv/bin/python" <<'STUB'
#!/bin/sh
touch "$CLAUDE_PROJECT_DIR/.backend-ran"
if [ -f "$CLAUDE_PROJECT_DIR/.backend-red" ]; then echo "FAILED tests/unit/test_service.py::test_a"; exit 1; fi
echo "1 passed"
STUB
cat > "$S/frontend/node_modules/.bin/vitest" <<'STUB'
#!/bin/sh
touch "$CLAUDE_PROJECT_DIR/.frontend-ran"
if [ -f "$CLAUDE_PROJECT_DIR/.frontend-red" ]; then echo "FAIL src/Page.test.tsx > renders"; exit 1; fi
echo "1 passed"
STUB
chmod +x "$S/backend/.venv/bin/python" "$S/frontend/node_modules/.bin/vitest"
printf '.backend-*\n.frontend-*\n.env\n.env.*\n!.env.example\n' > "$S/.gitignore"

git -C "$S" init -q
git -C "$S" -c user.name=test -c user.email=test@example.invalid add -A
git -C "$S" -c user.name=test -c user.email=test@example.invalid commit -q -m init

# ── Hook 1: block-secret-reads.sh ────────────────────────────────────────────

H=block-secret-reads.sh
expect "H1-1 .env"             deny  "$(decision $H "$(read_json "$S/.env")")"
expect "H1-1 backend/.env.local" deny "$(decision $H "$(read_json "$S/backend/.env.local")")"
expect "H1-2 .env.example"     allow "$(decision $H "$(read_json "$S/.env.example")")"
expect "H1-3 constants.py"     allow "$(decision $H "$(read_json "$S/backend/app/constants.py")")"

# ── Hook 2: protect-tests-and-specs.sh ───────────────────────────────────────

H=protect-tests-and-specs.sh
TEST_FILE="$S/backend/tests/unit/test_service.py"
SPEC_FILE="$S/docs/features/FEAT-003/spec.md"

expect "H2-1 new test file" allow \
  "$(decision $H "$(write_json "$S/backend/tests/unit/test_new.py" 'def test_new() -> None: ...')")"
expect "H2-2 append to an existing test" allow \
  "$(decision $H "$(edit_json "$TEST_FILE" '    assert 1 == 1
' '    assert 1 == 1


def test_b() -> None:
    assert 2 == 2
')")"
expect "H2-3 change an assertion" ask \
  "$(decision $H "$(edit_json "$TEST_FILE" 'assert 1 == 1' 'assert 1 == 2')")"
expect "H2-4 overwrite an existing test" ask \
  "$(decision $H "$(write_json "$TEST_FILE" 'def test_a() -> None: ...')")"
expect "H2-5 fill in the approval line" deny \
  "$(decision $H "$(edit_json "$SPEC_FILE" '- **Aprobado por:** pendiente' '- **Aprobado por:** Veronica Zacarias 19/11/2026')")"
expect "H2-6 add cases, approval still pending" allow \
  "$(decision $H "$(edit_json "$SPEC_FILE" '- **Aprobado por:** pendiente' '- C1-02: otro caso
- **Aprobado por:** pendiente')")"
expect "H2-7 edit a versioned migration" ask \
  "$(decision $H "$(edit_json "$S/backend/migrations/versions/0001_init.py" '"0001"' '"0001b"')")"
expect "H2-8 new migration" allow \
  "$(decision $H "$(write_json "$S/backend/migrations/versions/0002_more.py" 'revision = "0002"')")"
expect "H2-9 edit .env" deny \
  "$(decision $H "$(edit_json "$S/.env" 'A=1' 'A=2')")"
expect "H2-9 path with .." deny \
  "$(decision $H "$(write_json "$S/backend/../../outside.py" 'x = 1')")"

# ── Hook 3: verify-tests-on-stop.sh ──────────────────────────────────────────

H=verify-tests-on-stop.sh

reset_marks
expect "H3-1 clean tree" allow "$(decision $H "$(stop_json)")"
expect "H3-1 pytest did not run" no "$(ran backend)"
expect "H3-1 vitest did not run" no "$(ran frontend)"

reset_marks; restore_tree
printf '\n# changed\n' >> "$S/backend/app/service.py"
expect "H3-2 backend change, green" allow "$(decision $H "$(stop_json)")"
expect "H3-2 pytest ran" yes "$(ran backend)"

reset_marks; touch "$S/.backend-red"
expect "H3-3 backend change, red" block "$(decision $H "$(stop_json)")"

reset_marks; restore_tree; touch "$S/.backend-red"
printf '\ndef test_c() -> None:\n    assert False\n' >> "$TEST_FILE"
expect "H3-4 only backend tests changed, red" allow "$(decision $H "$(stop_json)")"

reset_marks; restore_tree; touch "$S/.backend-red"
printf '\n# changed\n' >> "$S/backend/app/service.py"
expect "H3-5 PLATITA_PERMITIR_ROJO=1" allow \
  "$(PLATITA_PERMITIR_ROJO=1 decision $H "$(stop_json)")"
expect "H3-5 pytest did not run" no "$(ran backend)"

reset_marks; touch "$S/.backend-red"
expect "H3-6 stop_hook_active" allow "$(decision $H "$(stop_json true)")"

reset_marks; restore_tree; touch "$S/.frontend-red"
printf '\n// changed\n' >> "$S/frontend/src/Page.tsx"
expect "H3-7 frontend change, red" block "$(decision $H "$(stop_json)")"

reset_marks; restore_tree; touch "$S/.frontend-red"
printf '\nit("fails", () => { throw new Error(); });\n' >> "$S/frontend/src/Page.test.tsx"
expect "H3-8 only frontend tests changed, red" allow "$(decision $H "$(stop_json)")"

reset_marks; restore_tree
printf '\n# changed\n' >> "$S/backend/app/service.py"
decision $H "$(stop_json)" >/dev/null
expect "H3-9 backend only: vitest did not run" no "$(ran frontend)"

reset_marks; restore_tree
printf '\n// changed\n' >> "$S/frontend/src/Page.tsx"
decision $H "$(stop_json)" >/dev/null
expect "H3-9 frontend only: pytest did not run" no "$(ran backend)"

reset_marks; restore_tree; touch "$S/.backend-red"
printf 'def helper() -> int:\n    return 2\n' > "$S/backend/app/new_module.py"
expect "H3-10 new file not yet added to git, red" block "$(decision $H "$(stop_json)")"
expect "H3-10 pytest ran" yes "$(ran backend)"

reset_marks; restore_tree

# ── Hook 4: block-dangerous-bash.sh ──────────────────────────────────────────

H=block-dangerous-bash.sh
expect "H4-1 rm -rf"              deny  "$(decision $H "$(bash_json 'rm -rf backend')")"
expect "H4-2 git push --force"    deny  "$(decision $H "$(bash_json 'git push --force')")"
expect "H4-2 git push -f"         deny  "$(decision $H "$(bash_json 'git push -f origin x')")"
expect "H4-3 commit --no-verify"  deny  "$(decision $H "$(bash_json 'git commit -m "x" --no-verify')")"
expect "H4-4 git commit"          ask   "$(decision $H "$(bash_json 'git commit -m "x"')")"
expect "H4-5 gh pr merge"         deny  "$(decision $H "$(bash_json 'gh pr merge 215')")"
expect "H4-6 evals --run"         ask   "$(decision $H "$(bash_json 'python -m evals.classification.run --run')")"
expect "H4-6 evals without --run" allow "$(decision $H "$(bash_json 'python -m evals.classification.run')")"
expect "H4-7 pip install pkg"     ask   "$(decision $H "$(bash_json 'pip install httpx')")"
expect "H4-7 pip install -r"      allow "$(decision $H "$(bash_json 'pip install -r requirements-dev.txt')")"
expect "H4-8 cat .env"            deny  "$(decision $H "$(bash_json 'cat .env')")"
expect "H4-9 git status"          allow "$(decision $H "$(bash_json 'git status')")"
expect "H4-9 pytest"              allow "$(decision $H "$(bash_json 'pytest')")"
expect "H4-9 ruff check"          allow "$(decision $H "$(bash_json 'ruff check .')")"

# ── Summary ──────────────────────────────────────────────────────────────────

echo ""
echo "test_assistant_hooks: $PASSED passed, $FAILED failed"
[[ $FAILED -eq 0 ]]
