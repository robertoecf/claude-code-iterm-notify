#!/bin/bash
set -euo pipefail

# Claude Code notification adapter.
# Keeps the original plugin behavior while allowing a dry-run mode for tests.

LOG="${CLAUDE_NOTIFY_LOG:-/tmp/claude-notify-debug.log}"

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

if [ "${NOTIFY_TEST_MODE:-0}" = "1" ]; then
  CLAUDE_NOTIFY_TITLE="$title" \
  CLAUDE_NOTIFY_MESSAGE="$message" \
  CLAUDE_NOTIFY_LABEL="$label" \
  CLAUDE_NOTIFY_VOICE_LABEL="$voice_label" \
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
        }
    )
)
PY
  exit 0
fi

if command -v terminal-notifier >/dev/null 2>&1; then
  terminal-notifier -title "$title ($label)" -message "$message" -sound "Submarine" 2>/dev/null || true
  echo "$(date '+%H:%M:%S') | NOTIFICATION (terminal-notifier)" >> "$LOG"
else
  osascript -e "display notification \"$message\" with title \"$title ($label)\" sound name \"Submarine\"" 2>/dev/null || true
  echo "$(date '+%H:%M:%S') | NOTIFICATION (osascript)" >> "$LOG"
fi

nohup bash -c "afplay \"/System/Library/Sounds/Basso.aiff\" & say -v Samantha -r 300 \"$voice_label\" && afplay \"/System/Library/Sounds/Submarine.aiff\"" >> "$LOG" 2>&1 &
disown
echo "$(date '+%H:%M:%S') | SOUND DISPATCHED" >> "$LOG"

exit 0
