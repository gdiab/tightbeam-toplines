# What to port from ATC, and under what terms

Source: `clickety-clacks/tightbeam-atc`, MIT License, Copyright (c) 2026 Mike
Manzano. Local checkout on George's Mac at `~/github/tightbeam-atc`; installed
on sirius at `/opt/tb-atc` and `/usr/local/bin/tb-weather-*`. Line numbers are
from commit `181ca45` (2026-08-25). Re-check them against the checkout before
porting; do not port from the installed copies.

Attribution: keep the header comment on each ported file naming the source
file, commit and license, and keep the notice at the bottom of this repo's
`LICENSE`. Port, do not import: TopLines must run with ATC absent.

## 1. The watcher

`bin/tb-weather-watch`, whole file (about 60 lines of bash with an inline
Python loop). Change: `MIN_GAP` default from 10 to 2, environment variable
names from `TB_WEATHER_*` to `TB_TOPLINES_*`, generator path. Keep the
cooldown measured from the end of a pass, the 0.5 s pulse, the 30 s heartbeat,
and the `mode=ro` URI. Its header comment explains why `data_version` beats
inotify and WAL watching; keep that reasoning in the ported header.

## 2. Holder kind

`bin/tb-weather-gen`, `kind_of(archetype, roles)` at line 61:

- `main` when the session holds a durable `main` role row;
- else archetype mapped: product-owner to po, orchestrator to orch, coder to
  coder, reviewer to rev, spec-writer to spec, recon to recon;
- else `agent`.

ATC's live `data.json` also emits `patrol`, which this function does not
return. Find where ATC derives it (search the generator for `patrol`) and port
that path too. Do not infer patrol from a display name; the mock did, as a
stopgap, and that is not acceptable in the generator.

Roles come from the `roles` table (`name`, `boundSessionKey`); see the query
at line 369.

## 3. Evidence stage

`bin/tb-weather-gen`, the block starting at the comment "Evidence stage drives
the page's core metaphor" at line 617. The ladder as of that commit:

| stage | condition |
|---|---|
| 6 | item state closed |
| 5 | ready to merge or merged (see the `readyToMerge` and merge logic near line 678; TopLines may treat a `ready-to-merge` verdict as 5 and skip git ancestry) |
| 4 | a verdict of kind reviewed-clean, spec-reviewed or verified |
| 3 | a completion attest |
| 2 | a tests-passed verdict |
| 1 | a progress attest |
| 0 | none of the above |

Evaluate top-down; the highest satisfied rung wins. Attest kinds and verdict
kinds are read per item across all its assignments (see `ev_by` near line
502). ATC's stage 5 consults git ancestry caches for "merged"; TopLines does
not probe git. Document the simplification in the ported code and expect the
daily parity check to flag any item where ATC says 5 by ancestry and TopLines
says 4.

## 4. Queries worth reading before writing your own

All in `bin/tb-weather-gen`:

| what | near line |
|---|---|
| last activity per session from turns | 354 |
| last attest per session | 360 |
| sessions with display name, state, spawner | 367 |
| live turns (started, not ended) | 413, 439 |
| pending wakes due | 460 |
| work items in scope | 479 |
| holders per item from open assignments | 500 |
| attest evidence per item | 502 |
| last close per item | 506 |

The `BEGIN` at line 74 that puts a whole pass on one snapshot is the pattern
to keep (decision D13).

## 5. Operating pattern, not code

`server/tb-atc-api.py` lines 300 to 302 record the incident behind hard
constraint 1: a read loop on the CLI grew `state.db` to 4.9 GB and crashed the
VM (clickety-clacks/tightbeam#10). Cite it in the generator's header.

## 6. What not to port

The 3D scene, the control API, the operator token, the git probes, the tag and
arrow store, the Desk layer. TopLines is read-only and has no control plane.

## ATC fields the mock joined in

For the record, the mock at `mock/toplines.html` joined ATC's live `data.json`
(19 KB, 51 agents, 18 items) by session suffix to get holder names, kinds and
stages. Fields used: `items[].id`, `items[].holders[]`, `items[].stage`,
`agents[].kind`, `agents[].harness`, `agents[].model`, `agents[].name`. The
generator computes all of these itself (decision D5).
