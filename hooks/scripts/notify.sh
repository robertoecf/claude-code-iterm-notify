#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ADAPTERS_DIR="$SCRIPT_DIR/../../adapters"

# Auto-detect which adapter to use based on environment variables or process tree
if [ "${CODEX_IS_COWORK:-}" = "1" ] || [ "${CODEX_DESKTOP:-}" = "1" ]; then
    exec "$ADAPTERS_DIR/codex/notify.sh" "$@"
elif [ "${PI_IS_COWORK:-}" = "1" ] || [ "${PI_DESKTOP:-}" = "1" ]; then
    exec "$ADAPTERS_DIR/pi/notify.sh" "$@"
elif [ "${OPENCODE:-}" = "1" ]; then
    exec "$ADAPTERS_DIR/opencode/notify.sh" "$@"
elif [ "${CLAUDE_CODE_IS_COWORK:-}" = "1" ] || [ "${CLAUDE_CODE_ENTRYPOINT:-}" = "claude-desktop" ]; then
    exec "$ADAPTERS_DIR/claude/notify.sh" "$@"
else
    # Default: try to detect from process tree
    parent_tree="$(ps -o command= -p $$ 2>/dev/null | head -5)"
    if echo "$parent_tree" | grep -qi "codex"; then
        exec "$ADAPTERS_DIR/codex/notify.sh" "$@"
    elif echo "$parent_tree" | grep -qiE "(^|/)pi(| |-coding-agent)"; then
        exec "$ADAPTERS_DIR/pi/notify.sh" "$@"
    elif echo "$parent_tree" | grep -qi "opencode"; then
        exec "$ADAPTERS_DIR/opencode/notify.sh" "$@"
    else
        # Default to claude
        exec "$ADAPTERS_DIR/claude/notify.sh" "$@"
    fi
fi
