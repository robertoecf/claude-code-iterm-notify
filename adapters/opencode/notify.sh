#!/bin/bash
set -euo pipefail

LOG="${OPENCODE_NOTIFY_LOG:-/tmp/opencode-notify-debug.log}"
SAFE_CWD="${OPENCODE_NOTIFY_SAFE_CWD:-${TMPDIR:-/tmp}}"
COOLDOWN_FILE="${OPENCODE_NOTIFY_COOLDOWN_FILE:-/tmp/opencode-notify-last.json}"
COOLDOWN_SECONDS="${OPENCODE_NOTIFY_COOLDOWN_SECONDS:-60}"

safe_python3() {
  (
    cd "$SAFE_CWD" 2>/dev/null || cd /tmp
    /usr/bin/python3 "$@"
  )
}

collect_parent_process_tree() {
  if [ -n "${OPENCODE_NOTIFY_PARENT_PROCESS_TREE:-}" ]; then
    printf '%s' "$OPENCODE_NOTIFY_PARENT_PROCESS_TREE"
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
  PAYLOAD="$payload" TERM_PROGRAM_VALUE="${TERM_PROGRAM:-}" ITERM_SESSION_VALUE="${ITERM_SESSION_ID:-}" PARENT_PROCESS_TREE="$parent_process_tree" safe_python3 - <<'PY'
import json
import os
from pathlib import Path

payload = os.environ.get("PAYLOAD", "").strip()
term_program = os.environ.get("TERM_PROGRAM_VALUE", "").strip()
iterm_session = os.environ.get("ITERM_SESSION_VALUE", "").strip()
parent_process_tree = os.environ.get("PARENT_PROCESS_TREE", "")

event_type = "agent-turn-complete"
cwd = ""
title = "OpenCode"
raw_message = ""

try:
    data = json.loads(payload) if payload else {}
except Exception:
    data = {}
    raw_message = payload

if isinstance(data, dict):
    event_type = str(data.get("type") or "agent-turn-complete").strip() or "agent-turn-complete"
    cwd = str(data.get("cwd") or "").strip()
    title = str(data.get("title") or title).strip() or "OpenCode"
    for key in (
        "last-assistant-message",
        "last_assistant_message",
        "last-agent-message",
        "last_agent_message",
        "message",
        "body",
        "prompt",
        "reason",
    ):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            raw_message = value.strip()
            break
elif isinstance(data, str) and data.strip():
    raw_message = data.strip()

def classify(text: str, fallback_event: str):
    stripped = text.strip()
    if stripped.startswith("AUTH_NEEDED:"):
        detail = stripped.split(":", 1)[1].strip() or "OpenCode precisa de autorizacao para continuar."
        return "Autorizacao necessaria", detail
    if stripped.startswith("INPUT_NEEDED:"):
        detail = stripped.split(":", 1)[1].strip() or "OpenCode precisa de informacao sua para continuar."
        return "Input necessario", detail
    if stripped.startswith("READY_FOR_REVIEW:"):
        detail = stripped.split(":", 1)[1].strip() or "OpenCode concluiu o trabalho e aguarda revisao."
        return "Pronto para revisao", detail
    # agent-turn-complete is noise - skip these
    if fallback_event == "agent-turn-complete":
        return None, None  # Signal to skip notification
    return "Sua atencao pode ser necessaria", stripped or "OpenCode precisa da sua atencao."

def is_opencode_process_tree(tree: str) -> bool:
    haystack = tree.lower()
    return (
        "/applications/opencode.app/contents/macos/opencode" in haystack
        or "/applications/opencode.app/contents/resources/opencode" in haystack
        or "com.opencode" in haystack
        or "opencode.app" in haystack
        or ".opencode/" in haystack
        or "opencode " in haystack
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

def fallback_label():
    if is_opencode_process_tree(parent_process_tree):
        return "OpenCode App"
    normalized_term = normalized_term_program(term_program)
    if normalized_term:
        return normalized_term
    if cwd:
        return Path(cwd).name or "OpenCode"
    return "OpenCode"

label = fallback_label()
if iterm_session:
    label = "__ITERM__"

subtitle, message = classify(raw_message, event_type)
# Skip if classify returned None (e.g., agent-turn-complete filtered out)
if subtitle is None:
    print(json.dumps({"skip": True}))
    exit(0)
voice_label = "OpenCode App" if label == "OpenCode App" else f"OpenCode {label}"

print(json.dumps({
    "title": title,
    "subtitle": subtitle,
    "message": message,
    "label": label,
    "voice_label": voice_label,
    "event_type": event_type,
    "cwd": cwd,
}))
PY
)"

# Check if this notification should be skipped (e.g., agent-turn-complete)
if [ "$(printf '%s' "$parsed" | safe_python3 -c 'import json,sys; print(json.load(sys.stdin).get("skip", False))' 2>/dev/null)" = "True" ]; then
  echo "$(date '+%Y-%m-%d %H:%M:%S') | SKIP (noise event)" >> "$LOG"
  exit 0
fi

title="$(printf '%s' "$parsed" | safe_python3 -c 'import json,sys; print(json.load(sys.stdin)["title"])')"
subtitle="$(printf '%s' "$parsed" | safe_python3 -c 'import json,sys; print(json.load(sys.stdin)["subtitle"])')"
message="$(printf '%s' "$parsed" | safe_python3 -c 'import json,sys; print(json.load(sys.stdin)["message"])')"
label="$(printf '%s' "$parsed" | safe_python3 -c 'import json,sys; print(json.load(sys.stdin)["label"])')"
voice_label="$(printf '%s' "$parsed" | safe_python3 -c 'import json,sys; print(json.load(sys.stdin)["voice_label"])')"
event_type="$(printf '%s' "$parsed" | safe_python3 -c 'import json,sys; print(json.load(sys.stdin)["event_type"])')"
cwd_value="$(printf '%s' "$parsed" | safe_python3 -c 'import json,sys; print(json.load(sys.stdin)["cwd"])') 2>/dev/null || echo \"\""

# Cooldown/deduplication check
should_notify=true
if [ -f "$COOLDOWN_FILE" ]; then
  last_data="$(cat "$COOLDOWN_FILE" 2>/dev/null || echo '{}')"
  last_msg="$(printf '%s' "$last_data" | safe_python3 -c 'import json,sys; print(json.load(sys.stdin).get("message",""))' 2>/dev/null || echo "")"
  last_time="$(printf '%s' "$last_data" | safe_python3 -c 'import json,sys; print(json.load(sys.stdin).get("timestamp",0))' 2>/dev/null || echo "0")"
  
  if [ "$message" = "$last_msg" ]; then
    now="$(date +%s)"
    elapsed=$((now - last_time))
    if [ "$elapsed" -lt "$COOLDOWN_SECONDS" ]; then
      echo "$(date '+%Y-%m-%d %H:%M:%S') | COOLDOWN skip (msg same, ${elapsed}s < ${COOLDOWN_SECONDS}s)" >> "$LOG"
      should_notify=false
    fi
  fi
fi

# Save current state for cooldown (before any exit) - use safe_python3 for JSON to avoid injection
safe_python3 - <<'PY'
import json
with open("$COOLDOWN_FILE", "w") as f:
    json.dump({"message": """ + '''$message''' + """, "timestamp": $(date +%s)}, f)
PY

if [ "$should_notify" = "false" ]; then
  exit 0
fi

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
      ghostty|Ghostty)
        label="Ghostty"
        ;;
      iTerm.app|iTerm2)
        label="iTerm2"
        ;;
      Apple_Terminal|Terminal|Terminal.app)
        label="Terminal.app"
        ;;
      vscode|"Visual Studio Code")
        label="VS Code"
        ;;
      *)
        label="$TERM_PROGRAM"
        ;;
    esac
  elif [ -n "$cwd_value" ]; then
    label="$(basename "$cwd_value")"
  else
    label="OpenCode"
  fi
  if [ "$label" = "OpenCode App" ]; then
    voice_label="OpenCode App"
  else
    voice_label="OpenCode $label"
  fi
fi

printf '%s | event=%s | label=%s | subtitle=%s | message=%s\n' \
  "$(date '+%Y-%m-%d %H:%M:%S')" \
  "$event_type" \
  "$label" \
  "$subtitle" \
  "$message" >> "$LOG"

if [ "${NOTIFY_TEST_MODE:-0}" = "1" ]; then
  TITLE="$title" SUBTITLE="$subtitle" MESSAGE="$message" LABEL="$label" VOICE_LABEL="$voice_label" EVENT_TYPE="$event_type" safe_python3 - <<'PY'
import json
import os

print(
    json.dumps(
        {
            "title": os.environ["TITLE"],
            "subtitle": os.environ["SUBTITLE"],
            "message": os.environ["MESSAGE"],
            "label": os.environ["LABEL"],
            "voice_label": os.environ["VOICE_LABEL"],
            "event_type": os.environ["EVENT_TYPE"],
        }
    )
)
PY
  exit 0
fi

if command -v terminal-notifier >/dev/null 2>&1; then
  terminal-notifier \
    -title "$title" \
    -subtitle "$subtitle" \
    -message "$message" \
    -sound "Submarine" \
    -group "opencode-user-attention" \
    >/dev/null 2>&1 || true
else
  osascript -e "display notification \"$message\" with title \"$title\" subtitle \"$subtitle\" sound name \"Submarine\"" >/dev/null 2>&1 || true
fi

nohup bash -c "afplay \"/System/Library/Sounds/Basso.aiff\" & say -v Zarvox -r 300 \"$voice_label\" && afplay \"/System/Library/Sounds/Submarine.aiff\"" >> "$LOG" 2>&1 &
disown

exit 0
