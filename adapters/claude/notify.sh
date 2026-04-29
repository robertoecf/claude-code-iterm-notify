#!/bin/bash
set -euo pipefail

# Claude Code notification adapter.
# Keeps the original plugin behavior while allowing a dry-run mode for tests.

LOG="${CLAUDE_NOTIFY_LOG:-/tmp/claude-notify-debug.log}"
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

input="$(cat 2>/dev/null || true)"
message="$(
  /usr/bin/python3 -c "import sys,json; print(json.load(sys.stdin).get('message','Claude needs your attention'))" \
    <<< "$input" 2>/dev/null || echo "Claude needs your attention"
)"
title="$(
  /usr/bin/python3 -c "import sys,json; print(json.load(sys.stdin).get('title','Claude Code'))" \
    <<< "$input" 2>/dev/null || echo "Claude Code"
)"

echo "$(date '+%H:%M:%S') | START | ENTRYPOINT=${CLAUDE_CODE_ENTRYPOINT:-unset} TERM=${TERM_PROGRAM:-unset} ITERM=${ITERM_SESSION_ID:-unset}" >> "$LOG"

label="Terminal"
voice_label="Claude Code"

if [ "${CLAUDE_CODE_IS_COWORK:-}" = "1" ]; then
  label="Cowork"
  voice_label="Claude Cowork App"
elif [ "${CLAUDE_CODE_ENTRYPOINT:-}" = "claude-desktop" ]; then
  label="App"
  voice_label="Claude Code App"
elif [ -n "${ITERM_SESSION_ID:-}" ]; then
  session_guid="$(echo "$ITERM_SESSION_ID" | cut -d: -f2)"
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
  label="${resolved:-iTerm2}"
  voice_label="Claude Code $label"
elif [ -n "${TERM_PROGRAM:-}" ]; then
  label="$TERM_PROGRAM"
  voice_label="Claude Code $label"
fi

echo "$(date '+%H:%M:%S') | LABEL=$label VOICE=$voice_label MSG=$message" >> "$LOG"

notification_sound="$(notify_notification_sound Submarine)"
voice_text="$(notify_effective_voice_text "Claude" "$label" "$voice_label" "$message")"
voice_name="$(notify_voice_name Samantha)"
voice_rate="$(notify_voice_rate 300)"
start_sound="$(notify_start_sound_path /System/Library/Sounds/Basso.aiff)"
end_sound="$(notify_end_sound_path /System/Library/Sounds/Submarine.aiff)"

if [ "${NOTIFY_TEST_MODE:-0}" = "1" ]; then
  CLAUDE_NOTIFY_TITLE="$title" \
  CLAUDE_NOTIFY_MESSAGE="$message" \
  CLAUDE_NOTIFY_LABEL="$label" \
  CLAUDE_NOTIFY_VOICE_LABEL="$voice_label" \
  CLAUDE_NOTIFY_VOICE_TEXT="$voice_text" \
  CLAUDE_NOTIFY_VOICE="$voice_name" \
  CLAUDE_NOTIFY_RATE="$voice_rate" \
  CLAUDE_NOTIFY_NOTIFICATION_SOUND="$notification_sound" \
  CLAUDE_NOTIFY_START_SOUND="$start_sound" \
  CLAUDE_NOTIFY_END_SOUND="$end_sound" \
  /usr/bin/python3 - <<'PY'
import json
import os

print(
    json.dumps(
        {
            "title": os.environ["CLAUDE_NOTIFY_TITLE"],
            "message": os.environ["CLAUDE_NOTIFY_MESSAGE"],
            "label": os.environ["CLAUDE_NOTIFY_LABEL"],
            "voice_label": os.environ["CLAUDE_NOTIFY_VOICE_LABEL"],
            "voice_text": os.environ["CLAUDE_NOTIFY_VOICE_TEXT"],
            "voice": os.environ["CLAUDE_NOTIFY_VOICE"],
            "rate": os.environ["CLAUDE_NOTIFY_RATE"],
            "notification_sound": os.environ["CLAUDE_NOTIFY_NOTIFICATION_SOUND"],
            "start_sound": os.environ["CLAUDE_NOTIFY_START_SOUND"],
            "end_sound": os.environ["CLAUDE_NOTIFY_END_SOUND"],
        }
    )
)
PY
  exit 0
fi

if command -v terminal-notifier >/dev/null 2>&1; then
  terminal-notifier -title "$title ($label)" -message "$message" -sound "$notification_sound" 2>/dev/null || true
  echo "$(date '+%H:%M:%S') | NOTIFICATION (terminal-notifier)" >> "$LOG"
else
  NOTIFY_TITLE="$title ($label)" NOTIFY_MESSAGE="$message" NOTIFY_SOUND="$notification_sound" \
    osascript - <<'APPLESCRIPT' >/dev/null 2>&1 || true
on run
  set theTitle to system attribute "NOTIFY_TITLE"
  set theMessage to system attribute "NOTIFY_MESSAGE"
  set theSound to system attribute "NOTIFY_SOUND"
  display notification theMessage with title theTitle sound name theSound
end run
APPLESCRIPT
  echo "$(date '+%H:%M:%S') | NOTIFICATION (osascript)" >> "$LOG"
fi

notify_dispatch_audio "$LOG" "Claude" "$label" "$voice_label" "$message"
echo "$(date '+%H:%M:%S') | SOUND DISPATCHED" >> "$LOG"

exit 0
