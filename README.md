# Dolmios

Warm theme for [Zed](https://zed.dev) with three variants:

- **dolmios (light, soft)**: warm cream bg, dark graphite text
- **dolmios (dark, soft)**: warm charcoal bg, cream text
- **dolmios (midnight)**: true black bg, cream text

Companion themes for **Claude Code** live in [`claude-code/`](./claude-code/) with the same palette and three variants.

## Install in Zed

Clone the repo, then install as a dev extension:

```bash
git clone https://github.com/dolmios/zed-dolmios.git ~/GitHub/zed-dolmios
```

In Zed: `cmd+shift+p` → `zed: extensions` → **Install Dev Extension** → pick `~/GitHub/zed-dolmios`.

Open the theme picker (`cmd+k cmd+t`) and pick one of the three variants. Edits to `themes/zed-dolmios.json` hot-reload without restarting Zed.

Alternative install via plain themes file:

```bash
mkdir -p ~/.config/zed/themes
ln -s ~/GitHub/zed-dolmios/themes/zed-dolmios.json ~/.config/zed/themes/zed-dolmios.json
```

## Install for Claude Code

See [`claude-code/README.md`](./claude-code/README.md). Symlinks the three companion JSONs into `~/.claude/themes/` for hot-reload, then pick via `/theme` inside Claude Code. Requires Claude Code v2.1.118 or later.

## Palette

### dolmios (light, soft)

Background `#F1F0E9` / text `#2a2b25` / single text-color family (alpha-tiered, no warm-brown grays).

| Role | Hex |
|---|---|
| keyword / boolean | `#7a5230` (coffee) |
| constructor / type | `#2e8f82` (teal) |
| number | `#2f798a` (teal-blue) |
| variable / attribute | `#b07d48` (caramel) |
| function / title / label | `#59873a` (olive) |
| tag | `#1e754f` (sage) |
| string / link | `#b56959` (terracotta) |
| constant / variable.special | `#a65e2b` (sienna) |
| operator | `#ab5959` (red) |
| punctuation | `#9a8e74` (warm stone) |
| comment (italic) | `#a0ada0` (sage-gray) |

### dolmios (dark, soft)

Background `#222222` / text `#dbd7ca`.

| Role | Hex |
|---|---|
| keyword / boolean | `#9e7748` (deep caramel) |
| constructor / type | `#5DA994` (teal) |
| number | `#4C9A91` (teal-cyan) |
| variable / attribute | `#bd976a` (caramel) |
| function / title / label | `#80a665` (olive) |
| tag | `#4d9375` (sage) |
| string / link | `#c98a7d` (terracotta) |
| constant / variable.special | `#c99076` (sienna) |
| operator | `#cb7676` (red) |
| punctuation | `#8a7e64` (warm stone) |
| comment (italic) | `#758575ee` (sage-gray) |

### dolmios (midnight)

Same palette as Dark Soft on `#000000` background, with deeper punctuation (`#6e6450`) and warmer active-line (`#161410`).

## Design choices

- **Single text-color family per variant.** All non-syntax text is one hex at varying alphas (`CC` / `80` / `40`). No warm-tan greys, no slate-cool greys.
- **Border hierarchy.** One base border shade per variant; only `border.focused` and `border.selected` differ.
- **Italic comments.** Subtle texture without shouting.
- **Active tab fill.** Active tabs get an `element.hover` background fill, not just a bottom border.
- **Six warm collaboration players.** Honey, terracotta, olive, caramel, teal, plum for multi-cursor / pair sessions (Vitesse left the players array empty).
- **All UI surface keys populated.** Drop targets, search match, document highlights, focused panel borders, predictive completion, plus every diagnostic `.background` and `.border`.
- **Bright ANSI nudged ~10% lighter** than base for terminal contrast.
- **Light Soft `terminal.ansi.white` / `bright_white`** mapped to readable dark greys (the default Vitesse values were invisible on cream).

## Release flow

Versioning is automated via the Makefile:

```bash
make help                                       # see all targets
make release V=0.2.0 NOTES="describe changes"   # bump, commit, tag, push
make release-gh V=0.2.0 NOTES="..."             # optional GitHub release
```

## Lineage

This theme started from [Vitesse Soft](https://github.com/antfu/vitesse-theme) (via [jordy25519/zed-theme-vitesse](https://github.com/jordy25519/zed-theme-vitesse), MIT). The warm syntax palette (caramel, terracotta, olive, teal, sage, sienna) is largely Vitesse's. UI chrome, text alpha system, border hierarchy, players array, populated null keys, italic comments, ANSI fixes, and Claude Code companions are all Dolmios. Attribution in [LICENSE](./LICENSE).

## License

MIT. See [LICENSE](./LICENSE).
