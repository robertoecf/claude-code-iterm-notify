# Adapters

`agentic-coding-notify` keeps one shared preference file and four host-specific entrypoints.

Shared preference path:

```text
~/.agentic-coding-notify/config.json
```

Override it with:

```bash
AGENTIC_CODING_NOTIFY_CONFIG=/path/to/config.json
```

## Adapter matrix

| Adapter | Entrypoint | Install model | Notes |
|---|---|---|---|
| Claude Code | `hooks/scripts/notify.sh` | Claude plugin hook | Backwards-compatible `claude-code-notify` plugin name |
| Codex | `adapters/codex/notify.sh` | `~/.codex/config.toml` `notify` command | Receives only `agent-turn-complete` |
| OpenCode | `adapters/opencode/notify.sh` | adapter install script | Filters noisy events; notifies on explicit action markers |
| Pi | `adapters/pi/notify.sh` | adapter install script | Filters noisy events; supports Cowork labeling |

## Claude Code

Install from a local checkout:

```bash
claude plugin marketplace add /path/to/agentic-coding-notify
claude plugin install claude-code-notify@agentic-coding-notify
```

Install from GitHub:

```bash
claude plugin marketplace add robertoecf/agentic-coding-notify
claude plugin install claude-code-notify@agentic-coding-notify
```

Restart Claude Code after installing or updating. Claude loads hooks at session start.

The plugin registers two `Notification` hooks:

- `permission_prompt`
- `idle_prompt`

Both call `hooks/scripts/notify.sh`, which delegates to `adapters/claude/notify.sh` unless another adapter is explicitly detected.

Manual Claude test:

```bash
echo '{"message":"test","title":"Claude Code"}' | bash hooks/scripts/notify.sh
```

Dry-run Claude test:

```bash
echo '{"message":"test","title":"Claude Code"}' |
  NOTIFY_TEST_MODE=1 CLAUDE_CODE_ENTRYPOINT=claude-desktop bash hooks/scripts/notify.sh
```

## Codex

Codex does not use the Claude plugin system. Configure Codex with a `notify` command in `~/.codex/config.toml`.

Install the script:

```bash
bash adapters/codex/install.sh --install-script ~/.codex/bin/codex-notify.sh
```

Print the config snippet:

```bash
bash adapters/codex/install.sh --print-config ~/.codex/bin/codex-notify.sh
```

Expected output:

```toml
notify = ["/Users/you/.codex/bin/codex-notify.sh"]
```

Add that line to `~/.codex/config.toml`.

Dry-run self-test:

```bash
bash adapters/codex/install.sh --self-test ~/.codex/bin/codex-notify.sh
```

Direct repository dry-run:

```bash
NOTIFY_TEST_MODE=1 bash adapters/codex/notify.sh \
  '{"type":"agent-turn-complete","cwd":"/tmp/example","last-assistant-message":"notifier pronto"}'
```

### Codex behavior

Codex currently invokes external `notify` hooks for `agent-turn-complete`. Approval/input alerts are separate UI/TUI channels and do not reach this script.

So the adapter deliberately does one thing:

- desktop notification with a truncated preview of the last assistant message;
- short voice announcement such as `Codex terminou em Ghostty`;
- special app wording: `Codex App terminou`;
- deduplication of identical events within the cooldown window.

It does **not** read the full assistant response aloud.

### Codex label strategy

The Codex adapter resolves labels in this order:

1. explicit iTerm2 profile name when available;
2. Codex App process ancestry or `CODEX_DESKTOP=1`;
3. normalized terminal name from `TERM_PROGRAM`;
4. basename of `cwd` from the Codex payload;
5. `Codex`.

Tip: for CLI sessions, use short terminal tab/profile names such as `One`, `Two`, or `Three`. The adapter already speaks the service name, so the tab/profile only needs to identify the session.

## OpenCode

Install:

```bash
bash adapters/opencode/install.sh
```

Optional install target override:

```bash
OPENCODE_PLUGIN_ROOT=/path/to/target bash adapters/opencode/install.sh
```

Dry-run example:

```bash
NOTIFY_TEST_MODE=1 OPENCODE=1 bash hooks/scripts/notify.sh \
  '{"type":"agent-turn-complete","cwd":"/tmp/proj","message":"READY_FOR_REVIEW: pronto"}'
```

The OpenCode adapter is intentionally quiet for generic messages. It notifies for explicit markers such as:

- `AUTH_NEEDED:`
- `INPUT_NEEDED:`
- `READY_FOR_REVIEW:`

## Pi

Install:

```bash
bash adapters/pi/install.sh
```

Optional install target override:

```bash
PI_PLUGIN_ROOT=/path/to/target bash adapters/pi/install.sh
```

Dry-run example:

```bash
NOTIFY_TEST_MODE=1 PI_IS_COWORK=1 bash hooks/scripts/notify.sh \
  '{"type":"agent-turn-complete","cwd":"/tmp/proj","message":"READY_FOR_REVIEW: pronto"}'
```

The Pi adapter follows the same noise-filtering shape as OpenCode and supports Cowork-style labels.

## Shared tunables

| Variable | Purpose |
|---|---|
| `AGENTIC_CODING_NOTIFY_CONFIG` | shared preferences JSON path |
| `NOTIFY_TEST_MODE=1` | parse and print JSON without real notifications/audio |

## Codex tunables

| Variable | Default | Purpose |
|---|---|---|
| `CODEX_NOTIFY_LOG` | `/tmp/codex-notify-debug.log` | debug log path |
| `CODEX_NOTIFY_COOLDOWN_FILE` | `/tmp/codex-notify-last.json` | dedup state file |
| `CODEX_NOTIFY_COOLDOWN_SECONDS` | `30` | identical-event suppression window |
| `CODEX_NOTIFY_PREVIEW_CHARS` | `160` | desktop notification preview length |
| `CODEX_NOTIFY_PARENT_PROCESS_TREE` | auto-detected | test/override process ancestry |
| `CODEX_DESKTOP=1` | unset | force Codex App wording |
