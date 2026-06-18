# Dolmios for Zed

Warm honey-amber theme for [Zed](https://zed.dev). Three variants: **Light Soft**, **Dark Soft**, **Black**.

Companion themes for **Claude Code** live in [`claude-code/`](./claude-code/) — same palette, same three variants.

Derived from [Vitesse](https://github.com/antfu/vitesse-theme) (via [jordy25519/zed-theme-vitesse](https://github.com/jordy25519/zed-theme-vitesse)) with the sage accent swapped for honey-amber, italic comments, visible borders, and fully populated UI surfaces.

## Palette

### Light Soft
| Role | Hex |
|---|---|
| Background | `#F1F0E9` |
| Text | `#393a34` |
| Accent (honey) | `#b07d2e` |
| Focused border (terracotta) | `#b56959` |
| Keyword / boolean | `#a4621f` |
| String | `#b56959` |
| Variable / attribute | `#b07d48` |
| Function / title | `#59873a` |
| Tag | `#1e754f` |
| Type / number | `#2e8f82` / `#2f798a` |
| Comment (italic) | `#a0ada0` |

### Dark Soft
| Role | Hex |
|---|---|
| Background | `#222222` |
| Text | `#dbd7ca` |
| Accent (honey) | `#d4a86a` |
| Focused border (terracotta) | `#c98a7d` |
| Keyword / boolean | `#d4a86a` |
| String | `#c98a7d` |
| Variable / attribute | `#bd976a` |
| Function / title | `#80a665` |
| Tag | `#4d9375` |
| Type / number | `#5DA994` / `#4C9A91` |
| Comment (italic) | `#758575ee` |

### Black
Same palette as Dark Soft on `#000000` background, with deeper punctuation (`#555555`) and warmer active-line (`#161410`).

## Install

### As a dev extension (recommended)

1. Clone:
   ```bash
   git clone https://github.com/jacksondolman/zed-dolmios.git ~/GitHub/zed-dolmios
   ```
2. In Zed: open the command palette (`cmd+shift+p`), run `zed: extensions`, click **Install Dev Extension**, pick `~/GitHub/zed-dolmios`.
3. Open the theme selector (`cmd+k cmd+t`) and pick **Dolmios Light Soft**, **Dolmios Dark Soft**, or **Dolmios Black**.

Edits to `themes/zed-dolmios.json` reload live, no Zed restart needed.

### As a plain themes file

```bash
mkdir -p ~/.config/zed/themes
ln -s ~/GitHub/zed-dolmios/themes/zed-dolmios.json ~/.config/zed/themes/zed-dolmios.json
```

Then pick a variant in `cmd+k cmd+t`.

## What's different from Vitesse Soft

The full audit and rationale lives in [CHANGELOG.md](./CHANGELOG.md). Headline changes:

- Sage accent (`#1c6b48` / `#4d9375`) -> honey-amber (`#b07d2e` / `#d4a86a`) on UI surfaces and `keyword`/`boolean`/`constructor` tokens. `tag` stays sage.
- Borders get a real hierarchy (focused/selected use the accent, base borders distinct from surfaces).
- Dark text bumped to full alpha. Comment alpha bumped from `dd` -> `ee`.
- Comments italic.
- All `null` UI keys filled in (icons, drop target, search match, document highlights, focused panel borders, predictive, renamed, success, unreachable, all diagnostic `.background`/`.border`).
- 6 warm-tone player colors populated (was empty).
- Bright ANSI colors nudged ~10% lighter than base.
- Light Soft scrollbar track border fixed (`#fff` -> `#E7E5DB`).

## License

MIT. See [LICENSE](./LICENSE). Vitesse and the original Zed port are also MIT.
