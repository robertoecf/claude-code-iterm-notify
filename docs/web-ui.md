# Local preferences UI

Run:

```bash
python3 web/notify_ui.py --open
```

Then open `http://127.0.0.1:8765`.

## Design

The UI is a local, self-contained web page inspired by the N64 gray hardware palette:

- light mode only;
- beveled console shell;
- colored N64-style stripes;
- large panel cards for voice, sounds, text, preview, and disclosure;
- bottom console buttons for save, export, dry-run, real notification, and preset actions;
- hover/focus tooltips on every action button explaining what each function does;
- JetBrains Mono for numeric/status/terminal-like values, with system monospace fallbacks.

No external stylesheets, remote fonts, or remote image assets are loaded.

## Controls

### Voice

- The voice field uses a shadcn-style combobox: type to filter, focus/click to show all values, and scroll the full list.
- The first combobox actions are `Show off one-by-one` and `SHOW OFF SELECTION`. `SHOW OFF SELECTION` enters selection mode; then you pick values and cycle only the selected values. Show-off cycles run once and stop automatically. In selection mode, the `×` control clears the selected set.
- The Play/Stop button samples the current voice with the phrase `Agentic Coding Notify`.
- Changing the voice automatically triggers the same sample.
- Speech rate maps directly to macOS `say -r` words per minute.

### Sounds

- Notification, start, and end sound fields use the same scrollable combobox behavior, including all-value and selected-value show-off modes.
- Every sound field has one Play/Stop toggle.
- Changing a sound field plays a sample automatically.
- `none` disables a start/end sound.

### Text templates

The app template, CLI template, override spoken text, and service fields are all typeable/searchable comboboxes.

Resolution order:

1. `voice_text_template`, when set;
2. `app_voice_text_template`, for app context;
3. `cli_voice_text_template`, for CLI context;
4. adapter fallback text.

Supported placeholders:

| Placeholder | Meaning |
|---|---|
| `{service}` | service name, e.g. `Claude`, `Codex`, `OpenCode`, `Pi` |
| `{label}` | app label, terminal tab/profile name, or cwd fallback |
| `{voice_label}` | adapter-computed fallback text |
| `{message}` | notification message preview |
| `{context}` | `app` or `cli` |

### Preview and tests

- Every action button includes a hover/focus tooltip and writes visible confirmation feedback to the bottom status panel.
- **Export Config** downloads the current UI preferences as `agentic-coding-notify-config.json`.
- **Dry-run JSON** runs the selected adapter with `NOTIFY_TEST_MODE=1` and returns the parsed payload.
- **Real Notification** runs the selected adapter without dry-run mode.
- **Classic Preset** restores the original voice/sound defaults.
- **Stop all samples** terminates active voice/sound sample processes started by the UI.

## Stop the server

If the UI is running in the foreground, press `Ctrl-C` in that terminal.

If it is running in the background on the default port:

```bash
lsof -tiTCP:8765 -sTCP:LISTEN | xargs kill
```

The server is intentionally lightweight: on this Mac, the Python process measured about 18 MB RSS while serving the UI. Voice and sound option lists are cached after the first `/api/options` request to avoid repeated `say -v ?` subprocess scans.

## Local API

The UI server exposes local-only JSON endpoints:

| Endpoint | Purpose |
|---|---|
| `GET /api/options` | list macOS voices and system sounds |
| `GET /api/config` | load saved preferences |
| `POST /api/config` | save preferences |
| `POST /api/test` | run an adapter dry-run or real notification test |
| `POST /api/play-sound` | play a sound sample |
| `POST /api/stop-sound` | stop one sound sample or all samples |
| `POST /api/play-voice` | play the voice sample |
| `POST /api/stop-voice` | stop the voice sample |

The default config path is:

```text
~/.agentic-coding-notify/config.json
```

Override it for tests with:

```bash
AGENTIC_CODING_NOTIFY_CONFIG=/tmp/notify-config.json python3 web/notify_ui.py --open
```
