#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SOURCE_SCRIPT="$ROOT_DIR/adapters/codex/notify.sh"
DEFAULT_TARGET="${HOME}/.codex/bin/codex-notify.sh"

print_usage() {
  cat <<'EOF'
Usage:
  install.sh --print-config [target-path]
  install.sh --install-script [target-path]
  install.sh --self-test [script-path]
EOF
}

print_config() {
  local target="${1:-$DEFAULT_TARGET}"
  printf 'notify = ["%s"]\n' "$target"
}

install_script() {
  local target="${1:-$DEFAULT_TARGET}"
  mkdir -p "$(dirname "$target")"
  cp "$SOURCE_SCRIPT" "$target"
  chmod +x "$target"
  printf 'Installed Codex notifier script to %s\n' "$target"
}

self_test() {
  local target="${1:-$SOURCE_SCRIPT}"
  NOTIFY_TEST_MODE=1 "$target" '{"type":"agent-turn-complete","cwd":"/tmp/example","last-assistant-message":"notifier pronto"}'
}

command_name="${1:-}"

case "$command_name" in
  --print-config)
    print_config "${2:-$DEFAULT_TARGET}"
    ;;
  --install-script)
    install_script "${2:-$DEFAULT_TARGET}"
    ;;
  --self-test)
    self_test "${2:-$SOURCE_SCRIPT}"
    ;;
  *)
    print_usage >&2
    exit 1
    ;;
esac
