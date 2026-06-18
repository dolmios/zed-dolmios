# Dolmios for Claude Code

Companion themes for [Claude Code](https://code.claude.com) that mirror the Zed Dolmios palette.

Requires Claude Code **v2.1.118 or later**.

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
