# claude-code-notify

macOS notification plugin for Claude Code. Plays sound alerts and desktop notifications when Claude needs your attention.

Works in **any environment**: iTerm2 (with session identification by profile name), Claude macOS desktop app, VS Code terminal, macOS Terminal.app, Ghostty, Kitty, and others.

## What it does

When Claude Code needs your authorization or input, you get:

1. **Desktop notification** (macOS Notification Center) with Submarine sound
2. **Audio alert**: Basso sound + Zarvox voice saying "Claude Code {label}" simultaneously
3. **Closing sound**: Submarine

The label adapts to your environment:

| Environment | Label | Example voice |
|---|---|---|
| iTerm2 (named profile) | Profile name | "Claude Code 2" |
| iTerm2 (default profile) | "iTerm2" | "Claude Code iTerm2" |
| VS Code | "vscode" | "Claude Code vscode" |
| Claude macOS app (Code) | "App" | "Claude Code App" |
| Claude macOS app (Cowork) | "Cowork" | "Claude Cowork App" |
| Other terminals | Terminal name | "Claude Code Apple_Terminal" |

## Requirements

- macOS (uses `afplay`, `say`, `osascript`)
- Claude Code v2.1+
- [`terminal-notifier`](https://github.com/julienXX/terminal-notifier) — required for notifications in the Claude macOS desktop app (sandbox blocks `osascript` notifications)
  ```bash
  brew install terminal-notifier
  ```

## Installation

### From local directory

```bash
claude plugin install /path/to/claude-code-notify
```

### From GitHub

```bash
claude plugin install github:robertoecf/claude-code-iterm-notify
```

> **Important:** After installing or updating the plugin, you must **restart Claude Code** (close and reopen the app or start a new terminal session) for hooks to take effect. Hooks are loaded at session start.

## iTerm2 multi-session setup (optional)

If you run multiple Claude Code sessions in iTerm2 and want to know *which* session needs attention, set up named profiles:

### Step 1: Open iTerm2 Preferences

- Press **Cmd + ,** or go to **iTerm2 > Settings** in the menu bar.

### Step 2: Go to Profiles

- Click the **Profiles** tab at the top of the Settings window.
- You'll see a list of profiles on the left (by default there's just "Default").

### Step 3: Create a new profile

- Click the **+** button at the bottom of the profiles list.
- A new profile called "New Profile" will appear.

### Step 4: Name the profile

- In the **General** tab on the right, find the **Name** field at the top.
- Change it to a short identifier, e.g., `1`.
- Repeat steps 3-4 to create profiles `2`, `3`, etc. — one for each Claude Code session you plan to run.

### Step 5: (Optional) Set the profile as the tab title

- Still in the **General** tab, under **Title**, check that **Profile Name** is selected in the title components. This makes the tab show "1", "2", "3" so you can visually identify them too.

### Step 6: Open tabs with the right profile

- In iTerm2, go to **Shell > New Tab** or press **Cmd + T**.
- To choose a specific profile: **Shell > New Tab > Profile Name** (e.g., "1").
- Or right-click the **+** button in the tab bar to pick a profile.
- Alternatively, use **Cmd + O** to open the profile selector.

### Step 7: Run Claude Code

- In each tab, run `claude` as usual.
- When Claude needs attention in tab "2", you'll hear: **"Claude Code 2"**.

### Result

You'll have tabs like this:

```
[ 1 ] [ 2 ] [ 3 ]
```

Each running a Claude Code session. When any session needs your attention, the notification will say the exact profile name — even if you drag tabs around or close and reopen them.

## How it works

The plugin registers two `Notification` hooks:

- **`permission_prompt`** — fires when Claude needs tool authorization (the `[Y/n]` prompt)
- **`idle_prompt`** — fires when Claude is waiting for user input

Both trigger `notify.sh`, which:

1. Reads the notification JSON from stdin
2. Detects the current environment (`ITERM_SESSION_ID`, `TERM_PROGRAM`, or fallback)
3. In iTerm2: queries the session's **profile name** via AppleScript
4. In the Claude macOS app: uses "App" as label
5. In other terminals: uses the terminal program name as label
6. Sends a macOS desktop notification via `terminal-notifier` (primary) or `osascript` (fallback)
7. Plays Basso + Zarvox voice (simultaneous), then Submarine — detached via `nohup` so it doesn't block Claude

## Customization

Edit `hooks/scripts/notify.sh` (then reinstall or copy to `~/.claude/hooks/notify.sh`) to change any of the options below.

### Voice

Change `-v Zarvox` in the `say` command to any installed macOS voice.

```bash
say -v '?'  # list all available voices
```

**Robotic/novelty voices (recommended for notifications — they stand out):**

| Voice | Style | Try it |
|---|---|---|
| `Zarvox` (default) | Classic robot | `say -v Zarvox "Claude Code App"` |
| `Bad News` | Dramatic, deep | `say -v "Bad News" "Claude Code App"` |
| `Wobble` | Wobbly, unstable | `say -v Wobble "Claude Code App"` |
| `Eddy (English (US))` | Modern robot | `say -v "Eddy (English (US))" "Claude Code App"` |
| `Organ` | Church organ | `say -v Organ "Claude Code App"` |
| `Reed (English (US))` | Reedy, nasal | `say -v "Reed (English (US))" "Claude Code App"` |

**Other fun voices:**

| Voice | Style | Try it |
|---|---|---|
| `Bells` | Bell-like tones | `say -v Bells "Claude Code App"` |
| `Boing` | Bouncy | `say -v Boing "Claude Code App"` |
| `Bubbles` | Underwater | `say -v Bubbles "Claude Code App"` |
| `Cellos` | Musical, deep | `say -v Cellos "Claude Code App"` |
| `Trinoids` | Alien | `say -v Trinoids "Claude Code App"` |
| `Whisper` | Quiet whisper | `say -v Whisper "Claude Code App"` |
| `Jester` | Playful | `say -v Jester "Claude Code App"` |
| `Superstar` | Enthusiastic | `say -v Superstar "Claude Code App"` |

**Natural voices:**

| Voice | Language | Try it |
|---|---|---|
| `Samantha` | English (US) | `say -v Samantha "Claude Code App"` |
| `Fred` | English (US) | `say -v Fred "Claude Code App"` |
| `Luciana` | Portuguese (BR) | `say -v Luciana "Claude Code App"` |

> **Tip:** macOS has many more voices available for download. Go to **System Settings > Accessibility > Spoken Content > System Voice > Manage Voices** to install additional voices.

To hear all installed voices:
```bash
say -v '?' | while IFS= read -r line; do
  v=$(echo "$line" | sed 's/ *[a-z_A-Z]*  *#.*//')
  echo "--- $v ---"
  say -v "$v" "Claude Code App"
  sleep 1
done
```

### Speech rate

Adjust `-r 300` (words per minute). Default macOS rate is ~175. Higher = faster.

```bash
say -v Zarvox -r 150 "Claude Code App"  # slower
say -v Zarvox -r 300 "Claude Code App"  # current (fast)
say -v Zarvox -r 500 "Claude Code App"  # very fast
```

### Sounds

Replace `Basso.aiff` (alert) and `Submarine.aiff` (closing) with any macOS system sound.

**Available system sounds:**

| Sound | Style | Try it |
|---|---|---|
| `Basso` (default alert) | Deep, attention-grabbing | `afplay /System/Library/Sounds/Basso.aiff` |
| `Submarine` (default closing) | Subtle, underwater | `afplay /System/Library/Sounds/Submarine.aiff` |
| `Blow` | Soft blow | `afplay /System/Library/Sounds/Blow.aiff` |
| `Bottle` | Bottle pop | `afplay /System/Library/Sounds/Bottle.aiff` |
| `Frog` | Frog croak | `afplay /System/Library/Sounds/Frog.aiff` |
| `Funk` | Funky alert | `afplay /System/Library/Sounds/Funk.aiff` |
| `Glass` | Glass tap | `afplay /System/Library/Sounds/Glass.aiff` |
| `Hero` | Heroic fanfare | `afplay /System/Library/Sounds/Hero.aiff` |
| `Morse` | Morse code beep | `afplay /System/Library/Sounds/Morse.aiff` |
| `Ping` | Clean ping | `afplay /System/Library/Sounds/Ping.aiff` |
| `Pop` | Quick pop | `afplay /System/Library/Sounds/Pop.aiff` |
| `Purr` | Soft purr | `afplay /System/Library/Sounds/Purr.aiff` |
| `Sosumi` | Classic Mac alert | `afplay /System/Library/Sounds/Sosumi.aiff` |
| `Tink` | Light tap | `afplay /System/Library/Sounds/Tink.aiff` |

You can also use any `.aiff`, `.mp3`, or `.wav` file:
```bash
afplay /path/to/your/custom-sound.mp3
```

### Message

Change the `voice_label` values in the script to customize what is spoken:

```bash
# Examples:
voice_label="Hey, come back"
voice_label="Task complete"
voice_label="Attention needed in session $label"
```

### Desktop notification

The notification title and message come from the hook JSON. You can change the notification sound in the `terminal-notifier` call:

```bash
terminal-notifier -title "..." -message "..." -sound "Glass"  # any macOS sound name
```

## Troubleshooting

### Hooks don't fire after install/update

- **Restart required**: Hooks are loaded at session start. Close and reopen Claude Code (or start a new conversation in the Claude macOS app) for changes to take effect.
- **Invalid settings**: Starting from Claude Code v1.0.95, any invalid configuration in `~/.claude/settings.json` silently disables all hooks. Check for syntax errors.

### No notification appears

- **Install `terminal-notifier`**: Required for the Claude macOS desktop app (the sandbox silently blocks `osascript` notifications).
  ```bash
  brew install terminal-notifier
  ```
- Check macOS notification permissions: **System Settings > Notifications** — enable notifications for **terminal-notifier** and/or **Script Editor**.
- Test the script manually:
  ```bash
  echo '{"message":"test","title":"test"}' | bash hooks/scripts/notify.sh
  ```

### No sound plays

- Make sure your Mac volume is not muted.
- Test sound directly: `afplay /System/Library/Sounds/Basso.aiff`

### Voice says "Claude Code App" in the desktop app

- This is expected — the Claude macOS app label is "App".

### In iTerm2, voice says "Claude Code iTerm2" (generic label)

- This means the profile name wasn't detected. Make sure you opened the tab using a named profile (not Default).
- Verify `ITERM_SESSION_ID` is set: run `echo $ITERM_SESSION_ID` in the tab.

## Compatibility

| Environment | Notifications | Sound | Session ID |
|---|---|---|---|
| iTerm2 | Yes | Yes | Profile name |
| Claude macOS app (Code) | Yes (needs `terminal-notifier`) | Yes | "App" |
| Claude macOS app (Cowork) | Yes (needs `terminal-notifier`) | Yes | "Cowork" |
| VS Code terminal | Yes | Yes | "vscode" |
| macOS Terminal.app | Yes | Yes | "Apple_Terminal" |
| Ghostty | Yes | Yes | "ghostty" |
| Kitty | Yes | Yes | "kitty" |

## License

MIT — see [LICENSE](LICENSE) file.
