# TopLines — a read-only live board of the org's work

Repo: `gdiab/tightbeam-toplines` (this repo), base `main`.
Requested by George 2026-09-01. Specified 2026-09-02 from a reviewed mock.
Host: `sirius`, the Tightbeam host. Sibling of `clickety-clacks/tightbeam-atc`,
which this work must not modify.

## Goal

The org's state is fully queryable, but only piecewise. `tightbeam toplines`
returns 400 KB of JSON for 184 items; `attests` and `transcript` read one card
or one session at a time; ATC shows the shape of the org beautifully and says
little about a specific row. The operator's actual question several times a day
is tabular: which items are open, who holds each, how long since anyone made
progress, what evidence each carries, which wakes fire next, and whether
anything is waiting on me. Today that means a terminal and several commands.
It should be a page on the tailnet that is always current. The v1 outcome is a
truthful, read-only table that lets the operator answer those questions without
assembling several terminal responses.

## Invariants

1. **No production `tightbeam` CLI polling.** Every CLI verb appends to the ledger's
   `events`; a read loop on the CLI grew `state.db` to 4.9 GB and cascaded
   into a VM crash (clickety-clacks/tightbeam#10). All live reads come from
   `state.db` opened `file:...?mode=ro`. Deployed code may make one CLI call:
   the daily parity check (§ Scope 6), once per day. The bounded manual calls
   named in Acceptance 2 and 9 are acceptance evidence, not a deployed cadence.
2. **Short read transactions only.** The generator takes one `BEGIN`, runs its
   queries, and closes, in well under a second. A long-lived read snapshot
   blocks WAL checkpointing and grows the log without bound.
3. **ATC is untouched.** No change to its repo, installed files, sidecar, or
   `tailscale serve` rules. TopLines has its own hostname, sidecar, service,
   port and files. Porting code from ATC is allowed under its MIT license with
   attribution (`reference/atc-derivations.md`).
4. **Read-only in v1.** The page changes nothing in the org. No control API, no
   operator token. Decision D4 in `docs/decisions.md`; George may reopen it.
5. **No external fetches.** The page loads with no internet: no CDN, no web
   fonts, no analytics. System fonts only.
6. **No third-party runtime dependencies.** The watcher keeps ATC's Bash wrapper
   plus inline Python 3.12 shape. The generator, server and parity check use only
   the Python 3.12 standard library. The page is one static HTML file with
   inline CSS and JavaScript.
7. **Deploy as `gd`, no root.** systemd user units, files under
   `/home/gd/tb-toplines/`, the sidecar via `docker` (gd is in the docker
   group). Loopback port 8898, bound to 127.0.0.1 only. No ufw change.

## Assumptions

- The production ledger is a local SQLite database in WAL mode at
  `/home/gd/.tightbeam/state.db`; deployment must verify that path and mode.
- George is the sole operator and the only person granted tailnet access to the
  TopLines hostname (D8). A second viewer invalidates the visibility model.
- User `gd` can read the ledger, manage systemd user units, use Docker, and bind
  loopback port 8898. Deployment must verify each capability before install.
- Schema drift is expected over time. An unknown required table or column is a
  named failure that preserves the last good page data; it is never guessed.

## Architecture

`docs/architecture.md` owns the component diagram, data flow, latency budget and
failure-mode rationale. The required components and behavior are the numbered
scope below. If the architecture note and this contract disagree, stop for a PO
ruling before implementation.

## Scope

1. **Watcher** `bin/tb-toplines-watch`. Open one read-only connection and run the
   generator once before waiting. Poll `PRAGMA data_version` every 0.5 s. A
   change sets a pending-generation flag. Run once as soon as at least 2 s have
   elapsed since the previous pass ended, then clear the flag only if no newer
   change arrived. A change during a pass or cooldown must cause a pass at the
   next eligible instant; it must not be discarded. Run at least every 30 s as
   a heartbeat so idle timers advance. Port ATC's `bin/tb-weather-watch` only
   where that behavior agrees with this clause.
2. **Generator** `bin/tb-toplines-gen`. Reads the ledger read-only in one
   short transaction and writes `web/toplines.json` atomically (temp file,
   rename). It resolves reviewed-assignment membership and reads every ledger
   table required by the Terms below. Emits exactly the shape in `docs/data-contract.md`.
   Per item:
   identity, state, time since last progress (the CLI's `sinceProgressMs`),
   running and queued turn
   state, pending wake, open and closed cards with outcomes, attest counts by
   kind and verdict kind, evidence stage on ATC's ladder, holders with name,
   kind, harness and model, turn count, open decision requests, fail reason.
   Org-wide: sessions by kind and harness, item counts by state, pending
   wakes with due time and origin, open operator decision requests, and a
   footprint block (database bytes, WAL bytes, pass duration). Target pass
   time under 300 ms on today's ledger (516 MB, 13k turns, 6.7k attests).
3. **Page** `web/index.html`. The reviewed mock (`mock/toplines.html`) with
   its inline snapshot replaced by a single-flight fetch of `toplines.json`
   every 2 s and a stale/error banner when `generatedAt` is older than 90 s or
   a fetch, parse, or schema-version check fails. Vitals strip, filters (state,
   every holder kind present, quiet band), the work-items table with quiet-band
   dividers for open items only (iceboxed items are a flat list),
   the right rail (needs your ruling, scheduled wakes, sessions by kind), the
   appearance toggle (system, light, dark, remembered per browser), and a
   link to ATC in the header. Visual system per `docs/design.md`.
4. **Server** `bin/tb-toplines-serve`. Static file server on 127.0.0.1:8898
   serving `web/`, `Cache-Control: no-store` on `toplines.json`. Stdlib
   `http.server` is acceptable; single process.
5. **Sidecar** `tb-toplines-ts`. A `tailscale/tailscale` container with host
   networking, `TS_USERSPACE=1`, `TS_HOSTNAME=toplines`, state in a named
   volume, serving `https://toplines.tailf064dc.ts.net/` to
   `http://127.0.0.1:8898`. Tailnet-only. Mirrors how `tb-atc-ts` is run,
   without touching it.
6. **Parity check** `bin/tb-toplines-parity` on a daily systemd user timer.
   Runs `tightbeam toplines --as-user george` exactly once, then immediately
   runs the generator and compares each open item's minutes-since-progress
   (`sinceProgressMs`, tolerance 120 s), open and closed card counts and attest totals against
   that generated `toplines.json`. It also compares each item's stage against
   ATC's `/opt/tb-atc/web/data.json` (read, not requested). If a compared input
   row changed between the CLI start and the generator snapshot, the result is
   `inconclusive` with the changing input named, not `ok` or a mismatch; the
   timer does not make a second CLI call that day. Writes a `parity` block into
   the next `toplines.json` via a sidecar file the generator merges, so the page
   shows "parity ok, 03:00", an inconclusive notice, or a warning naming the
   first mismatch. The sidecar also copies
   `coverage.basis` and `edgeBasis` from that same CLI response and stamps them
   with the parity run time; the generator never synthesizes either value.
7. **Runbook** `docs/runbook.md` finished: install, start, verify, logs,
   restart, roll back, and what to do when the parity check warns.
8. **Documented test seams.** Production defaults are fixed, but the binaries
   accept these environment overrides so destructive negative tests never touch
   production inputs: `TB_TOPLINES_DB` (a database path that code always turns
   into a `file:...?mode=ro` URI), `TB_TOPLINES_OUT`,
   `TB_TOPLINES_PARITY`, and `TB_TOPLINES_ATC_DATA`. Parity also accepts
   `TB_TOPLINES_CLI_JSON`, a captured real CLI response; when set it performs
   compare-only work and must not invoke `tightbeam`. Service units set none of
   these except the deployed output paths.

## Non-goals

- Any write to the org from the page (D4).
- Per-user visibility scoping. The board reads with operator visibility. The
  org has one operator; if that changes, this is reopened (D8).
- History, sparklines, per-agent pages, notifications, sound.
- A link from ATC back to TopLines. Desired, but it is a change to ATC and
  goes to `clickety-clacks/tightbeam-atc` as an issue or PR, outside this
  work.
- Supporting a second host or a remote ledger. One host, local file.

## Terms

Authority (PO governing principle, att_5ecfb687): where a definition feeds the
daily parity check, the authority is whatever parity measures against — the CLI's
actual algorithm for ledger-derived numbers, and the deployed (parity-target) ATC
for the stage ladder and holder kind. Where a Term's wording and that authority
disagree, the authority wins and this Term is corrected to it.

- **Assignment membership.** An assignment belongs to its non-null
  `workItemId`. Otherwise it belongs to the item resolved through its
  `reviewsAssignmentId` chain. One assignment belongs to at most one item.
- **Quiet (milliseconds since progress).** Mirror the CLI's `sinceProgressMs`
  exactly (D-d, ruled att_5ecfb687). `lastProgressAt` is the newest `progress`
  attest timestamp on any member assignment of the item (Assignment
  membership), else `null`. `sinceProgressMs` is `generatedAt` minus
  `(lastProgressAt ?? createdAt)`. `work_items` has only a `createdAt` column —
  there is no `startedAt`, so there is no `startedAt` fallback; the CLI's
  algorithm reduces to `lastProgressAt ?? createdAt` for the same reason. The
  contract field carrying the anchor is `lastProgressAt`. Parity tolerance is
  120 s.
- **Running / wake queued.** Mirror the CLI's `active.runningTurn` and
  `active.pendingSessionWake` (D-d). Running is true when any session holding a
  current open member assignment of the item has a `turns` row with `startedAt`
  set and `endedAt` null (equivalently `turns.status = 'running'`, the only
  started-but-not-ended status). Wake queued is true when any such holder
  session has a `wakes` row in state `pending`.
- **Turn counts.** `turns.total` and `turns.live` count the turns threaded to
  the item through Assignment membership and rows whose `jobRef` is the item id;
  `live` counts those started and not ended. An item with no such turns is `0`,
  a real zero. Turn counts are a display number and are not in the parity
  comparison.
- **Stage.** The evidence ladder is ported verbatim from the deployed
  (parity-target) ATC generator `/usr/local/bin/tb-weather-gen`, lines 282-306
  (D-b/D-c, ruled att_5ecfb687 + George dr_9daadbe0; `reference/atc-derivations.md`
  §3 is the source pin). Evaluate top-down; the highest satisfied rung wins: 0
  none; 1 a `progress` attest; 2 a `tests-passed` verdict; 3 a `completion`
  attest; 4 a `reviewed-clean`, `spec-reviewed`, or `verified` verdict; 5
  merge-ready — a `completion` attest AND a `reviewed-clean` verdict, the review
  not stale, and no open assignment; 6 a closed item with no open assignment. A
  `reviewed-clean` verdict is stale when a `tests-passed` verdict landed more than
  300 s after it (new code tested after the review), which drops the item back to
  4; this is the deployed predicate (lines 295-303). The stage reads only attest
  kinds, verdict kinds and item state — it does NOT consult git ancestry, in the
  deployed ATC or here. ATC's only git-derived signal is a separate `merged`
  green-ring boolean (deployed line 332); TopLines does not probe git and omits
  that field. Because the stage needs no git, TopLines' stage EQUALS the deployed
  ATC's stage for the same ledger, and the daily parity check (Scope 6) compares
  them expecting an exact match: a genuine mismatch warns, and a row that changed
  between the CLI start and the generator snapshot is `inconclusive`, not a
  mismatch. No `ready-to-merge` verdict exists in the ledger today, and no open
  item currently satisfies rung 5 (live stages are 1, 4 and 6), but rung 5 is
  reachable via `completion` + `reviewed-clean`. Closed items are omitted from
  `toplines.json` (`docs/data-contract.md`), so rung 6 does not appear in output;
  `stage` is `null` for an item whose ladder cannot be evaluated (missing rows),
  never guessed.
- **Holder kind.** Ported verbatim from the deployed ATC generator
  `/usr/local/bin/tb-weather-gen` `kind_of(name)`, lines 48-57 (D-a, ruled
  att_5ecfb687 + George dr_9daadbe0; `reference/atc-derivations.md` §2 is the
  source pin). Kind is inferred from the session DISPLAY NAME, lower-cased, first
  match wins: `main` when the name is exactly `main`; `po` when it contains
  `product owner`; `patrol` when it contains `patrol` or `watchdog`; `orch` when
  it contains `orchestrator`; `coder` when it contains `coder`; `rev` when it
  contains `review`; `spec` when it contains `spec`; otherwise `coder`. Then one
  post-step (deployed lines 164-168): a session that classified as `coder` but
  has no spawner (`sessions.spawnedBy` null) is re-labelled `po`. The vocabulary
  is exactly these seven kinds — `main`, `po`, `patrol`, `orch`, `coder`, `rev`,
  `spec` — with `coder` the default; there is no `recon` or `agent` kind, and
  nothing reads `sessions.kind` (the deployed sessions query selects no such
  column). Display-name inference is therefore the ruled approach for every kind,
  `patrol` included: the sole patrol session (display name
  `Stall Patrol - coordination flow`, archetype `orchestrator`) classifies as
  `patrol` by its name. The earlier archetype-based derivation and the "never
  infer kind from a display name" prohibition are superseded.
- **Needs you.** Only rows in `decision_requests` with `kind='operator'` and
  `status='open'` are needs-you rows. The per-item count joins those rows
  through Assignment membership; it does not copy the CLI's broader count of
  every open decision-request kind.

## Acceptance

Every line demonstrated on sirius, command and output on the card.

1. `https://toplines.tailf064dc.ts.net/` renders from a tailnet device with no
   external requests (browser network panel: only same-origin).
2. Capture one fresh `tightbeam toplines --as-user george` response by hand.
   The default open view's item-id set matches the response's open item set
   exactly. For every open item, quiet, card counts, attest totals and kinds,
   and active flags match within the stated tolerance. Holder session keys and
   their name, archetype, harness and model match one read-only ledger query;
   those fields are not claimed to come from the CLI response. Save the real
   CLI response as the parity negative-test input for Acceptance 9.
3. Latency: file a progress attest on a test card, time until the row's quiet
   resets on screen. Under 5 s, three trials, including one commit made during
   the watcher's cooldown.
4. Stale banner appears within 2 minutes of `systemctl --user stop
   tb-toplines-watch`, and disappears within 5 s of start without requiring a
   ledger change. A failed fetch, malformed JSON, and unsupported higher schema
   each show a named error while the last good rows remain visible.
5. Against a database copy captured from the live ledger, keep the watcher in
   its pulse, cooldown and heartbeat states while a second connection commits
   and checkpoints; the checkpoint completes and the WAL can truncate, proving
   no read transaction spans a sleep. On the live ledger, ten generator passes
   each complete under 300 ms by an independent wall-clock measurement; the
   footprint block agrees. All reader source paths construct a `mode=ro` URI.
6. Generator opens the ledger with `mode=ro` (grep the source) and exits
   non-zero, leaving the previous `toplines.json` intact, if the schema it
   expects is missing. Demonstrate with an existing empty database selected by
   `TB_TOPLINES_DB` and a seeded output selected by `TB_TOPLINES_OUT`; record
   the output hash before and after.
7. At the mock's desktop, 1000 px and 600 px widths, computed theme tokens match
   `docs/design.md`, text and controls remain readable, and the table stays
   inside its horizontal scroller. OS light/dark and each explicit toggle state
   work; the toggle survives reload.
8. Header link opens ATC at `https://atc.tailf064dc.ts.net/`.
9. Parity timer has run once, its result is visible on the page, and a
   deliberately corrupted stage in a copy of ATC's `data.json` makes it warn.
   Run the negative control with `TB_TOPLINES_CLI_JSON` set to the real capture
   from Acceptance 2 and `TB_TOPLINES_ATC_DATA` set to the corrupt copy; prove
   it makes no additional CLI call and does not modify ATC.
10. `docs/runbook.md` walks a fresh shell through install, verify and roll
    back, and the reviewer has followed it.
11. Nothing under `/opt/tb-atc`, `/usr/local/bin/tb-weather-*`, or the
    `tb-atc-ts` container changed. Compare before/after recursive SHA-256
    manifests and metadata for both filesystem paths, normalized
    `docker inspect` output, and `tailscale serve status` from `tb-atc-ts`.

## Fixtures

- Snapshot the mock renders: `mock/snapshot-2026-09-01T2055.json`.
- ATC's live picture at the same moment: fields listed in
  `reference/atc-derivations.md`.
- Ledger facts on 2026-09-01: 184 work items (17 open, 73 iceboxed, 93
  closed, 1 failed), 348 sessions (51 active), 717 assignments, 6,705
  attests, 13,134 turns, 17,392 wakes; `state.db` 516 MB, WAL 4 MB,
  `journal_mode=wal`, `wal_autocheckpoint=1000`.
- ATC cost on sirius over 16 h: watcher plus generator about 6% of one core,
  page server under 0.1%; one ATC pass 130 ms. The host was at load 0.03 on
  16 threads with 21 GB free.

## Open questions

None open. Every question this spec raised is ruled; no hole remains.

Resolved (George `dr_9daadbe0`, superseding the earlier `dr_3527028b` escalation):
- **D-a** — Holder kind is ported verbatim from the deployed ATC generator's
  display-name `kind_of` (`/usr/local/bin/tb-weather-gen` lines 48-57). Display-name
  inference is the ruled approach for every kind; the `patrol` session classifies
  as `patrol` by its name, and the vocabulary is the deployed seven kinds (no
  `recon`, no `agent`). See Terms → Holder kind and `reference/atc-derivations.md` §2.
- **D-b** — The authoritative ATC source is the DEPLOYED binary
  `/usr/local/bin/tb-weather-gen` (+ `/opt/tb-atc/web/data.json` for stage parity).
  The abandoned commit `181ca45` and the Desk-layer fork checkout are not
  authority. The Stage ladder is ported verbatim from deployed lines 282-306,
  including rung 5's exact predicate; the stage never consults git, so TopLines'
  stage matches the deployed ATC's exactly. See Terms → Stage and
  `reference/atc-derivations.md` §3.

Resolved earlier this pass (PO rulings att_5ecfb687):
- **D-d** — Quiet, Running and wake-queued match the CLI's algorithm exactly;
  Quiet reduces to `lastProgressAt ?? createdAt` because `work_items` has no
  `startedAt` column. See Terms.
- **D-c** — the Stage ladder STRUCTURE matches the deployed ATC; the simplification
  is that TopLines omits ATC's separate git-derived `merged` field, not the stage.

The original three questions are resolved: coverage provenance is copied from
the timestamped daily parity response; iceboxed items are flat; wake prompts
keep the first 140 Unicode code points in v1.

Integration note (`dr_b1b03664`): no session on sirius currently holds GitHub
write (gh unauthenticated, https origin). The final merge and push of this
spec-correction branch to `main` is performed by a designated write-capable
session (the operator/ops session), not by the coders or the orchestrator. The
PR is prepared locally; the designated session performs the push and merge. This
unblocks only the eventual merge, not this spec pass. See `docs/runbook.md`.

## Spec homing

This file owns required behavior and acceptance. `docs/data-contract.md` owns
the JSON field shape, `docs/design.md` and `mock/toplines.html` own presentation
as stated in the design document, `docs/architecture.md` owns rationale,
`docs/decisions.md` owns dated rulings, and `reference/atc-derivations.md` owns
source attribution. `AGENTS.md` is the operating pattern this work teaches
agents. A conflict between homes blocks implementation until the PO rules it.
