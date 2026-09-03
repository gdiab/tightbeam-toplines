# Runbook: TopLines on sirius

**Draft.** Written before the code exists so the coder has a target. Whoever
deploys finishes it; a deploy without a matching runbook update is incomplete.
Everything here runs as `gd`. Nothing needs root.

## Layout on the host

```
/home/gd/tb-toplines/
  bin/tb-toplines-watch      watcher (bash + inline python)
  bin/tb-toplines-gen        generator (python 3.12, stdlib)
  bin/tb-toplines-serve      static server (python 3.12, stdlib)
  bin/tb-toplines-parity     daily parity check (python 3.12, stdlib)
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
docker volume create tb-toplines-ts-state
docker run -d --name tb-toplines-ts --restart unless-stopped \
  --network host \
  -e TS_USERSPACE=1 -e TS_HOSTNAME=toplines -e TS_STATE_DIR=/var/lib/tailscale \
  -v tb-toplines-ts-state:/var/lib/tailscale \
  tailscale/tailscale:latest
docker logs -f tb-toplines-ts        # follow the auth URL, approve the node in the admin console once
docker exec tb-toplines-ts tailscale serve --bg http://127.0.0.1:8898
docker exec tb-toplines-ts tailscale serve status
```

Expected: `https://toplines.tailf064dc.ts.net (tailnet only)` proxying to
`http://127.0.0.1:8898`. Do not run any of this against `tb-atc-ts`.

## Verify

```sh
systemctl --user status tb-toplines tb-toplines-watch --no-pager
journalctl --user -u tb-toplines-watch -n 20 --no-pager
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
| restart the pipeline | `systemctl --user restart tb-toplines-watch` |
| restart the server | `systemctl --user restart tb-toplines` |
| run the generator once by hand | `~/tb-toplines/bin/tb-toplines-gen && head -c 400 ~/tb-toplines/web/toplines.json` |
| run parity now | `systemctl --user start tb-toplines-parity.service; journalctl --user -u tb-toplines-parity -n 30` |
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
cd ~/tb-toplines && git checkout <previous-tag-or-sha>
systemctl --user restart tb-toplines-watch tb-toplines
```

Remove entirely:

```sh
systemctl --user disable --now tb-toplines tb-toplines-watch tb-toplines-parity.timer
docker rm -f tb-toplines-ts && docker volume rm tb-toplines-ts-state
rm -rf ~/tb-toplines ~/.config/systemd/user/tb-toplines*
```

Then remove the `toplines` node in the Tailscale admin console. ATC is
unaffected by any of this.

## When the parity check warns

The page shows the first mismatch. Run `tightbeam toplines --as-user george`
once by hand and compare the named item. If the CLI changed a definition
(quiet attribution, card outcomes), update the generator's query and the
definition in `docs/spec.md`. If ATC's stage differs, read
`reference/atc-derivations.md` and re-port the ladder. Do not loosen the
tolerance to make the warning go away.

## After a Tightbeam upgrade

Run the generator by hand. A non-zero exit with a missing column named in the
error means schema drift; fix the query, run parity by hand, restart the
watcher.
