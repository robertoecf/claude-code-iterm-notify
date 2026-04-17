#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT_PATH="$ROOT_DIR/adapters/codex/notify.sh"
INSTALLER_PATH="$ROOT_DIR/adapters/codex/install.sh"

TMP_COOLDOWN="$(mktemp -t codex-notify-test.XXXXXX.json)"
trap 'rm -f "$TMP_COOLDOWN"' EXIT

fail() {
  printf 'FAIL: %s\n' "$1" >&2
  exit 1
}

assert_eq() {
  local actual="$1"
  local expected="$2"
  local label="$3"
  if [ "$actual" != "$expected" ]; then
    fail "$label: expected '$expected', got '$actual'"
  fi
}

field() {
  local json="$1"
  local key="$2"
  printf '%s' "$json" | /usr/bin/python3 -c "import json,sys; print(json.load(sys.stdin)[\"$key\"])"
}

run_case() {
  # Each case gets a fresh cooldown file so suppression doesn't leak between tests.
  : > "$TMP_COOLDOWN"
  rm -f "$TMP_COOLDOWN"
  local payload="$1"
  shift
  env NOTIFY_TEST_MODE=1 CODEX_NOTIFY_COOLDOWN_FILE="$TMP_COOLDOWN" "$@" "$SCRIPT_PATH" "$payload"
}

printf 'Running Codex notify adapter tests...\n'

if [ ! -x "$SCRIPT_PATH" ]; then
  fail "missing executable Codex adapter at $SCRIPT_PATH"
fi

if [ ! -x "$INSTALLER_PATH" ]; then
  fail "missing executable Codex installer at $INSTALLER_PATH"
fi

# 1) Standard agent-turn-complete with a short message — full text used as preview.
short_output="$(
  run_case \
    '{"type":"agent-turn-complete","cwd":"/tmp/wealthuman","last-assistant-message":"painel pronto","title":"Codex"}' \
    TERM_PROGRAM=Ghostty
)"
assert_eq "$(field "$short_output" subtitle)"    "Turno concluído"   "short subtitle"
assert_eq "$(field "$short_output" message)"     "painel pronto"     "short message"
assert_eq "$(field "$short_output" label)"       "Ghostty"           "short label"
assert_eq "$(field "$short_output" voice_label)" "Codex terminou em Ghostty" "short voice"

# 2) Long assistant message gets truncated (not read verbatim).
long_msg="$(printf 'lorem ipsum %.0s' $(seq 1 80))"
long_output="$(
  run_case \
    "{\"type\":\"agent-turn-complete\",\"cwd\":\"/tmp/wealthuman\",\"last-assistant-message\":\"$long_msg\"}" \
    TERM_PROGRAM=Apple_Terminal
)"
preview="$(field "$long_output" message)"
if [ "${#preview}" -ge "${#long_msg}" ]; then
  fail "long message preview not truncated (len=${#preview})"
fi
case "$preview" in
  *…) ;;
  *) fail "long preview missing ellipsis: $preview" ;;
esac
assert_eq "$(field "$long_output" label)" "Terminal.app" "long label"

# 3) Voice is constant regardless of assistant content — never reads the response.
assert_eq "$(field "$long_output" voice_label)" "Codex terminou em Terminal.app" "long voice"

# 4) Codex App process tree produces the "no app" voice.
app_output="$(
  env -u TERM_PROGRAM \
    NOTIFY_TEST_MODE=1 \
    CODEX_NOTIFY_COOLDOWN_FILE="$TMP_COOLDOWN" \
    CODEX_NOTIFY_PARENT_PROCESS_TREE="/Applications/Codex.app/Contents/MacOS/Codex" \
    "$SCRIPT_PATH" \
    '{"type":"agent-turn-complete","cwd":"/tmp/wealthuman-os","last-assistant-message":"qualquer coisa"}'
)"
assert_eq "$(field "$app_output" label)"       "Codex App"          "app label"
assert_eq "$(field "$app_output" voice_label)" "Codex terminou no app" "app voice"

# 5) cwd fallback when no TERM_PROGRAM and no Codex App.
: > "$TMP_COOLDOWN"
rm -f "$TMP_COOLDOWN"
fallback_output="$(
  env -u TERM_PROGRAM \
    NOTIFY_TEST_MODE=1 \
    CODEX_NOTIFY_COOLDOWN_FILE="$TMP_COOLDOWN" \
    "$SCRIPT_PATH" \
    '{"type":"agent-turn-complete","cwd":"/tmp/wealthuman-os","last-assistant-message":"deploy concluido"}'
)"
assert_eq "$(field "$fallback_output" label)"       "wealthuman-os"              "fallback label"
assert_eq "$(field "$fallback_output" voice_label)" "Codex terminou em wealthuman-os" "fallback voice"

# 6) Short label (<4 chars) falls back to plain "Codex terminou".
: > "$TMP_COOLDOWN"
rm -f "$TMP_COOLDOWN"
short_label_output="$(
  env -u TERM_PROGRAM \
    NOTIFY_TEST_MODE=1 \
    CODEX_NOTIFY_COOLDOWN_FILE="$TMP_COOLDOWN" \
    "$SCRIPT_PATH" \
    '{"type":"agent-turn-complete","cwd":"/tmp/lc","last-assistant-message":"x"}'
)"
assert_eq "$(field "$short_label_output" voice_label)" "Codex terminou" "short label voice"

# 7) Cowork env triggers the Cowork voice.
: > "$TMP_COOLDOWN"
rm -f "$TMP_COOLDOWN"
cowork_output="$(
  env -u TERM_PROGRAM \
    NOTIFY_TEST_MODE=1 \
    CODEX_IS_COWORK=1 \
    CODEX_NOTIFY_COOLDOWN_FILE="$TMP_COOLDOWN" \
    "$SCRIPT_PATH" \
    '{"type":"agent-turn-complete","cwd":"/tmp/cw","last-assistant-message":"ok"}'
)"
assert_eq "$(field "$cowork_output" label)"       "Cowork"                   "cowork label"
assert_eq "$(field "$cowork_output" voice_label)" "Codex terminou no Cowork" "cowork voice"

# 8) Installer prints the expected notify line.
config_output="$("$INSTALLER_PATH" --print-config "/tmp/codex-notify.sh")"
expected_line='notify = ["/tmp/codex-notify.sh"]'
if ! printf '%s\n' "$config_output" | grep -Fqx "$expected_line"; then
  fail "installer config output missing notify line"
fi

# 9) Unsupported future event types are skipped cleanly (no stdout in test mode).
: > "$TMP_COOLDOWN"
rm -f "$TMP_COOLDOWN"
skip_output="$(
  env NOTIFY_TEST_MODE=1 CODEX_NOTIFY_COOLDOWN_FILE="$TMP_COOLDOWN" \
    "$SCRIPT_PATH" \
    '{"type":"some-future-event","cwd":"/tmp/x","last-assistant-message":"ignored"}' || true
)"
if [ -n "$skip_output" ]; then
  fail "unsupported event should produce no test output, got: $skip_output"
fi

printf 'PASS: Codex notify adapter tests\n'
