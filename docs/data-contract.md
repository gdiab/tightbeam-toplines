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
  "config": {                         // runtime install configuration; no secrets
    "operator": "maya",              // TB_TOPLINES_OPERATOR stripped; null when unset/blank
    "atcUrl": "https://example.ts.net/atc", // safe http/https TB_TOPLINES_ATC_URL; null when unset/invalid
    "tz": "Europe/Berlin"             // TB_TOPLINES_TZ, default UTC
  },
  "passMs": 142,                        // generator wall time for this pass
  "footprint": {
    "dbBytes": 516587520,
    "walBytes": 4198312
  },
  "parity": {                           // merged from parity.json when present; the whole object is null until the first parity run
    "ranAt": 1788339600000,             // parity run wall clock; ALSO the stamp on coverageBasis/edgeBasis (Scope 6)
    "outcome": "ok",                    // "ok" | "ok-ledger-atc-missing" | "mismatch" | "inconclusive"
    "checked": 17,                      // open items compared this run
    "firstMismatch": null,              // outcome="mismatch": first mismatch only, e.g. "wi_8d658b1e: quiet 1810s vs cli 1620s" | stage; else null
    "changingInput": null,              // outcome="inconclusive": the compared input row that changed between the CLI start and the generator snapshot; else null
    "coverageBasis": "…",               // copied VERBATIM from the CLI response's coverage.basis; the generator never synthesizes it; null until first run
    "edgeBasis": "…",                   // copied VERBATIM from the CLI response's edgeBasis; the generator never synthesizes it; null until first run
    "atcEvidence": "present",           // "present" when local ATC data was read; "missing" when stage comparison was skipped
    "atcEvidenceReason": null            // named local read/parse failure when atcEvidence="missing"; else null
  },
  "org": {
    "runningTurns": 3,                 // all turns.status = 'running' rows in this ledger snapshot, including unattributed rows
    "sessions": {
      "total": 51,                      // sessions.state = 'active'
      // byKind is the DERIVED holder kind (see Rules -> holders[].kind), from the
      // deployed ATC kind_of on the session DISPLAY NAME — NOT the sessions.kind
      // column. The 'patrol' bucket is ruled (D-a, dr_9daadbe0): the sole patrol
      // session (display name "Stall Patrol - coordination flow") classifies as
      // 'patrol' by its name. Vocabulary is the deployed seven: main, po, patrol,
      // orch, coder, rev, spec.
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
        "prompt": "STALL PATROL CONTINUATION: …"   // wakes.prompt, first 140 Unicode code points (D17)
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
      "stage": 1,                       // ATC ladder 0..6, see spec.md Terms → Stage and reference/atc-derivations.md §3.
                                        // RULED D-b/D-c (dr_9daadbe0): ported verbatim from the deployed ATC
                                        // /usr/local/bin/tb-weather-gen lines 282-306. The stage reads only attest
                                        // kinds, verdict kinds and item state — it never consults git, in ATC or
                                        // here, so TopLines' stage EQUALS the deployed ATC's stage and the daily
                                        // parity check expects an exact match. ATC's separate git-derived 'merged'
                                        // green ring is NOT a stage input and is not emitted by TopLines. No
                                        // 'ready-to-merge' verdict exists; rung 5 = completion + reviewed-clean
                                        // (review not stale) + no open assignment. Evidence and the 'no open
                                        // assignment' test read ONLY assignments whose direct workItemId is this
                                        // item (deployed ev_by L248-251 / holders_by L246-247), NOT the
                                        // reviewsAssignmentId-chain membership Quiet/Running use. Always an
                                        // integer 0..6 for every emitted item; 0 = no qualifying evidence, never null.
      "holders": [                      // sessions holding an open card, in card order
        {
          "sessionKey": "agent:product-owner:pi-harness s_751dc31a",
          "short": "s_751dc31a",
          "name": "PO — Pi harness",
          "kind": "coder",               // deployed kind_of("po — pi harness") has no 'product owner' substring -> coder;
                                         // the session is spawned (spawnedBy set) so the coder->po upgrade does NOT apply.
                                         // This matches ATC's live data.json — the abbreviated "PO —" name does not classify as po.
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

The install directory is deliberately absent from `config`. The pinned units
default to `$HOME/tb-toplines`; an alternate absolute directory is selected by
installer-written systemd `root.conf` drop-ins and by passing the same path to
`tb-toplines-verify-install --root`. `TB_TOPLINES_ROOT` names that runbook choice,
but no generator, watcher, server, or parity process reads it.

## Rules

- `items` is sorted by `state` (open, iceboxed, failed) then `sinceProgressMs`
  ascending. The page re-sorts for its filters; the file order is a sane
  default for anyone reading it raw.
- `generatedAt` is the wall clock at the start of the pass, so a 90 s stale
  test on the page measures the watcher, not the generator.
- `stage` is always an integer 0..6 for every emitted item (open, iceboxed,
  failed); `0` means no rung's evidence qualifies — it is never `null` and never
  guessed. Closed items (which the deployed ladder rates 6) are omitted from
  output entirely. A required table or column missing from the ledger is a
  generator-wide non-zero exit that preserves the last good page (Acceptance 6),
  not a per-item `null`.
- `holders[].kind` uses the deployed ATC vocabulary — exactly seven kinds:
  `main`, `po`, `patrol`, `orch`, `coder`, `rev`, `spec` (no `recon`, no
  `agent`). Derivation is ported verbatim from the deployed generator
  `/usr/local/bin/tb-weather-gen` `kind_of(name)` (lines 48-57), ruled D-a
  (dr_9daadbe0); spec.md Terms → Holder kind is the home:
  - Kind is inferred from the session DISPLAY NAME, lower-cased, first match
    wins: `main` when the name is exactly `main`; `po` when it contains
    `product owner`; `patrol` when it contains `patrol` or `watchdog`; `orch`
    when it contains `orchestrator`; `coder` when it contains `coder`; `rev`
    when it contains `review`; `spec` when it contains `spec`; otherwise
    `coder`.
  - Post-step (deployed lines 164-168): a session that classified as `coder`
    but has no spawner (`sessions.spawnedBy` null) is re-labelled `po`.
  - Nothing reads `sessions.kind`; the deployed sessions query selects no such
    column. Every kind, `main` included, comes from the display name. The
    `patrol` session (display name `Stall Patrol - coordination flow`, archetype
    `orchestrator`) classifies as `patrol` by its name.
  - Provenance: ported from the DEPLOYED binary (D-b, dr_9daadbe0). The upstream
    commit `181ca45` is abandoned and the Desk-layer fork checkout
    (`~/github/tightbeam-atc@a7d14e6`) is not authority. `reference/atc-derivations.md`
    §2 holds the source pin.
- Unknown harness or model strings pass through as found in `sessions`.
- The parity block is `null` until the first parity run.
- `ok-ledger-atc-missing` means ledger-versus-CLI parity held while local ATC
  stage evidence was unavailable. It exits successfully but remains visible on
  the page. An ATC URL does not count as local evidence.
- `schema` increments only on an incompatible change; the page refuses a
  higher `schema` than it knows and says so in the stale banner.

## Size

Today's org: 91 items in scope, expected 60 to 80 KB. Wake prompts are
truncated and closed items are excluded to keep the two-second fetch cheap.
