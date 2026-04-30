#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

fail() {
  printf 'FAIL: %s\n' "$1" >&2
  exit 1
}

field() {
  local json="$1"
  local key="$2"
  printf '%s' "$json" | /usr/bin/python3 -c "import json,sys; print(json.load(sys.stdin)[\"$key\"])"
}

assert_eq() {
  local actual="$1"
  local expected="$2"
  local label="$3"
  if [ "$actual" != "$expected" ]; then
    fail "$label: expected '$expected', got '$actual'"
  fi
}

cd "$ROOT_DIR"

printf 'Running plugin smoke tests...\n'

# Static validation.
/usr/bin/python3 -m json.tool hooks/hooks.json >/dev/null
/usr/bin/python3 -m json.tool .claude-plugin/plugin.json >/dev/null
/usr/bin/python3 -m json.tool .claude-plugin/marketplace.json >/dev/null
/usr/bin/python3 -m py_compile web/notify_ui.py
bash -n \
  lib/notify-config.sh \
  hooks/scripts/notify.sh \
  adapters/claude/notify.sh \
  adapters/codex/notify.sh \
  adapters/codex/install.sh \
  adapters/opencode/notify.sh \
  adapters/opencode/install.sh \
  adapters/pi/notify.sh \
  adapters/pi/install.sh \
  tests/codex_notify_test.sh \
  tests/plugin_smoke_test.sh

if command -v claude >/dev/null 2>&1; then
  claude plugin validate . >/dev/null

  # Prove the marketplace can be registered and the Claude plugin installed
  # without mutating the user's real ~/.claude state.
  HOME="$TMP_DIR/home" claude plugin marketplace add "$ROOT_DIR" >/dev/null
  HOME="$TMP_DIR/home" claude plugin install --scope user claude-code-notify@agentic-coding-notify >/dev/null
fi

# Codex regression suite.
./tests/codex_notify_test.sh >/dev/null

# Hook dispatch smoke tests. NOTIFY_TEST_MODE prevents real notifications.
claude_output="$(
  printf '%s' '{"message":"Claude hook","title":"Claude Code"}' |
    env NOTIFY_TEST_MODE=1 \
      CLAUDE_NOTIFY_LOG="$TMP_DIR/claude.log" \
      CLAUDE_CODE_ENTRYPOINT=claude-desktop \
      bash hooks/scripts/notify.sh
)"
assert_eq "$(field "$claude_output" label)" "App" "Claude hook label"
assert_eq "$(field "$claude_output" voice_label)" "Claude Code App" "Claude hook voice"

codex_output="$(
  env NOTIFY_TEST_MODE=1 \
    CODEX_NOTIFY_LOG="$TMP_DIR/codex.log" \
    CODEX_NOTIFY_COOLDOWN_FILE="$TMP_DIR/codex-cooldown.json" \
    CODEX_NOTIFY_PARENT_PROCESS_TREE='/usr/bin/zsh' \
    CODEX_DESKTOP=1 \
    bash hooks/scripts/notify.sh \
    '{"type":"agent-turn-complete","cwd":"/tmp/proj","last-assistant-message":"Hook Codex"}'
)"
assert_eq "$(field "$codex_output" label)" "Codex App" "Codex hook label"
assert_eq "$(field "$codex_output" voice_label)" "Codex App terminou" "Codex hook voice"

cat >"$TMP_DIR/no-tab-title-config.json" <<'JSON'
{
  "voice": "Zarvox",
  "rate": "250",
  "notification_sound": "Submarine",
  "start_sound": "Basso",
  "end_sound": "Submarine",
  "app_voice_text_template": "{service} App",
  "cli_voice_text_template": "{service} {label}",
  "voice_text_template": "",
  "speak_tab_title": "false"
}
JSON
codex_no_tab_output="$(
  env NOTIFY_TEST_MODE=1 \
    AGENTIC_CODING_NOTIFY_CONFIG="$TMP_DIR/no-tab-title-config.json" \
    CODEX_NOTIFY_LOG="$TMP_DIR/codex-no-tab.log" \
    CODEX_NOTIFY_COOLDOWN_FILE="$TMP_DIR/codex-no-tab-cooldown.json" \
    CODEX_NOTIFY_PARENT_PROCESS_TREE='/usr/bin/zsh' \
    bash adapters/codex/notify.sh \
    '{"type":"agent-turn-complete","cwd":"/tmp/review","last-assistant-message":"done"}'
)"
assert_eq "$(field "$codex_no_tab_output" voice_text)" "Codex" "Codex no-tab voice text"

opencode_output="$(
  env NOTIFY_TEST_MODE=1 \
    OPENCODE_NOTIFY_LOG="$TMP_DIR/opencode.log" \
    OPENCODE_NOTIFY_COOLDOWN_FILE="$TMP_DIR/opencode-cooldown.json" \
    OPENCODE_NOTIFY_PARENT_PROCESS_TREE='/usr/bin/zsh' \
    OPENCODE=1 \
    bash hooks/scripts/notify.sh \
    '{"type":"agent-turn-complete","cwd":"/tmp/proj","message":"AUTH_NEEDED: login"}'
)"
assert_eq "$(field "$opencode_output" subtitle)" "Autorizacao necessaria" "OpenCode hook subtitle"
assert_eq "$(field "$opencode_output" message)" "login" "OpenCode hook message"

pi_output="$(
  env NOTIFY_TEST_MODE=1 \
    PI_NOTIFY_LOG="$TMP_DIR/pi.log" \
    PI_NOTIFY_COOLDOWN_FILE="$TMP_DIR/pi-cooldown.json" \
    PI_NOTIFY_PARENT_PROCESS_TREE='/usr/bin/zsh' \
    PI_IS_COWORK=1 \
    bash hooks/scripts/notify.sh \
    '{"type":"agent-turn-complete","cwd":"/tmp/proj","message":"READY_FOR_REVIEW: pronto"}'
)"
assert_eq "$(field "$pi_output" label)" "Cowork" "Pi hook label"
assert_eq "$(field "$pi_output" voice_label)" "Pi Cowork App" "Pi hook voice"

# Noise events are intentionally silent for Pi/OpenCode.
opencode_noise="$(
  env NOTIFY_TEST_MODE=1 \
    OPENCODE_NOTIFY_LOG="$TMP_DIR/opencode-noise.log" \
    OPENCODE_NOTIFY_COOLDOWN_FILE="$TMP_DIR/opencode-noise-cooldown.json" \
    OPENCODE_NOTIFY_PARENT_PROCESS_TREE='/usr/bin/zsh' \
    bash adapters/opencode/notify.sh \
    '{"type":"agent-turn-complete","cwd":"/tmp/proj","message":"normal noise"}'
)"
[ -z "$opencode_noise" ] || fail "OpenCode noise should be silent"

pi_noise="$(
  env NOTIFY_TEST_MODE=1 \
    PI_NOTIFY_LOG="$TMP_DIR/pi-noise.log" \
    PI_NOTIFY_COOLDOWN_FILE="$TMP_DIR/pi-noise-cooldown.json" \
    PI_NOTIFY_PARENT_PROCESS_TREE='/usr/bin/zsh' \
    bash adapters/pi/notify.sh \
    '{"type":"agent-turn-complete","cwd":"/tmp/proj","message":"normal noise"}'
)"
[ -z "$pi_noise" ] || fail "Pi noise should be silent"

# Installer smoke tests, scoped to temp paths.
bash adapters/codex/install.sh --print-config "$TMP_DIR/codex-notify.sh" |
  grep -Fqx "notify = [\"$TMP_DIR/codex-notify.sh\"]"
bash adapters/codex/install.sh --install-script "$TMP_DIR/codex-notify.sh" >/dev/null
[ -x "$TMP_DIR/codex-notify.sh" ] || fail "Codex installer did not create executable"
[ -x "$TMP_DIR/notify-config.sh" ] || fail "Codex installer did not copy config helper"

PI_PLUGIN_ROOT="$TMP_DIR/pi-root" bash adapters/pi/install.sh >/dev/null
[ -x "$TMP_DIR/pi-root/adapters/pi/notify.sh" ] || fail "Pi installer did not create executable"
[ -x "$TMP_DIR/pi-root/adapters/pi/notify-config.sh" ] || fail "Pi installer did not copy config helper"

OPENCODE_PLUGIN_ROOT="$TMP_DIR/opencode-root" bash adapters/opencode/install.sh >/dev/null
[ -x "$TMP_DIR/opencode-root/adapters/opencode/notify.sh" ] || fail "OpenCode installer did not create executable"
[ -x "$TMP_DIR/opencode-root/adapters/opencode/notify-config.sh" ] || fail "OpenCode installer did not copy config helper"

# Local web UI API smoke test.
AGENTIC_CODING_NOTIFY_CONFIG="$TMP_DIR/ui-config.json" /usr/bin/python3 web/notify_ui.py --port 18765 >"$TMP_DIR/ui.log" 2>&1 &
ui_pid=$!
for _ in 1 2 3 4 5; do
  if /usr/bin/python3 - <<'PY' >/dev/null 2>&1
import urllib.request
urllib.request.urlopen("http://127.0.0.1:18765/api/config", timeout=1).read()
PY
  then
    break
  fi
  sleep 0.5
done
/usr/bin/python3 - <<'PY'
import json
import urllib.request

def request(path, payload=None):
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(
        f"http://127.0.0.1:18765{path}",
        data=data,
        headers={"content-type": "application/json"},
        method="POST" if payload is not None else "GET",
    )
    return json.loads(urllib.request.urlopen(req, timeout=3).read())

html = urllib.request.urlopen("http://127.0.0.1:18765/", timeout=3).read().decode()
assert "Disclosure" not in html
assert "Terminal label disclosure" in html
assert "JetBrains Mono" in html
assert "Apps do not need terminal labels" in html
assert "color-scheme: light" in html
assert "N64 gray palette" in html
assert "READY" in html
assert "Stop all" in html
assert "Export Config" in html
assert "agentic-coding-notify-config.json" in html
assert "toast-panel" in html
assert "button-label" in html
assert html.count("data-tooltip=") >= 10
assert "Run the selected adapter in NOTIFY_TEST_MODE" in html
assert "Run full notification preview" in html
assert "notification sound, start sound, spoken text, and end sound" in html
assert "preview-grid" in html
assert "Agentic Coding Notify" in html
assert "Speak terminal tab title" in html
assert "speak_tab_title" in html
assert 'data-combo="voices"' in html
assert 'data-combo="sounds"' in html
assert 'data-combo="services"' in html
assert 'data-combo="templates"' in html
assert 'class="combo-list" role="listbox"' in html
assert "Show off one-by-one" in html
assert "Stop show-off" in html
assert "SHOW OFF SELECTION" in html
assert "Selecting: pick values" in html
assert "Cycle selected" in html
assert "Stop selected cycle" in html
assert "Clear show-off selection" in html
assert 'role="combobox"' not in html  # set by JS after load
config = request("/api/config")
assert config["voice"] == "Zarvox"
assert config["speak_tab_title"] == "true"
saved = request("/api/config", config)
assert saved["ok"] is True
result = request("/api/test", {
    "config": config,
    "service": "Codex App",
    "label": "review",
    "message": "smoke",
    "dry_run": True,
})
assert result["ok"] is True, result
assert "Codex App" in result["stdout"], result
no_tab = dict(config)
no_tab["speak_tab_title"] = "false"
result = request("/api/test", {
    "config": no_tab,
    "service": "Codex CLI",
    "label": "review",
    "message": "smoke",
    "dry_run": True,
})
assert result["ok"] is True, result
payload = json.loads(result["stdout"])
assert payload["voice_text"] == "Codex", payload
play = request("/api/play-sound", {"field": "notification_sound", "sound": "Basso"})
assert play["ok"] is True, play
stop = request("/api/stop-sound", {"field": "notification_sound"})
assert stop["ok"] is True, stop
voice = request("/api/play-voice", {"field": "voice", "voice": "Zarvox", "rate": "250", "text": "Agentic Coding Notify"})
assert voice["ok"] is True, voice
assert voice["text"] == "Agentic Coding Notify", voice
stop_voice = request("/api/stop-voice", {"field": "voice"})
assert stop_voice["ok"] is True, stop_voice
PY
kill "$ui_pid" 2>/dev/null || true
wait "$ui_pid" 2>/dev/null || true

printf 'PASS: plugin smoke tests\n'
