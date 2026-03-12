# claude-code-iterm-notify

macOS notification plugin for Claude Code running in iTerm2. Plays sound alerts and identifies which session needs your attention by profile name.

## What it does

When Claude Code needs your authorization or input, you get:

1. **Desktop notification** (macOS Notification Center) with Submarine sound
2. **Audio alert**: Basso sound + Zarvox voice saying "Claude Code {session name}" simultaneously
3. **Closing sound**: Submarine

The session name comes from your **iTerm2 profile name**, so it works even if you reorder, close, or reopen tabs.

## Requirements

- macOS (uses `osascript`, `afplay`, `say`)
- [iTerm2](https://iterm2.com/) (uses `ITERM_SESSION_ID` and AppleScript for profile name detection)
- Claude Code v2.1+

> **Note:** This plugin does NOT work with the Claude desktop app or macOS Terminal.app — it requires iTerm2 specifically.

## Installation

### From local directory

```bash
claude /plugin install /path/to/claude-code-iterm-notify
```

### From GitHub

```bash
claude /plugin install github:robertoecf/claude-code-iterm-notify
```

## Setup: Creating iTerm2 profiles (step by step)

The plugin identifies each Claude Code session by its **iTerm2 profile name**. You need to create one profile per session you want to run. Here's how:

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
2. Extracts the session GUID from `$ITERM_SESSION_ID`
3. Queries iTerm2 via AppleScript to find the matching session's **profile name**
4. Sends a macOS desktop notification
5. Plays Basso + Zarvox voice (simultaneous), then Submarine — detached via `nohup` so it doesn't block Claude

## Customization

Edit `hooks/scripts/notify.sh` to change:

- **Sounds**: Replace `Basso.aiff` / `Submarine.aiff` with any file in `/System/Library/Sounds/`
  ```bash
  ls /System/Library/Sounds/  # list available sounds
  ```
- **Voice**: Change `-v Zarvox` to another macOS voice
  ```bash
  say -v ?  # list all available voices
  ```
- **Speech rate**: Adjust `-r 300` (words per minute)
- **Message**: Change `"Claude Code $session_name"` to whatever you want

## Troubleshooting

### No sound plays
- Make sure your Mac volume is not muted
- Test the script manually: `echo '{"message":"test","title":"test"}' | bash hooks/scripts/notify.sh`

### Voice says "Claude Code ?"
- The `?` fallback means iTerm2 profile name couldn't be detected
- Make sure you opened the tab using a named profile (not the Default profile)
- Verify `ITERM_SESSION_ID` is set: run `echo $ITERM_SESSION_ID` in the tab

### Notification doesn't fire
- Make sure macOS notifications are enabled for iTerm2 in **System Settings > Notifications**
- Restart Claude Code after installing the plugin (hooks load at session start)

## License

MIT — see [LICENSE](LICENSE) file.
