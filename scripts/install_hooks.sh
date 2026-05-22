#!/usr/bin/env bash
# install_hooks.sh — idempotently install repo git hooks.
#
# Symlinks .git/hooks/pre-commit to scripts/hooks/pre-commit so future edits
# to the in-repo source take effect immediately. Idempotent: running it twice
# leaves the same symlink and does not error.
#
# Usage:
#   ./scripts/install_hooks.sh

set -euo pipefail

repo_root=$(git rev-parse --show-toplevel)
cd "$repo_root"

if [ ! -d .git ] && [ ! -f .git ]; then
    echo "install_hooks.sh: not inside a git repository (.git missing at $repo_root)" >&2
    exit 1
fi

# git rev-parse --git-path also resolves correctly inside worktrees, but for
# the symlink target we want a stable relative path that works from inside
# .git/hooks/. The source lives at scripts/hooks/pre-commit at the repo root,
# so the relative target from .git/hooks/ is ../../scripts/hooks/pre-commit.

source_rel="../../scripts/hooks/pre-commit"
hook_dir="$(git rev-parse --git-path hooks)"
target="$hook_dir/pre-commit"

mkdir -p "$hook_dir"

# Ensure the source file is executable (scripts/hooks/pre-commit lives in the
# repo; permission bits are tracked by git, so this is belt-and-suspenders).
chmod +x scripts/hooks/pre-commit

# Idempotent symlink: remove any existing pre-commit (file or symlink), then
# create the symlink. `ln -sf` would overwrite a symlink but would also
# overwrite a regular file silently — be explicit.
if [ -L "$target" ] || [ -e "$target" ]; then
    rm -f "$target"
fi
ln -s "$source_rel" "$target"

echo "pre-commit hook installed: $target -> $source_rel"
