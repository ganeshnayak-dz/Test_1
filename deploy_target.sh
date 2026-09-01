#!/bin/bash
# =============================================================================
# deploy_target.sh
#
# Run this in the OTHER workspace - the one you're moving the Genie Agent
# TO. Pulls the latest bundle from GitHub, then deploys ONLY the Genie
# Agent. It never touches skills/notebooks folders - for now, deploy those
# by hand in this workspace.
#
# Usage:
#   bash deploy_target.sh         # deploys the "dev" target (default)
#   bash deploy_target.sh test    # deploys the "test" target instead -
#                                    only works if databricks.yml has one
#                                    (i.e. config.json has a "test" section -
#                                    see README.md)
# =============================================================================

set -e

TARGET="${1:-dev}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

REPO_ROOT="$(dirname "$SCRIPT_DIR")"

echo "[1/2] Pulling latest from GitHub ..."
# Best-effort only - if the git CLI isn't usable from this terminal (common
# in Databricks Web Terminals), this never succeeds on its own, so we must
# NOT abort here. Pull via the Workspace Git sidebar (Git icon -> Pull)
# yourself, either before running this script or right now in another tab,
# then let this script carry on to the deploy step below either way.
(
  cd "$REPO_ROOT"
  if git status > /dev/null 2>&1; then
    if git pull; then
      echo "      Pull complete."
    else
      echo "      ⚠️  git pull failed - pull via the Workspace Git sidebar (Git icon > Pull) instead."
      echo "      Continuing to deploy whatever is currently in these files."
    fi
  else
    echo "      ⚠️  Git CLI not available from terminal - pull via the Workspace Git sidebar (Git icon > Pull) instead"
    echo "      (do this now if you haven't already - this script can't tell whether you have)."
    echo "      Continuing to deploy whatever is currently in these files."
  fi
) || true

echo ""
echo "[2/2] Deploying the Genie Agent to this workspace (target: $TARGET) ..."
databricks bundle validate --strict --target "$TARGET"
databricks bundle deploy --target "$TARGET"
echo "      Deploy complete."
