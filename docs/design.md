# Design

TopLines is a sibling of ATC behind the same tailnet and should read as the
same instrument panel. ATC has no design system, only a `THEMES` object in
`web/index.html` (line 384 at commit `181ca45`, 2026-08-25). TopLines copies
those values into its own tokens and cites the source. Drift is then a
deliberate act.

## Metaphor

- Light: "NASA documentation / plotter paper". Warm paper, blue-grey rules,
  flat, drawn.
- Dark: a vector display. Near-black, flat surfaces, thin bright lines, no
  glow.

Both are flat. No shadows, no gradients, corners square or two pixels.

## Tokens

Grounds and ink:

| token | light | dark | ATC source |
|---|---|---|---|
| `--page` | `#f2eee2` | `#101214` | `bg` |
| `--surface` | `#faf7ee` | `#14171b` | `fill` |
| `--rule` | `#a9bccf` | `#2a2d31` | `grid1` |
| `--rule-2` | `#d8dfe6` | `#1c1f23` | `grid2` |
| `--ink` | `#1b232b` | `#e4e6ea` | `tetherSched` (light); chosen for dark, ATC has no text ink |
| `--ink-2` | `#5c6b78` | `#9aa0a8` | `tag.neutral` |
| `--muted` | `#8a97a3` | `#5f6670` | `pulseSub` |

Meaning colors. These are inherited encodings, not decoration:

| meaning on the board | light | dark | ATC source |
|---|---|---|---|
| running turn | `#2e7d4f` | `#6fae4e` | `tetherRun` |
| wake queued, waiting | `#b8860b` | `#c9a835` | `tetherWait` |
| needs you, no live holder | `#c23b22` | `#c4453c` | `itemOpen`, `orphan` |
| closed, done | `#1f5e46` | `#2c7a4b` | `itemClosed` |
| recent activity, hot | `#2f6fb5` | `#3d8fd6` | `liveHot` |
| recent activity, cold | `#aab3bc` | `#4e545c` | `liveCold` |

Holder kinds, from ATC's `kind` map:

| kind | light | dark |
|---|---|---|
| main | `#c23b22` | `#b08d57` |
| po | `#b06a3b` | `#a58968` |
| patrol | `#c9a227` | `#c9a835` |
| orch | `#5c6b78` | `#8a8f96` |
| coder | `#6e7b87` | `#7f8890` |
| rev | `#52616e` | `#6b7684` |
| spec | `#7a6a4f` | `#91836b` |

Stage ramp, ATC's seven stops, index 0 to 6:

| | 0 | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|---|
| light | `#c23b22` | `#d07a2a` | `#c9a227` | `#8a9a2e` | `#4e8a4e` | `#2e7d5b` | `#1f5e46` |
| dark | `#c4453c` | `#c97b35` | `#c9a835` | `#a3b23c` | `#6fae4e` | `#3f9d63` | `#2c7a4b` |

## Encodings

- **Quiet.** A number in mono plus a dot on a shared log strip from one minute
  to thirty days with ticks at one hour, one day, one week. The dot's color is
  ATC's recency fade: `liveHot` at zero minutes to `liveCold` at sixty, then
  flat. Same rule ATC applies to agent discs.
- **Status chip.** running (filled, `tetherRun`), wake queued (half-filled,
  `tetherWait`), idle (outline, muted), needs you (filled, `itemOpen`, bold).
- **Holders.** A square in the kind color, the session display name, then
  harness and model in muted text. An item with no live holder shows "no live
  holder" in `orphan` red, matching ATC's red ring.
- **Stage.** Six cells; the satisfied ones filled with the ramp color of the
  current stage; label "N/6" in mono; tooltip names the bands: progress, tests
  passed, completion, independent review, ready to merge, closed.
- **Attests.** Total in mono plus a bar of four ink weights in fixed order:
  progress, surrender, completion, verdict. ATC has no color for attest kinds,
  so the bar stays monochrome and the stage chip carries the semantic color.
  Legend in the panel header.
- **Sessions.** Split by kind in the vitals tile and the rail, harness counts
  as a text line. Kind, not harness, is what ATC colors.
- **Quiet-band dividers** in the open list: within the hour, within the day,
  more than a day, more than a week.

## Typography

System stacks only, as ATC: `ui-sans-serif, -apple-system, "Helvetica Neue",
Arial, sans-serif` for labels and titles; `ui-monospace, Menlo, Consolas,
monospace` with `font-variant-numeric: tabular-nums` for identifiers and every
numeric column. Section labels uppercase with wide tracking, like a drawing
sheet's title block. No web fonts: the page must load with no internet.

## Theme handling

Three states. The bare `:root` holds the complete light palette. A
`prefers-color-scheme: dark` block guarded as `:root:not([data-theme="light"])`
redefines only tokens. `:root[data-theme="dark"]` redefines them again so an
explicit choice wins both ways. The toggle (system, light, dark) stamps
`data-theme` on the root or removes it, and remembers the choice in
`localStorage` inside try/catch. Default is system.

## Cross-link

Header carries a plain link labelled "ATC" to `https://atc.tailf064dc.ts.net/`,
in `--ink-2`, no icon. Same treatment as the command echo beside the title.

## Mock

`mock/toplines.html` is the reviewed reference. When the page and the mock
disagree, the mock wins on appearance and this document wins on tokens and
encodings; raise the disagreement on the card.
