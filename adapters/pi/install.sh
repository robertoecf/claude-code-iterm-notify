#!/bin/bash
set -euo pipefail

# Pi notification adapter installer
# Symlinks the notify script to the plugin hooks directory

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ADAPTER_NAME="pi"
NOTIFY_SCRIPT="$SCRIPT_DIR/notify.sh"
TARGET_DIR="${PI_PLUGIN_ROOT:-$HOME/.config/superpowers/worktrees/claude-code-iterm-notify/codex-notify}"

echo "Installing Pi notification adapter..."

if [ ! -f "$NOTIFY_SCRIPT" ]; then
  echo "Error: notify.sh not found at $NOTIFY_SCRIPT"
  exit 1
fi

# Create adapters directory if needed
mkdir -p "$TARGET_DIR/adapters/$ADAPTER_NAME"

# Copy the notify script
cp "$NOTIFY_SCRIPT" "$TARGET_DIR/adapters/$ADAPTER_NAME/notify.sh"
chmod +x "$TARGET_DIR/adapters/$ADAPTER_NAME/notify.sh"

echo "✓ Pi adapter installed to $TARGET_DIR/adapters/$ADAPTER_NAME/"
echo ""
echo "To use with Pi, set in your Pi config:"
echo "  export PI_NOTIFY_LOG=/tmp/pi-notify-debug.log"
