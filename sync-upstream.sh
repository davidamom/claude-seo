#!/usr/bin/env bash
# Sync this fork (davidamom/claude-seo) with upstream (AgriciDaniel/claude-seo),
# preserving the fork's own commits. Run from anywhere; it cd's to the repo.
#
#   bash sync-upstream.sh
#
# After it finishes cleanly, run `/plugin` in Claude Code and update claude-seo
# to pull the refreshed fork into the plugin cache.
set -euo pipefail

cd "$(dirname "$0")"

if ! git remote | grep -qx upstream; then
  echo "Adding 'upstream' remote -> AgriciDaniel/claude-seo"
  git remote add upstream https://github.com/AgriciDaniel/claude-seo.git
fi

echo "==> Fetching upstream..."
git fetch upstream

echo "==> Merging upstream/main into $(git branch --show-current)..."
if git merge upstream/main --no-edit; then
  echo "==> Pushing to origin..."
  git push origin HEAD
  echo
  echo "Done. The fork is synced with upstream + fork commits preserved."
  echo "Next: run /plugin in Claude Code and update claude-seo."
else
  echo
  echo "MERGE CONFLICT — upstream changed lines the fork also patched."
  echo "Resolve the conflicts, then run:"
  echo "    git add -A && git commit && git push origin HEAD"
  exit 1
fi
