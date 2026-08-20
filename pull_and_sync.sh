#!/bin/bash
# =============================================================================
# pull_and_sync.sh
#
# COMMAND 1 of 2: Pull the live Genie Space into the bundle files, and sync
# the shared folders alongside it - so both always stay in step. Reads
# space_id / resource_key from config.json.
#
# Usage:
#   bash pull_and_sync.sh              # pull genie space + sync folders
#   bash pull_and_sync.sh --validate   # + validate the bundle afterwards
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

CONFIG_FILE="config.json"
if [ ! -f "$CONFIG_FILE" ]; then
  echo "❌ config.json not found in $SCRIPT_DIR"
  echo "   Run init_genie_bundle.sh first, or create config.json by hand (see README.md)."
  exit 1
fi

json_get() {
  python3 -c "
import json, sys
d = json.load(open('$CONFIG_FILE'))
v = d.get('$1', '')
print(str(v).lower() if isinstance(v, bool) else v)
"
}

SPACE_ID="$(json_get space_id)"
RESOURCE_KEY="$(json_get resource_key)"

if [ -z "$SPACE_ID" ] || [ -z "$RESOURCE_KEY" ]; then
  echo "❌ config.json is missing space_id or resource_key. Check the file and try again."
  exit 1
fi

echo "[1/3] Pulling Genie Space (ID: $SPACE_ID) into bundle..."
databricks bundle generate genie-space \
  --existing-id "$SPACE_ID" \
  --target dev \
  --key "$RESOURCE_KEY" \
  --force
echo "      Pull complete."

echo "      Restoring dynamic references..."
GENERATED_YML="resources/${RESOURCE_KEY}.genie_space.yml"
if [ -f "$GENERATED_YML" ]; then
  python3 postprocess_generated_yml.py < "$GENERATED_YML" > "${GENERATED_YML}.tmp" && mv "${GENERATED_YML}.tmp" "$GENERATED_YML"
else
  echo "      ⚠️  Could not find $GENERATED_YML - check resource_key in config.json."
fi

echo ""
echo "[2/3] Syncing shared folders..."
if [ -f "sync_shared_folders.sh" ]; then
  bash sync_shared_folders.sh || echo "      ⚠️  Folder sync reported errors above - continuing anyway."
else
  echo "      ⚠️  sync_shared_folders.sh not found - skipping folder sync."
fi

if [[ "$1" == "--validate" ]]; then
  echo ""
  echo "[3/3] Validating bundle..."
  databricks bundle validate --strict --target dev
  echo "      Validation passed."
else
  echo ""
  echo "[3/3] Skipping validation (use --validate to include)"
fi

echo ""
echo "Done. Files are up to date locally but NOT yet pushed to Git."
echo "Next: bash push_and_deploy.sh   (or push_and_deploy.sh 'my commit message')"
