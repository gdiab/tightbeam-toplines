# TopLines: working checklist

## Phase 0: specification (George's session, 2026-09-01 to 09-02)

- [x] Establish that Tightbeam agents are ACP stdio processes with nothing for a multiplexer to attach to; the observation surfaces are the ledger and the CLI
- [x] Mock the toplines board from a real snapshot; review; restyle onto ATC's tokens; add the appearance toggle
- [x] Ground the architecture in ATC's snapshot pipeline (watcher, generator, static page) and the #10 incident
- [x] Measure reader cost on sirius (ATC 6% of one core over 16 h, 130 ms pass, WAL 4 MB, load 0.03)
- [x] George's rulings: own hostname, read-only v1, public repo, name, toggle, Tightbeam builds it
- [x] Write spec, architecture v2, decisions, design, data contract, runbook draft, PO brief, ATC derivations reference
- [x] Create `gdiab/tightbeam-toplines`, push
- [ ] George files the work item and hires the PO per `docs/po-brief.md`

## Phase 1: PO re-review

- [ ] PO reviews `docs/spec.md`; findings as attests; edits as a PR
- [ ] PO verifies ledger column names read-only and corrects `docs/data-contract.md`
- [ ] PO answers or escalates the three open questions
- [ ] PO staffs: coder(s), cross-family reviewer

## Phase 2: build

- [ ] `bin/tb-toplines-watch` ported from ATC with attribution, 2 s cooldown
- [ ] `bin/tb-toplines-gen` emitting `docs/data-contract.md`, one short transaction, atomic write, non-zero on schema drift
- [ ] `bin/tb-toplines-serve` on 127.0.0.1:8898, no-store on the JSON
- [ ] `web/index.html` from the mock: fetch loop, in-place rows, stale banner, ATC link
- [ ] `bin/tb-toplines-parity` and its timer
- [ ] `systemd/` user units
- [ ] Pass time under 300 ms measured on sirius

## Phase 3: deploy and accept

- [ ] Sidecar `tb-toplines-ts` created; `toplines.tailf064dc.ts.net` serving
- [ ] All eleven acceptance lines in `docs/spec.md` demonstrated, output on the card
- [ ] `docs/runbook.md` finished by the deployer; reviewer followed it
- [ ] Nothing under ATC's paths changed (stat and docker inspect diffs on the card)
- [ ] Reviewer verdict filed

## Later, outside this work

- [ ] Issue or PR on `clickety-clacks/tightbeam-atc` for a link back to TopLines
- [ ] Reopen D4 if George wants rule and wake actions

## Review

Filled in by the PO at the end of Phase 3: what shipped, what deviated from
the spec and why, what the parity check has flagged in its first week, and
what to reopen.
