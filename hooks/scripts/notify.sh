#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ADAPTERS_DIR="$SCRIPT_DIR/../../adapters"

collect_parent_process_tree() {
    if [ -n "${NOTIFY_PARENT_PROCESS_TREE:-}" ]; then
        printf '%s' "$NOTIFY_PARENT_PROCESS_TREE"
        return 0
    fi

    local pid="$$"
    local depth=0
    local tree=""
    local command=""
    local parent=""

    while [ -n "$pid" ] && [ "$pid" -gt 1 ] 2>/dev/null && [ "$depth" -lt 12 ]; do
        command="$(ps -o command= -p "$pid" 2>/dev/null | sed 's/^ *//')"
        if [ -n "$command" ]; then
            if [ -n "$tree" ]; then
                tree="$tree\n$command"
            else
                tree="$command"
            fi
        fi

        parent="$(ps -o ppid= -p "$pid" 2>/dev/null | tr -d ' ')"
        if [ -z "$parent" ] || [ "$parent" = "$pid" ]; then
            break
        fi

        pid="$parent"
        depth=$((depth + 1))
    done

    printf '%b' "$tree"
}

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
    parent_tree="$(collect_parent_process_tree)"
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
