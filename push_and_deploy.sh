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
