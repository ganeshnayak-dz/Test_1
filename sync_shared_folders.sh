#!/bin/bash
# =============================================================================
# sync_shared_folders.sh
#
# STANDALONE COMMAND: pulls and syncs shared folders ONLY. It never touches
# the Genie Space, databricks.yml, or resources/*.yml - run this on its own
# any time you just want to refresh shared folders, with no risk of pulling
# or deploying any Genie Space changes.
#
# (It is ALSO called automatically as step 2 of pull_and_sync.sh, so you
# don't have to run it separately during your normal pull -> push cycle -
# but you're free to run it by itself whenever you like.)
#
# Keeps shared workspace folders (skills, reference notebooks, etc.) BOTH
# version-controlled in this Git repo AND live in each user's own workspace
# path. Based on entries listed in folder_sync_config.json.
#
# For each entry, this does two things:
#   A) (best-effort) Pull the current content from the live "master" copy
#      (master_src) down into a folder INSIDE this repo (repo_path). Because
#      repo_path lives inside the Git folder, it gets picked up by
#      `git add .` in push_and_deploy.sh and actually reaches GitHub.
#   B) Deploy whatever is currently in that repo folder out to the CURRENT
#      user's own live workspace path (dest), so it actually works as a
#      skill/notebook for them.
#
# Step A only succeeds for whoever has read access to master_src (usually
# the folder's owner) - that's fine. Everyone else still gets step B, using
# whatever is already in repo_path (e.g. from a `git pull`), so the config
# file works for anyone regardless of whether they can reach the master.
#
# You do NOT edit this script to add/remove folders - edit
# folder_sync_config.json instead. Any {username} in a path is replaced
# with whoever runs this script (their Databricks userName/email).
#
# Usage:
#   bash sync_shared_folders.sh                     # uses folder_sync_config.json
#   bash sync_shared_folders.sh path/to/other.json   # use a different config file
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

CONFIG_FILE="${1:-folder_sync_config.json}"

if [ ! -f "$CONFIG_FILE" ]; then
  echo "❌ Config file not found: $CONFIG_FILE"
  echo "   Create folder_sync_config.json in this folder, or pass a path as the first argument."
  exit 1
fi

echo "=================================================================="
echo " Folder Sync  (config: $CONFIG_FILE)"
echo "=================================================================="

echo "Detecting current user..."
CURRENT_USER=$(databricks current-user me --output json | python3 -c "import json,sys; print(json.load(sys.stdin)['userName'])")
if [ -z "$CURRENT_USER" ]; then
  echo "❌ Could not determine current user via 'databricks current-user me'."
  exit 1
fi
echo "  Current user: $CURRENT_USER"
echo ""

NORMALIZED=$(mktemp)
trap 'rm -f "$NORMALIZED"' EXIT

python3 - "$CONFIG_FILE" > "$NORMALIZED" << 'PYEOF'
import json, sys
data = json.load(open(sys.argv[1]))
for item in data.get("folders", []):
    master_src = item.get("master_src", "").strip()
    repo_path = item.get("repo_path", "").strip()
    dest = item.get("dest", "").strip()
    if repo_path and dest:
        print(f"{master_src}|{repo_path}|{dest}")
PYEOF

if [ ! -s "$NORMALIZED" ]; then
  echo "(No folder entries found in $CONFIG_FILE - nothing to sync. Add entries to the \"folders\" list.)"
  exit 0
fi

LOG_DIR=$(mktemp -d)
trap 'rm -rf "$LOG_DIR" "$NORMALIZED"' EXIT

LINE_NUM=0
DEPLOYED=0
FAILED=0

while IFS='|' read -r MASTER_SRC REPO_PATH DEST; do
  LINE_NUM=$((LINE_NUM+1))

  MASTER_SRC="${MASTER_SRC//\{username\}/$CURRENT_USER}"
  REPO_PATH="${REPO_PATH//\{username\}/$CURRENT_USER}"
  DEST="${DEST//\{username\}/$CURRENT_USER}"
  ABS_REPO_PATH="$SCRIPT_DIR/$REPO_PATH"

  echo "-------------------------------------------------------------"
  echo "[$LINE_NUM] repo path: $REPO_PATH"

  mkdir -p "$ABS_REPO_PATH"

  # --- Step A: refresh the repo's copy from the live master (best-effort) ---
  if [ -n "$MASTER_SRC" ]; then
    echo "    Pulling from master: $MASTER_SRC"
    if databricks workspace export-dir "$MASTER_SRC" "$ABS_REPO_PATH" --overwrite > "$LOG_DIR/export_$LINE_NUM.log" 2>&1; then
      echo "    ✅ Repo copy refreshed from master - will be committed/pushed on your next push_and_deploy.sh."
    else
      echo "    ⚠️  Could not read master_src (no access, or it doesn't exist for you)."
      echo "       Using whatever is already in $REPO_PATH instead (e.g. from a git pull)."
    fi
  else
    echo "    (no master_src set - using whatever is already in $REPO_PATH, e.g. from a git pull)"
  fi

  # --- Step B: deploy the repo's copy out to the current user's live workspace path ---
  if [ -z "$(ls -A "$ABS_REPO_PATH" 2>/dev/null)" ]; then
    echo "    ❌ $REPO_PATH is empty - nothing to deploy to $DEST yet."
    echo "       Either set master_src to a real path you can read, or 'git pull' to get files someone else already committed here."
    FAILED=$((FAILED+1))
    continue
  fi

  echo "    Deploying to your workspace: $DEST"
  databricks workspace mkdirs "$(dirname "$DEST")" > /dev/null 2>&1 || true
  if databricks workspace import-dir "$ABS_REPO_PATH" "$DEST" --overwrite > "$LOG_DIR/import_$LINE_NUM.log" 2>&1; then
    echo "    ✅ Deployed."
    DEPLOYED=$((DEPLOYED+1))
  else
    echo "    ❌ Deploy failed:"
    cat "$LOG_DIR/import_$LINE_NUM.log"
    FAILED=$((FAILED+1))
  fi
done < "$NORMALIZED"

echo "-------------------------------------------------------------"
echo "Folder sync done. Deployed to your workspace: $DEPLOYED   Failed: $FAILED"
echo "(Repo copies under the paths above are now local files here - run push_and_deploy.sh to commit/push them.)"
echo ""
