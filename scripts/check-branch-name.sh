#!/usr/bin/env bash
set -euo pipefail

branch=$(git rev-parse --abbrev-ref HEAD)

if ! echo "$branch" | grep -qE "^(feature|fix|bugfix|hotfix|release|claude|copilot)/|^main$"; then
    echo "ERROR: Branch \"$branch\" does not follow naming convention."
    echo "Allowed prefixes: feature/, fix/, bugfix/, hotfix/, release/, claude/, copilot/"
    echo "Example: feature/add-new-strategy"
    exit 1
fi
