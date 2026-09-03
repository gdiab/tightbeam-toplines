# What to port from ATC, and under what terms

Source: `clickety-clacks/tightbeam-atc`, MIT License, Copyright (c) 2026 Mike
Manzano. The porting AUTHORITY for TopLines is the copy DEPLOYED on sirius: the
generator `/usr/local/bin/tb-weather-gen` (read 2026-08-31, 529 lines) and, for
the daily stage parity check, the snapshot it publishes at
`/opt/tb-atc/web/data.json`. Line numbers below are from that deployed
generator; re-check them against the file on the host before porting. The
upstream commit `181ca45` is ABANDONED (unfetchable) and the local Desk-layer
fork checkout (`~/github/tightbeam-atc`, HEAD `a7d14e6`) is NOT authority —
port from the deployed binary only (D-a + D-b, ruled by George `dr_9daadbe0`).

Attribution: keep the header comment on each ported file naming the upstream
`clickety-clacks/tightbeam-atc` source file and its MIT license, and keep the
notice at the bottom of this repo's `LICENSE`. Port, do not import: TopLines
must run with ATC absent.

## 1. The watcher

`bin/tb-weather-watch`, whole file (about 60 lines of bash with an inline
Python loop). Change: `MIN_GAP` default from 10 to 2, environment variable
names from `TB_WEATHER_*` to `TB_TOPLINES_*`, generator path. Keep the
cooldown measured from the end of a pass, the 0.5 s pulse, the 30 s heartbeat,
and the `mode=ro` URI. Its header comment explains why `data_version` beats
inotify and WAL watching; keep that reasoning in the ported header.

## 2. Holder kind (D-a ruled, `dr_9daadbe0`)

`kind_of(name)` at lines 48-57. It classifies purely on the session DISPLAY
NAME (lower-cased); first match wins:

- `main` when the name is exactly `main`;
- `po` when it contains `product owner`;
- `patrol` when it contains `patrol` or `watchdog`;
- `orch` when it contains `orchestrator`;
- `coder` when it contains `coder`;
- `rev` when it contains `review`;
- `spec` when it contains `spec`;
- otherwise `coder`.

Then one post-step at lines 164-168: a session that classified as `coder` but
has no spawner (`sessions.spawnedBy` null) is re-labelled `po` — a top-of-tree
session named after nothing else is an owner-level mind, not a worker.

The vocabulary is exactly these seven kinds: `main`, `po`, `patrol`, `orch`,
`coder`, `rev`, `spec`. There is NO `recon` kind and NO `agent` kind; `coder`
is the default. `kind_of` is called at line 164 as `kind_of(displayName)`, and
the sessions query (lines 144-145) selects no `kind` column — so nothing here
reads `sessions.kind`. Every kind, `main` included, is derived from the display
name. This is the ruled correction: display-name inference is the port, and the
patrol session (display name `Stall Patrol - coordination flow`, archetype
`orchestrator`) classifies as `patrol` by its name. The earlier archetype+roles
derivation and the "never infer kind from a display name" prohibition are
dropped. `docs/spec.md` Terms → Holder kind is the home; keep it identical.

## 3. Evidence stage (D-b/D-c ruled, `dr_9daadbe0`)

The stage block at lines 282-306. Evaluate top-down; the highest satisfied rung
wins:

| stage | condition (deployed `tb-weather-gen`) |
|---|---|
| 6 | `work_items.state = 'closed'` and the item has no open assignment |
| 5 | a `completion` attest AND a `reviewed-clean` verdict, the review not stale, and no open assignment |
| 4 | a verdict of `reviewed-clean`, `spec-reviewed`, or `verified` |
| 3 | a `completion` attest |
| 2 | a `tests-passed` verdict |
| 1 | a `progress` attest |
| 0 | none of the above |

"Review not stale" is the deployed predicate at lines 295-303: the newest
`reviewed-clean` verdict is stale when a `tests-passed` verdict landed more than
300 s (300_000 ms) after it — new code tested after the review, so the review no
longer covers the work. Attest kinds and verdict kinds are read per item across
all its assignments (the `ev_by` query, lines 248-249).

Git ancestry does NOT enter the stage. The deployed stage block reads only
attest kinds, verdict kinds and item state; it never consults git. The only
git-derived signal in the deployed generator is a SEPARATE per-item `merged`
boolean (the green ring, line 332, from `merged_in_branch`), which is `null`
whenever no repo is configured — as it is on the deployed instance today (every
`merged` in `/opt/tb-atc/web/data.json` is `null`). TopLines does not probe git,
so it OMITS the `merged` field entirely. Because stage needs no git, TopLines'
stage EQUALS the deployed ATC's stage for the same ledger, and the daily parity
check (`docs/spec.md` Terms → Stage, Scope 6) compares the two expecting an
exact match: a genuine stage mismatch warns; a row that changed between the CLI
start and the generator snapshot is `inconclusive`, not a mismatch. (The
abandoned-fork note that "ATC rates 5 by ancestry, TopLines reads 4" described
that fork, not the deployed authority, and is dropped.)

No `ready-to-merge` verdict exists in the ledger; rung 5 is reached by
`completion` + `reviewed-clean`, not by any single verdict, and in today's
snapshot no open item satisfies it (live stages are 1, 4 and 6).

## 4. Queries worth reading before writing your own

All in the deployed `/usr/local/bin/tb-weather-gen`:

| what | line |
|---|---|
| last activity per session, from turns | 134-135 |
| last attest per session | 137 |
| sessions with display name, state, spawner, archetype, harness, model | 144-145 |
| live turns (started, not ended) | 189, 191-194, 199-202 |
| pending wakes due | 206 |
| work items in scope | 225 |
| holders per item from open assignments | 246-247 |
| attest evidence per item (kind, verdictKind, commitRefs, ts) | 248-249 |
| last close per item | 252 |
| pending wakes joined to items | 255-256 |

The deployed generator opens ONE read-only connection (`file:...?mode=ro`,
lines 38-39 and 59) and runs every query on it; it does not wrap the pass in an
explicit `BEGIN`. TopLines adds the explicit short read transaction its
Invariant 2 (decision D13) requires — that hardening is TopLines', not a
verbatim port.

## 5. Operating pattern, not code

The deployed generator's own module docstring (lines 30-33) records the incident
behind hard constraint 1: CLI reads append to `events` on a cadence, which grew
`state.db` to 4.9 GB and cascaded into a VM crash
(clickety-clacks/tightbeam#10). The generator never shells out to the
`tightbeam` CLI — every signal is read from `state.db` on the one `mode=ro`
connection. Cite this in the ported generator's header.

## 6. What not to port

The 3D scene, the control API, the operator token, the git probes (and the
`merged` field they feed), the tag and arrow store, the Desk layer. TopLines is
read-only and has no control plane.

## ATC fields the mock joined in

For the record, the mock at `mock/toplines.html` joined ATC's live `data.json`
(19 KB, 51 agents, 18 items) by session suffix to get holder names, kinds and
stages. Fields used: `items[].id`, `items[].holders[]`, `items[].stage`,
`agents[].kind`, `agents[].harness`, `agents[].model`, `agents[].name`. The
generator computes all of these itself (decision D5).
