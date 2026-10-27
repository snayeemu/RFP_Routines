#!/bin/sh
# Build mybidmatch_screening.zip for installing on another Mac (see automation/SETUP.md).
# Leaves out run output, state, the tracker workbook and the reference download folders;
# the package gets an empty state file and blank settings instead.
set -e
root="$(cd "$(dirname "$0")/.." && pwd)"
out="$root/mybidmatch_screening.zip"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
rm -f "$out"
cd "$root"
zip -rq "$out" INSTALL_PROMPT.md automation Inovi_Profile .mcp.json .claude/settings.local.json \
  -x 'automation/state/*' 'automation/config.json' 'automation/package.sh' '*/__pycache__/*' '*.DS_Store'
mkdir -p "$tmp/automation/state"
echo '{"processed": []}' > "$tmp/automation/state/processed.json"
# Blank settings: the installer fills them (INSTALL_PROMPT.md), so the test recipient never ships.
echo '{"recipient": "", "start_date": ""}' > "$tmp/automation/config.json"
mkdir -p "$tmp/runs"
(cd "$tmp" && zip -q "$out" automation/state/processed.json automation/config.json runs/)
echo "wrote $out"
