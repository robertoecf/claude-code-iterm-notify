#!/bin/bash
set -euo pipefail

# Claude Code Notification Hook — Universal
# Works in: iTerm2, Claude macOS app (Code & Cowork), VS Code, Terminal.app, Ghostty, Kitty
# Plays sound alerts + voice announcement + desktop notification

LOG="/tmp/claude-notify-debug.log"

# Read input from stdin
input=$(cat)
message=$(/usr/bin/python3 -c "import sys,json; print(json.load(sys.stdin).get('message','Claude needs your attention'))" <<< "$input" 2>/dev/null || echo "Claude needs your attention")
title=$(/usr/bin/python3 -c "import sys,json; print(json.load(sys.stdin).get('title','Claude Code'))" <<< "$input" 2>/dev/null || echo "Claude Code")

echo "$(date '+%H:%M:%S') | START | ENTRYPOINT=${CLAUDE_CODE_ENTRYPOINT:-unset} TERM=${TERM_PROGRAM:-unset} ITERM=${ITERM_SESSION_ID:-unset}" >> "$LOG"

# Detect environment and resolve session label
label="Terminal"
voice_label="Claude Code"

if [ "${CLAUDE_CODE_IS_COWORK:-}" = "1" ]; then
  # Claude Desktop — Cowork tab (ENTRYPOINT=local-agent, CLAUDE_CODE_IS_COWORK=1)
  label="Cowork"
  voice_label="Claude Cowork App"
elif [ "${CLAUDE_CODE_ENTRYPOINT:-}" = "claude-desktop" ]; then
  # Claude Desktop — Code tab
  label="App"
  voice_label="Claude Code App"
elif [ -n "${ITERM_SESSION_ID:-}" ]; then
  # iTerm2: resolve profile name via AppleScript for multi-session identification
  session_guid=$(echo "$ITERM_SESSION_ID" | cut -d: -f2)
  resolved=$(osascript <<EOF 2>/dev/null
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
  ) || true
  label="${resolved:-iTerm2}"
  voice_label="Claude Code $label"
elif [ -n "${TERM_PROGRAM:-}" ]; then
  # Other terminals: use terminal name as label
  label="$TERM_PROGRAM"
  voice_label="Claude Code $label"
fi

echo "$(date '+%H:%M:%S') | LABEL=$label VOICE=$voice_label MSG=$message" >> "$LOG"

# Desktop notification
# osascript is silently blocked in Claude macOS app sandbox — use terminal-notifier as primary
if command -v terminal-notifier &>/dev/null; then
  terminal-notifier -title "$title ($label)" -message "$message" -sound "Submarine" 2>/dev/null || true
  echo "$(date '+%H:%M:%S') | NOTIFICATION (terminal-notifier)" >> "$LOG"
else
  osascript -e "display notification \"$message\" with title \"$title ($label)\" sound name \"Submarine\"" 2>/dev/null || true
  echo "$(date '+%H:%M:%S') | NOTIFICATION (osascript)" >> "$LOG"
fi

# Sound: Basso + voice announcement (simultaneous), then Submarine — detached so it won't block Claude
nohup bash -c "afplay \"/System/Library/Sounds/Basso.aiff\" & say -v Zarvox -r 300 \"$voice_label\" && afplay \"/System/Library/Sounds/Submarine.aiff\"" >> "$LOG" 2>&1 &
disown
echo "$(date '+%H:%M:%S') | SOUND DISPATCHED" >> "$LOG"

exit 0
