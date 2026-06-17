#!/usr/bin/env sh
set -eu

scope="${1:-agents}"
repo_dir="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
src="$repo_dir/skill/context-proof"

case "$scope" in
  agents)
    dest="${HOME}/.agents/skills/context-proof"
    ;;
  codex)
    dest="${HOME}/.codex/skills/context-proof"
    ;;
  claude)
    dest="${HOME}/.claude/skills/context-proof"
    ;;
  opencode)
    dest="${HOME}/.config/opencode/skills/context-proof"
    ;;
  project-claude)
    dest=".claude/skills/context-proof"
    ;;
  project-opencode)
    dest=".opencode/skills/context-proof"
    ;;
  project-agents)
    dest=".agents/skills/context-proof"
    ;;
  *)
    echo "Unknown scope: $scope" >&2
    echo "Use: agents | codex | claude | opencode | project-claude | project-opencode | project-agents" >&2
    exit 2
    ;;
esac

mkdir -p "$(dirname "$dest")"
rm -rf "$dest"
cp -R "$src" "$dest"
echo "Installed context-proof skill to $dest"
