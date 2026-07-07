#!/bin/bash
#
# Bootstrap Claude Code config on a new machine.
# Symlinks this repo's config into ~/.claude so edits here hot-reload
# into running sessions and every machine shares one source of truth.
#
# Usage:  ./bootstrap.sh
#
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE="$HOME/.claude"

mkdir -p "$CLAUDE/themes"

# Themes (read-only from Claude's side — safe to symlink)
for f in dolmios-light-soft dolmios-dark-soft dolmios-midnight; do
  ln -sf "$REPO/$f.json" "$CLAUDE/themes/$f.json"
done

# Global settings + statusline
ln -sf "$REPO/settings.json" "$CLAUDE/settings.json"
ln -sf "$REPO/statusline-command.sh" "$CLAUDE/statusline-command.sh"
chmod +x "$REPO/statusline-command.sh"

echo "Linked into ~/.claude:"
ls -la "$CLAUDE/settings.json" "$CLAUDE/statusline-command.sh" "$CLAUDE/themes/"

cat <<'EOF'

Done. Still machine-local (NOT in this repo, set up once per machine):
  - MCP servers      : run the commands in the README "MCP servers" section
  - MCP OAuth tokens : re-auth in Claude Code with /mcp (linear, sentry, ...)
EOF
