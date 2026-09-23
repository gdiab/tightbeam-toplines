# Runbook: TopLines

Run TopLines as the installing user. Nothing needs root. Set `INSTALL_DIR` to an
absolute directory that the user owns; it defaults to `$HOME/tb-toplines`. The
Sirius migration section records that host's explicit values separately.

## Layout on the host

```
$INSTALL_DIR/                    default: $HOME/tb-toplines
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
  tb-toplines-parity.timer   daily 03:00 in the configured install timezone
$HOME/.config/tb-toplines/
  toplines.env               per-install configuration (mode 0600)
$HOME/.config/systemd/user/tb-toplines-parity.timer.d/
  schedule.conf              install-time timezone schedule
$HOME/.config/systemd/user/tb-toplines{,-watch,-parity}.service.d/
  root.conf                  only for a non-default install directory
```

The ledger defaults to `$HOME/.tightbeam/state.db`. Generator, watcher, and
parity resolve it identically and open it with `file:...?mode=ro`. Port
`127.0.0.1:8898` remains fixed.

## Landing this to `main` (`dr_b1b03664`)

No session on sirius currently holds GitHub write: `gh` is unauthenticated and
the origin is `https`. The PR is prepared locally on its branch; the final push
and merge to `main` are performed by a designated write-capable session (the
operator/ops session), NOT by the coders or the orchestrator. GitHub `main` is
still merge-gated (`dr_b1b03664`) and does not yet carry the reviewed code, so
the canonical Install below cannot run until that merge lands.

## Install sources

Final acceptance uses the canonical origin. A local source may be used only to
rehearse the same procedure before merge.

1. **Canonical / steady-state (`spec.md` Scope-7):**
   `https://github.com/gdiab/tightbeam-toplines.git` (`main`). This is the shipped,
   permanent install method, used once the gated merge (`dr_b1b03664`) has landed
   the reviewed code on `main`.

2. **Historical pre-merge rehearsal stand-in:** `/home/gd/tb-toplines-reviewed.git`, a
   durable, local, `gd`-owned bare repo. GitHub `main` is unpopulated until the
   post-acceptance merge, so this stand-in may be used **only** for a pre-merge
   reviewer rehearsal. Its tree is SHA-matched to the pin table — the same
   ten reviewed artifacts, each verified — so the gate passes on it exactly as it
   will on `main` post-merge. This is a pre-merge stand-in, **not** a permanent
   deviation and cannot satisfy final A7 acceptance. The reviewed heads and the corrected-integ head were reaped once
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
bin/tb-toplines-verify-install --root /path/to/tree   # verify a tree other than $HOME/tb-toplines
```

### Pinned reviewed-clean artifacts

Ten deployed artifacts (five `bin/` scripts, four systemd units, one page). The
generated outputs `web/toplines.json` and `web/parity.json` are runtime state,
not artifacts, and are never pinned. `docs/runbook.md` is **deliberately
excluded**: it is the gate's own host file, and a gate cannot pre-verify the
document that carries it. (The redeploy verifier counted an "eleventh" artifact;
that was this runbook, excluded here for exactly that reason.)

The unchanged pins retain the provenance of the reviewed product on Sirius.
The changed pins identify portability R5 and preserve the 2026-09-16
running-turn correction. Install this candidate only after independent review
clears its exact commit.
The prior-release provenance basis is PO-locked (verbatim below);
`docs/runbook.md` is not gate-pinned (the gate's own host file) but appears in
the provenance record.

```
PRIOR-RELEASE PIN PROVENANCE (PO-locked, wi_f9a21185; state residual):
TIER A blob-cryptographic vs 26a3641 = 4 gate-pinned artifacts: parity 09de23f1, ts cd307aed, tb-toplines-parity.service d070d2ca, tb-toplines-parity.timer bd7d6af5.
GEN b1d4c392: authoritative reviewed sha + installed match + Acc2 functional.
TIER B (independent reviewer-commit-anchored + installed==pin + redeploy record att_b5a53254 + functional; reviewed git-objects reaped => NOT blob-cryptographic): gen->reviewed-clean @6853091 (att_24278bde); web/index.html->reviewed-clean @36a4b4f9 (att_82cde5af); serve+watch->reviewed-clean @8d33eb23 (asg_04c93305); tb-toplines.service+tb-toplines-watch.service->reviewed-clean @8d33eb23 (asg_04c93305).
docs/runbook.md = reviewed 26a3641 base + the R1-reviewed newly-authored install-gate delta -- provenance is reviewed-base + THIS (R1) review, NOT a 26a3641 cryptographic match.
RESIDUAL: Tier-B installed<->reviewed-commit link is reviewer-anchored + functional, NOT blob-cryptographic. Do NOT cite att#6/att_d117b2c2 or the superseded pre-D19 page sha b39347c8.

CURRENT RELEASE CANDIDATE (wi_06502874): portability R5 across generator, watcher, parity, page and systemd preserves the running-turn headline. Install only after independent review clears the exact candidate commit that contains these pins.
```

Full pin values (the ten gate-verified artifacts):

| Deployed artifact | sha256 |
|---|---|
| `bin/tb-toplines-gen` | `355ce9a53dc834aebb7a63e71e49dc6d312b6b1a6b8eb832e4b1244dae4af28b` |
| `bin/tb-toplines-parity` | `e8a85979b0c06fe5906bac894461327e3eb9460c72d94403a332a12fa9dbdd51` |
| `bin/tb-toplines-serve` | `81e905f676f45e2a9270292d1fdf23b09fc29fc49ac4041f959de538bcc44182` |
| `bin/tb-toplines-watch` | `34a4ea6f193bb987275bd02214caf1e132ab4b992b55f097c7f82b75675b26e0` |
| `bin/tb-toplines-ts` | `cd307aedea5cc010075f3e4355a3c12b26237e3501a56e156784e3ccd554b506` |
| `web/index.html` | `0ecbb12b43a91f04911288f65c117db201bc91d5f78ded99fe927710472a0579` |
| `systemd/tb-toplines.service` | `7a8e4a03d6851fb71d9432839662060860088f5a5384575e66cd9831335c5abe` |
| `systemd/tb-toplines-watch.service` | `e909efac9770a0276d82552499389fa98415167a1164a84c82ad747d17dd329a` |
| `systemd/tb-toplines-parity.service` | `82fd7d165dc4f1314cbe9c8958ed860cb3f49e26b96f1ded1f0e13f566a86ad8` |
| `systemd/tb-toplines-parity.timer` | `9c06b0c70221e005f2a4e64ac7faf440798ff37f638f3745e7e85723fc6e089a` |

The pins are the whole set the gate protects, held in the `PINS` table inside
`bin/tb-toplines-verify-install`. A new reviewed release that intentionally
changes an artifact updates its pin in the same change, under review; otherwise
the gate will (correctly) abort on the drift.

## Fresh install

For final acceptance, clone the canonical origin after the reviewed change is
merged to `main`, check out the exact merged commit, and record it. Before merge,
a SHA-matched local clone may rehearse these commands, but that rehearsal does
not satisfy final A7 acceptance. The gate runs first: nothing is copied or
activated unless every artifact matches its reviewed-clean pin.

```sh
INSTALL_DIR="${TB_TOPLINES_ROOT:-$HOME/tb-toplines}"
case "$INSTALL_DIR" in /*) ;; *) echo "INSTALL_DIR must be absolute" >&2; exit 2;; esac
git clone https://github.com/gdiab/tightbeam-toplines.git "$INSTALL_DIR"
cd "$INSTALL_DIR"
MERGED_COMMIT=PASTE_EXACT_40_HEX_MERGED_MAIN_COMMIT
git fetch origin main
git checkout --detach "$MERGED_COMMIT"
test "$(git rev-parse HEAD)" = "$MERGED_COMMIT"
git rev-parse HEAD
bin/tb-toplines-verify-install --root "$INSTALL_DIR"

mkdir -p "$HOME/.config/tb-toplines" \
  "$HOME/.config/systemd/user/tb-toplines-parity.timer.d"
install -m 0600 /dev/null "$HOME/.config/tb-toplines/toplines.env"
cat >"$HOME/.config/tb-toplines/toplines.env" <<EOF
TB_TOPLINES_OPERATOR=maya
# TB_BASE_DIR=$HOME/.tightbeam
# TB_TOPLINES_ATC_URL=https://atc.example.ts.net/
# TB_TOPLINES_ATC_DATA=/opt/tb-atc/web/data.json
TB_TOPLINES_TZ=Europe/Berlin
EOF

TB_TOPLINES_TZ=Europe/Berlin
cat >"$HOME/.config/systemd/user/tb-toplines-parity.timer.d/schedule.conf" <<EOF
[Timer]
OnCalendar=
OnCalendar=*-*-* 03:00:00 $TB_TOPLINES_TZ
EOF

cp systemd/*.service systemd/*.timer "$HOME/.config/systemd/user/"

if test "$INSTALL_DIR" != "$HOME/tb-toplines"; then
  for pair in \
    "tb-toplines.service tb-toplines-serve" \
    "tb-toplines-watch.service tb-toplines-watch" \
    "tb-toplines-parity.service tb-toplines-parity"
  do
    set -- $pair
    mkdir -p "$HOME/.config/systemd/user/$1.d"
    cat >"$HOME/.config/systemd/user/$1.d/root.conf" <<EOF
[Service]
WorkingDirectory=$INSTALL_DIR
ExecStart=
ExecStart=$INSTALL_DIR/bin/$2
EOF
  done
fi
systemctl --user daemon-reload
systemctl --user enable --now \
  tb-toplines.service tb-toplines-watch.service tb-toplines-parity.timer
```

Replace `maya`, `Europe/Berlin`, and optional ATC values with this install's
values. `TB_TOPLINES_OPERATOR` is required for live parity and has no default.
`TB_TOPLINES_ATC_URL` is optional and controls only the page link.
`TB_TOPLINES_ATC_DATA` controls the local read-only stage evidence and defaults
to `/opt/tb-atc/web/data.json`. `TB_BASE_DIR` defaults to `$HOME/.tightbeam` and
selects both `state.db` and its sibling `gateway.json`. `TB_TOPLINES_DB` is the
higher-precedence test/advanced override; live parity then requires
`gateway.json` beside that database. `TB_TOPLINES_TZ` defaults to UTC and must
match the timezone in `schedule.conf`. An invalid IANA timezone makes parity
fail loudly. `TB_TOPLINES_ROOT` is only a shell/runbook choice: no binary reads
it. A non-default directory is effective only through the three unpinned
`root.conf` files above. The parity service's PATH and EnvironmentFile remain
under `%h` because Tightbeam and install configuration remain in the user's home.

## Sirius migration

Preserve Sirius behavior by writing these explicit values before restarting:

```sh
ssh gd@sirius.tailf064dc.ts.net
INSTALL_DIR="$HOME/tb-toplines"
cd "$INSTALL_DIR"
bin/tb-toplines-verify-install --root "$INSTALL_DIR"
mkdir -p "$HOME/.config/tb-toplines" \
  "$HOME/.config/systemd/user/tb-toplines-parity.timer.d"
cat >"$HOME/.config/tb-toplines/toplines.env" <<'EOF'
TB_TOPLINES_OPERATOR=george
TB_BASE_DIR=/home/gd/.tightbeam
TB_TOPLINES_ATC_URL=https://atc.tailf064dc.ts.net/
TB_TOPLINES_ATC_DATA=/opt/tb-atc/web/data.json
TB_TOPLINES_TZ=America/Los_Angeles
EOF
chmod 0600 "$HOME/.config/tb-toplines/toplines.env"
cat >"$HOME/.config/systemd/user/tb-toplines-parity.timer.d/schedule.conf" <<'EOF'
[Timer]
OnCalendar=
OnCalendar=*-*-* 03:00:00 America/Los_Angeles
EOF
cp systemd/*.service systemd/*.timer "$HOME/.config/systemd/user/"
systemctl --user daemon-reload
systemctl --user restart tb-toplines-watch tb-toplines
systemctl --user enable --now tb-toplines-parity.timer
```

Sirius uses the default `$HOME/tb-toplines`, so do not create any service
`root.conf` drop-in there.

Verify the effective configuration without printing secrets:

```sh
systemctl --user show tb-toplines.service -p WorkingDirectory -p ExecStart
systemctl --user show tb-toplines-watch.service -p EnvironmentFiles -p WorkingDirectory -p ExecStart
systemctl --user show tb-toplines-parity.service -p EnvironmentFiles -p Environment -p WorkingDirectory -p ExecStart
systemctl --user cat tb-toplines-parity.timer
curl -s http://127.0.0.1:8898/toplines.json | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d["config"], d["org"]["runningTurns"], d.get("parity"))'
```

The timer must show one 03:00 Pacific schedule. The snapshot must show operator
`george`, the existing ATC URL, and timezone `America/Los_Angeles`. The served
page must keep the same ATC destination and the running-turn count semantics
from `b922a5d`.

`--root "$INSTALL_DIR"` makes the gate verify exactly the checkout that the `cp` then
installs from, so the tree that is verified and the tree that is installed can
never differ. The gate is identical for both sources. If it prints `ABORT`, stop: the clone
does not match the reviewed-clean set — an artifact was altered, or (for the
canonical source) `main` has not yet been merged with the reviewed heads. Resolve
provenance before re-running; nothing was installed.

## Sirius-only sidecar and tailnet setup

These paths, hostnames, and credentials apply only to Sirius. Other installs
use their own tailnet values.

Sidecar, once:

The sidecar joins the tailnet with a **file-based** auth key. Never pass the key
through a host environment variable or a command argument. A host-env key leaks to
the ledger and to every agent's environment; an argv key leaks to the transcript.
`containerboot` reads the key from the file itself, so the value never passes
through env, argv, `cat`, `echo`, or `docker exec env`.

1. **Remove any stale `toplines` node first.** In the admin console, delete an
   existing `toplines` node before you bootstrap. A leftover node forces the new
   node to register as `toplines-1` with URL `toplines-1.tailf064dc.ts.net`. If you
   see a `-1` suffix, stop and report — do not work around it.

2. **Generate the auth key.** In the admin console, create a Tailscale auth key.
   Make it reusable, set a 90-day expiry, and tag it `tag:service-host`. List
   `tag:service-host` under `tagOwners` in the ACL. A tagged key gives the node no
   node-key expiry.

3. **Place the key as a file** at
   `/home/gd/.tightbeam/auth/tailscale/authkey`. Set the directory to mode `0700`
   and the file to mode `0600`. Verify presence with `ls -l` only; never read the
   value.

4. **Write the serve boot-config** to
   `~/.tightbeam/auth/tailscale/serve/tb-toplines-ts.json`:

   ```json
   {"TCP":{"443":{"HTTPS":true}},"Web":{"${TS_CERT_DOMAIN}:443":{"Handlers":{"/":{"Proxy":"http://127.0.0.1:8898"}}}}}
   ```

5. **Bootstrap the container:**

   ```sh
   docker rm -f tb-toplines-ts
   docker run -d --name tb-toplines-ts --restart unless-stopped --network host \
     -e TS_USERSPACE=1 -e TS_HOSTNAME=toplines -e TS_STATE_DIR=/var/lib/tailscale \
     -e TS_AUTHKEY=file:/run/secrets/ts-authkey -e TS_AUTH_ONCE=true \
     -e TS_EXTRA_ARGS=--advertise-tags=tag:service-host \
     -e TS_SERVE_CONFIG=/config/serve.json \
     -v tb-toplines-ts-state:/var/lib/tailscale \
     -v /home/gd/.tightbeam/auth/tailscale/authkey:/run/secrets/ts-authkey:ro \
     -v /home/gd/.tightbeam/auth/tailscale/serve/tb-toplines-ts.json:/config/serve.json:ro \
     tailscale/tailscale:latest
   ```

The auth state and the serve config persist in the `tb-toplines-ts-state` volume.
`TS_AUTH_ONCE=true` means a restart reuses the persisted state and does not
re-consume the key. Keep the key file in place for ops custody and 90-day rotation.
Do not delete the file, and do not revoke the key.

Verify:

```sh
docker restart tb-toplines-ts
docker exec tb-toplines-ts tailscale status --json | grep -i '"BackendState"'   # expect "Running", not "NeedsLogin"
docker exec tb-toplines-ts tailscale serve status
```

Expected: `tailscale serve status` shows `https://toplines.tailf064dc.ts.net`
proxying to `http://127.0.0.1:8898`. Confirm HTTP 200 from another tailnet device.
Do not run any of this against `tb-atc-ts`.

## Verify

```sh
INSTALL_DIR="${TB_TOPLINES_ROOT:-$HOME/tb-toplines}"
bin/tb-toplines-verify-install --root "$INSTALL_DIR"  # expect: OK — all 10 deployed artifacts match
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

## Release evidence and notification

Before merge, record an independent reviewed-clean verdict for the exact
candidate commit. Record the local install walkthrough as pre-merge rehearsal.
After merge, final A7 acceptance must clone or fetch the canonical GitHub origin
at the exact merged `main` commit and record `git rev-parse HEAD`; local sources
cannot supply this final proof. Include the canonical origin commit, the installed revision
and file equivalence, the effective configuration, the served snapshot and
page result, and the commands with their exact output. Record the operator,
ATC URL and local data path, base directory and effective ledger, timezone, and
install root. Preserve before-and-after evidence that `/opt/tb-atc`,
`/usr/local/bin/tb-weather-*`, the `tb-atc-ts` container, and Tailscale serve
state did not change.

After origin and Sirius both pass, Notify George through Main with the PR and
commit, deployed verification, installer values, and remaining limitations.
Retain delivery ownership until both origin and Sirius are verified.

## Fresh-shell walkthrough (reviewer)

Run this in a fresh shell to exercise an explicit install directory, the gate,
the service drop-ins, verify, and rollback. It works entirely in scratch
directories and never touches the live board, the real systemd units, or ATC.
After merge, final A7 acceptance must use the canonical URL and exact merged
commit shown below. Before merge, replace `SOURCE` with a SHA-matched local
stand-in and record the result as **pre-merge rehearsal only**. The old
`/home/gd/tb-toplines-reviewed.git` source is historical provenance only.

```sh
set -eu
SCRATCH="$(mktemp -d)"
HOME="$SCRATCH/non-gd-home"
INSTALL_DIR="$SCRATCH/srv-toplines"  # explicit root outside HOME/tb-toplines
SYSD="$HOME/.config/systemd/user"
SOURCE=https://github.com/gdiab/tightbeam-toplines.git
MERGED_COMMIT=PASTE_EXACT_40_HEX_MERGED_MAIN_COMMIT
mkdir -p "$HOME" "$SYSD"
git clone -q "$SOURCE" "$INSTALL_DIR"
cd "$INSTALL_DIR"
git checkout --detach "$MERGED_COMMIT"
test "$(git rev-parse HEAD)" = "$MERGED_COMMIT"
git rev-parse HEAD

# 1. INSTALL (gated): units are staged only if every artifact matches its pin.
bin/tb-toplines-verify-install --root "$INSTALL_DIR" \
  && cp systemd/*.service systemd/*.timer "$SYSD/" \
  && echo "install: units staged into $SYSD"
# expect: OK — all 10 deployed artifacts match ... ; install: units staged

for pair in \
  "tb-toplines.service tb-toplines-serve" \
  "tb-toplines-watch.service tb-toplines-watch" \
  "tb-toplines-parity.service tb-toplines-parity"
do
  set -- $pair
  mkdir -p "$SYSD/$1.d"
  cat >"$SYSD/$1.d/root.conf" <<EOF
[Service]
WorkingDirectory=$INSTALL_DIR
ExecStart=
ExecStart=$INSTALL_DIR/bin/$2
EOF
done

for unit in tb-toplines.service tb-toplines-watch.service tb-toplines-parity.service; do
  cat "$SYSD/$unit" "$SYSD/$unit.d/root.conf"
done
# expect: each effective WorkingDirectory and final ExecStart names INSTALL_DIR.
# In final acceptance, confirm the live manager with:
# systemctl --user show -p WorkingDirectory -p ExecStart <each service>

# 2. FAIL-CLOSED PROOF: alter one artifact; the gate aborts and nothing stages.
printf '\n# tampered\n' >> "$INSTALL_DIR/bin/tb-toplines-gen"
bin/tb-toplines-verify-install --root "$INSTALL_DIR" \
  && cp systemd/*.service systemd/*.timer "$SYSD/" \
  || echo "install correctly refused (gate exit $?)"
# expect: ABORT — 1 of 10 ... bin/tb-toplines-gen ; install correctly refused
git -C "$INSTALL_DIR" checkout -- bin/tb-toplines-gen

# 3. VERIFY: the restored tree matches again.
bin/tb-toplines-verify-install --root "$INSTALL_DIR"
# expect: OK — all 10 deployed artifacts match the reviewed-clean pin set

# 4. ROLL BACK guard: a prior/altered build drifts from this release's pins, so
#    the gate blocks re-activating it. (Simulates rolling an artifact back to an
#    earlier, unreviewed version.)
printf 'OLD unreviewed build\n' > "$INSTALL_DIR/bin/tb-toplines-gen"
bin/tb-toplines-verify-install --root "$INSTALL_DIR" \
  || echo "gate blocks a drifted rollback, as documented"
# expect: ABORT — 1 of 10 ... bin/tb-toplines-gen ; gate blocks a drifted rollback
git -C "$INSTALL_DIR" checkout -- bin/tb-toplines-gen
bin/tb-toplines-verify-install --root "$INSTALL_DIR"    # green again

# 5. CLEANUP: scratch only; the live board and ATC are untouched.
cd / && rm -rf "$SCRATCH"
echo "walkthrough complete"
```

## Operate

| Need | Command |
|---|---|
| logs | `journalctl --user -u tb-toplines-watch -f` |
| parity logs | `journalctl --user -u tb-toplines-parity -n 30 --no-pager` |
| restart the pipeline | `systemctl --user restart tb-toplines-watch` |
| restart the server | `systemctl --user restart tb-toplines` |
| run the generator once by hand | `INSTALL_DIR="${TB_TOPLINES_ROOT:-$HOME/tb-toplines}"; "$INSTALL_DIR/bin/tb-toplines-gen" && head -c 400 "$INSTALL_DIR/web/toplines.json"` |
| show today's parity attempt | `. "$HOME/.config/tb-toplines/toplines.env"; ls -l "${XDG_STATE_HOME:-$HOME/.local/state}/tb-toplines/parity-attempt-$(TZ="${TB_TOPLINES_TZ:-UTC}" date +%F)"` |
| run parity now | `systemctl --user start tb-toplines-parity.service; journalctl --user -u tb-toplines-parity -n 30` (the atomic daily guard skips a second CLI call) |
| sidecar status | `docker exec tb-toplines-ts tailscale status; docker exec tb-toplines-ts tailscale serve status` |
| footprint on the page | vitals footer shows WAL bytes and pass ms; WAL over 64 MB means a long reader somewhere, find it with `fuser ~/.tightbeam/state.db` |

## Upgrade

The pull brings new artifacts, so the gate runs again before restart. A reviewed
release that changed an artifact carries the matching pin update, so the gate
passes; unexpected drift aborts the upgrade before anything restarts.

```sh
INSTALL_DIR="${TB_TOPLINES_ROOT:-$HOME/tb-toplines}"
cd "$INSTALL_DIR" && git pull --ff-only
bin/tb-toplines-verify-install --root "$INSTALL_DIR" \
  && cp systemd/* ~/.config/systemd/user/ && systemctl --user daemon-reload \
  && systemctl --user restart tb-toplines-watch tb-toplines
```

Keep existing service `root.conf` drop-ins when `INSTALL_DIR` is non-default;
they are unpinned install configuration and continue to select that tree.

## Roll back

```sh
systemctl --user disable --now tb-toplines-parity.timer tb-toplines-parity.service tb-toplines-watch.service tb-toplines.service 2>/dev/null || true
rm -f ~/.config/systemd/user/tb-toplines-parity.timer ~/.config/systemd/user/tb-toplines-parity.service ~/.config/systemd/user/tb-toplines-watch.service ~/.config/systemd/user/tb-toplines.service
rm -rf ~/.config/systemd/user/tb-toplines-parity.timer.d ~/.config/tb-toplines
INSTALL_DIR="${TB_TOPLINES_ROOT:-$HOME/tb-toplines}"
cd "$INSTALL_DIR"
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
INSTALL_DIR="${TB_TOPLINES_ROOT:-$HOME/tb-toplines}"
rm -rf "$INSTALL_DIR" ~/.config/systemd/user/tb-toplines*
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
An `ok-ledger-atc-missing` result means ledger parity held but the configured
local ATC file could not be read. The oneshot remains successful and the page
shows “ATC stage evidence unavailable.” Repair `TB_TOPLINES_ATC_DATA`; an ATC
web URL does not supply stage evidence.

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
(wi_7c4802fc-f46c-4c46-b10f-0ece2ac65dc0).

To recognise a likely clock-gap warn on the page: the footer names the
first mismatch only, one row whose quiet value differs from the CLI value by
an amount close to that run's CLI-to-generator gap (about 124s in the
observed case), near the daily-run time. That is consistent with a benign
clock-gap, but does not by itself prove data parity: the page shows only the
first mismatch, so a real divergence on another row or field can hide behind
it. To confirm, re-run the comparison writing to a scratch output. Set
`TB_TOPLINES_PARITY` to a temp path (for example `/tmp/parity-check.json`) so
the live `web/parity.json` stays untouched, and check every compared field:
quiet, card counts, and attest totals against the CLI, and stage against
ATC's data.json (`/opt/tb-atc/web/data.json`). If the only discrepancy is the
uniform quiet gap, it is benign; if any other field diverges (including stage
vs ATC), treat it as a real mismatch.

## After a Tightbeam upgrade

Run the generator by hand. A non-zero exit with a missing column named in the
error means schema drift; fix the query, restart the watcher, and let the next
scheduled parity run validate the repair.
