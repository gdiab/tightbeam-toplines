# Data contract: `toplines.json`

Written by `tb-toplines-gen`, read by `web/index.html` and by
`tb-toplines-parity`. One file, rewritten atomically. All timestamps are epoch
milliseconds, matching the ledger. Durations are milliseconds. Strings are
UTF-8. Absent facts are `null`, never omitted, so the page can tell "unknown"
from "zero".

```jsonc
{
  "schema": 1,
  "generatedAt": 1788322006642,
  "host": "sirius",
  "passMs": 142,                        // generator wall time for this pass
  "footprint": {
    "dbBytes": 516587520,
    "walBytes": 4198312
  },
  "parity": {                           // merged from parity.json when present, else null
    "ranAt": 1788339600000,
    "ok": true,
    "checked": 17,
    "firstMismatch": null               // or "wi_8d658b1e: quiet 1810s vs cli 1620s"
  },
  "org": {
    "sessions": {
      "total": 51,                      // sessions.state = 'active'
      // byKind is the DERIVED holder kind (see Rules), NOT the sessions.kind column
      // (sessions.kind is only 'main'|'dm'|'custom').
      // HOLE D-a (dr_3527028b): the 'patrol' bucket is unresolved — the sole patrol
      // session has archetype='orchestrator' (handle orchestrator:stall-patrol) and only
      // its display name says "patrol", which the spec forbids inferring from. Until
      // George rules, do not emit a 'patrol' bucket by guessing; see Rules → holders[].kind.
      "byKind":    {"main":1,"po":9,"patrol":1,"orch":5,"coder":18,"rev":16,"spec":1},
      "byHarness": {"codex":25,"claude":19,"cursor":7}
    },
    "items": {"open":17,"iceboxed":73,"closed":93,"failed":1},
    "decisionRequests": [               // kind = operator, status = open
      {
        "id": "dr_…",
        "question": "…",
        "raiser": "agent:product-owner:pi-harness",
        "raisedAt": 1788300000000,
        "deadlineAt": 1788386400000,
        "workItemId": "wi_…"            // via assignmentId when resolvable, else null
      }
    ],
    "wakes": [                          // state = pending, soonest first, at most 20
      {
        "id": "w_…",
        "dueAt": 1788321861784,
        "origin": "agent:orchestrator:stall-patrol",
        "toSessionKey": "agent:…",
        "workItemId": "wi_…",           // via assignmentId (wakes.assignmentId -> assignments.workItemId).
                                        // RECON: correct — wakes also has a direct work_item_id column
                                        // but it is unpopulated (0 of 17 pending rows), so assignmentId
                                        // routing is the right source; else null.
        "prompt": "STALL PATROL CONTINUATION: …"   // wakes.prompt, first 140 characters (D17)
      }
    ],
    "wakesPending": 7
  },
  "items": [                            // state in open, iceboxed, failed; closed omitted
    {
      "id": "wi_8d658b1e-7c29-4cb6-9a1c-e8c91f94885b",
      "short": "wi_8d658b1e",
      "title": "Pi v2 → ONE Pi PR against 0.1.9 …",
      "state": "open",                  // work_items.state; open | iceboxed | failed
      "failReason": null,               // work_items.failReason
      // RULED D-d (att_5ecfb687): work_items has ONLY createdAt (no startedAt/finishedAt
      // columns — recon B2/B2b). Quiet matches the CLI's sinceProgressMs exactly, which
      // with no startedAt reduces to (lastProgressAt ?? createdAt). The fictional
      // startedAt/finishedAt fields are dropped; createdAt (the real column) is exposed
      // and also drives the item's "started N ago" age display.
      "createdAt": 1788300000000,       // work_items.createdAt (real column)
      "lastProgressAt": 1788320961000,  // newest 'progress' attest (attests.ts) on any member assignment of the item, else null
      "sinceProgressMs": 1080000,       // generatedAt - (lastProgressAt ?? createdAt)  [D-d]
      "active": {
        "runningTurn": false,           // RULED D-d: mirror CLI active.runningTurn — any holder session (holding
                                        // a current open member assignment) has a turns row with startedAt set and
                                        // endedAt null. Verified: today this equals turns.status='running' (the only
                                        // started-but-not-ended status).
        "pendingSessionWake": true      // RULED D-d: mirror CLI active.pendingSessionWake — any such holder has a
                                        // wakes row in state 'pending'
      },
      "cards": {
        "open": 1,
        "closed": 0,
        "byOutcome": {"completed":0,"surrendered":0,"revoked":0}
      },
      "attests": {
        "total": 1,
        "byKind": {"progress":1},       // attests.kind: progress | surrender | completion | verdict, zero counts omitted
        "byVerdictKind": {}             // attests.verdictKind — free TEXT, no CHECK enum; pass through as found.
                                        // RECON: live values include reviewed-clean, tests-passed, verified,
                                        // spec-reviewed, changes-requested, spirit-accepted, thermo-clean, … (open set)
      },
      "stage": 1,                       // ATC ladder 0..6, see spec.md Terms → Stage and reference/atc-derivations.md.
                                        // RULED D-c: STRUCTURE mirrors the deployed (parity-target) ATC. TopLines
                                        // drops git ancestry and no 'ready-to-merge' verdict exists (0 rows), so
                                        // rung 5 is effectively unreached — items ATC rates 5 read 4 here and the
                                        // daily parity check flags them (expected).
                                        // HOLE D-b (dr_3527028b): the authoritative ATC source + reachable pin are
                                        // pending George; rung 5's exact predicate is not hardened until he pins it.
      "holders": [                      // sessions holding an open card, in card order
        {
          "sessionKey": "agent:product-owner:pi-harness s_751dc31a",
          "short": "s_751dc31a",
          "name": "PO — Pi harness",
          "kind": "po",
          "harness": "codex",
          "model": "gpt-5.6-sol"
        }
      ],
      "turns": {"total": 4, "live": 0},
      "openDecisionRequests": 0
    }
  ]
}
```

## Rules

- `items` is sorted by `state` (open, iceboxed, failed) then `sinceProgressMs`
  ascending. The page re-sorts for its filters; the file order is a sane
  default for anyone reading it raw.
- `generatedAt` is the wall clock at the start of the pass, so a 90 s stale
  test on the page measures the watcher, not the generator.
- `stage` is `null` when the item is closed or when ATC's ladder cannot be
  evaluated (missing attest rows), never guessed.
- `holders[].kind` uses ATC's vocabulary: `main`, `po`, `orch`, `coder`, `rev`,
  `spec`, `recon`, `agent`, plus `patrol` pending D-a. Derivation (ruled
  corrections, spec.md Terms → Holder kind is the home):
  - `main`: from `sessions.kind = 'main'`, NOT a durable `main` role row — there
    is no such role row, and the main session's archetype is `default`.
  - `po`/`orch`/`coder`/`rev`/`spec`/`recon`: map from `sessions.archetype`
    (product-owner, orchestrator, coder, reviewer, spec-writer, recon) — verified
    computable and clean.
  - unknown archetype: `agent`. Never infer kind from a display name.
  - `patrol`: **HOLE D-a (dr_3527028b)** — not derivable from archetype+roles (the
    patrol session is archetype `orchestrator`); its only signal is the display
    name, which the spec forbids. George decides: accept display-name inference for
    `patrol` as a single documented exception (PO recommendation), or drop `patrol`
    and classify that session as `orch`. Do not guess until he rules.
  - Provenance: **HOLE D-b (dr_3527028b)** — `reference/atc-derivations.md` pins
    these to `tb-weather-gen@181ca45`, which is ABSENT from the only checkout
    (`~/github/tightbeam-atc`, HEAD `a7d14e6`, a Desk-layer fork). Its live
    `kind_of(name)` is display-name-based (default `coder`) and it has no matching
    stage block; "port verbatim" is impossible from what exists. Until George pins
    a reachable authoritative ATC source, treat spec.md Terms as the authority for
    the ruled derivations, not the checkout.
- Unknown harness or model strings pass through as found in `sessions`.
- The parity block is `null` until the first parity run.
- `schema` increments only on an incompatible change; the page refuses a
  higher `schema` than it knows and says so in the stale banner.

## Size

Today's org: 91 items in scope, expected 60 to 80 KB. Wake prompts are
truncated and closed items are excluded to keep the two-second fetch cheap.
