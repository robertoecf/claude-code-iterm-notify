#!/bin/bash
# Codex `notify` hook adapter.
#
# Codex invokes this script (configured as `notify = [...]` in ~/.codex/config.toml)
# ONLY for the `agent-turn-complete` event. There is no approval/input event on
# this channel today — see https://github.com/openai/codex/issues/11808.
#
# So this script does one thing: when Codex finishes a turn, emit a short voice
# announcement "Codex terminou em <label>" plus a desktop notification with a
# truncated preview of the last assistant message. It does NOT read the full
# response aloud.
#
# For approval/input alerts:
#   - Codex macOS App: enable approval notifications in the app preferences.
#   - Codex CLI (TUI):   add to ~/.codex/config.toml:
#       [tui]
#       notifications = ["agent-turn-complete", "approval-requested"]
#       notification_method = "osc9"
#     The terminal (iTerm2, Ghostty, …) then shows native desktop notifications
#     for approval requests directly.
set -euo pipefail

LOG="${CODEX_NOTIFY_LOG:-/tmp/codex-notify-debug.log}"
SAFE_CWD="${CODEX_NOTIFY_SAFE_CWD:-${TMPDIR:-/tmp}}"
COOLDOWN_FILE="${CODEX_NOTIFY_COOLDOWN_FILE:-/tmp/codex-notify-last.json}"
COOLDOWN_SECONDS="${CODEX_NOTIFY_COOLDOWN_SECONDS:-30}"
MESSAGE_PREVIEW_CHARS="${CODEX_NOTIFY_PREVIEW_CHARS:-160}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
if [ -f "$ROOT_DIR/lib/notify-config.sh" ]; then
  # shellcheck source=/dev/null
  . "$ROOT_DIR/lib/notify-config.sh"
elif [ -f "$SCRIPT_DIR/notify-config.sh" ]; then
  # Installed adapter copy.
  # shellcheck source=/dev/null
  . "$SCRIPT_DIR/notify-config.sh"
else
  echo "Missing notify-config.sh" >&2
  exit 1
fi

safe_python3() {
  (
    cd "$SAFE_CWD" 2>/dev/null || cd /tmp
    /usr/bin/python3 "$@"
  )
}

collect_parent_process_tree() {
  if [ -n "${CODEX_NOTIFY_PARENT_PROCESS_TREE:-}" ]; then
    printf '%s' "$CODEX_NOTIFY_PARENT_PROCESS_TREE"
    return 0
  fi

  local pid="$$"
  local depth=0
  local tree=""
  local command=""
  local parent=""

  while [ -n "$pid" ] && [ "$pid" -gt 1 ] 2>/dev/null && [ "$depth" -lt 12 ]; do
    command="$(ps -o command= -p "$pid" 2>/dev/null | sed 's/^ *//')"
    if [ -n "$command" ]; then
      if [ -n "$tree" ]; then
        tree="$tree\n$command"
      else
        tree="$command"
      fi
    fi

    parent="$(ps -o ppid= -p "$pid" 2>/dev/null | tr -d ' ')"
    if [ -z "$parent" ] || [ "$parent" = "$pid" ]; then
      break
    fi

    pid="$parent"
    depth=$((depth + 1))
  done

  printf '%b' "$tree"
}

read_payload() {
  if [ "$#" -gt 0 ] && [ -n "${1:-}" ]; then
    printf '%s' "$1"
  else
    cat 2>/dev/null || true
  fi
}

payload="$(read_payload "$@")"
parent_process_tree="$(collect_parent_process_tree)"

parsed="$(
  PAYLOAD="$payload" \
  TERM_PROGRAM_VALUE="${TERM_PROGRAM:-}" \
  ITERM_SESSION_VALUE="${ITERM_SESSION_ID:-}" \
  CODEX_IS_COWORK_VALUE="${CODEX_IS_COWORK:-}" \
  CODEX_DESKTOP_VALUE="${CODEX_DESKTOP:-}" \
  CLAUDE_CODE_IS_COWORK_VALUE="${CLAUDE_CODE_IS_COWORK:-}" \
  PARENT_PROCESS_TREE="$parent_process_tree" \
  PREVIEW_CHARS="$MESSAGE_PREVIEW_CHARS" \
  safe_python3 - <<'PY'
import json
import os
from pathlib import Path

payload = os.environ.get("PAYLOAD", "").strip()
term_program = os.environ.get("TERM_PROGRAM_VALUE", "").strip()
iterm_session = os.environ.get("ITERM_SESSION_VALUE", "").strip()
parent_process_tree = os.environ.get("PARENT_PROCESS_TREE", "")
codex_is_cowork = os.environ.get("CODEX_IS_COWORK_VALUE", "")
codex_desktop = os.environ.get("CODEX_DESKTOP_VALUE", "")
claude_code_is_cowork = os.environ.get("CLAUDE_CODE_IS_COWORK_VALUE", "")
try:
    preview_chars = max(40, int(os.environ.get("PREVIEW_CHARS", "160")))
except ValueError:
    preview_chars = 160

# Per https://developers.openai.com/codex/config-advanced, Codex passes a JSON
# argument with these documented fields:
#   type (always "agent-turn-complete" today), thread-id, turn-id, cwd,
#   input-messages, last-assistant-message
event_type = "agent-turn-complete"
cwd = ""
assistant_msg = ""

try:
    data = json.loads(payload) if payload else {}
except Exception:
    data = {}
    assistant_msg = payload

if isinstance(data, dict):
    event_type = str(data.get("type") or "agent-turn-complete").strip() or "agent-turn-complete"
    cwd = str(data.get("cwd") or "").strip()
    for key in ("last-assistant-message", "last_assistant_message"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            assistant_msg = value.strip()
            break
elif isinstance(data, str) and data.strip():
    assistant_msg = data.strip()


def truncate(text: str, limit: int) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0]
    return (cut or text[:limit]).rstrip() + "…"


def is_codex_app_process_tree(tree: str) -> bool:
    haystack = tree.lower()
    return (
        "/applications/codex.app/contents/macos/codex" in haystack
        or "/applications/codex.app/contents/resources/codex app-server" in haystack
        or "com.openai.codex" in haystack
    )


def normalized_term_program(value: str) -> str:
    normalized = value.strip()
    lookup = normalized.lower()
    if not lookup:
        return ""
    if lookup == "ghostty":
        return "Ghostty"
    if lookup in {"iterm.app", "iterm2"}:
        return "iTerm2"
    if lookup in {"apple_terminal", "terminal", "terminal.app"}:
        return "Terminal.app"
    if lookup in {"vscode", "visual studio code"}:
        return "VS Code"
    return normalized


def fallback_label() -> str:
    if codex_desktop == "1":
        return "Codex App"
    if is_codex_app_process_tree(parent_process_tree):
        return "Codex App"
    normalized_term = normalized_term_program(term_program)
    if normalized_term:
        return normalized_term
    if cwd:
        return Path(cwd).name or "Codex"
    return "Codex"


is_cowork = codex_is_cowork == "1" or claude_code_is_cowork == "1"
label = fallback_label()
if is_cowork:
    label = "Cowork"
if iterm_session:
    label = "__ITERM__"

message_preview = truncate(assistant_msg, preview_chars) if assistant_msg else "Codex concluiu um turno."
subtitle = "Turno concluído"

print(
    json.dumps(
        {
            "title": "Codex",
            "subtitle": subtitle,
            "message": message_preview,
            "full_msg": assistant_msg,
            "label": label,
            "event_type": event_type,
            "cwd": cwd,
        }
    )
)
PY
)"

# Extract all fields in a single python3 call (instead of 6 separate forks).
eval "$(PARSED_JSON="$parsed" safe_python3 - <<'EXTRACT'
import json, os, shlex
d = json.loads(os.environ["PARSED_JSON"])
mapping = [
    ("title", "title"), ("subtitle", "subtitle"), ("message", "message"),
    ("full_msg", "full_msg"), ("label", "label"), ("event_type", "event_type"),
    ("cwd_value", "cwd"),
]
for shell_name, json_key in mapping:
    val = shlex.quote(d.get(json_key, ""))
    print("%s=%s" % (shell_name, val))
EXTRACT
)"

# Ignore events we don't handle today. `agent-turn-complete` is the only one
# Codex emits right now, but guard against future additions.
if [ "$event_type" != "agent-turn-complete" ]; then
  echo "$(date '+%Y-%m-%d %H:%M:%S') | SKIP unsupported event=$event_type" >> "$LOG"
  exit 0
fi

# Resolve iTerm2 profile name when we have a session id.
if [ "$label" = "__ITERM__" ]; then
  session_guid="$(echo "${ITERM_SESSION_ID:-}" | cut -d: -f2)"
  resolved="$(
    osascript <<EOF 2>/dev/null
tell application "iTerm2"
  repeat with w in windows
    repeat with t in tabs of w
      repeat with s in sessions of t
        if unique ID of s contains "$session_guid" then
          return profile name of s
        end if
      end repeat
    end repeat
  end repeat
end tell
EOF
  )" || true

  if [ -n "$resolved" ]; then
    label="$resolved"
  elif [ -n "${TERM_PROGRAM:-}" ]; then
    case "${TERM_PROGRAM}" in
      ghostty|Ghostty) label="Ghostty" ;;
      iTerm.app|iTerm2) label="iTerm2" ;;
      Apple_Terminal|Terminal|Terminal.app) label="Terminal.app" ;;
      vscode|"Visual Studio Code") label="VS Code" ;;
      *) label="$TERM_PROGRAM" ;;
    esac
  elif [ -n "$cwd_value" ]; then
    label="$(basename "$cwd_value")"
  else
    label="Codex"
  fi
fi

# Short, fixed voice message. We do NOT read the assistant response aloud —
# that was the source of noise. The user can glance at the desktop
# notification or the terminal/app for the actual content.
case "$label" in
  "Codex App") voice_label="Codex App terminou" ;;
  "Cowork")    voice_label="Codex terminou no Cowork" ;;
  *)
    if [ ${#label} -lt 4 ] && [ "$label" != "App" ]; then
      voice_label="Codex terminou"
    else
      voice_label="Codex terminou em $label"
    fi
    ;;
esac

# Cooldown: suppress identical events within the window. Keyed on
# (label, full_assistant_msg) — NOT the truncated preview — so two distinct
# long messages that share the same first 160 chars are still distinguishable.
#
# Sliding-window semantics: the timestamp is always refreshed, even when
# suppressed. This means a steady stream of identical events keeps extending
# the suppression. That is intentional: if Codex fires the same turn-complete
# ten times in a row, the user only needs one notification. A new *distinct*
# message resets the window immediately.
# Hash the key so the full assistant message is never persisted to disk.
cooldown_key="$(printf '%s' "${label}::${full_msg}" | shasum -a 256 | cut -d' ' -f1)"
export _COOLDOWN_FILE="$COOLDOWN_FILE"
export _COOLDOWN_KEY="$cooldown_key"
export _COOLDOWN_WINDOW="$COOLDOWN_SECONDS"
if ! safe_python3 - <<'PY'
import json, os, sys, time

path = os.environ["_COOLDOWN_FILE"]
key = os.environ["_COOLDOWN_KEY"]
window = int(os.environ["_COOLDOWN_WINDOW"])
now = int(time.time())

# Check existing state.
suppressed = False
try:
    with open(path) as f:
        data = json.load(f)
    if data.get("key") == key and now - int(data.get("timestamp", 0)) < window:
        suppressed = True
except Exception:
    pass

# Always persist current state so rapid retries stay suppressed.
with open(path, "w") as f:
    json.dump({"key": key, "timestamp": now}, f)

sys.exit(1 if suppressed else 0)
PY
then
  echo "$(date '+%Y-%m-%d %H:%M:%S') | COOLDOWN skip label=$label" >> "$LOG"
  should_notify=false
else
  should_notify=true
fi

printf '%s | event=%s | label=%s | voice=%s | preview=%s\n' \
  "$(date '+%Y-%m-%d %H:%M:%S')" "$event_type" "$label" "$voice_label" "$message" >> "$LOG"

notification_sound="$(notify_notification_sound Submarine)"
voice_text="$(notify_effective_voice_text "Codex" "$label" "$voice_label" "$message")"
voice_name="$(notify_voice_name Samantha)"
voice_rate="$(notify_voice_rate 300)"
start_sound="$(notify_start_sound_path /System/Library/Sounds/Basso.aiff)"
end_sound="$(notify_end_sound_path /System/Library/Sounds/Submarine.aiff)"

if [ "${NOTIFY_TEST_MODE:-0}" = "1" ]; then
  TITLE="$title" SUBTITLE="$subtitle" MESSAGE="$message" LABEL="$label" VOICE_LABEL="$voice_label" EVENT_TYPE="$event_type" VOICE_TEXT="$voice_text" VOICE="$voice_name" RATE="$voice_rate" NOTIFICATION_SOUND="$notification_sound" START_SOUND="$start_sound" END_SOUND="$end_sound" safe_python3 - <<'PY'
import json, os
print(
    json.dumps(
        {
            "title": os.environ["TITLE"],
            "subtitle": os.environ["SUBTITLE"],
            "message": os.environ["MESSAGE"],
            "label": os.environ["LABEL"],
            "voice_label": os.environ["VOICE_LABEL"],
            "event_type": os.environ["EVENT_TYPE"],
            "voice_text": os.environ["VOICE_TEXT"],
            "voice": os.environ["VOICE"],
            "rate": os.environ["RATE"],
            "notification_sound": os.environ["NOTIFICATION_SOUND"],
            "start_sound": os.environ["START_SOUND"],
            "end_sound": os.environ["END_SOUND"],
        }
    )
)
PY
  exit 0
fi

if [ "$should_notify" = "false" ]; then
  exit 0
fi

if command -v terminal-notifier >/dev/null 2>&1; then
  terminal-notifier \
    -title "$title" \
    -subtitle "$subtitle — $label" \
    -message "$message" \
    -sound "$notification_sound" \
    -group "codex-user-attention" \
    >/dev/null 2>&1 || true
else
  # Pass values via env to avoid shell/AppleScript injection from $message.
  NOTIFY_TITLE="$title" NOTIFY_SUBTITLE="$subtitle — $label" NOTIFY_MESSAGE="$message" NOTIFY_SOUND="$notification_sound" \
    osascript - <<'APPLESCRIPT' >/dev/null 2>&1 || true
on run
  set theTitle to system attribute "NOTIFY_TITLE"
  set theSubtitle to system attribute "NOTIFY_SUBTITLE"
  set theMessage to system attribute "NOTIFY_MESSAGE"
  set theSound to system attribute "NOTIFY_SOUND"
  display notification theMessage with title theTitle subtitle theSubtitle sound name theSound
end run
APPLESCRIPT
fi

notify_dispatch_audio "$LOG" "Codex" "$label" "$voice_label" "$message"

exit 0
