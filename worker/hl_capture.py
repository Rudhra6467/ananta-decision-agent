#!/usr/bin/env python3
"""Ananta worker: other traders' fills, saved every day (decision OD-HL-FILLS, option (a); Madhav, 2026-10-20: "let the worker Mac
save other traders' fills every day, data only ... Yes. We have to do it.").

DATA ONLY. Other traders are reference and event generators, never teachers or copy signals (docs/LOCK.md, D8). This file reads
one public endpoint (Hyperliquid's info API, request type userFillsByTime) for a fixed list of public accounts and writes one file
per finished UTC day. It holds no keys, has no account, and has no code that can place, change or cancel an order anywhere: it never
calls Hyperliquid's /exchange endpoint, and the only request type it sends is userFillsByTime (tests/test_hl_daily.py checks both).

The accounts: hl_accounts.json, the fixed sample of review #2 (the Sep 29-30 collection, src/research/hl_bench.py: random accounts
from the leaderboard's winners / middle / losers, the live tape on the 10 lab coins and public vaults, seed 20260929; the file says
how it was chosen). The installer builds it once on the main Mac and copies it here. It never changes by itself.

Every run (launchd, every hour: com.ananta.worker.hlcapture.plist) fetches every FINISHED UTC day of the last 7 that is not held
yet, so a sleep or an outage catches up by itself. Per account and day: userFillsByTime from 00:00 to 24:00 UTC, paged (2,000 fills
an answer), at least 1.2 s between calls, backoff on errors and on HTTP 429. A day is written to data/hl_YYYY-MM-DD.sqlite.part
(resumable: an account that failed is tried again next hour, 3 times at most, then recorded as GAVE_UP) and renamed to
data/hl_YYYY-MM-DD.sqlite only when every account is done, so a half-written day never looks finished. 45 days are kept (14 when
the disk has under 5 GB free). The API serves only each account's 10,000 most recent fills, so a very busy account's older days can
come back short; each account's row says how many fills and pages it got.

  python3 hl_capture.py run                     one round (what launchd runs)
  python3 hl_capture.py run --days 1 --accounts FILE   a test: only yesterday, another account list
  python3 hl_capture.py status                  one line for the main Mac; exit 0 when the last run is under 2.5 hours old and
                                                every finished day of the last 7 is held (yesterday gets 3 hours' grace), 1 stale,
                                                2 never ran
  python3 hl_capture.py ping                    one small request (the installer's test)

Python 3.8+ standard library only (the old Mac's own Python); nothing to install.
"""
from __future__ import annotations

import calendar
import json
import os
import shutil
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

VERSION = "1.0 (2026-10-20)"
HOME = Path(os.environ.get("ANANTA_WORKER_HOME", str(Path.home() / "ananta_worker")))
DATA, LOGS = HOME / "data", HOME / "logs"
ACCOUNTS = HOME / "hl_accounts.json"
HEARTBEAT = HOME / "hl_heartbeat.json"
LOCK = HOME / "hl_capture.lock"
INFO = "https://api.hyperliquid.xyz/info"
REQUEST_TYPE = "userFillsByTime"            # the only request this file sends
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) AnantaWorker/1.0"
DAY_S, DAY_MS = 86400, 86_400_000
LOOKBACK_DAYS = 7
KEEP_DAYS, KEEP_DAYS_LOW_DISK, MIN_FREE_GB = 45, 14, 5
MIN_GAP_S = 1.2                             # between any two calls
PAGE = 2000                                 # the API's most fills in one answer
MAX_FILLS_DAY = 50_000                      # per account and day; beyond it the account's row says truncated
BACKOFF_S = (10, 20, 40, 80)                # waits before the 2nd..5th try of one call
MAX_ATTEMPTS = 3                            # runs an account may fail on one day before it is recorded as GAVE_UP
RUN_BUDGET_S = 50 * 60                      # no new account after 50 minutes (the next hourly run continues)
STALE_S = int(2.5 * 3600)
GRACE_S = 3 * 3600                          # yesterday may be missing for 3 hours after 00:00 UTC
KNOWN = {"coin": "coin", "px": "px", "sz": "sz", "side": "side", "time": "time", "startPosition": "start_position", "dir": "dir",
         "closedPnl": "closed_pnl", "hash": "hash", "oid": "oid", "crossed": "crossed", "fee": "fee", "tid": "tid",
         "feeToken": "fee_token", "builderFee": "builder_fee", "liquidation": "liquidation", "cloid": "cloid", "twapId": "twap_id"}
REAL = {"px", "sz", "start_position", "closed_pnl", "fee", "builder_fee"}
INT = {"time", "oid", "tid", "twap_id", "crossed"}
SCHEMA = """
CREATE TABLE IF NOT EXISTS fills (account TEXT NOT NULL, coin TEXT, px REAL, sz REAL, side TEXT, time INTEGER, start_position REAL,
    dir TEXT, closed_pnl REAL, hash TEXT, oid INTEGER, crossed INTEGER, fee REAL, tid INTEGER, fee_token TEXT, builder_fee REAL,
    liquidation TEXT, cloid TEXT, twap_id INTEGER, extra TEXT, fetched_at INTEGER, PRIMARY KEY (account, tid, oid));
CREATE INDEX IF NOT EXISTS fills_time ON fills (time);
CREATE TABLE IF NOT EXISTS accounts (account TEXT PRIMARY KEY, label TEXT, source TEXT, status TEXT, fills INTEGER, pages INTEGER,
    truncated INTEGER, attempts INTEGER, error TEXT, fetched_at INTEGER);
CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT);
"""


class RateLimited(Exception):
    """HTTP 429 after every backoff: stop this run, the next hour continues."""


def log(msg: str) -> None:
    try:
        LOGS.mkdir(parents=True, exist_ok=True)
        f = LOGS / "hl_capture.log"
        if f.exists() and f.stat().st_size > 5_000_000:
            f.replace(LOGS / "hl_capture.log.1")
        with f.open("a") as fh:
            fh.write(time.strftime("%Y-%m-%d %H:%M:%S ") + msg + "\n")
    except OSError:
        pass


# ---------- HTTP: one endpoint, one request type, gentle ----------
_clock = time.monotonic                    # tests replace these two to check the pacing without waiting
_sleep = time.sleep
_last = [-1e9]


def _pace() -> None:
    gap = _clock() - _last[0]
    if gap < MIN_GAP_S:
        _sleep(MIN_GAP_S - gap)
    _last[0] = _clock()


def http_post(body: dict, timeout: int = 60):
    """POST JSON to the info endpoint. urllib first; the system curl when this Python cannot verify certificates (old macOS
    Pythons). Raises RateLimited on HTTP 429 (once; post() decides about retrying)."""
    data = json.dumps(body).encode()
    try:
        req = urllib.request.Request(INFO, data=data, headers={"Content-Type": "application/json", "User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            raise RateLimited("HTTP 429") from None
        raise
    except Exception as exc:  # noqa: BLE001
        text = str(exc).upper()
        if "CERTIFICATE" not in text and "SSL" not in text:
            raise
    out = subprocess.run(["/usr/bin/curl", "-sS", "--fail", "--max-time", str(timeout), "-A", UA, "-H", "Content-Type: application/json",
                          "--data-binary", "@-", INFO], input=data.decode(), capture_output=True, text=True, timeout=timeout + 5)
    if out.returncode != 0:
        if "429" in out.stderr:
            raise RateLimited("HTTP 429 (curl)")
        raise RuntimeError("curl: " + out.stderr.strip()[:200])
    return json.loads(out.stdout)


def post(body: dict):
    """One paced call with backoff: up to 5 tries; a 429 that outlasts every wait raises RateLimited."""
    if body.get("type") != REQUEST_TYPE:
        raise ValueError("hl_capture sends userFillsByTime only")
    for i in range(len(BACKOFF_S) + 1):
        _pace()
        try:
            return http_post(body)
        except Exception as exc:  # noqa: BLE001
            if i == len(BACKOFF_S):
                raise
            log(f"retry {i + 1} after {type(exc).__name__}: {str(exc)[:120]}")
            _sleep(BACKOFF_S[i])


def fetch_day(account: str, start_ms: int, end_ms: int) -> tuple:
    """Every fill of one account with start_ms <= time < end_ms: (fills, pages, truncated). Pages forward from the newest time of
    each full answer; the same fill seen twice (same tid and oid) is kept once."""
    got: dict = {}
    start, pages, truncated = start_ms, 0, False
    while True:
        batch = post({"type": REQUEST_TYPE, "user": account, "startTime": start, "endTime": end_ms - 1})
        pages += 1
        if not isinstance(batch, list):
            raise ValueError(f"unexpected answer: {str(batch)[:120]}")
        for f in batch:
            t = int(f.get("time") or 0)
            if start_ms <= t < end_ms:
                got[(f.get("tid"), f.get("oid"))] = f
        if len(got) >= MAX_FILLS_DAY:
            truncated = True
            break
        if len(batch) < PAGE:
            break
        last = max(int(f.get("time") or 0) for f in batch)
        if last <= start:                      # a full page inside one millisecond: cannot page further
            truncated = True
            break
        start = last
    return list(got.values()), pages, truncated


def _row(account: str, f: dict, fetched_at: int) -> tuple:
    vals = {}
    for k, col in KNOWN.items():
        v = f.get(k)
        if v is None:
            vals[col] = None
        elif col == "liquidation":
            vals[col] = json.dumps(v, separators=(",", ":"))
        elif col in REAL:
            try:
                vals[col] = float(v)
            except (TypeError, ValueError):
                vals[col] = None
        elif col in INT:
            vals[col] = int(bool(v)) if col == "crossed" else int(v)
        else:
            vals[col] = str(v)
    extra = {k: v for k, v in f.items() if k not in KNOWN}
    return (account, *[vals[c] for c in KNOWN.values()], json.dumps(extra, separators=(",", ":")) if extra else None, fetched_at)


# ---------- the day files ----------
def _day(t: float) -> str:
    return time.strftime("%Y-%m-%d", time.gmtime(t))


def _day_t(day: str) -> int:
    return calendar.timegm(time.strptime(day, "%Y-%m-%d"))


def final_path(day: str) -> Path:
    return DATA / f"hl_{day}.sqlite"


def part_path(day: str) -> Path:
    return DATA / f"hl_{day}.sqlite.part"


def finished_days(now: float, days: int = LOOKBACK_DAYS) -> list:
    """The last `days` finished UTC days, oldest first (today is never finished)."""
    today = int(now) - int(now) % DAY_S
    return [_day(today - k * DAY_S) for k in range(days, 0, -1)]


def load_accounts(path: Path | None = None) -> dict:
    d = json.loads(Path(path or ACCOUNTS).read_text())
    rows = [a for a in d.get("accounts") or [] if str(a.get("account", "")).startswith("0x")]
    if not rows:
        raise ValueError("the account list is empty")
    return {"accounts": rows, "how_chosen": d.get("how_chosen", ""), "version": d.get("version", "")}


def _open_part(day: str, accts: dict) -> sqlite3.Connection:
    DATA.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(part_path(day)), timeout=30)
    con.executescript(SCHEMA)
    con.executemany("INSERT OR IGNORE INTO accounts (account, label, source, status, fills, pages, truncated, attempts) "
                    "VALUES (?,?,?,'PENDING',0,0,0,0)", [(a["account"].lower(), a.get("label"), a.get("source")) for a in accts["accounts"]])
    t0 = _day_t(day)
    for k, v in (("version", VERSION), ("day", day), ("start_ms", str(t0 * 1000)), ("end_ms", str((t0 + DAY_S) * 1000)),
                 ("accounts_list", accts.get("version") or ""), ("how_chosen", accts.get("how_chosen") or ""), ("host", socket.gethostname())):
        con.execute("INSERT OR IGNORE INTO meta VALUES (?,?)", (k, v))
    con.commit()
    return con


def capture_day(day: str, accts: dict, deadline: float) -> dict:
    """Fetch the accounts of one day not done yet; rename the file to its final name when every account is OK or GAVE_UP."""
    t0 = _day_t(day)
    con = _open_part(day, accts)
    out = {"day": day, "accounts_done": 0, "fills": 0, "errors": 0, "rate_limited": False, "finished": False}
    try:
        todo = [r[0] for r in con.execute("SELECT account FROM accounts WHERE status IN ('PENDING','ERROR') ORDER BY account")]
        for a in todo:
            if _clock() > deadline:
                out["out_of_time"] = True
                break
            try:
                fills, pages, trunc = fetch_day(a, t0 * 1000, (t0 + DAY_S) * 1000)
            except RateLimited as exc:
                out["rate_limited"] = True
                log(f"{day} {a[:10]}: rate limited ({exc}); stopping this run")
                break
            except Exception as exc:  # noqa: BLE001  one account failing never stops the others
                n = (con.execute("SELECT attempts FROM accounts WHERE account=?", (a,)).fetchone()[0] or 0) + 1
                con.execute("UPDATE accounts SET status=?, attempts=?, error=?, fetched_at=? WHERE account=?",
                            ("GAVE_UP" if n >= MAX_ATTEMPTS else "ERROR", n, str(exc)[:200], int(time.time()), a))
                con.commit()
                out["errors"] += 1
                log(f"{day} {a[:10]}: error {n} of {MAX_ATTEMPTS}: {str(exc)[:160]}")
                continue
            now = int(time.time())
            with con:                                            # one account's day is written whole or not at all
                con.execute("DELETE FROM fills WHERE account=?", (a,))
                con.executemany(f"INSERT OR REPLACE INTO fills VALUES ({','.join('?' * (len(KNOWN) + 3))})", [_row(a, f, now) for f in fills])
                con.execute("UPDATE accounts SET status='OK', fills=?, pages=?, truncated=?, error=NULL, fetched_at=? WHERE account=?",
                            (len(fills), pages, int(trunc), now, a))
            out["accounts_done"] += 1
            out["fills"] += len(fills)
        left = con.execute("SELECT COUNT(*) FROM accounts WHERE status IN ('PENDING','ERROR')").fetchone()[0]
        if not left:
            gave_up = con.execute("SELECT COUNT(*) FROM accounts WHERE status='GAVE_UP'").fetchone()[0]
            con.execute("INSERT OR REPLACE INTO meta VALUES ('finished_at', ?)", (str(int(time.time())),))
            con.execute("INSERT OR REPLACE INTO meta VALUES ('complete', ?)", ("all accounts" if not gave_up else f"{gave_up} accounts gave up",))
            con.commit()
            ok = con.execute("PRAGMA integrity_check").fetchone()[0]
            con.close()
            con = None
            if ok != "ok":
                raise RuntimeError(f"integrity check of {part_path(day).name}: {ok}")
            os.replace(str(part_path(day)), str(final_path(day)))   # atomic: the day appears whole or not at all
            out["finished"] = True
            log(f"{day}: finished ({'all accounts' if not gave_up else str(gave_up) + ' gave up'})")
    finally:
        if con is not None:
            con.close()
    return out


def day_summary(day: str) -> dict:
    con = sqlite3.connect(f"file:{final_path(day)}?mode=ro", uri=True)
    try:
        st = dict(con.execute("SELECT status, COUNT(*) FROM accounts GROUP BY status").fetchall())
        return {"fills": con.execute("SELECT COUNT(*) FROM fills").fetchone()[0], "accounts_ok": st.get("OK", 0),
                "gave_up": st.get("GAVE_UP", 0), "with_fills": con.execute("SELECT COUNT(*) FROM accounts WHERE fills > 0").fetchone()[0]}
    finally:
        con.close()


# ---------- housekeeping, the run, the status ----------
def free_gb() -> float:
    try:
        return round(shutil.disk_usage(str(HOME)).free / 1e9, 1)
    except OSError:
        return -1.0


def prune(now: float) -> list:
    keep = KEEP_DAYS if free_gb() >= MIN_FREE_GB else KEEP_DAYS_LOW_DISK
    cutoff = _day(now - keep * DAY_S)
    gone = []
    for p in sorted(DATA.glob("hl_*.sqlite")) + sorted(DATA.glob("hl_*.sqlite.part")):
        day = p.name[3:13]
        if day < cutoff or (p.name.endswith(".part") and day < _day(now - (LOOKBACK_DAYS + 1) * DAY_S)):
            try:
                p.unlink()
                gone.append(p.name)
                log(f"pruned {p.name} (keeping {keep} days)")
            except OSError:
                pass
    return gone


def _locked():
    """An exclusive lock for the run (launchd never starts two, a hand-run test might); None when another run holds it."""
    import fcntl

    HOME.mkdir(parents=True, exist_ok=True)
    fh = open(str(LOCK), "w")
    try:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        fh.close()
        return None
    return fh


def run(days: int = LOOKBACK_DAYS, accounts: Path | None = None, now: float | None = None) -> dict:
    lock = _locked()
    if lock is None:
        return {"skipped": "another capture is running"}
    try:
        now = now or time.time()
        started = _clock()
        accts = load_accounts(accounts)
        todo = [d for d in finished_days(now, days) if not final_path(d).exists()]
        res, err = [], None
        for day in todo:
            try:
                r = capture_day(day, accts, started + RUN_BUDGET_S)
            except Exception as exc:  # noqa: BLE001
                err = f"{day}: {str(exc)[:200]}"
                log("error " + err)
                break
            res.append(r)
            if r.get("rate_limited") or r.get("out_of_time"):
                break
        pruned = prune(now)
        held = [d for d in finished_days(now, LOOKBACK_DAYS) if final_path(d).exists()]
        summ = {}
        for d in held[-2:]:
            try:
                summ[d] = day_summary(d)
            except sqlite3.Error as exc:
                summ[d] = {"error": str(exc)[:120]}
        hb = {"t": int(now), "utc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(now)), "host": socket.gethostname(),
              "version": VERSION, "accounts": len(accts["accounts"]), "todo": todo, "this_run": res, "error": err,
              "errors": sum(r.get("errors", 0) for r in res) + (1 if err else 0), "rate_limited": any(r.get("rate_limited") for r in res),
              "held_last_7": held, "days": summ, "pruned": pruned, "seconds": round(_clock() - started, 1), "free_gb": free_gb(),
              "python": sys.version.split()[0]}
        tmp = HEARTBEAT.with_name("hl_heartbeat.tmp")
        tmp.write_text(json.dumps(hb, indent=1))
        tmp.replace(HEARTBEAT)
        return hb
    finally:
        lock.close()


def status(now: float | None = None) -> int:
    now = now or time.time()
    try:
        hb = json.loads(HEARTBEAT.read_text())
    except (OSError, ValueError):
        print("hl NEVER · other traders' fills: no capture yet")
        return 2
    want = finished_days(now, LOOKBACK_DAYS)
    held = [d for d in want if final_path(d).exists()]
    missing = [d for d in want if d not in held]
    if missing == [want[-1]] and now % DAY_S < GRACE_S:
        missing = []                                             # yesterday just finished: the next hourly run takes it
    age = int(now - hb.get("t", 0))
    ok = age < STALE_S and not missing
    newest = held[-1] if held else None
    s = (hb.get("days") or {}).get(newest) or {}
    print(f"hl {'OK' if ok else 'STALE'} · other traders' fills: {len(held)} of the last {LOOKBACK_DAYS} finished days held"
          + (f" (newest {newest}: {s.get('fills', 0):,} fills, {s.get('with_fills', 0)} of {hb.get('accounts')} accounts traded"
             + (f", {s['gave_up']} gave up" if s.get("gave_up") else "") + ")" if newest else "")
          + (f" · missing {', '.join(missing)}" if missing else "") + f" · last run {age // 60} min ago · {hb.get('errors', 0)} errors"
          + (" · rate limited" if hb.get("rate_limited") else "") + f" · v{hb.get('version')}")
    return 0 if ok else 1


def ping(accounts: Path | None = None) -> int:
    try:
        a = load_accounts(accounts)["accounts"][0]
        now = int(time.time() * 1000)
        n = len(post({"type": REQUEST_TYPE, "user": a["account"], "startTime": now - 3_600_000, "endTime": now}) or [])
        print(f"ok · the info API answers · {n} fills in the last hour for {a.get('label') or 'the first account'}")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"failed · {type(exc).__name__}: {str(exc)[:200]}")
        return 1


def _arg(argv: list, name: str, default=None):
    return argv[argv.index(name) + 1] if name in argv and argv.index(name) + 1 < len(argv) else default


if __name__ == "__main__":
    argv = sys.argv[1:]
    cmd = argv[0] if argv else "status"
    acc = _arg(argv, "--accounts")
    if cmd == "run":
        r = run(int(_arg(argv, "--days", LOOKBACK_DAYS)), Path(acc) if acc else None)
        print(json.dumps({k: r.get(k) for k in ("skipped", "todo", "this_run", "held_last_7", "errors", "rate_limited", "seconds")}, indent=1))
        sys.exit(0 if not r.get("error") else 1)
    elif cmd == "ping":
        sys.exit(ping(Path(acc) if acc else None))
    else:
        sys.exit(status())
