# TopLines — a read-only live board of the org's work

Repo: `gdiab/tightbeam-toplines` (this repo), base `main`.
Requested by George 2026-09-01. Specified 2026-09-02 from a reviewed mock.
Host: `sirius`, the Tightbeam host. Sibling of `clickety-clacks/tightbeam-atc`,
which this work must not modify.

## Problem

The org's state is fully queryable, but only piecewise. `tightbeam toplines`
returns 400 KB of JSON for 184 items; `attests` and `transcript` read one card
or one session at a time; ATC shows the shape of the org beautifully and says
little about a specific row. The operator's actual question several times a day
is tabular: which items are open, who holds each, how long since anyone made
progress, what evidence each carries, which wakes fire next, and whether
anything is waiting on me. Today that means a terminal and several commands.
It should be a page on the tailnet that is always current.

## Hard constraints

1. **No `tightbeam` CLI polling.** Every CLI verb appends to the ledger's
   `events`; a read loop on the CLI grew `state.db` to 4.9 GB and cascaded
   into a VM crash (clickety-clacks/tightbeam#10). All live reads come from
   `state.db` opened `file:...?mode=ro`. The one sanctioned CLI call is the
   nightly parity check (§ Scope 6), once per day.
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
6. **Standard library only.** Python 3.12 stdlib for the watcher, generator,
   server and parity check. One static HTML file for the page.
7. **Deploy as `gd`, no root.** systemd user units, files under
   `/home/gd/tb-toplines/`, the sidecar via `docker` (gd is in the docker
   group). Loopback port 8898, bound to 127.0.0.1 only. No ufw change.

## Scope

1. **Watcher** `bin/tb-toplines-watch`. One read-only connection; poll
   `PRAGMA data_version` every 0.5 s; on change run the generator with a 2 s
   cooldown measured from the end of the previous pass; run it anyway every
   30 s as a heartbeat so idle timers advance. Port of ATC's
   `bin/tb-weather-watch` with the cooldown changed.
2. **Generator** `bin/tb-toplines-gen`. Reads the ledger read-only in one
   short transaction and writes `web/toplines.json` atomically (temp file,
   rename). Emits exactly the shape in `docs/data-contract.md`. Per item:
   identity, state, minutes since last progress, running and queued turn
   state, pending wake, open and closed cards with outcomes, attest counts by
   kind and verdict kind, evidence stage on ATC's ladder, holders with name,
   kind, harness and model, turn count, open decision requests, fail reason.
   Org-wide: sessions by kind and harness, item counts by state, pending
   wakes with due time and origin, open operator decision requests, and a
   footprint block (database bytes, WAL bytes, pass duration). Target pass
   time under 300 ms on today's ledger (516 MB, 13k turns, 6.7k attests).
3. **Page** `web/index.html`. The reviewed mock (`mock/toplines.html`) with
   its inline snapshot replaced by a single-flight fetch of `toplines.json`
   every 2 s, rows keyed by item id and updated in place, and a stale banner
   when `generatedAt` is older than 90 s. Vitals strip, filters (state,
   holder kind, quiet band), the work-items table with quiet-band dividers,
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
   Runs `tightbeam toplines --as-user george` exactly once, compares each open
   item's minutes-since-progress (tolerance 120 s), open and closed card
   counts and attest totals against the latest `toplines.json`, and compares
   each item's stage against ATC's `/opt/tb-atc/web/data.json` (read, not
   requested). Writes a `parity` block into the next `toplines.json` via a
   sidecar file the generator merges, so the page shows "parity ok, 03:00" or
   a warning naming the first mismatch.
7. **Runbook** `docs/runbook.md` finished: install, start, verify, logs,
   restart, roll back, and what to do when the parity check warns.

## Non-goals

- Any write to the org from the page (D4).
- Per-user visibility scoping. The board reads with operator visibility. The
  org has one operator; if that changes, this is reopened (D8).
- History, sparklines, per-agent pages, notifications, sound.
- A link from ATC back to TopLines. Desired, but it is a change to ATC and
  goes to `clickety-clacks/tightbeam-atc` as an issue or PR, outside this
  work.
- Supporting a second host or a remote ledger. One host, local file.

## Definitions the generator must match

- **Quiet (minutes since progress).** Milliseconds since the newest
  `progress` attest on any assignment threaded to the item; if none, since
  the item's `startedAt`, else its `createdAt`. Must agree with the CLI's
  `sinceProgressMs` within 120 s; the parity check enforces it.
- **Running / wake queued.** Running: a `turns` row for a holder session with
  `startedAt` set and `endedAt` null. Wake queued: a `wakes` row in state
  `pending` addressed to a holder session. Mirror the CLI's
  `active.runningTurn` and `active.pendingSessionWake`.
- **Stage.** ATC's ladder, ported verbatim from `tb-weather-gen`: 0 nothing;
  1 a progress attest; 2 a tests-passed verdict; 3 a completion attest; 4 a
  reviewed-clean, spec-reviewed or verified verdict; 5 ready to merge or
  merged; 6 closed. The page labels the bands by name in the tooltip.
- **Holder kind.** ATC's `kind_of(archetype, roles)`: main from a durable
  `main` role row, else archetype mapped to po, orch, coder, rev, spec, recon,
  else agent. Reproduce ATC's derivation of `patrol` too; find where ATC
  derives it and port that, do not infer it from display names.
- **Needs you.** Rows in `decision_requests` with `kind='operator'` and
  `status='open'`, plus the per-item count the CLI reports as
  `openDecisionRequests`.

## Acceptance

Every line demonstrated on sirius, command and output on the card.

1. `https://toplines.tailf064dc.ts.net/` renders from a tailnet device with no
   external requests (browser network panel: only same-origin).
2. With the mock's 17 open items as reference, the live page shows the same
   items with quiet, cards, attests and holders that match a fresh
   `tightbeam toplines --as-user george` run (one call, made by hand for this
   check) within the stated tolerances.
3. Latency: file a progress attest on a test card, time until the row's quiet
   resets on screen. Under 5 s, three trials.
4. Stale banner appears within 2 minutes of `systemctl --user stop
   tb-toplines-watch`, disappears within 5 s of start.
5. `PRAGMA data_version` poll and generator pass cause no write: `ls -la
   ~/.tightbeam/state.db-wal` size stays within its checkpoint band (about
   4 MB) across an hour of operation; generator pass under 300 ms per the
   footprint block.
6. Generator opens the ledger with `mode=ro` (grep the source) and exits
   non-zero, leaving the previous `toplines.json` intact, if the schema it
   expects is missing (test by pointing it at an empty database).
7. Light and dark render correctly from the OS setting and from the toggle;
   the toggle survives reload.
8. Header link opens ATC at `https://atc.tailf064dc.ts.net/`.
9. Parity timer has run once, its result is visible on the page, and a
   deliberately corrupted stage in `data.json` copy makes it warn.
10. `docs/runbook.md` walks a fresh shell through install, verify and roll
    back, and the reviewer has followed it.
11. Nothing under `/opt/tb-atc`, `/usr/local/bin/tb-weather-*`, or the
    `tb-atc-ts` container changed (`stat` before and after; `docker inspect`
    diff).

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

## Open questions for the PO

1. The CLI's `coverage.basis` and `edgeBasis` are shown in the mock footer as
   provenance. The generator cannot compute them from the ledger. Drop them,
   or copy them once from the nightly parity output?
2. Should iceboxed items get quiet-band dividers like open ones, or a flat
   list? The mock does flat.
3. Wake prompts are truncated to 140 characters in the rail. Enough?
