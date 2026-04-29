# agentic-coding-notify

macOS notifications with sound and voice alerts for agent CLIs.

The repository still ships the original **Claude Code plugin**, and now also includes dedicated adapters for **Codex**, **OpenCode**, and **Pi**. They live in one repo, but each environment keeps its own entrypoint and installation flow.

The Claude plugin name remains `claude-code-notify` for compatibility with existing installs.

## Adapters

| Adapter | Entry point | Installation model |
|---|---|---|
| Claude Code | `hooks/scripts/notify.sh` | Claude plugin |
| Codex | `adapters/codex/notify.sh` | `~/.codex/config.toml` `notify` command |
| OpenCode | `adapters/opencode/notify.sh` | adapter install script |
| Pi | `adapters/pi/notify.sh` | adapter install script |

## What you get

When the adapter fires, you get:

1. Desktop notification via `terminal-notifier` (with `Submarine` sound) when available
2. Audio alert with `Basso`
3. Voice announcement with the session label

The spoken label is environment-specific. For Codex, the voice says `Codex terminou em {label}` (or `Codex App terminou` for the Codex macOS App). For Claude, the existing `Claude Code {label}` behavior is preserved unless you override it in the local preferences UI.

## Requirements

- macOS
- `afplay`
- `say`
- `osascript`
- [`terminal-notifier`](https://github.com/julienXX/terminal-notifier)

```bash
brew install terminal-notifier
```

## Local preferences UI

Run the local web UI:

```bash
python3 web/notify_ui.py --open
```

Then use `http://127.0.0.1:8765` to choose. The UI is a compact light-mode-only dashboard with an N64 gray-first retro palette; numeric/status values use JetBrains Mono when available, with system fallbacks. It does not import external CSS or art assets.

- spoken text templates for app and CLI contexts
- searchable macOS `say` voice, with a Play/Stop sample that says `Agentic Coding Notify`
- `say -r` speech rate
- searchable notification sound
- searchable start and end sounds played with `afplay`
- sound samples: changing a sound field plays a sample automatically, and voice/sound fields each have a single Play/Stop toggle control
- searchable list fields for voice, sounds, and service
- disclosure guidance: app sessions do not need terminal labels; CLI sessions can use short tab/profile labels like `One`, `Two`, or `Three` because the adapter already detects the service

Preferences are saved to:

```text
~/.agentic-coding-notify/config.json
```

The UI defaults to the older classic style:

```json
{
  "voice": "Zarvox",
  "rate": "250",
  "notification_sound": "Submarine",
  "start_sound": "Basso",
  "end_sound": "Submarine",
  "app_voice_text_template": "{service} App",
  "cli_voice_text_template": "{service} {label}"
}
```

Supported template placeholders:

- `{service}`: `Claude`, `Codex`, `OpenCode`, or `Pi`
- `{label}`: app label or CLI tab/profile/cwd label
- `{voice_label}`: adapter-computed fallback text
- `{message}`: notification message preview
- `{context}`: `app` or `cli`

## Claude Code

The Claude adapter stays backward-compatible with the existing plugin layout.

### Install

From a local directory:

```bash
claude plugin marketplace add /path/to/agentic-coding-notify
claude plugin install claude-code-notify@agentic-coding-notify
```

From GitHub:

```bash
claude plugin marketplace add robertoecf/agentic-coding-notify
claude plugin install claude-code-notify@agentic-coding-notify
```

Restart Claude Code after installing or updating. Claude loads hooks at session start.

### Claude hooks

The plugin registers two `Notification` hooks:

- `permission_prompt`
- `idle_prompt`

Both still call `hooks/scripts/notify.sh`. That path is now a shim that delegates to `adapters/claude/notify.sh`, so older setups do not break.

### Claude test

```bash
echo '{"message":"test","title":"Claude Code"}' | bash hooks/scripts/notify.sh
```

## Codex

Codex does not use the Claude plugin system. The supported integration point is the `notify` command in `~/.codex/config.toml`.

### Install script only

Copy the adapter to your Codex bin directory:

```bash
bash adapters/codex/install.sh --install-script ~/.codex/bin/codex-notify.sh
```

### Print the config snippet

```bash
bash adapters/codex/install.sh --print-config ~/.codex/bin/codex-notify.sh
```

Expected output:

```toml
notify = ["/Users/you/.codex/bin/codex-notify.sh"]
```

Then add that line to `~/.codex/config.toml`.

### Codex self-test

Run the adapter in dry-run mode:

```bash
bash adapters/codex/install.sh --self-test ~/.codex/bin/codex-notify.sh
```

Or invoke the repository script directly:

```bash
NOTIFY_TEST_MODE=1 bash adapters/codex/notify.sh \
  '{"type":"agent-turn-complete","cwd":"/tmp/example","last-assistant-message":"notifier pronto"}'
```

### What the Codex adapter does (and what it cannot do)

Codex exposes exactly one event to the `notify` hook: `agent-turn-complete`. Approval requests, input requests, exec-approval, and patch-approval events all travel on different channels and never reach this script — see [openai/codex#11808](https://github.com/openai/codex/issues/11808) and [protocol source](https://github.com/openai/codex/blob/main/codex-rs/protocol/src/protocol.rs).

So the adapter is deliberately minimal:

- On every `agent-turn-complete`, it fires a short voice announcement `Codex terminou em <label>` (or `Codex terminou no app` for the Codex macOS App).
- The desktop notification shows the first ~160 characters of the last assistant message as a preview.
- Identical events within 30 s (same label+message) are suppressed via a cooldown file.
- The adapter does **not** read the assistant response aloud — that was the source of noise. Glance at the notification or the terminal/app for the actual content.

### Getting alerts for approval / input (not `notify`)

Because Codex does not send those signals to the `notify` hook, use the right layer for each environment:

**Codex macOS App** — enable approval-request notifications in the app preferences. The app delivers them natively through macOS notifications.

**Codex CLI (TUI)** — add to `~/.codex/config.toml`:

```toml
[tui]
notifications = ["agent-turn-complete", "approval-requested"]
notification_method = "osc9"
```

The terminal (iTerm2, Ghostty, Terminal.app) then emits native desktop notifications via OSC 9 when Codex asks for approval. See [Advanced configuration](https://developers.openai.com/codex/config-advanced).

**Fully custom behavior** — the only way to react to every `EventMsg` in the adapter itself is to consume Codex as an MCP server (`codex mcp`) instead of via the one-shot `notify` hook. That is out of scope for this repo today.

### Tunables

| Environment variable | Default | Purpose |
|---|---|---|
| `AGENTIC_CODING_NOTIFY_CONFIG` | `~/.agentic-coding-notify/config.json` | Shared voice/sound preferences file |
| `CODEX_NOTIFY_LOG` | `/tmp/codex-notify-debug.log` | Debug log path |
| `CODEX_NOTIFY_COOLDOWN_FILE` | `/tmp/codex-notify-last.json` | Dedup state file |
| `CODEX_NOTIFY_COOLDOWN_SECONDS` | `30` | Window for suppressing identical events |
| `CODEX_NOTIFY_PREVIEW_CHARS` | `160` | Desktop notification preview length |

### Session label strategy

The Codex adapter resolves the label in this order:

1. iTerm2 profile name when `ITERM_SESSION_ID` is available
2. Codex App process ancestry when the script is launched from the macOS app
3. normalized terminal name from `TERM_PROGRAM`
4. basename of the `cwd` in the Codex payload
5. `Codex`

This keeps multiple tabs distinguishable without hardcoding agent names into the voice message.

### Supported Codex environments

The adapter now resolves these environments explicitly:

- `Ghostty` → `Ghostty`
- `iTerm2` → profile name when available, otherwise `iTerm2`
- `Apple_Terminal` → `Terminal.app`
- `vscode` → `VS Code`
- Codex macOS App process tree → `Codex App`

## iTerm2 multi-session setup

If you run multiple Claude or Codex sessions in iTerm2, create named profiles such as `1`, `2`, `api`, or `review`.

When a session needs attention, the voice will use the profile name when it can be resolved. That is the cleanest way to identify parallel sessions.

Tip: use short terminal tab/profile names such as `One`, `Two`, or `Three`. The adapter already identifies the CLI service (`Claude`, `Codex`, `OpenCode`, `Pi`), so the tab/profile name only needs to identify the session.

## Repository layout

```text
.
├── adapters
│   ├── claude
│   │   └── notify.sh
│   ├── codex
│   │   ├── install.sh
│   │   └── notify.sh
│   ├── opencode
│   │   ├── install.sh
│   │   └── notify.sh
│   └── pi
│       ├── install.sh
│       └── notify.sh
├── hooks
│   ├── hooks.json
│   └── scripts
│       └── notify.sh
├── lib
│   └── notify-config.sh
├── tests
│   ├── codex_notify_test.sh
│   └── plugin_smoke_test.sh
└── web
    └── notify_ui.py
```

## Development

Run the full smoke suite:

```bash
./tests/plugin_smoke_test.sh
```

Run only the Codex adapter regression test:

```bash
./tests/codex_notify_test.sh
```

## Troubleshooting

### Claude plugin stopped firing

- Restart Claude Code
- Check `~/.claude/settings.json` for invalid configuration
- Test `hooks/scripts/notify.sh` manually

### Codex notifications are generic

- Confirm `notify` in `~/.codex/config.toml` points to the right script
- Confirm the script receives the payload as an argument
- Use `NOTIFY_TEST_MODE=1` to inspect parsed output without sending desktop notifications

### Codex does not expose the same events as Claude

That is expected. Codex `notify` is configured through `config.toml`, and the current documented external notification event is `agent-turn-complete`. This repository keeps adapters separate so each environment can use the signals it actually exposes.

## License

MIT — see [LICENSE](LICENSE).
