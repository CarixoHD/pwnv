#!/usr/bin/env bash
# End-to-end check of the installed `pwnv` command.
# Usage: scripts/smoke.sh [python-version]
set -euo pipefail

PYTHON_VERSION="${1:-3.13}"
WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT

FAILURES=0

step() { printf '\n\033[1;35m==> %s\033[0m\n' "$1"; }
ok() { printf '  \033[32mok\033[0m %s\n' "$1"; }
fail() {
  printf '  \033[31mFAIL\033[0m %s\n' "$1"
  FAILURES=$((FAILURES + 1))
}

exists() {
  if [ -e "$1" ]; then
    ok "$2"
  else
    fail "$2 (missing $1)"
  fi
}

# The document is an argument: piping into the function would run it in a subshell and drop FAILURES.
expect_json() {
  local description="$1" expression="$2" document="$3"
  if printf '%s' "$document" |
    python3 -c "import json,sys; d=json.load(sys.stdin); sys.exit(0 if ($expression) else 1)"; then
    ok "$description"
  else
    fail "$description"
    printf '%s\n' "$document" | head -20
  fi
}

step "installed distribution"
command -v pwnv
python3 -c "from importlib.metadata import version; print('pwnv', version('pwnv'))"
pwnv --help >/dev/null

# --- First machine -----------------------------------------------------------

export PWNV_CONFIG="$WORKDIR/old/pwnv_config.json"
CTFS="$WORKDIR/old/CTFs"

step "init"
pwnv init --yes --no-install --python "$PYTHON_VERSION" --ctfs-folder "$CTFS"

exists "$PWNV_CONFIG" "config written"
exists "$CTFS/.pwnvenv" "CTF environment created"
exists "$WORKDIR/old/templates" "templates folder created"
if compgen -G "$WORKDIR/old/templates/*" >/dev/null; then
  ok "bundled templates installed from package data"
else
  fail "bundled templates installed from package data"
fi
if compgen -G "$WORKDIR/old/plugins/*" >/dev/null; then
  ok "bundled plugins installed from package data"
else
  fail "bundled plugins installed from package data"
fi

expect_failure() {
  local description="$1"
  shift
  local output status=0
  output="$("$@" 2>&1)" || status=$?
  if [ "$status" -eq 0 ]; then
    fail "$description (exited 0)"
    printf '%s\n' "$output" | head -5
  else
    ok "$description"
  fi
}

step "ctf add / challenge add"
pwnv ctf add smoke --local
pwnv challenge add babyrop --ctf smoke --category pwn

expect_failure "adding the same CTF twice fails" pwnv ctf add smoke --local
expect_failure "an unknown platform is rejected" \
  pwnv ctf add other --url https://ctf.invalid --platform notaplatform

challenge_path() {
  pwnv challenge info --challenge babyrop --json |
    python3 -c 'import json,sys; print(json.load(sys.stdin)["challenges"][0]["path"])'
}

CHALLENGE_DIR="$(challenge_path)"
exists "$CHALLENGE_DIR" "challenge directory created"
exists "$CHALLENGE_DIR/solve.py" "solve script scaffolded"

step "solve"
pwnv solve --challenge babyrop --flag "flag{smoke}" --tags smoke

step "json output"
STATUS_JSON="$(pwnv status --json)"
expect_json "status reports the CTF as solved" \
  'd["ctfs"][0]["challenges"] == 1 and d["ctfs"][0]["solved"] == 1' \
  "$STATUS_JSON"

CHALLENGE_JSON="$(pwnv challenge info --challenge babyrop --json)"
expect_json "challenge info carries the flag and tags" \
  'd["challenges"][0]["flag"] == "flag{smoke}" and "smoke" in d["challenges"][0]["tags"]' \
  "$CHALLENGE_JSON"

step "the challenge object"
if (
  cd "$CHALLENGE_DIR"
  python3 -c '
from pwnv import challenge

assert challenge.name == "babyrop", challenge.name
assert challenge.category == "pwn", challenge.category
assert challenge.flag == "flag{smoke}", challenge.flag
print("  resolved", challenge.name, "at", challenge.path)
'
); then
  ok "from pwnv import challenge resolves in place"
else
  fail "from pwnv import challenge resolves in place"
fi

step "backup"
printf 'notes from the old machine\n' >"$CHALLENGE_DIR/NOTES.md"
pwnv workspace backup "$WORKDIR/move"
exists "$WORKDIR/move.tar.gz" "archive written"

# --- Second machine ----------------------------------------------------------

step "restore onto a fresh machine"
export PWNV_CONFIG="$WORKDIR/new/pwnv_config.json"
NEW_CTFS="$WORKDIR/new/CTFs"

pwnv init --yes --no-install --no-examples --python "$PYTHON_VERSION" \
  --ctfs-folder "$NEW_CTFS"
pwnv workspace restore "$WORKDIR/move.tar.gz"

STATUS_JSON="$(pwnv status --json)"
expect_json "restored workspace kept the CTF, the challenge and the flag" \
  'len(d["ctfs"]) == 1 and d["ctfs"][0]["challenges"] == 1 and d["ctfs"][0]["solved"] == 1' \
  "$STATUS_JSON"

NEW_DIR="$(challenge_path)"
case "$NEW_DIR" in
"$NEW_CTFS"/*) ok "challenge rebased onto the new CTF root" ;;
*) fail "challenge rebased onto the new CTF root (got $NEW_DIR)" ;;
esac
exists "$NEW_DIR/NOTES.md" "notes travelled with the archive"
exists "$NEW_DIR/solve.py" "solve script travelled with the archive"

pwnv workspace restore "$WORKDIR/move.tar.gz" >/dev/null
STATUS_JSON="$(pwnv status --json)"
expect_json "restoring twice is a no-op" \
  'len(d["ctfs"]) == 1 and d["ctfs"][0]["challenges"] == 1' \
  "$STATUS_JSON"

step "result"
if [ "$FAILURES" -eq 0 ]; then
  printf '\033[32mSmoke test passed.\033[0m\n'
else
  printf '\033[31m%s check(s) failed.\033[0m\n' "$FAILURES"
  exit 1
fi
