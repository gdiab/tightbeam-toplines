# Decisions

Dated, with the reasoning, so a reviewer can tell a settled question from an
open one. Reopen by adding a new entry that supersedes the old one, never by
editing history.

## D1 · 2026-09-01 · Read the ledger read-only; never poll the CLI

Every CLI verb is a dispatch the gateway records in the ledger. A read loop on
the CLI grew `state.db` to 4.9 GB and crashed the earlier host
(clickety-clacks/tightbeam#10). ATC's generator reads `state.db` with
`mode=ro` and has run daily without incident. TopLines does the same. The one
CLI call is the nightly parity check.

## D2 · 2026-09-01 · Wake on `PRAGMA data_version`, not on gateway doorbells

The gateway's `work_state` WebSocket doorbells are hints to re-read and cover
only assignment and item events. `data_version` moves on every commit, costs
microseconds, needs no device pairing, and is what ATC already uses.

## D3 · 2026-09-02 · Own hostname and sidecar: `toplines.tailf064dc.ts.net`

Ruled by George. ATC's sidecar routes live in the `tb-atc-ts` container's
Tailscale state, set by a `tailscale serve` command, not in any repo. Adding a
`/board` path would mutate ATC's live deployment even with its repo untouched,
and a fresh sidecar redeploy from Mike's runbook would drop it. A second
sidecar costs one tailnet node and shares nothing.

## D4 · 2026-09-02 · Read-only in v1

Ruled by George, with "we may change that." No control API, no operator token,
no buttons that change org state. If reopened, actions should call ATC's
control API endpoints (`/api/decisions/...`, one CLI call per click under the
operator token, audited) rather than growing a second token and audit log.

## D5 · 2026-09-02 · Recompute holders, kind and stage from the ledger

Recommended and accepted. Port ATC's `kind_of` and stage ladder under MIT with
attribution rather than reading ATC's `data.json` at runtime. The parity check
compares stage per item against ATC's file daily so the two views agree.

## D6 · 2026-09-02 · Public repo `gdiab/tightbeam-toplines`, MIT

Ruled by George. Layout mirrors tightbeam-atc (`bin/`, `web/`, `docs/`,
`systemd/`) since it is the same kind of thing on the same host.

## D7 · 2026-09-02 · Name: TopLines

Ruled by George. Hostname `toplines`, repo `tightbeam-toplines`, page title
"TopLines". The name is the CLI verb it replaces at the terminal.

## D8 · 2026-09-02 · Operator-scope visibility, one operator

Reading the ledger bypasses the gateway's per-user visibility. The org has one
operator (George), so this is the intended view. Reopen if anyone else gets
tailnet access to the hostname: either scope rows by owner in the generator or
move reads behind device tokens.

## D9 · 2026-09-02 · Visual system mirrors ATC's tokens

ATC has no design system, only a `THEMES` object in its page. TopLines copies
those values into its own token file with a comment naming the ATC commit, so
the two pages read as one instrument panel without code coupling. Encodings
inherit ATC's meanings: recency fade for quiet, tether colors for running and
waiting, the stage ramp for evidence, kind colors for holders. Details in
`design.md`.

## D10 · 2026-09-02 · Appearance toggle, a deliberate deviation from ATC

Ruled by George. ATC follows the OS only. TopLines offers system, light and
dark, remembered per browser. The default remains the OS setting.

## D11 · 2026-09-02 · Cross-links

TopLines links to ATC in its header. A link from ATC back to TopLines is
desired but is a change to ATC; it goes to `clickety-clacks/tightbeam-atc` as
an issue or PR after TopLines is live, outside this work.

## D12 · 2026-09-02 · Deploy as `gd`, user units, no root

Everything TopLines needs runs as the user that owns the ledger. systemd user
units (linger is on), files under `/home/gd/tb-toplines/`, the sidecar started
with `docker` as gd. Loopback port 8898 reserved. No ufw change since the
sidecar reaches loopback directly.

## D13 · 2026-09-02 · One short read transaction per pass

ATC's generator opens one `BEGIN` so every fact in a pass comes from one
snapshot, then closes. TopLines copies that. The earlier v1 note said "no
explicit transactions"; that was too strict. The rule is short, never long.

## D14 · 2026-09-02 · Tightbeam builds it

Ruled by George. The repo and these documents are handed to a new Tightbeam
product owner for re-review, then staffed. `po-brief.md` is the handoff.

## D15 · 2026-09-02 · Coverage provenance is copied, never synthesized

Resolves the first original open question. The footer's `coverageBasis` and
`edgeBasis` are copied verbatim from the daily parity check's one
`tightbeam toplines` response and stamped with the parity run time (`ranAt`).
The generator never computes or estimates either value; both are `null` until
the first parity run. See `docs/spec.md` Scope 6 and `docs/data-contract.md`
(`parity` object).

## D16 · 2026-09-02 · Iceboxed items are a flat list

Resolves the second original open question. Open items get quiet-band dividers;
iceboxed items are shown as a single flat list with no dividers. See
`docs/spec.md` Scope 3.

## D17 · 2026-09-02 · Wake prompts keep 140 code points

Resolves the third original open question. A pending wake's `prompt` carries the
first 140 Unicode code points of `wakes.prompt` in v1; the rest is dropped. See
`docs/data-contract.md` (`org.wakes[].prompt`).

## D18 · 2026-09-03 · Spec-correction rulings — CLI and deployed-ATC authority

Ruled by George (`dr_9daadbe0`) and the PO (`att_5ecfb687`), homing the
spec-correction pass. (D-d) Quiet, Running and wake-queued mirror the CLI's
algorithm exactly; Quiet reduces to `lastProgressAt ?? createdAt` because
`work_items` has no `startedAt` column. (D-a) Holder kind is ported verbatim
from the deployed ATC generator's display-name `kind_of`
(`/usr/local/bin/tb-weather-gen` lines 48-57); display-name inference is the
ruled approach, the vocabulary is the deployed seven kinds. (D-b/D-c) The stage
ladder is ported verbatim from the deployed binary (lines 282-306); the stage
never consults git, so TopLines' stage matches the deployed ATC exactly, and
TopLines omits ATC's separate git-derived `merged` field. The abandoned commit
`181ca45` and the Desk-layer fork checkout are not authority. See `docs/spec.md`
Terms → Stage / Holder kind and `reference/atc-derivations.md`.
