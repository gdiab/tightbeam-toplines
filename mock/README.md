# Mock

`toplines.html` is the reviewed mock. Open it directly in a browser; it has no
dependencies and makes no requests. George approved its appearance on
2026-09-02 after the restyle onto ATC's tokens and the addition of the
appearance toggle.

## What it renders

A snapshot of George's org on sirius taken 2026-09-01 20:55 PDT, inlined as
the `D` constant near the top of the script and saved separately as
`snapshot-2026-09-01T2055.json`. Sources:

- `tightbeam toplines --as-user george` (184 items, reduced to the 91 open,
  iceboxed and failed ones) for titles, states, quiet time, cards, attests,
  minds, turns.
- `tightbeam list --as-user george` for the 51 active sessions and the 7
  pending wakes.
- ATC's live `data.json` at the same moment, joined by session id, for holder
  names, holder kinds and evidence stage.

Two CLI calls were made by hand to build it. That is the correct use of the
CLI. The live page never calls it; see `docs/spec.md` hard constraint 1.

## Known gaps between the mock and the spec

- The mock's holder kind for "Stall Patrol" was inferred from the display
  name. The generator ports ATC's derivation instead
  (`reference/atc-derivations.md` § 2).
- The mock shows "refresh 2 s" but is static. The live page fetches
  `toplines.json`.
- The footer's coverage basis and edge basis come from the CLI and are an open
  question in the spec.
- The header has no ATC link yet; the spec and `docs/design.md` add one.
- The holder line wraps when an item has two long-named holders. Acceptable
  for v1; the coder may tighten it.

## Versions

The mock's history is in the Claude artifact where it was reviewed:
first draft with a teal palette and web fonts (2026-09-01), restyle onto ATC
tokens (2026-09-02 07:36), appearance toggle (2026-09-02 08:20). This file is
the last of those.
