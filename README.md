# TopLines

A read-only, live board of where every piece of work in a running
[Tightbeam](https://github.com/clickety-clacks/tightbeam) organization stands:
which items are open, who holds them, how long since anyone made progress, what
evidence they carry, which wakes are queued, and what is waiting on the
operator. It is the tabular sibling of
[Air Traffic Control](https://github.com/clickety-clacks/tightbeam-atc): ATC
draws the org as a 3D diagram, TopLines lays the same facts out as rows you can
sort and filter.

Status: **specified, not yet built.** This repo currently holds the spec, the
architecture, the design tokens, a reviewed mock, and the brief for the Tightbeam
product owner who will re-review and staff the work. See `docs/po-brief.md`.

## What it looks like

`mock/toplines.html` is the reviewed mock, built from a real snapshot of George's
org taken 2026-09-01 20:55 PDT. Open it in a browser; it needs no server. The
appearance toggle top right switches between the OS setting, light (ATC's
plotter paper) and dark (ATC's vector display).

## How it works, in one paragraph

A watcher on the Tightbeam host holds one read-only SQLite connection to the
ledger and polls `PRAGMA data_version` twice a second. When the counter moves,
a generator reads the ledger read-only in one short transaction, derives the
board's facts, and atomically rewrites `toplines.json`. A static page fetches
that file every two seconds. Commit to screen is one to five seconds. Nothing
in this pipeline talks to the gateway, holds a write lock, or calls the
`tightbeam` CLI on a cadence. Full detail in `docs/architecture.md`.

## Two rules that are not negotiable

1. **Read the ledger read-only. Never poll the CLI.** Every CLI verb is a
   dispatch the gateway records. A read loop built on the CLI once grew the
   ledger to 4.9 GB and crashed the host
   ([clickety-clacks/tightbeam#10](https://github.com/clickety-clacks/tightbeam/issues/10)).
   The single sanctioned CLI call is the nightly parity check.
2. **Nothing in this repo changes ATC.** TopLines shares a tailnet with ATC and
   links to it. It has its own hostname, its own service, its own sidecar, and
   ports nothing from ATC's repo without attribution (see `reference/`).

## Layout

| path | what |
|---|---|
| `docs/spec.md` | The spec a Tightbeam PO re-reviews and staffs against. Start here. |
| `docs/architecture.md` | Components, data flow, latency budget, failure modes. |
| `docs/decisions.md` | Decision log, dated, with the reasoning. |
| `docs/design.md` | Tokens mirrored from ATC, typography, encodings, the toggle. |
| `docs/data-contract.md` | The shape of `toplines.json` the generator emits and the page reads. |
| `docs/runbook.md` | Deploy, operate, roll back on sirius. Draft until the coder finishes it. |
| `docs/po-brief.md` | The handoff to the product owner, with the exact Tightbeam commands. |
| `mock/` | The reviewed mock and the snapshot it renders. |
| `reference/atc-derivations.md` | What to port from ATC, by file and line, and under what license. |
| `tasks/todo.md` | Working checklist, with a review section at the end. |
| `AGENTS.md` | Conventions for the agents that work this repo. |

## License

MIT. Portions derived from tightbeam-atc, MIT, copyright 2026 Mike Manzano; see
`reference/atc-derivations.md`.
