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
      "total": 51,                      // state = active
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
        "workItemId": "wi_…",           // via assignmentId when resolvable, else null
        "prompt": "STALL PATROL CONTINUATION: …"   // first 140 characters
      }
    ],
    "wakesPending": 7
  },
  "items": [                            // state in open, iceboxed, failed; closed omitted
    {
      "id": "wi_8d658b1e-7c29-4cb6-9a1c-e8c91f94885b",
      "short": "wi_8d658b1e",
      "title": "Pi v2 → ONE Pi PR against 0.1.9 …",
      "state": "open",                  // open | iceboxed | failed
      "failReason": null,
      "startedAt": 1788300000000,
      "finishedAt": null,
      "lastProgressAt": 1788320961000,  // newest progress attest on any card of the item, else null
      "sinceProgressMs": 1080000,       // generatedAt - (lastProgressAt ?? startedAt ?? createdAt)
      "active": {
        "runningTurn": false,           // any holder has a turn with startedAt set and endedAt null
        "pendingSessionWake": true      // any holder has a wake in state pending
      },
      "cards": {
        "open": 1,
        "closed": 0,
        "byOutcome": {"completed":0,"surrendered":0,"revoked":0}
      },
      "attests": {
        "total": 1,
        "byKind": {"progress":1},       // progress | surrender | completion | verdict, zero counts omitted
        "byVerdictKind": {}             // reviewed-clean, tests-passed, verified, … as found
      },
      "stage": 1,                       // ATC ladder 0..6, see design.md and reference/atc-derivations.md
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
- `holders[].kind` uses ATC's vocabulary exactly: `main`, `po`, `patrol`,
  `orch`, `coder`, `rev`, `spec`, `recon`, `agent`.
- Unknown harness or model strings pass through as found in `sessions`.
- The parity block is `null` until the first parity run.
- `schema` increments only on an incompatible change; the page refuses a
  higher `schema` than it knows and says so in the stale banner.

## Size

Today's org: 91 items in scope, expected 60 to 80 KB. Wake prompts are
truncated and closed items are excluded to keep the two-second fetch cheap.
