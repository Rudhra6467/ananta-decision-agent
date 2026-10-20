# The worker Mac (2017 MacBook Air)

A read-only second machine. It records, once a minute, what cannot be fetched again later:
- NDAX's bid and ask for every CAD pair
- Binance's bid and ask for the same coins
- the USD/CAD rate
- whether Ananta's public status page answers

And, every hour since Oct 20 (decision OD-HL-FILLS, option (a): data only), other traders' fills: every finished UTC day of the
last 7 it does not hold yet, for the fixed sample of review #2 without its 6 market-maker / HFT accounts (59 accounts) (Hyperliquid's public info API, `userFillsByTime` only). Other
traders are reference, never teachers or copy signals (docs/LOCK.md, D8).

It holds **no keys, no passwords and no accounts**, and it never places an order. The main Mac connects to it; it never
connects to the main Mac.

| File | What it is |
|---|---|
| `collector.py` | the collector (Python 3.8+, standard library only) |
| `com.ananta.worker.collector.plist` | the launchd job (keeps it running, keeps the Mac awake on power) |
| `hl_capture.py` | other traders' fills, one file per finished UTC day (Python 3.8+, standard library only) |
| `com.ananta.worker.hlcapture.plist` | its launchd job (every hour and at login; a run ends by itself) |
| `install_worker.sh` | installs or updates both from the main Mac over SSH |

On the worker, everything lives in `~/ananta_worker`: `data/l1_YYYY-MM-DD.sqlite` (one file per UTC day, 45 days kept),
`data/hl_YYYY-MM-DD.sqlite` (other traders' fills, written as `.part` and renamed only when the day is whole, 45 days kept),
`hl_accounts.json` (the fixed account list), `heartbeat.json`, `hl_heartbeat.json`, `logs/`, and `status`. The main Mac's 03:40
backup pulls both kinds of finished day into `~/ananta_worker_data` (`jarvis/service/worker.py`, `pull`).

## Setup (once)

**Step 1, on the old Mac:**

1. Plug it in and keep the lid open (a closed lid makes it sleep).
2. In System Preferences, open Sharing and check that Remote Login is on.
3. Open Terminal and type:

   ```
   sudo pmset -c sleep 0 displaysleep 10 disksleep 0 womp 1 autorestart 1
   ```

   Type the old Mac's password when asked (nothing shows while you type). The screen may still turn off; the Mac stays awake
   and restarts by itself after a power cut.
4. In the same Terminal, type `xcode-select --install`. Click **Install** if a window appears. If it says the tools are
   already installed, that's fine.

**Step 2, on the main Mac** (the SSH key already exists in `~/.ssh/ananta_worker`). Open Terminal and type:

```
ssh-copy-id -i ~/.ssh/ananta_worker.pub ananta-worker
```

Type the **old Mac's** password once. After that, the main Mac logs in with the key and nobody types a password again.

**Step 3, on the main Mac:**

```
bash ~/code/ananta-agent-research/worker/install_worker.sh
```

## The one-line check (from the main Mac)

```
ssh ananta-worker '~/ananta_worker/status'
```

It prints `OK · … last good round 23 s ago · today: NDAX … rows …`. It exits 0 when the last round is under 3 minutes old,
1 when stale, and 2 when there has never been a heartbeat. A second line, `hl OK · other traders' fills: 7 of the last 7
finished days held …`, is the fills capture; it never changes the exit code (the collector's line is the worker's health).

## The daily comparison on the main Mac (installed by hand, not by the script)

`src/research/others_daily.py` reads the pulled `hl_*.sqlite` days, rebuilds the round trips, holds each against what Ananta
saw and did at the trader's entry (read-only), and writes `docs/repair_shop/daily/others_YYYY-MM-DD.md` plus a row in
`docs/repair_shop/daily/others_history.jsonl`. A situation no rule of ours covers that repeats on 3 days in 7 becomes one
repair-board request worded as a DRAFT finding. Its launchd job is `scripts/launchd/com.ananta.othersdaily.plist` (04:30, after
the 03:40 pull). To install it, on the main Mac, after this branch is merged into the checkout the service runs from:

```
cd ~/code/ananta-agent-research
~/ananta_venvs/jarvis/bin/python -m src.research.others_daily run --no-requests     # a dry run: pages, nothing filed
sed -e "s#__REPO__#$PWD#g" -e "s#__HOME__#$HOME#g" scripts/launchd/com.ananta.othersdaily.plist > ~/Library/LaunchAgents/com.ananta.othersdaily.plist
plutil -lint ~/Library/LaunchAgents/com.ananta.othersdaily.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.ananta.othersdaily.plist
```

To stop it: `launchctl bootout gui/$(id -u)/com.ananta.othersdaily`.
