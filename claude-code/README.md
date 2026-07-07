# Dolmios for Claude Code

Portable [Claude Code](https://code.claude.com) config: themes, global settings, statusline, and the MCP setup that follows me across machines and repos.

Requires Claude Code **v2.1.118 or later**.

## New machine setup

One command symlinks the config in this repo into `~/.claude` (edits here hot-reload into running sessions):

```bash
./bootstrap.sh
```

That covers everything version-controlled here. Two things stay machine-local and are set up once per machine:

1. **MCP servers** (see below) — the definitions, run once.
2. **MCP OAuth tokens** — re-auth in Claude Code with `/mcp` (linear, sentry, etc). Tokens live in the local keychain, never in this repo.

## What's tracked here

| File | Symlinked to | Notes |
|------|--------------|-------|
| `settings.json` | `~/.claude/settings.json` | Theme, voice, plugins, TUI mode |
| `statusline-command.sh` | `~/.claude/statusline-command.sh` | Model + dir + git branch/dirty statusline |
| `dolmios-*.json` | `~/.claude/themes/` | Theme variants (below) |

> Note: `settings.json` is written by Claude Code when you change settings in-app (`/theme`, voice toggles). If a future version writes it via atomic rename, the symlink can detach into a plain file. If your in-app changes stop showing up in `git status` here, re-run `./bootstrap.sh` to re-link, then copy any drifted values across.

## MCP servers

MCP config is per-machine, not in this repo (definitions live in `~/.claude.json`, tokens in the keychain). Personal servers I want in **every** repo are added at user scope:

```bash
claude mcp add --scope user --transport http linear   https://mcp.linear.app/mcp
claude mcp add --scope user --transport http sentry   https://mcp.sentry.dev/mcp
claude mcp add --scope user context7 -- npx -y @upstash/context7-mcp
```

Project-specific servers (e.g. a repo's Supabase / logging) stay in that repo's committed `.mcp.json` via `claude mcp add --scope project <name> ...`.

Check state anytime: `claude mcp list` · inspect one: `claude mcp get <name>` · remove: `claude mcp remove --scope user <name>`.

## Variants

- `dolmios-light-soft.json`: warm cream bg, dark text
- `dolmios-dark-soft.json`: warm charcoal bg, cream text
- `dolmios-midnight.json`: true black bg, cream text

## Install

Symlink the JSON files into `~/.claude/themes/` so edits in this repo hot-reload into running Claude Code sessions:

```bash
mkdir -p ~/.claude/themes
for f in dolmios-light-soft dolmios-dark-soft dolmios-midnight; do
  ln -sf "$(pwd)/claude-code/$f.json" ~/.claude/themes/$f.json
done
```

Or copy them (no hot-reload from repo edits):

```bash
mkdir -p ~/.claude/themes
cp claude-code/*.json ~/.claude/themes/
```

## Activate

In Claude Code:

```
/theme
```

Pick **Dolmios (light, soft)**, **Dolmios (dark, soft)**, or **Dolmios (midnight)** from the list.

Claude Code stores `custom:<slug>` in `~/.claude/settings.json` once selected.

## What gets themed

Each variant overrides ~40 tokens covering:

- Brand accent (the `claude` spinner color)
- Text and inactive text colors
- Status colors (success / error / warning / merged)
- Permission, plan-mode, auto-accept, bash, IDE, fast-mode indicators
- Diff backgrounds and word-level highlights
- Fullscreen mode message backgrounds
- Selection background, usage meter, message labels
- Shimmer variants for animated tokens

Unset tokens fall through to the base preset (`light-ansi` for the light variant, `dark-ansi` for the dark variants).

## Notes

- Claude Code custom themes don't support "auto" light/dark switching. Pick one manually when you switch your Zed theme.
- Colors don't accept alpha channels (`#rrggbb` only, no `#rrggbbaa`), so all "muted" colors are precomputed blends against the bg.
- Inside Zed's integrated terminal, ANSI colors come from the active Zed theme, so even the unstyled base palette already matches Dolmios.
