# Troubleshooting

## Claude Desktop notifications do not appear

Symptom: notifications work in terminal sessions but not in the Claude macOS desktop app.

Likely cause: `osascript -e "display notification ..."` can return exit code `0` while the Claude Desktop sandbox silently blocks the notification.

Fix:

```bash
brew install terminal-notifier
```

`agentic-coding-notify` prefers `terminal-notifier` and falls back to `osascript` only when `terminal-notifier` is unavailable. Audio playback through `afplay` and speech through `say` are usually not blocked by the Claude Desktop sandbox.

Useful Claude Desktop markers:

- `CLAUDE_CODE_ENTRYPOINT=claude-desktop`
- `__CFBundleIdentifier=com.anthropic.claudefordesktop`

Manual test:

```bash
echo '{"message":"Claude hook","title":"Claude Code"}' |
  NOTIFY_TEST_MODE=1 CLAUDE_CODE_ENTRYPOINT=claude-desktop bash hooks/scripts/notify.sh
```

## Claude plugin stopped firing

- Restart Claude Code after installing or updating the plugin.
- Validate the plugin manifest:

  ```bash
  claude plugin validate .
  ```

- Check the hook shim manually:

  ```bash
  echo '{"message":"test","title":"Claude Code"}' | bash hooks/scripts/notify.sh
  ```

- Check the local Claude settings file for invalid JSON or conflicting hook configuration.

## Codex notifications sound generic

- Confirm `notify` in `~/.codex/config.toml` points to the installed script.
- Confirm the script receives the Codex payload as an argument.
- Run a dry-run event:

  ```bash
  NOTIFY_TEST_MODE=1 bash adapters/codex/notify.sh \
    '{"type":"agent-turn-complete","cwd":"/tmp/example","last-assistant-message":"done"}'
  ```

- If several CLI sessions sound too similar, rename terminal tabs/profiles to short labels such as `One`, `Two`, or `Three`.

## Codex approval/input notifications are missing

This is expected for the external `notify` hook. Codex currently sends `agent-turn-complete` to the external hook; approval/input signals are handled by the Codex app or TUI notification layer.

Use the app preferences for Codex macOS App approval notifications.

For Codex CLI/TUI, configure terminal-native notifications in `~/.codex/config.toml`, for example:

```toml
[tui]
notifications = ["agent-turn-complete", "approval-requested"]
notification_method = "osc9"
```

## Local web UI port is already in use

Run the UI on another port:

```bash
python3 web/notify_ui.py --host 127.0.0.1 --port 8877 --open
```

Or find the process using the default port:

```bash
lsof -iTCP:8765 -sTCP:LISTEN -n -P
```

## Voice or sound samples do not play

Check that macOS tools are present:

```bash
command -v say afplay osascript
```

Check available voices:

```bash
say -v '?'
```

Check available system sounds:

```bash
ls /System/Library/Sounds/*.aiff
```

Then test through the UI or directly with:

```bash
say -v Zarvox -r 250 'Agentic Coding Notify'
afplay /System/Library/Sounds/Basso.aiff
```
