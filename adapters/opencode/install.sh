#!/bin/bash
set -euo pipefail

# OpenCode notification adapter installer
# Symlinks the notify script to the plugin hooks directory

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ADAPTER_NAME="opencode"
NOTIFY_SCRIPT="$SCRIPT_DIR/notify.sh"
TARGET_DIR="${OPENCODE_PLUGIN_ROOT:-$HOME/.config/superpowers/worktrees/claude-code-iterm-notify/codex-notify}"

echo "Installing OpenCode notification adapter..."

if [ ! -f "$NOTIFY_SCRIPT" ]; then
  echo "Error: notify.sh not found at $NOTIFY_SCRIPT"
  exit 1
fi

# Create adapters directory if needed
mkdir -p "$TARGET_DIR/adapters/$ADAPTER_NAME"

# Copy the notify script
cp "$NOTIFY_SCRIPT" "$TARGET_DIR/adapters/$ADAPTER_NAME/notify.sh"
chmod +x "$TARGET_DIR/adapters/$ADAPTER_NAME/notify.sh"

echo "✓ OpenCode adapter installed to $TARGET_DIR/adapters/$ADAPTER_NAME/"
echo ""
echo "To use with OpenCode, set in your OpenCode config:"
echo "  export OPENCODE_NOTIFY_LOG=/tmp/opencode-notify-debug.log"
