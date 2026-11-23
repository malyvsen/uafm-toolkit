#!/usr/bin/env bash
# Fail fast when UAFM credentials are missing, before anything needs them.
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
env_file="$root/.env"

required=(UAFM_USERNAME UAFM_PASSWORD UAFM_TOTP_SECRET)

value_from_file() {
  [ -f "$env_file" ] || return 0
  grep -E "^$1=" "$env_file" | tail -n 1 | cut -d= -f2- | tr -d "[:space:]" | tr -d "\"'"
}

effective_value() {
  if [ -n "${!1:-}" ]; then
    printf '%s' "${!1}"
  else
    value_from_file "$1"
  fi
}

missing=()
for name in "${required[@]}"; do
  [ -n "$(effective_value "$name")" ] || missing+=("$name")
done

if [ ${#missing[@]} -gt 0 ]; then
  if [ ! -f "$env_file" ]; then
    echo "Missing $env_file - run \`task init\`, then fill in ${missing[*]}." >&2
  else
    echo "Fill in ${missing[*]} in $env_file." >&2
  fi
  exit 1
fi
