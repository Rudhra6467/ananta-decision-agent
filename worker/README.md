# The worker Mac (2017 MacBook Air)

A read-only second machine. It records, once a minute, what cannot be fetched again later:
- NDAX's bid and ask for every CAD pair
- Binance's bid and ask for the same coins
- the USD/CAD rate
- whether Ananta's public status page answers

It holds **no keys, no passwords and no accounts**, and it never places an order. The main Mac connects to it; it never
connects to the main Mac.

| File | What it is |
|---|---|
| `collector.py` | the collector (Python 3.8+, standard library only) |
| `com.ananta.worker.collector.plist` | the launchd job (keeps it running, keeps the Mac awake on power) |
| `install_worker.sh` | installs or updates it from the main Mac over SSH |

On the worker, everything lives in `~/ananta_worker`: `data/l1_YYYY-MM-DD.sqlite` (one file per UTC day, 45 days kept),
`heartbeat.json`, `logs/`, and `status`.

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
1 when stale, and 2 when there has never been a heartbeat.
