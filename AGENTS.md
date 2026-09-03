# AGENTS.md

Conventions for any agent, Tightbeam-spawned or not, that works in this repo.

## Read first

1. `docs/spec.md`. It is the contract. If the work you are about to do is not
   in its scope, stop and raise it on your card rather than expanding scope.
2. `docs/decisions.md`. Decisions there are settled unless George reopens them.
3. `reference/atc-derivations.md` before porting anything from ATC.

## Hard rules

- **Ledger reads are read-only.** Open `state.db` with
  `file:...?mode=ro` (URI form). Never `sqlite3 state.db` without `mode=ro`.
  Never leave a transaction open across a sleep. One short `BEGIN` per
  generator pass, then close.
- **No `tightbeam` CLI on a cadence.** One-shot verbs for your own coordination
  (attest, wake) are fine. A loop, a timer, or a "refresh" that shells out to
  the CLI is a defect (clickety-clacks/tightbeam#10). The nightly parity check
  is the one exception and it is one call per day.
- **Do not modify tightbeam-atc.** Not its repo, not its installed files under
  `/opt/tb-atc` or `/usr/local/bin/tb-weather-*`, not its sidecar container,
  not its `tailscale serve` rules. A desired change to ATC is an issue or PR on
  `clickety-clacks/tightbeam-atc`, filed and noted on your card.
- **No secrets in this repo.** No tokens, no `gateway.json`, no credential
  paths beyond the documented ones.
- **Zero external fetches from the page.** No CDN scripts, no web fonts, no
  analytics. The page must load on the tailnet with the internet unplugged.
- **v1 is read-only.** No buttons that change org state. That decision is
  George's to reopen (`docs/decisions.md` D4).

## Working the repo

- Branch from `main`, one branch per assignment, named `asg-<short>/<slug>`.
- Commits: imperative subject under 72 characters; body says why. Agent
  commits follow the Tightbeam org convention of a `Co-Authored-By:` trailer
  naming the harness and model. Do not put work-item or assignment ids in
  subjects; put them in the body.
- PRs against `main` on `gdiab/tightbeam-toplines`. The PR body links the
  assignment card and states which acceptance criteria in `docs/spec.md` §
  Acceptance it satisfies and how that was verified. A claim without the
  command and its output is not verification.
- Python 3.12 standard library only for anything that runs on the host. No
  pip, no venv, no node. Plain HTML, CSS and JavaScript for the page, one file.
- `docs/runbook.md` is finished by whoever deploys. A deploy without a matching
  runbook update is incomplete.

## Where things run

- Host: `sirius` (Ubuntu 24.04). The Tightbeam org runs there under user `gd`;
  the ledger is `/home/gd/.tightbeam/state.db`.
- Deploy as user `gd`, no root: systemd **user** units (linger is enabled),
  files under `/home/gd/tb-toplines/`, the sidecar started with `docker` (gd is
  in the docker group).
- Loopback port **8898**, reserved for TopLines. Do not bind `0.0.0.0`.
- Hostname on the tailnet: `toplines.tailf064dc.ts.net`, served by the
  `tb-toplines-ts` sidecar. ATC is `atc.tailf064dc.ts.net`; link to it, do not
  touch it.

## Definition of done

Every item under `docs/spec.md` § Acceptance demonstrated on sirius, with
output pasted on the card; `docs/runbook.md` updated; `tasks/todo.md` review
section filled in; an independent reviewer's verdict on the assignment.
