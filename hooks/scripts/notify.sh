#!/bin/bash
set -euo pipefail

# Claude Code Notification Hook — Universal
# Works in: iTerm2, Claude macOS app, VS Code terminal, macOS Terminal.app, Ghostty, Kitty
# Plays sound alerts and desktop notification when Claude needs attention

input=$(cat)
message=$(echo "$input" | /usr/bin/python3 -c "import sys,json; print(json.load(sys.stdin).get('message','Claude needs your attention'))" 2>/dev/null || echo "Claude needs your attention")
title=$(echo "$input" | /usr/bin/python3 -c "import sys,json; print(json.load(sys.stdin).get('title','Claude Code'))" 2>/dev/null || echo "Claude Code")

# Detect environment and resolve session label
label="App"
if [ "${CLAUDE_CODE_ENTRYPOINT:-}" = "claude-desktop" ]; then
  label="App"
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
elif [ -n "${TERM_PROGRAM:-}" ]; then
  # Other terminals: use terminal name as label
  label="$TERM_PROGRAM"
fi

# Desktop notification
# osascript is silently blocked in Claude macOS app sandbox — use terminal-notifier as primary
if command -v terminal-notifier &>/dev/null; then
  terminal-notifier -title "$title ($label)" -message "$message" -sound "Submarine" 2>/dev/null || true
else
  osascript -e "display notification \"$message\" with title \"$title ($label)\" sound name \"Submarine\"" 2>/dev/null || true
fi

# Basso + voice with label (simultaneous), then Submarine — detached so it won't block Claude
nohup bash -c "afplay \"/System/Library/Sounds/Basso.aiff\" & say -v Zarvox -r 300 \"Claude Code $label\" && afplay \"/System/Library/Sounds/Submarine.aiff\"" &>/dev/null &
disown

exit 0
