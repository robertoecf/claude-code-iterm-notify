#!/bin/bash
set -euo pipefail

# Claude Code iTerm2 Notification Hook
# Plays Basso + Zarvox voice (simultaneous), then Submarine
# Identifies iTerm2 session by profile name

input=$(cat)
message=$(echo "$input" | /usr/bin/python3 -c "import sys,json; print(json.load(sys.stdin).get('message','Claude needs your attention'))" 2>/dev/null || echo "Claude needs your attention")
title=$(echo "$input" | /usr/bin/python3 -c "import sys,json; print(json.load(sys.stdin).get('title','Claude Code'))" 2>/dev/null || echo "Claude Code")

# Get iTerm2 session profile name via AppleScript (unique by GUID)
session_name="?"
if [ -n "${ITERM_SESSION_ID:-}" ]; then
  session_guid=$(echo "$ITERM_SESSION_ID" | cut -d: -f2)
  session_name=$(osascript <<EOF 2>/dev/null
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
  ) || session_name="?"
fi

# Desktop notification
osascript -e "display notification \"$message\" with title \"$title\" sound name \"Submarine\""

# Basso + voice with session name (simultaneous), then Submarine
nohup bash -c "afplay \"/System/Library/Sounds/Basso.aiff\" & say -v Zarvox -r 300 \"Claude Code $session_name\" && afplay \"/System/Library/Sounds/Submarine.aiff\"" &>/dev/null &
disown

exit 0
