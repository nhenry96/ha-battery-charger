#!/usr/bin/env bash
# Sync Node-RED addon files into the git repo.
#
# Run this on the HA host before committing to capture the latest flows:
#   bash /config/scripts/sync_nodered.sh
#
# The script copies flow and settings files from the live addon config
# directory into the tracked addon_configs/ directory in this repo,
# excluding credential files (which are gitignored).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

SRC="/addon_configs/a0d7b954_nodered"
DEST="${REPO_ROOT}/addon_configs/a0d7b954_nodered"

if [ ! -d "${SRC}" ]; then
  echo "ERROR: Source directory ${SRC} not found. Run this script on the HA host."
  exit 1
fi

echo "Syncing ${SRC} -> ${DEST}"

rsync -av \
  --exclude='*_cred.json' \
  --exclude='*.cred.json' \
  --exclude='.config.runtime.json' \
  --exclude='node_modules/' \
  --exclude='.npm/' \
  "${SRC}/" "${DEST}/"

echo ""
echo "Done. Review changes with: git diff addon_configs/"
echo "Then commit:               git add addon_configs/ && git commit -m 'chore: sync node-red flows'"
