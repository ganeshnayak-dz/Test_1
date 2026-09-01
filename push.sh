#!/bin/bash
# =============================================================================
# push.sh
#
# Commits and pushes everything in this Git folder to GitHub - the Genie
# Agent bundle plus any skills/notebooks folders pulled in by dev_sync.sh.
#
# Run dev_sync.sh first if you haven't already - this script does not pull
# anything itself, it only validates/commits/pushes whatever is currently
# sitting in your files.
#
# Usage:
#   bash push.sh                     # commit with a default message, push
#   bash push.sh 'my commit message' # commit with your own message, push
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -f "databricks.yml" ]; then
  echo "[1/2] Validating bundle ..."
  databricks bundle validate --strict --target dev
  echo "      Validation passed."
else
  echo "[1/2] No databricks.yml yet - run dev_sync.sh first. Skipping validation."
fi

COMMIT_MSG="${1:-sync genie agent changes}"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

echo ""
echo "[2/2] Committing and pushing to Git..."
echo "      Commit message: $COMMIT_MSG"
(
  cd "$REPO_ROOT"
  if git status > /dev/null 2>&1; then
    git add .
    git commit -m "$COMMIT_MSG" || echo "      Nothing new to commit."
    if git push origin "$(git branch --show-current)"; then
      echo "      Push complete."
    else
      echo "      ⚠️  Commit succeeded locally, but 'git push' failed (see the error above)."
      echo "      Push via the Workspace Git sidebar (Git icon > Commit & Push) instead,"
      echo "      or ask the Databricks Assistant: 'push my changes'."
    fi
  else
    echo "      ⚠️  Git CLI not available from terminal."
    echo "      Commit via the Workspace Git sidebar (Git icon > Commit & Push),"
    echo "      or ask the Databricks Assistant: 'commit and push my changes'."
  fi
)
