#!/usr/bin/env bash
# Re-download the SunFounder UNO/Mega kit template that three of the .sb3
# generators read from the hardcoded /tmp path. /tmp is ephemeral, so this
# runs on every boot (via the `start` phase) and is idempotent.
set -euo pipefail

TEMPLATE_DIR="/tmp/uno/sunfounder-uno-and-mega-kit-master/scratch(uno)/code"
STAGE="${TEMPLATE_DIR}/1. Stage Mode.sb3"
UPLOAD="${TEMPLATE_DIR}/1. Upload Mode.sb3"
KIT_URL="https://github.com/sunfounder/sunfounder-uno-and-mega-kit/archive/refs/heads/master.zip"

if [[ -f "${STAGE}" && -f "${UPLOAD}" ]]; then
  echo "SunFounder template already present at ${TEMPLATE_DIR}"
  exit 0
fi

echo "Downloading SunFounder UNO/Mega kit template..."
mkdir -p /tmp/uno
tmp_zip="$(mktemp /tmp/uno/kit.XXXXXX.zip)"
curl -fsSL -o "${tmp_zip}" "${KIT_URL}"
unzip -q -o "${tmp_zip}" -d /tmp/uno
rm -f "${tmp_zip}"

if [[ -f "${STAGE}" && -f "${UPLOAD}" ]]; then
  echo "SunFounder template ready at ${TEMPLATE_DIR}"
else
  echo "ERROR: expected template files not found after extraction" >&2
  exit 1
fi
