#!/bin/bash
# =============================================================================
# dev_sync.sh
#
# ONE script for the DEV workspace (where the Genie Agent, its skills, and
# its notebooks actually live and get edited).
#
#   FIRST TIME you run it in an empty Git folder: asks a few setup
#   questions, creates the DAB (databricks.yml + config.json), pulls the
#   Genie Space, and pulls your skills/notebooks folders (listed in the
#   "folders" list in config.json) into this repo - so everything needed
#   to recreate the agent ends up in Git.
#
#   EVERY TIME AFTER THAT: skips all the setup questions (config.json
#   already has a real space_id) and just refreshes everything from the
#   live workspace - Genie Space content + skills/notebooks folders - so
#   you can review and push whatever changed.
#
# This script never pushes to Git and never deploys anywhere.
#   Next step after running it: bash push.sh
#
# Usage:
#   bash dev_sync.sh
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

CONFIG_FILE="config.json"

json_get() {
  python3 -c "
import json
d = json.load(open('$CONFIG_FILE'))
print(d.get('$1',''))
" 2>/dev/null
}

# --- Decide first-run vs update. It's a first run if config.json has no
# real space_id yet, OR databricks.yml is missing (e.g. config.json was
# copied/edited by hand but the bundle itself was never generated) ---
FIRST_RUN="n"
SPACE_ID=""
if [ -f "$CONFIG_FILE" ]; then
  SPACE_ID="$(json_get space_id)"
fi
if [ -z "$SPACE_ID" ] || [ "$SPACE_ID" == "PASTE_YOUR_GENIE_SPACE_ID_HERE" ]; then
  FIRST_RUN="y"
fi
if [ ! -f "databricks.yml" ]; then
  FIRST_RUN="y"
fi

if [[ "$FIRST_RUN" == "y" ]]; then
  echo "=================================================================="
  echo " First run - setting up the bundle"
  echo "=================================================================="
  if [ -n "$SPACE_ID" ] && [ "$SPACE_ID" != "PASTE_YOUR_GENIE_SPACE_ID_HERE" ]; then
    read -p "Genie Space ID [${SPACE_ID}]: " INPUT_SPACE_ID
    SPACE_ID="${INPUT_SPACE_ID:-$SPACE_ID}"
  else
    read -p "Genie Space ID (Genie UI -> About -> Space ID, or from the URL): " SPACE_ID
  fi
  while [ -z "$SPACE_ID" ]; do
    read -p "  Cannot be empty. Try again: " SPACE_ID
  done
  read -p "Bundle name [genie-agent]: " BUNDLE_NAME
  BUNDLE_NAME="${BUNDLE_NAME:-genie-agent}"
  read -p "Display title [${BUNDLE_NAME}]: " TITLE
  TITLE="${TITLE:-$BUNDLE_NAME}"
  RESOURCE_KEY="$(echo "$BUNDLE_NAME" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/_/g; s/^_+|_+$//g')"

  mkdir -p resources src

  # Minimal databricks.yml, just enough for `bundle generate` to run
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
    workspace:
      root_path: /Workspace/Users/\${workspace.current_user.userName}/.bundle/\${bundle.name}/\${bundle.target}
EOF

  python3 - "$BUNDLE_NAME" "$RESOURCE_KEY" "$TITLE" "$SPACE_ID" << 'PYEOF'
import json, os, sys
bundle_name, resource_key, title, space_id = sys.argv[1:5]

# Preserve existing "folders"/"dev"/"test" sections (and any existing
# warehouse_id) if config.json already existed - a first run can still
# happen with config.json already present (e.g. databricks.yml was
# missing), and we must not wipe out settings someone already added.
folders = [
    {"src": "/Workspace/Users/you@company.com/.assistant/skills/my-skill",
     "repo_path": "shared_folders/my-skill"},
]
warehouse_id = "auto-detected-on-first-run"
dev = None
test = None
if os.path.exists("config.json"):
    try:
        old = json.load(open("config.json"))
        if isinstance(old.get("folders"), list) and old["folders"]:
            folders = old["folders"]
        if old.get("warehouse_id"):
            warehouse_id = old["warehouse_id"]
        if isinstance(old.get("dev"), dict):
            dev = old["dev"]
        if isinstance(old.get("test"), dict):
            test = old["test"]
    except Exception:
        pass

config = {
    "bundle_name": bundle_name,
    "resource_key": resource_key,
    "title": title,
    "space_id": space_id,
    "warehouse_id": warehouse_id,
    "folders": folders,
}
if dev is not None:
    config["dev"] = dev
if test is not None:
    config["test"] = test
with open("config.json", "w") as f:
    json.dump(config, f, indent=2)
    f.write("\n")
PYEOF
else
  BUNDLE_NAME="$(json_get bundle_name)"
  RESOURCE_KEY="$(json_get resource_key)"
  TITLE="$(json_get title)"
  WAREHOUSE_ID="$(json_get warehouse_id)"
  echo "Updating existing bundle (space_id: $SPACE_ID) ..."
fi

echo ""
echo "[1/2] Pulling Genie Space (ID: $SPACE_ID) ..."
databricks bundle generate genie-space \
  --existing-id "$SPACE_ID" \
  --target dev \
  --key "$RESOURCE_KEY" \
  --force
echo "      Pull complete."

GENERATED_YML="resources/${RESOURCE_KEY}.genie_space.yml"
if [ ! -f "$GENERATED_YML" ]; then
  echo "❌ Expected $GENERATED_YML but it wasn't created. Check the Space ID / resource_key in config.json."
  exit 1
fi

if [[ "$FIRST_RUN" == "y" ]]; then
  echo "      Detecting warehouse ID ..."
  WAREHOUSE_ID="$(grep -m1 'warehouse_id:' "$GENERATED_YML" | sed -E 's/.*warehouse_id:[[:space:]]*//; s/["'"'"']//g; s/[[:space:]]*$//')"
  if [ -z "$WAREHOUSE_ID" ]; then
    read -p "      Could not auto-detect - please enter the SQL warehouse ID: " WAREHOUSE_ID
  else
    echo "      Detected warehouse ID: $WAREHOUSE_ID"
  fi

  python3 -c "
import json
c = json.load(open('config.json'))
c['warehouse_id'] = '$WAREHOUSE_ID'
with open('config.json', 'w') as f:
    json.dump(c, f, indent=2)
    f.write('\n')
"
fi

# --- Write databricks.yml's "targets:" section from config.json - always a
# "dev" target (using the optional "dev" section for mode/title/permissions,
# falling back to the top-level title if "dev" isn't set), plus a "test"
# target too if config.json has a usable "test" section (needs at least
# workspace_host and warehouse_id). Runs every time (not just first run) so
# editing config.json's "dev"/"test" sections and re-running this script is
# enough to update databricks.yml - no need to hand-edit it. ---
TARGETS_BLOCK="$(python3 - "$RESOURCE_KEY" "$TITLE" << 'PYEOF'
import json, sys

resource_key, fallback_title = sys.argv[1:3]
try:
    cfg = json.load(open("config.json"))
except Exception:
    cfg = {}

def permission_lines(permissions):
    lines = []
    if not isinstance(permissions, list):
        permissions = []
    if permissions:
        lines.append("    permissions:")
        for p in permissions:
            if not isinstance(p, dict) or not p.get("user_name"):
                continue
            lines.append(f"      - user_name: {p['user_name']}")
            lines.append(f"        level: {p.get('level', 'CAN_MANAGE')}")
    return lines

# --- dev target (always present) ---
dev = cfg.get("dev")
if not isinstance(dev, dict):
    dev = {}
dev_mode = dev.get("mode", "development")
dev_title = dev.get("title") or fallback_title

lines = [
    "  dev:",
    "    default: true",
    f"    mode: {dev_mode}",
    "    workspace:",
    "      root_path: /Workspace/Users/${workspace.current_user.userName}/.bundle/${bundle.name}/${bundle.target}",
]
lines += permission_lines(dev.get("permissions", []))
lines += [
    "    resources:",
    "      genie_spaces:",
    f"        {resource_key}:",
    f"          title: '{dev_title}'",
    "          warehouse_id: ${var.warehouse_id}",
    "          parent_path: /Workspace/Users/${workspace.current_user.userName}",
]

# --- test target (only if config.json has a usable "test" section) ---
test = cfg.get("test")
has_test = isinstance(test, dict) and test.get("workspace_host") and test.get("warehouse_id")
if has_test:
    test_mode = test.get("mode", "production")
    host = test["workspace_host"]
    warehouse_id = test["warehouse_id"]
    title = test.get("title") or f"[Test] {fallback_title}"

    lines += [
        "",
        "  test:",
        f"    mode: {test_mode}",
        "    workspace:",
        f"      host: {host}",
        "      root_path: /Workspace/Users/${workspace.current_user.userName}/.bundle/${bundle.name}/${bundle.target}",
        "    variables:",
        f"      warehouse_id: {warehouse_id}",
    ]
    lines += permission_lines(test.get("permissions", []))
    lines += [
        "    resources:",
        "      genie_spaces:",
        f"        {resource_key}:",
        f"          title: '{title}'",
        "          warehouse_id: ${var.warehouse_id}",
        "          parent_path: /Workspace/Users/${workspace.current_user.userName}",
    ]

print("\n".join(lines))
PYEOF
)"

cat > databricks.yml << EOF
bundle:
  name: ${BUNDLE_NAME}
  engine: direct

include:
  - resources/*.yml

variables:
  warehouse_id:
    description: SQL warehouse ID for the Genie space
    default: ${WAREHOUSE_ID}

targets:
${TARGETS_BLOCK}
EOF

if grep -q '^  test:' <<< "$TARGETS_BLOCK"; then
  echo "      Wrote databricks.yml with dev + test targets (test section found in config.json)."
else
  echo "      Wrote databricks.yml with dev target only (no usable \"test\" section in config.json)."
fi

echo "      Restoring dynamic references ..."
python3 postprocess_generated_yml.py < "$GENERATED_YML" > "${GENERATED_YML}.tmp" && mv "${GENERATED_YML}.tmp" "$GENERATED_YML"
echo "      Done."

echo ""
echo "[2/2] Pulling skills/notebooks folders into the repo ..."
NORMALIZED=$(mktemp)
trap 'rm -f "$NORMALIZED"' EXIT
python3 - "$CONFIG_FILE" > "$NORMALIZED" << 'PYEOF'
import json, sys

path = sys.argv[1]
try:
    data = json.load(open(path))
except Exception as e:
    print(f"ERR: {path} is not valid JSON - fix it and re-run: {e}", file=sys.stderr)
    sys.exit(1)

folders = data.get("folders", [])
if not isinstance(folders, list):
    print(f"ERR: \"folders\" in {path} must be a list - found {type(folders).__name__}.", file=sys.stderr)
    sys.exit(1)

if not folders:
    print(f"WARN: no entries in \"folders\" in {path} - nothing to pull. Add entries like:", file=sys.stderr)
    print('  {"src": "/Workspace/Users/you@company.com/.../my-skill", "repo_path": "shared_folders/skills"}', file=sys.stderr)

# repo_path is a GROUP folder - multiple entries can share the same one.
# Each src lands in its own subfolder underneath it, named after src's
# own last path segment, so several skills/notebooks can sit side by
# side under e.g. "shared_folders/skills" without overwriting each other.
seen_dest = {}
for i, item in enumerate(folders, 1):
    if not isinstance(item, dict):
        print(f"WARN: folders[{i}] is not a {{...}} object ({item!r}) - skipping.", file=sys.stderr)
        continue
    src = str(item.get("src", "")).strip()
    repo_path = str(item.get("repo_path", "")).strip()
    if not src or not repo_path:
        print(f"WARN: folders[{i}] is missing \"src\" or \"repo_path\" ({item!r}) - skipping.", file=sys.stderr)
        continue
    base = src.rstrip("/").split("/")[-1] or f"item{i}"
    dest = f"{repo_path.rstrip('/')}/{base}"
    if dest in seen_dest:
        print(f"WARN: folders[{i}] resolves to \"{dest}\", the same as folders[{seen_dest[dest]}] "
              f"(same repo_path AND same folder name) - skipping folders[{i}]. "
              f"Rename one of the two source folders, or give it a different repo_path.", file=sys.stderr)
        continue
    seen_dest[dest] = i
    print(f"{src}|{dest}")
PYEOF

if [ -s "$NORMALIZED" ]; then
  while IFS='|' read -r SRC DEST; do
    ABS_DEST="$SCRIPT_DIR/$DEST"
    PARENT_DIR="$(dirname "$ABS_DEST")"
    # Only create the PARENT dir - let export-dir create the leaf folder
    # itself. Pre-creating the leaf too can race with export-dir on
    # Workspace-backed filesystems and surface a spurious
    # "Node ... already exists" error.
    # Retry + never let this one mkdir kill the whole script (set -e) -
    # Workspace-backed filesystems can transiently fail mkdir too.
    MKDIR_OK="n"
    for ATTEMPT in 1 2 3; do
      if mkdir -p "$PARENT_DIR" 2>/dev/null || [ -d "$PARENT_DIR" ]; then
        MKDIR_OK="y"
        break
      fi
      sleep 1
    done
    if [[ "$MKDIR_OK" != "y" ]]; then
      echo "  ❌ Could not create $PARENT_DIR after 3 tries - skipping $DEST (pulled from $SRC)."
      continue
    fi
    echo "  Pulling $SRC -> $DEST"
    EXPORT_LOG=$(mktemp)
    OK="n"
    for ATTEMPT in 1 2; do
      if databricks workspace export-dir "$SRC" "$ABS_DEST" --overwrite > "$EXPORT_LOG" 2>&1; then
        OK="y"
        break
      fi
      [ "$ATTEMPT" == "1" ] && sleep 2   # brief retry - covers transient workspace-fs conflicts
    done
    if [[ "$OK" == "y" ]]; then
      echo "    ✅ Done."
    else
      echo "    ⚠️  Could not read $SRC - check the path and your access. Left $DEST as-is."
      echo "       $(tail -n 1 "$EXPORT_LOG")"
    fi
    rm -f "$EXPORT_LOG"
  done < "$NORMALIZED"
else
  echo "  (Nothing pulled - see WARN/ERR messages above, if any.)"
fi

echo ""
echo "=================================================================="
echo " Done. Everything needed is now in this folder (nothing was pushed"
echo " to Git yet - this script never touches git)."
echo " Review the changes, then run this SEPARATE command when ready:"
echo "   bash push.sh                     (or: bash push.sh 'my commit message')"
echo "=================================================================="
