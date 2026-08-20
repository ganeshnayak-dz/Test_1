#!/bin/bash
# ============================================================================
# Genie Agent DAB - Interactive Initial Setup Script
#
# Run this ONCE inside an empty Git folder (via the Databricks Web Terminal)
# to bootstrap a brand-new Genie Agent bundle project. It is the ONLY file
# you need to paste in to begin - it writes everything else:
#
#   config.json                 - central config (space id, warehouse id, ...)
#   databricks.yml               - the DAB project file
#   resources/, src/             - pulled from your live Genie Space
#   postprocess_generated_yml.py - restores dynamic var references
#   pull_and_sync.sh             - COMMAND 1: pull genie space + sync folders
#   push_and_deploy.sh           - COMMAND 2: validate/deploy, then commit+push
#   sync_shared_folders.sh       - copies shared workspace folders per-user
#   folder_sync_config.json      - the editable list of folders to sync
#   README.md                    - full usage guide
#
# Usage:
#   bash init_genie_bundle.sh
# ============================================================================

set -e

echo "=================================================================="
echo " Genie Agent DAB - Initial Setup"
echo "=================================================================="
echo ""

# If config.json already exists WITH a space_id filled in, use it directly -
# no prompting for it or anything else already answered. This is the case
# when you've hand-edited config.json (e.g. to point at a new Space ID) and
# just want init_genie_bundle.sh to pick that up and (re)build the project
# from it.
USE_EXISTING_CONFIG="n"
if [ -f "config.json" ]; then
  CFG_SPACE_ID="$(python3 -c "import json; print(json.load(open('config.json')).get('space_id',''))" 2>/dev/null)"
  if [ -n "$CFG_SPACE_ID" ] && [ "$CFG_SPACE_ID" != "PASTE_YOUR_GENIE_SPACE_ID_HERE" ]; then
    USE_EXISTING_CONFIG="y"
    SPACE_ID="$CFG_SPACE_ID"
    BUNDLE_NAME="$(python3 -c "import json; print(json.load(open('config.json')).get('bundle_name',''))" 2>/dev/null)"
    SPACE_TITLE="$(python3 -c "import json; print(json.load(open('config.json')).get('title',''))" 2>/dev/null)"
    RESOURCE_KEY="$(python3 -c "import json; print(json.load(open('config.json')).get('resource_key',''))" 2>/dev/null)"
    ADD_TEST_TARGET="$(python3 -c "import json; print('y' if json.load(open('config.json')).get('test_target') else 'n')" 2>/dev/null)"
    TEST_HOST="$(python3 -c "import json; print(json.load(open('config.json')).get('test_host',''))" 2>/dev/null)"
    TEST_WAREHOUSE_ID_INPUT="$(python3 -c "
import json
v = json.load(open('config.json')).get('test_warehouse_id','')
print('' if v == 'auto-detected-on-first-run' else v)
" 2>/dev/null)"
    echo "ℹ️  Found config.json with a Space ID already set - using it directly, no prompts for it:"
    echo "     space_id:      $SPACE_ID"
    echo "     bundle_name:   $BUNDLE_NAME"
    echo "     title:         $SPACE_TITLE"
    echo "     resource_key:  $RESOURCE_KEY"
    echo "     test_target:   $ADD_TEST_TARGET"
    echo ""
    echo "   (To change any of these, edit config.json directly and re-run this script -"
    echo "   or for everyday work, you don't need this script at all: use"
    echo "   'bash pull_and_sync.sh' and 'bash push_and_deploy.sh' instead.)"
    echo ""
  fi
fi

if [ -f "databricks.yml" ]; then
  echo "⚠️  A databricks.yml already exists in this folder."
  read -p "   Overwrite and continue? (y/N): " CONFIRM
  if [[ "$CONFIRM" != "y" && "$CONFIRM" != "Y" ]]; then
    echo "Aborted."
    exit 1
  fi
fi

if [[ "$USE_EXISTING_CONFIG" != "y" ]]; then
  # --- Collect inputs (no config.json yet, or it has no space_id set) ---
  read -p "1) Existing Genie Space ID (Genie UI -> About -> Space ID, or from the URL): " SPACE_ID
  while [ -z "$SPACE_ID" ]; do
    read -p "   Space ID cannot be empty. Try again: " SPACE_ID
  done

  read -p "2) Bundle name (e.g. my-project-genie-agent): " BUNDLE_NAME
  while [ -z "$BUNDLE_NAME" ]; do
    read -p "   Bundle name cannot be empty. Try again: " BUNDLE_NAME
  done

  read -p "3) Display title for the Genie Space (e.g. 'My Project Genie Agent'): " SPACE_TITLE
  while [ -z "$SPACE_TITLE" ]; do
    read -p "   Title cannot be empty. Try again: " SPACE_TITLE
  done

  # Auto-suggest a resource key from the bundle name (letters/digits -> _)
  SUGGESTED_KEY="$(echo "$BUNDLE_NAME" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/_/g; s/^_+|_+$//g')"
  read -p "4) Resource key [press Enter to use: ${SUGGESTED_KEY}]: " RESOURCE_KEY
  RESOURCE_KEY="${RESOURCE_KEY:-$SUGGESTED_KEY}"

  read -p "5) Also set up a 'test' target, so --deploy-test works? (Y/n): " ADD_TEST_TARGET
  if [[ "$ADD_TEST_TARGET" == "n" || "$ADD_TEST_TARGET" == "N" ]]; then
    ADD_TEST_TARGET="n"
  else
    ADD_TEST_TARGET="y"
  fi
  if [[ "$ADD_TEST_TARGET" == "y" ]]; then
    read -p "   Test workspace host URL (leave blank to use the same workspace): " TEST_HOST
    read -p "   Warehouse ID for test target (leave blank to auto-detect / reuse dev's): " TEST_WAREHOUSE_ID_INPUT
  fi
fi

read -p "6) Deploy a dev copy right now after setup? (y/N): " DO_DEPLOY
read -p "7) Sync shared folders right now too (see folder_sync_config)? (y/N): " DO_FOLDER_SYNC

echo ""
echo "-------------------------------------------------------------"
echo " Summary:"
echo "   Space ID:       $SPACE_ID"
echo "   Bundle name:    $BUNDLE_NAME"
echo "   Title:          $SPACE_TITLE"
echo "   Resource key:   $RESOURCE_KEY"
echo "   Test target:    $ADD_TEST_TARGET"
echo "   Warehouse ID:   will be auto-detected from the live space"
echo "-------------------------------------------------------------"
read -p "Proceed with these values? (y/N): " CONFIRM_ALL
if [[ "$CONFIRM_ALL" != "y" && "$CONFIRM_ALL" != "Y" ]]; then
  echo "Aborted. Re-run the script to try again."
  exit 1
fi

mkdir -p resources src

# --- Step 1: minimal databricks.yml, just enough for `bundle generate` to run ---
echo ""
echo "[1/9] Creating a minimal databricks.yml (warehouse ID not known yet) ..."
cat > databricks.yml << EOF
bundle:
  name: ${BUNDLE_NAME}
  engine: direct

include:
  - resources/*.yml

targets:
  dev:
    default: true
    mode: development
EOF
echo "      Done."

# --- Step 2: pull the existing space (this is where we learn the real warehouse_id) ---
echo "[2/9] Pulling existing Genie Space (ID: $SPACE_ID) into files ..."
databricks bundle generate genie-space \
  --existing-id "$SPACE_ID" \
  --target dev \
  --key "$RESOURCE_KEY" \
  --force
echo "      Done."

GENERATED_YML="resources/${RESOURCE_KEY}.genie_space.yml"
if [ ! -f "$GENERATED_YML" ]; then
  echo "❌ Expected $GENERATED_YML but it wasn't created. Check the Space ID and resource key, then re-run."
  exit 1
fi

# --- Step 3: auto-detect the warehouse ID from what was just pulled ---
echo "[3/9] Auto-detecting warehouse ID from the pulled space ..."
DETECTED_WAREHOUSE_ID="$(grep -m1 'warehouse_id:' "$GENERATED_YML" | sed -E 's/.*warehouse_id:[[:space:]]*//; s/["'"'"']//g; s/[[:space:]]*$//')"
if [ -z "$DETECTED_WAREHOUSE_ID" ]; then
  echo "   ⚠️  Could not auto-detect a warehouse ID from $GENERATED_YML."
  read -p "   Please enter the SQL warehouse ID manually: " DETECTED_WAREHOUSE_ID
else
  echo "      Detected warehouse ID: $DETECTED_WAREHOUSE_ID"
fi
TEST_WAREHOUSE_ID="${TEST_WAREHOUSE_ID_INPUT:-$DETECTED_WAREHOUSE_ID}"

# --- Step 4: write postprocess_generated_yml.py ---
echo "[4/9] Writing postprocess_generated_yml.py ..."
cat > postprocess_generated_yml.py << 'PYEOF'
#!/usr/bin/env python3
"""Restore dynamic DAB variable references after bundle generate.

Reads a YAML file from stdin, replaces hardcoded warehouse_id and
parent_path with DAB variable references, outputs to stdout.

Usage: python3 postprocess_generated_yml.py < input.yml > output.yml
"""
import re
import sys

text = sys.stdin.read()

# 16-char hex warehouse_id -> ${var.warehouse_id}
text = re.sub(
    r'(warehouse_id:\s*)[a-f0-9]{16}',
    r'\g<1>${var.warehouse_id}',
    text,
)

# /Workspace/Users/<any-user> -> dynamic current_user
text = re.sub(
    r'(parent_path:\s*)/Workspace/Users/[^\s]+',
    r'\g<1>/Workspace/Users/${workspace.current_user.userName}',
    text,
)

sys.stdout.write(text)
PYEOF
echo "      Done."

# --- Step 5: restore dynamic references in the just-generated file ---
echo "[5/9] Restoring dynamic references in generated YAML ..."
python3 postprocess_generated_yml.py < "$GENERATED_YML" > "${GENERATED_YML}.tmp" && mv "${GENERATED_YML}.tmp" "$GENERATED_YML"
echo "      Done."

# --- Step 6: rewrite databricks.yml fully, now that we know the warehouse ID ---
echo "[6/9] Rewriting databricks.yml with the full configuration ..."

TEST_TARGET_BLOCK=""
if [[ "$ADD_TEST_TARGET" == "y" ]]; then
  HOST_LINE=""
  if [ -n "$TEST_HOST" ]; then
    HOST_LINE="      host: ${TEST_HOST}
"
  fi
  TEST_TARGET_BLOCK=$(cat << EOF

  test:
    mode: production
    workspace:
${HOST_LINE}      root_path: /Workspace/Users/\${workspace.current_user.userName}/.bundle/\${bundle.name}/\${bundle.target}
    variables:
      warehouse_id: ${TEST_WAREHOUSE_ID}
    resources:
      genie_spaces:
        ${RESOURCE_KEY}:
          title: '[Test] ${SPACE_TITLE}'
          warehouse_id: \${var.warehouse_id}
          parent_path: /Workspace/Users/\${workspace.current_user.userName}
EOF
)
fi

cat > databricks.yml << EOF
bundle:
  name: ${BUNDLE_NAME}
  engine: direct

include:
  - resources/*.yml

variables:
  warehouse_id:
    description: SQL warehouse ID for the Genie space
    default: ${DETECTED_WAREHOUSE_ID}

targets:
  dev:
    default: true
    mode: development
    workspace:
      root_path: /Workspace/Users/\${workspace.current_user.userName}/.bundle/\${bundle.name}/\${bundle.target}
    resources:
      genie_spaces:
        ${RESOURCE_KEY}:
          title: '[Dev] ${SPACE_TITLE}'
          warehouse_id: \${var.warehouse_id}
          parent_path: /Workspace/Users/\${workspace.current_user.userName}
${TEST_TARGET_BLOCK}
EOF
echo "      Done."

# --- Step 7: write config.json - the single source of truth other scripts read from ---
echo "[7/9] Writing config.json ..."
python3 - "$BUNDLE_NAME" "$RESOURCE_KEY" "$SPACE_TITLE" "$SPACE_ID" "$DETECTED_WAREHOUSE_ID" "$ADD_TEST_TARGET" "$TEST_HOST" "$TEST_WAREHOUSE_ID" << 'PYEOF'
import json, sys
(bundle_name, resource_key, title, space_id, warehouse_id,
 add_test_target, test_host, test_warehouse_id) = sys.argv[1:9]
config = {
    "bundle_name": bundle_name,
    "resource_key": resource_key,
    "title": title,
    "space_id": space_id,
    "warehouse_id": warehouse_id,
    "test_target": add_test_target == "y",
    "test_host": test_host,
    "test_warehouse_id": test_warehouse_id,
}
with open("config.json", "w") as f:
    json.dump(config, f, indent=2)
    f.write("\n")
PYEOF
echo "      Done."

# --- Step 8: write pull_and_sync.sh, push_and_deploy.sh, sync_shared_folders.sh, sample folder config, README ---
echo "[8/9] Writing sync scripts, sample folder-sync config, and README.md ..."

cat > sync_shared_folders.sh << 'SFEOF'
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
SFEOF
chmod +x sync_shared_folders.sh

cat > pull_and_sync.sh << 'PSEOF'
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
PSEOF
chmod +x pull_and_sync.sh

cat > push_and_deploy.sh << 'PDEOF'
#!/bin/bash
# =============================================================================
# push_and_deploy.sh
#
# COMMAND 2 of 2: Runs the bundle checks (and optionally a deploy), THEN
# commits and pushes to Git - with a commit message you give it, or a
# default one if you don't.
#
# Usage:
#   bash push_and_deploy.sh                          # validate, commit (default msg), push
#   bash push_and_deploy.sh 'my commit message'      # validate, commit (custom msg), push
#   bash push_and_deploy.sh --deploy-test                        # validate + deploy to test, commit (default msg), push
#   bash push_and_deploy.sh --deploy-test 'my commit message'    # validate + deploy to test, commit (custom msg), push
#
# Run pull_and_sync.sh first if you haven't already - this script does not
# pull the Genie Space or sync folders itself, it only checks/deploys/pushes
# whatever is currently sitting in your files.
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

HAS_TEST_TARGET="$(json_get test_target)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

DEPLOY_TEST="false"
if [[ "$1" == "--deploy-test" ]]; then
  DEPLOY_TEST="true"
  COMMIT_MSG="${2:-sync genie space changes}"
else
  COMMIT_MSG="${1:-sync genie space changes}"
fi

echo "[1/3] Validating bundle..."
databricks bundle validate --strict --target dev
echo "      Validation passed."

if [[ "$DEPLOY_TEST" == "true" ]]; then
  echo ""
  echo "      Deploying to test workspace..."
  if [[ "$HAS_TEST_TARGET" != "true" ]]; then
    echo "      ⚠️  config.json has test_target=false (or is missing it) - no 'test' target expected."
    echo "      Add one via init_genie_bundle.sh (test target option) or edit databricks.yml/config.json by hand."
    echo "      Skipping deploy."
  elif databricks bundle validate --target test > /dev/null 2>&1; then
    databricks bundle deploy --target test
    echo "      Deployment to test complete."
  else
    echo "      ⚠️  config.json says test_target=true, but no valid 'test' target found in databricks.yml."
    echo "      Check the 'test:' block under targets: in databricks.yml. Skipping deploy."
  fi
fi

echo ""
echo "[2/3] Committing and pushing to Git..."
echo "      Commit message: $COMMIT_MSG"
(
  cd "$REPO_ROOT"
  if git status > /dev/null 2>&1; then
    git add .
    git commit -m "$COMMIT_MSG" || echo "      Nothing new to commit."
    if git push origin "$(git branch --show-current)"; then
      echo "      Git commit and push complete."
    else
      echo "      ⚠️  Commit succeeded locally, but 'git push' failed (see the error above)."
      echo "      Common causes: no 'origin' remote configured, no upstream branch, or an auth issue."
      echo "      Your commit is saved locally - push it via the Workspace Git sidebar (Git icon > Commit & Push)"
      echo "      or ask the Databricks Assistant: 'push my changes'."
    fi
  else
    echo "      ⚠️  Git CLI not available from terminal."
    echo "      To commit, use one of these methods:"
    echo "        1. Workspace Git sidebar (left panel > Git icon > Commit & Push)"
    echo "        2. Ask the Databricks Assistant: 'commit and push my changes'"
    echo ""
    echo "      Changes are saved in workspace but NOT yet pushed to remote."
  fi
)

echo ""
echo "[3/3] Done."
if [[ "$DEPLOY_TEST" != "true" ]]; then
  echo "(No deploy was requested - use --deploy-test as the first argument to also promote to the test target.)"
fi
PDEOF
chmod +x push_and_deploy.sh

if [ ! -f "folder_sync_config.json" ]; then
  cat > folder_sync_config.json << 'JSONEOF'
{
  "_comment": "One entry per folder to keep in sync. master_src = the LIVE workspace path of the shared/master copy - pulled into repo_path on a best-effort basis, so only whoever has read access to it needs this to succeed; everyone else still gets deployed from whatever is already in repo_path (e.g. from a git pull). repo_path = where that content lives INSIDE this Git repo (relative to this folder) - this is what actually gets committed and pushed to GitHub. dest = the LIVE workspace path repo_path gets deployed to for whoever is currently running the sync. {username} anywhere in master_src or dest is replaced with the current Databricks user (their userName/email) at run time. Using {username} in master_src (as below) is just a generic placeholder - in real use, set master_src to ONE FIXED path (the actual owner's account), so everyone pulls the same shared source; only dest should vary per-user.",
  "folders": [
    {
      "master_src": "/Workspace/Users/{username}/.assistant/skills/marketing-eda-notebook",
      "repo_path": "shared_folders/marketing-eda-notebook",
      "dest": "/Workspace/Users/{username}/.assistant/skills/marketing-eda-notebook"
    }
  ]
}
JSONEOF
  echo "      Wrote sample folder_sync_config.json - edit its \"folders\" list to add/remove folders."
else
  echo "      folder_sync_config.json already exists - left untouched."
fi

if [ ! -f "README.md" ]; then
cat > README.md << 'MDEOF'
# Genie Agent DAB - Setup & Sync Guide

This project keeps a Databricks Genie Space under version control using a
Databricks Asset Bundle (DAB), and keeps a set of shared workspace folders
(skills, reference notebooks, etc.) in sync alongside it.

## Files in this project

| File | Purpose |
|---|---|
| `init_genie_bundle.sh` | One-time interactive setup. Run this first, only once, in a brand-new empty Git folder. |
| `config.json` | Central config: Space ID, warehouse ID, bundle name, resource key, test-target settings. Edit this instead of the scripts. |
| `databricks.yml` | The DAB project file (generated from `config.json`). |
| `resources/*.genie_space.yml` | Genie Space resource definition, pulled from the live space. |
| `src/*.geniespace.json` | The actual Genie Space content (instructions, SQL examples, tables). |
| `postprocess_generated_yml.py` | Restores `${var.warehouse_id}` / `${workspace.current_user.userName}` references after each pull (bundle generate overwrites them with hardcoded values). |
| `pull_and_sync.sh` | **Command 1.** Pulls the Genie Space and syncs shared folders. Optionally validates. |
| `push_and_deploy.sh` | **Command 2.** Runs bundle checks (and optionally deploys to test), THEN commits and pushes to Git. |
| `sync_shared_folders.sh` | Pulls shared workspace folders INTO this repo (so they get committed/pushed to GitHub) and deploys them out to your own workspace path, based on `folder_sync_config.json`. Called automatically by `pull_and_sync.sh`, but can be run standalone too. |
| `folder_sync_config.json` | The editable list of folders to sync. Add or remove entries here - no script editing needed. |
| `shared_folders/` | Created automatically the first time a folder is synced. This is the actual, version-controlled copy that gets committed and pushed to GitHub. |

## One-time setup

1. Create an empty Git folder in Databricks, linked to your GitHub repo.
2. Open the Web Terminal (via a throwaway notebook -> connect to serverless compute -> terminal icon).
3. `cd` into the Git folder.
4. Paste in `init_genie_bundle.sh` and run:
   ```
   bash init_genie_bundle.sh
   ```
5. Answer the prompts:
   - **Genie Space ID** - from the Genie UI -> About -> Space ID, or the URL.
   - **Bundle name** - a project label, e.g. `my-project-genie-agent`.
   - **Display title** - what shows in the Genie UI.
   - **Resource key** - internal short name; a suggestion is auto-filled from the bundle name, just press Enter to accept it.
   - **Test target?** - whether to also configure a `test` deployment target now.
   - **Deploy dev now?** - whether to immediately create a live dev copy.
   - **Sync folders now?** - whether to run the folder sync immediately.

   The warehouse ID is **auto-detected** from the live Genie Space after
   the first pull - you do not need to look it up yourself.

6. Once it finishes, commit to GitHub via the Git folder UI (Changes tab ->
   commit message -> Commit & Push). This can't be done from the terminal.

### Re-running init_genie_bundle.sh later

You should not need to run this script again for everyday work - use
`pull_and_sync.sh` and `push_and_deploy.sh` instead (see below). But if you
ever do re-run it (e.g. to point the project at a different Genie Space),
it behaves differently the second time:

- If `config.json` already has a `space_id` filled in, the script uses
  `space_id`, `bundle_name`, `title`, `resource_key`, and `test_target`
  straight from that file - it will **not** ask you for the Space ID (or
  any of those) again.
- To reconfigure, just edit `config.json` by hand first (e.g. change
  `space_id` to a different space) and then re-run the script - it picks
  up whatever is in the file.
- It still asks the two action questions each time ("deploy dev now?" and
  "sync folders now?"), since those are one-off actions, not project config.

## Everyday use - three commands

**1. Pull and sync** - whenever the Genie Space is edited in the UI, or you
want to check for updates:

```
bash pull_and_sync.sh                # pull Genie Space + sync shared folders
bash pull_and_sync.sh --validate     # + validate the bundle afterwards
```

**1b. Folders only** - if you just want to refresh shared folders WITHOUT
touching the Genie Space at all:

```
bash sync_shared_folders.sh
```

This never runs `bundle generate`, never touches `databricks.yml` or
`resources/*.yml` - it only pulls/deploys folders. See "Syncing shared
folders on their own" below for details. Push afterwards with
`push_and_deploy.sh`, same as after `pull_and_sync.sh`.

This only updates your local files. Nothing is pushed to Git and nothing is
deployed yet.

**2. Push (and optionally deploy)** - once you're happy with what's in your
files:

```
bash push_and_deploy.sh                                   # validate, commit (default message), push
bash push_and_deploy.sh 'my commit message'               # validate, commit (custom message), push
bash push_and_deploy.sh --deploy-test                     # validate + deploy to test, commit (default message), push
bash push_and_deploy.sh --deploy-test 'my commit message' # validate + deploy to test, commit (custom message), push
```

This runs the bundle checks (and the test deploy, if you asked for one)
*first*, then commits and pushes to Git - with whatever commit message you
give it, or "sync genie space changes" if you don't give one.

**Golden rule:** always run `pull_and_sync.sh` before `push_and_deploy.sh`,
even if you're not sure anything changed - it prevents accidentally
overwriting someone else's UI edit with stale files.

## Syncing shared folders on their own

If you just want to refresh the shared folders without touching the Genie
Space, run:

```
bash sync_shared_folders.sh
```

It reads `folder_sync_config.json`. Each entry has three fields:

- **`master_src`** - the LIVE Workspace path of the shared/master copy (e.g.
  the folder as it exists in the owner's own account). Pulled down into
  `repo_path` on a best-effort basis - only whoever has read access to it
  needs this step to succeed.
- **`repo_path`** - where that content lives INSIDE this Git repo, relative
  to this folder (e.g. `shared_folders/marketing-eda-notebook`). This is
  what actually gets committed and pushed to GitHub - `push_and_deploy.sh`'s
  `git add .` picks it up automatically, no extra step needed.
- **`dest`** - the LIVE Workspace path that `repo_path` gets deployed to for
  whoever is currently running the sync.

`{username}` anywhere in `master_src` or `dest` is replaced with whoever is
currently running the script, so the same config file works for anyone.

Example entry - real usage (one fixed master, per-user destination):
```json
{
  "master_src": "/Workspace/Users/owner@company.com/.assistant/skills/marketing-eda-notebook",
  "repo_path": "shared_folders/marketing-eda-notebook",
  "dest": "/Workspace/Users/{username}/.assistant/skills/marketing-eda-notebook"
}
```

**How the two systems connect:** the folder owner runs `pull_and_sync.sh`,
which calls `sync_shared_folders.sh` and pulls the current content of
`master_src` down into `repo_path` inside this repo. They then run
`push_and_deploy.sh`, which commits and pushes `repo_path` to GitHub along
with the rest of the bundle. Anyone else who `git pull`s this repo already
has those files locally (from GitHub, no live access to `master_src`
needed) - running `sync_shared_folders.sh` for them just deploys whatever
is in `repo_path` out to their own `dest`. This is what makes the shared
folder both version-controlled in Git and immediately usable for everyone.

## config.json reference

```json
{
  "bundle_name": "my-genie-bundle",
  "resource_key": "my_genie_agent",
  "title": "My Genie Agent",
  "space_id": "01f...",
  "warehouse_id": "auto-detected-on-first-run",
  "test_target": true,
  "test_host": "",
  "test_warehouse_id": "auto-detected-on-first-run"
}
```

`warehouse_id` and `test_warehouse_id` are filled in automatically by
`init_genie_bundle.sh` after it pulls the space for the first time - you
never need to look these up or type them in yourself.

Both `pull_and_sync.sh` and `push_and_deploy.sh` read `space_id`,
`resource_key`, and `test_target` directly from this file at run time - to
point the project at a different Space ID or resource key later, edit this
file (and re-run `init_genie_bundle.sh` if you also need `databricks.yml`
regenerated).

## Adding a project to a new/empty Genie Agent later

Just run `init_genie_bundle.sh` again in a different empty Git folder with
a different Space ID - it's fully self-contained and reusable per project.

## Common issues

| Problem | Fix |
|---|---|
| `Error: test: no such target` | You skipped the test-target step during setup, or it failed to write. Re-run `init_genie_bundle.sh` and say yes, or hand-edit `databricks.yml` to add a `test:` block, and set `test_target: true` in `config.json`. |
| "Git CLI not available from terminal" | Normal in the Web Terminal. Commit via the Workspace Git sidebar (Git icon -> Commit & Push), or ask the Databricks Assistant to commit and push. |
| Folder sync "Export failed" | Check the source path is correct and you have read access to it. |
| `Resources:` empty in `bundle summary` | Usually a missing `include: - resources/*.yml` line in `databricks.yml`. |
MDEOF
  echo "      Wrote README.md."
else
  echo "      README.md already exists - left untouched."
fi

echo ".databricks/" >> .gitignore 2>/dev/null || true
# de-dupe .gitignore if run more than once
if [ -f ".gitignore" ]; then
  sort -u .gitignore -o .gitignore
fi

echo "      Done."

# --- Step 9: validate, optionally sync folders now, optionally deploy dev ---
echo "[9/9] Validating bundle ..."
databricks bundle validate --strict --target dev
echo "      Validation passed."

echo ""
echo "=================================================================="
echo " Setup complete!"
echo "=================================================================="
databricks bundle summary -t dev || true

if [[ "$DO_FOLDER_SYNC" == "y" || "$DO_FOLDER_SYNC" == "Y" ]]; then
  echo ""
  echo "Syncing shared folders now (edit folder_sync_config.json first if you want real folders synced) ..."
  bash sync_shared_folders.sh || true
fi

if [[ "$DO_DEPLOY" == "y" || "$DO_DEPLOY" == "Y" ]]; then
  echo ""
  echo "Deploying dev copy..."
  databricks bundle deploy -t dev
  echo "Deploy complete."
fi

echo ""
echo "Next steps:"
echo "  1. Add any folders you want kept in sync to folder_sync_config.json (the \"folders\" list)."
echo "  2. Open the Git folder UI -> Changes tab -> commit message -> Commit & Push"
echo "     (this is the actual 'save to GitHub' step - it does NOT happen automatically)"
echo "  3. From now on, use these two commands:"
echo "       bash pull_and_sync.sh          # pulls the Genie Space + syncs shared folders"
if [[ "$ADD_TEST_TARGET" == "y" ]]; then
echo "       bash push_and_deploy.sh --deploy-test   # validates, deploys to test, commits, and pushes"
else
echo "       bash push_and_deploy.sh                 # validates, commits, and pushes (no test target was set up)"
fi
echo "  See README.md for the full command reference."
echo ""
