#!/usr/bin/env python3
"""Ananta worker: the read-only collector on the second Mac (the 2017 MacBook Air).

Once a minute it records what cannot be fetched again later, from public endpoints only (no keys, no accounts, no orders):
  ndax     NDAX's best bid and ask for every CAD pair (one request: GetLevel1Summary): the real spreads the $500 book pays
  binance  Binance's best bid and ask for the same coins against USDT (one request): checks NDAX's prices and spreads
  fx       the Bank of Canada's USD/CAD rate (every 6 hours)
  site     whether Ananta's public status page answers: an outside view of the main Mac, its service and its tunnel
Each UTC day goes into its own file, data/l1_YYYY-MM-DD.sqlite; the main Mac pulls them. heartbeat.json says how the last round went.

  python3 collector.py run      the loop launchd keeps alive
  python3 collector.py once     one round (a test)
  python3 collector.py status   one line for the main Mac; exit 0 when the last good round is under 3 minutes old

Python 3.8+ standard library only (the old Mac's own Python); nothing to install.
"""
from __future__ import annotations

import json
import os
import shutil
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

VERSION = "1.0 (2026-10-11)"
HOME = Path(os.environ.get("ANANTA_WORKER_HOME", str(Path.home() / "ananta_worker")))
DATA, LOGS = HOME / "data", HOME / "logs"
HEARTBEAT = HOME / "heartbeat.json"
INTERVAL = 60
KEEP_DAYS, KEEP_DAYS_LOW_DISK, MIN_FREE_GB = 45, 14, 5
STALE_S = 180
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) AnantaWorker/1.0"
NDAX = "https://api.ndax.io:8443/AP"
BINANCE = "https://api.binance.com/api/v3"
FX_URL = "https://www.bankofcanada.ca/valet/observations/FXUSDCAD/json?recent=1"
SITE = "https://api.livetrading247.com/v3/public/status"
DAY = 86400

STATE: dict = {"inst": {}, "inst_t": 0.0, "syms": [], "syms_t": 0.0, "fx_t": 0.0, "errors": [], "last_ok": {}, "last_error": None,
               "site_last_ok": None, "prune_t": 0.0}


def log(msg: str) -> None:
    try:
        LOGS.mkdir(parents=True, exist_ok=True)
        f = LOGS / "collector.log"
        if f.exists() and f.stat().st_size > 5_000_000:
            f.replace(LOGS / "collector.log.1")
        with f.open("a") as fh:
            fh.write(time.strftime("%Y-%m-%d %H:%M:%S ") + msg + "\n")
    except OSError:
        pass


def get(url: str, timeout: int = 20):
    """GET and parse JSON. urllib first; the system curl when this Python cannot verify certificates (old macOS Pythons)."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except Exception as exc:  # noqa: BLE001
        text = str(exc).upper()
        if "CERTIFICATE" not in text and "SSL" not in text:
            raise
    out = subprocess.run(["/usr/bin/curl", "-sS", "--fail", "--max-time", str(timeout), "-A", UA, url],
                         capture_output=True, text=True, timeout=timeout + 5)
    if out.returncode != 0:
        raise RuntimeError("curl: " + out.stderr.strip()[:200])
    return json.loads(out.stdout)


def _f(x) -> float | None:
    try:
        v = float(x)
        return v if v > 0 else None
    except (TypeError, ValueError):
        return None


def _day(t: float) -> str:
    return time.strftime("%Y-%m-%d", time.gmtime(t))


def db(t: float) -> sqlite3.Connection:
    DATA.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(DATA / f"l1_{_day(t)}.sqlite"), timeout=30)
    con.executescript(
        "CREATE TABLE IF NOT EXISTS ndax (t INTEGER, coin TEXT, bid REAL, ask REAL, last REAL, notional24_cad REAL, ex_ms INTEGER);"
        "CREATE TABLE IF NOT EXISTS binance (t INTEGER, coin TEXT, bid REAL, ask REAL, bid_qty REAL, ask_qty REAL);"
        "CREATE TABLE IF NOT EXISTS fx (t INTEGER, usdcad REAL, obs_day TEXT);"
        "CREATE TABLE IF NOT EXISTS site (t INTEGER, ok INTEGER, ms INTEGER, detail TEXT);"
        "CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT);")
    con.execute("INSERT OR REPLACE INTO meta VALUES ('version', ?)", (VERSION,))
    return con


# ---------- the four sources ----------
def ndax(con: sqlite3.Connection, t: int) -> int:
    if not STATE["inst"] or time.time() - STATE["inst_t"] > DAY:
        ins = get(NDAX + "/GetInstruments?OMSId=1")
        STATE["inst"] = {i["InstrumentId"]: i["Product1Symbol"] for i in ins
                         if i.get("Product2Symbol") == "CAD" and not i.get("IsDisable")}
        STATE["inst_t"] = time.time()
    rows = []
    for s in get(NDAX + "/GetLevel1Summary?OMSId=1"):
        d = json.loads(s) if isinstance(s, str) else s
        coin = STATE["inst"].get(d.get("InstrumentId"))
        if coin:
            try:
                ex = int(str(d.get("TimeStamp") or 0))
            except ValueError:
                ex = 0
            rows.append((t, coin, _f(d.get("BestBid")), _f(d.get("BestOffer")), _f(d.get("LastTradedPx")), _f(d.get("Rolling24HrNotional")), ex))
    con.executemany("INSERT INTO ndax VALUES (?,?,?,?,?,?,?)", rows)
    return len(rows)


def binance(con: sqlite3.Connection, t: int) -> int:
    if not STATE["syms"] or time.time() - STATE["syms_t"] > DAY:
        if not STATE["inst"]:
            return 0
        live = {x["symbol"] for x in get(BINANCE + "/ticker/price")}
        STATE["syms"] = sorted(c + "USDT" for c in set(STATE["inst"].values()) if c + "USDT" in live)
        STATE["syms_t"] = time.time()
    if not STATE["syms"]:
        return 0
    q = urllib.parse.quote(json.dumps(STATE["syms"], separators=(",", ":")))
    rows = [(t, x["symbol"][:-4], _f(x.get("bidPrice")), _f(x.get("askPrice")), _f(x.get("bidQty")), _f(x.get("askQty")))
            for x in get(BINANCE + "/ticker/bookTicker?symbols=" + q)]
    con.executemany("INSERT INTO binance VALUES (?,?,?,?,?,?)", rows)
    return len(rows)


def fx(con: sqlite3.Connection, t: int) -> int:
    if time.time() - STATE["fx_t"] < 6 * 3600:
        return 0
    o = get(FX_URL)["observations"][-1]
    con.execute("INSERT INTO fx VALUES (?,?,?)", (t, float(o["FXUSDCAD"]["v"]), o["d"]))
    STATE["fx_t"] = time.time()
    return 1


def site(con: sqlite3.Connection, t: int) -> int:
    t0 = time.time()
    try:
        get(SITE, timeout=15)
        ok, detail = 1, ""
        STATE["site_last_ok"] = t
    except Exception as exc:  # noqa: BLE001
        ok, detail = 0, str(exc)[:160]
    con.execute("INSERT INTO site VALUES (?,?,?,?)", (t, ok, int(1000 * (time.time() - t0)), detail))
    return ok


SOURCES = (("ndax", ndax), ("binance", binance), ("fx", fx), ("site", site))


# ---------- one round, the heartbeat, housekeeping ----------
def free_gb() -> float:
    try:
        return round(shutil.disk_usage(str(HOME)).free / 1e9, 1)
    except OSError:
        return -1.0


def prune() -> None:
    if time.time() - STATE["prune_t"] < 3600:
        return
    STATE["prune_t"] = time.time()
    keep = KEEP_DAYS if free_gb() >= MIN_FREE_GB else KEEP_DAYS_LOW_DISK
    cutoff = _day(time.time() - keep * DAY)
    for p in sorted(DATA.glob("l1_*.sqlite")):
        if p.stem[3:] < cutoff:
            try:
                p.unlink()
                log(f"pruned {p.name} (keeping {keep} days)")
            except OSError:
                pass


def round_once() -> dict:
    t = int(time.time())
    con = db(t)
    got: dict = {}
    for name, fn in SOURCES:
        try:
            got[name] = fn(con, t)
            con.commit()
            if name != "site" or got[name]:
                STATE["last_ok"][name] = t
        except Exception as exc:  # noqa: BLE001  one source failing never stops the others
            con.rollback()
            msg = f"{name}: {str(exc)[:200]}"
            STATE["errors"].append((t, msg))
            STATE["last_error"] = {"t": t, "what": msg}
            log("error " + msg)
    STATE["errors"] = [e for e in STATE["errors"] if e[0] > t - 3600]
    counts = {}
    for tb in ("ndax", "binance", "fx", "site"):
        counts[tb] = con.execute(f"SELECT COUNT(*) FROM {tb}").fetchone()[0]
    counts["site_failed"] = con.execute("SELECT COUNT(*) FROM site WHERE ok=0").fetchone()[0]
    con.close()
    hb = {"t": t, "utc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(t)), "host": socket.gethostname(), "version": VERSION,
          "this_round": got, "last_ok": STATE["last_ok"], "today": counts, "errors_last_hour": len(STATE["errors"]),
          "last_error": STATE["last_error"], "site_last_ok": STATE["site_last_ok"], "free_gb": free_gb(), "python": sys.version.split()[0]}
    tmp = HEARTBEAT.with_name("heartbeat.tmp")
    tmp.write_text(json.dumps(hb, indent=1))
    tmp.replace(HEARTBEAT)
    prune()
    return hb


def run() -> None:
    log(f"start v{VERSION} python {sys.version.split()[0]} home {HOME}")
    while True:
        try:
            round_once()
        except Exception as exc:  # noqa: BLE001
            log(f"round failed: {exc}")
        time.sleep(max(5.0, INTERVAL - time.time() % INTERVAL))      # on the minute


def status() -> int:
    try:
        hb = json.loads(HEARTBEAT.read_text())
    except (OSError, ValueError):
        print("DOWN · no heartbeat yet")
        return 2
    now = time.time()
    last = hb.get("last_ok", {}).get("ndax")
    age = int(now - last) if last else None
    ok = age is not None and age < STALE_S
    td = hb.get("today", {})
    site_txt = ("site OK" if hb.get("site_last_ok") and now - hb["site_last_ok"] < STALE_S
                else "site NOT answering" + (f" for {int((now - hb['site_last_ok']) / 60)} min" if hb.get("site_last_ok") else ""))
    print(f"{'OK' if ok else 'STALE'} · {hb.get('host')} · last good round {age if age is not None else '?'} s ago · today: "
          f"NDAX {td.get('ndax', 0):,} rows, Binance {td.get('binance', 0):,}, site checks {td.get('site', 0):,} "
          f"({td.get('site_failed', 0)} failed) · {site_txt} · {hb.get('errors_last_hour', 0)} errors in the last hour · "
          f"{hb.get('free_gb')} GB free · v{hb.get('version')}")
    return 0 if ok else 1


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "run":
        run()
    elif cmd == "once":
        print(json.dumps(round_once(), indent=1))
    else:
        sys.exit(status())
