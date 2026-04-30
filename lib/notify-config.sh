#!/bin/bash
# Shared notification preferences for agentic-coding-notify.
# Reads ~/.agentic-coding-notify/config.json by default. The file is optional;
# adapters keep their built-in defaults when no config exists.

notify_config_path() {
  printf '%s' "${AGENTIC_CODING_NOTIFY_CONFIG:-$HOME/.agentic-coding-notify/config.json}"
}

notify_config_field() {
  local key="$1"
  local default_value="${2:-}"
  local path
  path="$(notify_config_path)"
  CONFIG_PATH="$path" CONFIG_KEY="$key" CONFIG_DEFAULT="$default_value" /usr/bin/python3 - <<'PY'
import json
import os
from pathlib import Path

path = Path(os.environ["CONFIG_PATH"])
key = os.environ["CONFIG_KEY"]
default = os.environ.get("CONFIG_DEFAULT", "")
try:
    data = json.loads(path.read_text()) if path.exists() else {}
except Exception:
    data = {}
value = data.get(key, default)
if value is None:
    value = default
print(str(value))
PY
}

notify_voice_name() {
  notify_config_field voice "${1:-Samantha}"
}

notify_voice_rate() {
  notify_config_field rate "${1:-300}"
}

notify_notification_sound() {
  notify_config_field notification_sound "${1:-Submarine}"
}

notify_sound_path() {
  local key="$1"
  local default_path="$2"
  local configured
  configured="$(notify_config_field "$key" "$default_path")"

  if [ -z "$configured" ] || [ "$configured" = "none" ] || [ "$configured" = "None" ]; then
    printf '%s' ""
    return 0
  fi

  if [ -f "$configured" ]; then
    printf '%s' "$configured"
    return 0
  fi

  configured="${configured%.aiff}"
  if [ -f "/System/Library/Sounds/$configured.aiff" ]; then
    printf '%s' "/System/Library/Sounds/$configured.aiff"
    return 0
  fi

  printf '%s' "$default_path"
}

notify_start_sound_path() {
  notify_sound_path start_sound "${1:-/System/Library/Sounds/Basso.aiff}"
}

notify_end_sound_path() {
  notify_sound_path end_sound "${1:-/System/Library/Sounds/Submarine.aiff}"
}

notify_speak_tab_title() {
  local value
  value="$(notify_config_field speak_tab_title "true")"
  case "$value" in
    false|False|FALSE|0|no|No|NO|off|Off|OFF) printf 'false' ;;
    *) printf 'true' ;;
  esac
}

notify_context_kind() {
  local label="$1"
  case "$label" in
    App|*" App") printf 'app' ;;
    *) printf 'cli' ;;
  esac
}

notify_effective_voice_text() {
  local service="$1"
  local label="$2"
  local default_voice_label="$3"
  local message="${4:-}"
  local context template speak_tab_title spoken_label voice_label_value
  context="$(notify_context_kind "$label")"
  speak_tab_title="$(notify_speak_tab_title)"
  spoken_label="$label"
  voice_label_value="$default_voice_label"
  if [ "$context" = "cli" ] && [ "$speak_tab_title" = "false" ]; then
    spoken_label=""
    voice_label_value="$service"
  fi

  template="$(notify_config_field voice_text_template "")"
  if [ -z "$template" ]; then
    if [ "$context" = "app" ]; then
      template="$(notify_config_field app_voice_text_template "{voice_label}")"
    else
      template="$(notify_config_field cli_voice_text_template "{voice_label}")"
    fi
  fi

  SERVICE_VALUE="$service" \
  LABEL_VALUE="$spoken_label" \
  VOICE_LABEL_VALUE="$voice_label_value" \
  MESSAGE_VALUE="$message" \
  TEMPLATE_VALUE="$template" \
  CONTEXT_VALUE="$context" \
  /usr/bin/python3 - <<'PY'
import os

template = os.environ.get("TEMPLATE_VALUE") or "{voice_label}"
values = {
    "service": os.environ.get("SERVICE_VALUE", ""),
    "label": os.environ.get("LABEL_VALUE", ""),
    "voice_label": os.environ.get("VOICE_LABEL_VALUE", ""),
    "message": os.environ.get("MESSAGE_VALUE", ""),
    "context": os.environ.get("CONTEXT_VALUE", ""),
}
for key, value in values.items():
    template = template.replace("{" + key + "}", value)
print(" ".join(template.split()))
PY
}

notify_dispatch_audio() {
  local log_file="$1"
  local service="$2"
  local label="$3"
  local default_voice_label="$4"
  local message="${5:-}"
  local voice rate start_sound end_sound voice_text

  voice="$(notify_voice_name Samantha)"
  rate="$(notify_voice_rate 300)"
  start_sound="$(notify_start_sound_path /System/Library/Sounds/Basso.aiff)"
  end_sound="$(notify_end_sound_path /System/Library/Sounds/Submarine.aiff)"
  voice_text="$(notify_effective_voice_text "$service" "$label" "$default_voice_label" "$message")"

  printf '%s | AUDIO voice=%s rate=%s start=%s end=%s text=%s\n' \
    "$(date '+%Y-%m-%d %H:%M:%S')" "$voice" "$rate" "${start_sound:-none}" "${end_sound:-none}" "$voice_text" >> "$log_file"

  (
    if [ -n "$start_sound" ]; then
      afplay "$start_sound" &
    fi
    say -v "$voice" -r "$rate" -- "$voice_text"
    if [ -n "$end_sound" ]; then
      afplay "$end_sound"
    fi
  ) >> "$log_file" 2>&1 &
  disown
}
