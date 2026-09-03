# Brief for the TopLines product owner

You are being handed a specified, unbuilt project. George wants a Tightbeam
product owner to re-review the spec with fresh eyes, then staff it. This page
tells you what exists, what you are being asked to decide, and how George will
file the work.

## What exists

- `docs/spec.md`: the contract. Problem, hard constraints, numbered scope,
  definitions, acceptance criteria, fixtures, three open questions for you.
- `docs/architecture.md`: components, data flow, latency budget, failure
  modes, and why each alternative was rejected.
- `docs/decisions.md`: fourteen dated decisions. D3, D4, D6, D7, D10, D14 are
  George's rulings; the rest were recommended and accepted.
- `docs/design.md`, `docs/data-contract.md`, `docs/runbook.md` (draft).
- `mock/toplines.html`: the reviewed mock, rendered from a real snapshot.
  George has approved its appearance. Open it in a browser.
- `reference/atc-derivations.md`: exactly what to port from ATC and the
  license terms.
- `AGENTS.md`: conventions and hard rules for everyone who works the repo.

## What you are asked to do

1. **Re-review the spec** as if you had not seen the conversation that
   produced it. Look for scope that is not justified by the problem statement,
   acceptance criteria that cannot be demonstrated, definitions the generator
   cannot meet from the ledger, and anything that contradicts a hard
   constraint. File findings as attests on your card; propose edits as a PR to
   `docs/spec.md` rather than editing on `main`.
2. **Answer the three open questions** in `docs/spec.md`, or escalate them to
   George with a recommendation if they need his ruling.
3. **Verify the ledger definitions against the live database, read-only.**
   Column names in `docs/data-contract.md` are stated from the CLI's output
   shape and ATC's queries, not from a schema dump. Confirm them with
   `sqlite3 'file:/home/gd/.tightbeam/state.db?mode=ro' '.schema attests'` and
   friends before staffing, and correct the contract.
4. **Staff it.** Suggested shape, yours to change:
   - one coder for `bin/` (Python stdlib) and `systemd/`;
   - one coder for `web/index.html` from the mock, or the same coder if you
     prefer one hand on the whole thing;
   - one cross-family reviewer (a different harness from the coder) with the
     acceptance list as the review rubric;
   - the deploy and acceptance run on sirius by a session that can reach the
     host; George's ops session can do that on request.
   Name hires by purpose: display "Coder — TopLines generator", name
   `coder:toplines-gen`, and so on.
5. **Hold the bar.** Done means every acceptance line demonstrated on sirius
   with output on the card, the runbook finished, a reviewer's verdict, and
   nothing under ATC's paths changed. A completion attest without those is
   a claim, not evidence.

## Hard rules you enforce

Read `AGENTS.md`. The two that matter most: the ledger is read-only and the
CLI is never polled (clickety-clacks/tightbeam#10), and nothing in ATC's repo,
files, container or serve rules changes. A coder who "just added a path to the
ATC sidecar for now" has violated D3.

## How George files this

Run from a machine with the `tightbeam` CLI configured, as George:

```sh
cd ~/github/tightbeam-toplines
SPEC_SHA=$(shasum -a 256 docs/spec.md | cut -d' ' -f1)
SPEC_REF="gdiab/tightbeam-toplines/docs/spec.md@$(git rev-parse --short HEAD)"

# 1. the durable thread
tightbeam work-item-create \
  --title "TopLines: read-only live board of the org's work, on sirius" \
  --spec-ref "$SPEC_REF" --spec-sha256 "$SPEC_SHA" \
  --key toplines-v1 --as-user george

# 2. hire the PO (model must be copied verbatim from `tightbeam list`'s catalog)
tightbeam list --as-user george | python3 -c 'import json,sys; print(json.dumps(json.load(sys.stdin)["models"], indent=1))'
tightbeam spawn --display "PO — TopLines" --name po:toplines \
  --archetype product-owner --harness claude --model <catalog-model> --as-user george

# 3. open the obligation and wake the PO, threaded to the item
tightbeam dispatch --to <po-sessionKey> \
  --subject "Re-review the TopLines spec, answer its open questions, then staff it" \
  --brief "Repo gdiab/tightbeam-toplines. Start with docs/po-brief.md. Read-only ledger, never poll the CLI, never touch ATC. First attest: your review findings on docs/spec.md, before any hiring." \
  --work-item <wi_id> --as-user george
```

Monitor with `tightbeam attests <asg_id> --as-user george` and
`tightbeam decision-requests --as-user george`. Expected first event: the PO's
review findings as an attest, before any spawn.

## Things George decided that you do not re-decide

Own hostname (D3), read-only v1 (D4), public repo (D6), the name (D7), the
toggle (D10), Tightbeam builds it (D14). Everything else is open to a better
argument, made on your card with reasoning.
