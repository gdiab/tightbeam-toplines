# Runbook: TopLines on sirius

Everything here runs as `gd`. Nothing needs root.

## Layout on the host

```
/home/gd/tb-toplines/
  bin/tb-toplines-watch      watcher (bash + inline python)
  bin/tb-toplines-gen        generator (python 3.12, stdlib)
  bin/tb-toplines-serve      static server (python 3.12, stdlib)
  bin/tb-toplines-parity     daily parity check (python 3.12, stdlib)
  bin/tb-toplines-ts         create TopLines' own Tailscale sidecar
  bin/tb-toplines-verify-install  install-provenance gate (python 3.12, stdlib)
  web/index.html             the page
  web/toplines.json          generator output (not in git)
  web/parity.json            parity output, merged by the generator (not in git)
~/.config/systemd/user/
  tb-toplines.service        serve
  tb-toplines-watch.service  watch + gen
  tb-toplines-parity.service oneshot
  tb-toplines-parity.timer   daily 03:00 America/Los_Angeles
```

Ledger: `/home/gd/.tightbeam/state.db`, opened `file:...?mode=ro` everywhere.
Port: 127.0.0.1:8898. Hostname: `https://toplines.tailf064dc.ts.net/`.

## Landing this to `main` (`dr_b1b03664`)

No session on sirius currently holds GitHub write: `gh` is unauthenticated and
the origin is `https`. The PR is prepared locally on its branch; the final push
and merge to `main` are performed by a designated write-capable session (the
operator/ops session), NOT by the coders or the orchestrator. GitHub `main` is
still merge-gated (`dr_b1b03664`) and does not yet carry the reviewed code, so
the canonical Install below cannot run until that merge lands.

## Install sources

Install clones from one of two sources; the install-provenance gate below runs
identically against whichever one you clone, so provenance is guaranteed either
way.

1. **Canonical / steady-state (`spec.md` Scope-7):**
   `https://github.com/gdiab/tightbeam-toplines.git` (`main`). This is the shipped,
   permanent install method, used once the gated merge (`dr_b1b03664`) has landed
   the reviewed code on `main`.

2. **Pre-merge acceptance-demo stand-in:** `/home/gd/tb-toplines-reviewed.git`, a
   durable, local, `gd`-owned bare repo. GitHub `main` is unpopulated until the
   post-acceptance merge, so this stand-in is used **now** for acceptance and for
   the reviewer walkthrough. Its tree is SHA-matched to the pin table — the same
   ten reviewed artifacts, each verified — so the gate passes on it exactly as it
   will on `main` post-merge. This is a pre-merge stand-in, **not** a permanent
   deviation: the reviewed heads and the corrected-integ head were reaped once
   when their build sessions retired, and this reap-proof repo holds the recovered
   reviewed tree until `main` carries it. It is local only, never pushed outward.

## Install-provenance gate

Installing the wrong artifact is what breaks TopLines: an earlier deploy shipped
an unreviewed, progress-anchored generator and the board failed acceptance. The
gate makes that unrepresentable at install time. `bin/tb-toplines-verify-install`
computes the sha256 of every deployed artifact under the install root and
**aborts (non-zero exit, nothing copied or activated) on ANY mismatch** against
the pinned reviewed-clean set below. It is fail-closed: the Install, Upgrade, and
Verify steps run it *before* any `cp`/`enable`/`restart`, chained with `&&`, so a
mismatch stops the sequence before systemd sees anything.

```sh
bin/tb-toplines-verify-install            # exit 0 = every artifact matches; exit 1 = abort
bin/tb-toplines-verify-install --root /path/to/tree   # verify a tree other than /home/gd/tb-toplines
```

### Pinned reviewed-clean artifacts

Ten deployed artifacts (five `bin/` scripts, four systemd units, one page). The
generated outputs `web/toplines.json` and `web/parity.json` are runtime state,
not artifacts, and are never pinned. `docs/runbook.md` is **deliberately
excluded**: it is the gate's own host file, and a gate cannot pre-verify the
document that carries it. (The redeploy verifier counted an "eleventh" artifact;
that was this runbook, excluded here for exactly that reason.)

The pin source is the reviewed-clean deployed product on sirius, which is
be525345's corrected redeploy materialised on disk. The provenance basis is
PO-locked (verbatim below); `docs/runbook.md` is not gate-pinned (the gate's own
host file) but appears in the provenance record.

```
PIN PROVENANCE (PO-locked, wi_f9a21185; present exactly + state residual):
TIER A blob-cryptographic vs 26a3641 = 4 gate-pinned artifacts: parity 09de23f1, ts cd307aed, tb-toplines-parity.service d070d2ca, tb-toplines-parity.timer bd7d6af5.
GEN b1d4c392: authoritative reviewed sha + installed match + Acc2 functional.
TIER B (independent reviewer-commit-anchored + installed==pin + redeploy record att_b5a53254 + functional; reviewed git-objects reaped => NOT blob-cryptographic): gen->reviewed-clean @6853091 (att_24278bde); web/index.html->reviewed-clean @36a4b4f9 (att_82cde5af); serve+watch->reviewed-clean @8d33eb23 (asg_04c93305); tb-toplines.service+tb-toplines-watch.service->reviewed-clean @8d33eb23 (asg_04c93305).
docs/runbook.md = reviewed 26a3641 base + the R1-reviewed newly-authored install-gate delta -- provenance is reviewed-base + THIS (R1) review, NOT a 26a3641 cryptographic match.
RESIDUAL: Tier-B installed<->reviewed-commit link is reviewer-anchored + functional, NOT blob-cryptographic. Do NOT cite att#6/att_d117b2c2 or the superseded pre-D19 page sha b39347c8.
```

Full pin values (the ten gate-verified artifacts):

| Deployed artifact | sha256 |
|---|---|
| `bin/tb-toplines-gen` | `b1d4c392c7324ec1835d1609a10599d6051081f41c230a525a692bebdcf0ded2` |
| `bin/tb-toplines-parity` | `09de23f15f7d560b1450a96f70033abf5ca7d2332c74a88b20ac4455d376ff4e` |
| `bin/tb-toplines-serve` | `81e905f676f45e2a9270292d1fdf23b09fc29fc49ac4041f959de538bcc44182` |
| `bin/tb-toplines-watch` | `7f5497002ae3be05182d3066aea711db1766c15ccf3855af3c237f96b4cc3e81` |
| `bin/tb-toplines-ts` | `cd307aedea5cc010075f3e4355a3c12b26237e3501a56e156784e3ccd554b506` |
| `web/index.html` | `321b39c1a939499db4bdca8d891523764a76340b333003c04297fc69d137c159` |
| `systemd/tb-toplines.service` | `5beb3ed03a4019327137885334aa03090bb3f1fa579547edc4018c97842da33d` |
| `systemd/tb-toplines-watch.service` | `2f94734e69daffd84faef63cd37374add89edac18af64a20e1c76f465d00fdc7` |
| `systemd/tb-toplines-parity.service` | `d070d2ca776972a199cd9a9ebf8e683f9b9195f72dca4a1d919e0f615229373b` |
| `systemd/tb-toplines-parity.timer` | `bd7d6af51b2503959d7bd2349dec069274365882d61b999c6366a381d329137a` |

The pins are the whole set the gate protects, held in the `PINS` table inside
`bin/tb-toplines-verify-install`. A new reviewed release that intentionally
changes an artifact updates its pin in the same change, under review; otherwise
the gate will (correctly) abort on the drift.

## Install

Clone one source, then the gate runs first: nothing is copied or activated unless
every artifact matches its reviewed-clean pin.

```sh
ssh gd@sirius.tailf064dc.ts.net

# Canonical / steady-state (post-merge) — spec Scope-7:
git clone https://github.com/gdiab/tightbeam-toplines.git ~/tb-toplines

# Pre-merge acceptance-demo stand-in (use this NOW; main is unpopulated):
# git clone /home/gd/tb-toplines-reviewed.git ~/tb-toplines

cd ~/tb-toplines
bin/tb-toplines-verify-install --root "$PWD" \
  && cp systemd/*.service systemd/*.timer ~/.config/systemd/user/ \
  && systemctl --user daemon-reload \
  && systemctl --user enable --now tb-toplines.service tb-toplines-watch.service tb-toplines-parity.timer
```

`--root "$PWD"` makes the gate verify exactly the checkout that the `cp` then
installs from, so the tree that is verified and the tree that is installed can
never differ. The gate is identical for both sources. If it prints `ABORT`, stop: the clone
does not match the reviewed-clean set — an artifact was altered, or (for the
canonical source) `main` has not yet been merged with the reviewed heads. Resolve
provenance before re-running; nothing was installed.

Sidecar, once:

```sh
bin/tb-toplines-ts
docker logs -f tb-toplines-ts        # follow the auth URL, approve the node in the admin console once
docker exec tb-toplines-ts tailscale serve --bg http://127.0.0.1:8898
docker exec tb-toplines-ts tailscale serve status
```

Expected: `https://toplines.tailf064dc.ts.net (tailnet only)` proxying to
`http://127.0.0.1:8898`. Do not run any of this against `tb-atc-ts`.

## Verify

```sh
bin/tb-toplines-verify-install    # expect: OK — all 10 deployed artifacts match the reviewed-clean pin set
systemctl --user status tb-toplines tb-toplines-watch --no-pager
journalctl --user -u tb-toplines -n 20 --no-pager
journalctl --user -u tb-toplines-watch -n 20 --no-pager
systemctl --user list-timers tb-toplines-parity.timer --no-pager
curl -s http://127.0.0.1:8898/toplines.json | python3 -c 'import json,sys,time; d=json.load(sys.stdin); print("age s", round(time.time()-d["generatedAt"]/1000,1), "pass ms", d["passMs"], "items", len(d["items"]))'
ls -la ~/.tightbeam/state.db-wal          # expect a few MB, not growing
grep -n 'mode=ro' bin/tb-toplines-gen bin/tb-toplines-watch bin/tb-toplines-parity
```

From a tailnet device, open the hostname; the browser's network panel should
show same-origin requests only.

## Fresh-shell walkthrough (reviewer)

Run this verbatim in a fresh shell on sirius as `gd` to exercise the gate through
install, verify, and rollback. It clones the pre-merge acceptance-demo stand-in
(`/home/gd/tb-toplines-reviewed.git`, since GitHub `main` is not yet populated)
and works entirely in scratch directories: it never touches the live board, the
real systemd units under `~/.config/systemd/user`, or ATC.

```sh
set -eu
STAGE="$(mktemp -d)/tb-toplines"     # scratch install root
SYSD="$(mktemp -d)"                   # scratch systemd dir (real units untouched)
git clone -q /home/gd/tb-toplines-reviewed.git "$STAGE"   # pre-merge stand-in source
cd "$STAGE"

# 1. INSTALL (gated): units are staged only if every artifact matches its pin.
bin/tb-toplines-verify-install --root "$STAGE" \
  && cp systemd/*.service systemd/*.timer "$SYSD/" \
  && echo "install: units staged into $SYSD"
# expect: OK — all 10 deployed artifacts match ... ; install: units staged

# 2. FAIL-CLOSED PROOF: alter one artifact; the gate aborts and nothing stages.
printf '\n# tampered\n' >> "$STAGE/bin/tb-toplines-gen"
bin/tb-toplines-verify-install --root "$STAGE" \
  && cp systemd/*.service systemd/*.timer "$SYSD/" \
  || echo "install correctly refused (gate exit $?)"
# expect: ABORT — 1 of 10 ... bin/tb-toplines-gen ; install correctly refused
git -C "$STAGE" checkout -- bin/tb-toplines-gen   # restore from the reviewed clone

# 3. VERIFY: the restored tree matches again.
bin/tb-toplines-verify-install --root "$STAGE"
# expect: OK — all 10 deployed artifacts match the reviewed-clean pin set

# 4. ROLL BACK guard: a prior/altered build drifts from this release's pins, so
#    the gate blocks re-activating it. (Simulates rolling an artifact back to an
#    earlier, unreviewed version.)
printf 'OLD unreviewed build\n' > "$STAGE/bin/tb-toplines-gen"
bin/tb-toplines-verify-install --root "$STAGE" \
  || echo "gate blocks a drifted rollback, as documented"
# expect: ABORT — 1 of 10 ... bin/tb-toplines-gen ; gate blocks a drifted rollback
git -C "$STAGE" checkout -- bin/tb-toplines-gen   # return to this reviewed release
bin/tb-toplines-verify-install --root "$STAGE"    # green again

# 5. CLEANUP: scratch only; the live board and ATC are untouched.
cd ~ && rm -rf "$STAGE" "$SYSD"
echo "walkthrough complete"
```

## Operate

| Need | Command |
|---|---|
| logs | `journalctl --user -u tb-toplines-watch -f` |
| parity logs | `journalctl --user -u tb-toplines-parity -n 30 --no-pager` |
| restart the pipeline | `systemctl --user restart tb-toplines-watch` |
| restart the server | `systemctl --user restart tb-toplines` |
| run the generator once by hand | `~/tb-toplines/bin/tb-toplines-gen && head -c 400 ~/tb-toplines/web/toplines.json` |
| show today's parity attempt | `ls -l "${XDG_STATE_HOME:-$HOME/.local/state}/tb-toplines/parity-attempt-$(TZ=America/Los_Angeles date +%F)"` |
| run parity now | `systemctl --user start tb-toplines-parity.service; journalctl --user -u tb-toplines-parity -n 30` (the atomic daily guard skips a second CLI call) |
| sidecar status | `docker exec tb-toplines-ts tailscale status; docker exec tb-toplines-ts tailscale serve status` |
| footprint on the page | vitals footer shows WAL bytes and pass ms; WAL over 64 MB means a long reader somewhere, find it with `fuser ~/.tightbeam/state.db` |

## Upgrade

The pull brings new artifacts, so the gate runs again before restart. A reviewed
release that changed an artifact carries the matching pin update, so the gate
passes; unexpected drift aborts the upgrade before anything restarts.

```sh
cd ~/tb-toplines && git pull --ff-only
bin/tb-toplines-verify-install --root "$PWD" \
  && cp systemd/* ~/.config/systemd/user/ && systemctl --user daemon-reload \
  && systemctl --user restart tb-toplines-watch tb-toplines
```

## Roll back

```sh
systemctl --user disable --now tb-toplines-parity.timer tb-toplines-parity.service tb-toplines-watch.service tb-toplines.service 2>/dev/null || true
rm -f ~/.config/systemd/user/tb-toplines-parity.timer ~/.config/systemd/user/tb-toplines-parity.service ~/.config/systemd/user/tb-toplines-watch.service ~/.config/systemd/user/tb-toplines.service
cd ~/tb-toplines
git checkout <previous-tag-or-sha>
if test -d systemd; then
  find systemd -maxdepth 1 -type f \( -name 'tb-toplines*.service' -o -name 'tb-toplines*.timer' \) -exec cp {} ~/.config/systemd/user/ \;
fi
systemctl --user daemon-reload
for unit in tb-toplines.service tb-toplines-watch.service tb-toplines-parity.timer; do
  test -f "$HOME/.config/systemd/user/$unit" && systemctl --user enable --now "$unit"
done
if test ! -x bin/tb-toplines-ts; then
  docker rm -f tb-toplines-ts 2>/dev/null || true
fi
```

The pins in `bin/tb-toplines-verify-install` describe *this* reviewed release, so
the gate is not chained into rollback: an older revision has its own artifact
sha256 set and the current gate would correctly report drift against it. When you
roll back **to this release**, run `bin/tb-toplines-verify-install` afterward and
expect `OK`; when you roll back to an older revision, verify it against that
revision's own provenance record instead.

The sidecar removal keeps the named `tb-toplines-ts-state` volume, so returning
to a revision that includes the sidecar does not require a new node login.

Remove entirely:

```sh
systemctl --user disable --now tb-toplines tb-toplines-watch tb-toplines-parity.timer
docker rm -f tb-toplines-ts && docker volume rm tb-toplines-ts-state
rm -rf ~/tb-toplines ~/.config/systemd/user/tb-toplines*
```

Then remove the `toplines` node in the Tailscale admin console. ATC is
unaffected by any of this.

## When the parity check warns

The page shows the first mismatch. Do not rerun the timer or invoke
`tightbeam toplines` again that day: parity makes at most one CLI call per day.
Inspect the named row in `web/toplines.json`, the read-only ledger, and the
installed CLI source. If the CLI changed a definition for quiet or card counts,
update the generator query and the matching definition in `docs/spec.md`. If
ATC's stage differs, read
`reference/atc-derivations.md`, inspect `/opt/tb-atc/web/data.json` read-only,
and re-port the ladder. Do not edit ATC or loosen the tolerance to hide the
warning. An `inconclusive` result names a row that changed during the capture;
leave it visible and let the next daily timer run perform the next comparison.

A near-daily-run clock-gap warn is benign. When the sanctioned daily CLI parity
run executes more than 120s before its generator pass, the uniform capture-time
gap pushes each open item's minutes-since-progress just over the 120s parity
tolerance, and the page shows a false warn (observed ~124.5s gap, ~4.5s over
tolerance). Parity itself is fine: the CLI and the page report the same open
count with zero mismatches, so this is not a real parity failure. The warn can
recur while the CLI-versus-generator capture-time gap stays over 120s; it clears
only once a daily run's gap falls under the 120s tolerance. Do not read a
recurring warn as one that self-clears automatically, and do not loosen the
tolerance to hide it. A permanent fix is tracked in the v1.1 backlog
(wi_664b1447).

## After a Tightbeam upgrade

Run the generator by hand. A non-zero exit with a missing column named in the
error means schema drift; fix the query, restart the watcher, and let the next
scheduled parity run validate the repair.
