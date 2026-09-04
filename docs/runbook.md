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
operator/ops session), NOT by the coders or the orchestrator. The Install step
below clones `main` over `https`, so it can only run after that designated
session has merged.

## Install

```sh
ssh gd@sirius.tailf064dc.ts.net
git clone https://github.com/gdiab/tightbeam-toplines.git ~/tb-toplines
cd ~/tb-toplines
cp systemd/*.service systemd/*.timer ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now tb-toplines.service tb-toplines-watch.service tb-toplines-parity.timer
```

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

```sh
cd ~/tb-toplines && git pull --ff-only
cp systemd/* ~/.config/systemd/user/ && systemctl --user daemon-reload
systemctl --user restart tb-toplines-watch tb-toplines
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

## After a Tightbeam upgrade

Run the generator by hand. A non-zero exit with a missing column named in the
error means schema drift; fix the query, restart the watcher, and let the next
scheduled parity run validate the repair.
