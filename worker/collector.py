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

VERSION = "1.1 (2026-10-15)"
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
               "site_last_ok": None, "prune_t": 0.0, "down_since": None, "alerted_t": None}
# The outside alert (Madhav's yes, Oct 15): when the public page has not answered for 10 minutes (the main Mac asleep, frozen or
# offline, or its tunnel down), one phone note through the same ntfy topic the main Mac uses, a reminder every 3 hours, and a note
# when it answers again. alert.json ({"server", "topic"}) is written by the main Mac (scripts/worker_alert_setup.py), mode 600;
# without it there is no alert. It can only send notes to Madhav's phone: it opens nothing and reads nothing.
ALERT_FILE = HOME / "alert.json"
ALERT_AFTER_S, REMIND_S = 10 * 60, 3 * 3600


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
        "CREATE TABLE IF NOT EXISTS alerts (t INTEGER, kind TEXT, result TEXT);"
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


def alert(title: str, body: str) -> str:
    """One phone note through ntfy; 'off' without alert.json. Never raises."""
    try:
        cfg = json.loads(ALERT_FILE.read_text())
        url = str(cfg["server"]).rstrip("/") + "/" + str(cfg["topic"])
    except (OSError, ValueError, KeyError):
        return "off"
    head = {"Title": title.encode("ascii", "replace").decode()[:100], "Priority": "4", "Tags": "warning"}
    try:
        req = urllib.request.Request(url, data=body[:500].encode(), headers=head, method="POST")
        with urllib.request.urlopen(req, timeout=15) as r:
            return "sent" if 200 <= r.status < 300 else f"failed: HTTP {r.status}"
    except Exception as exc:  # noqa: BLE001  old Pythons that cannot verify certificates: the system curl
        if "CERTIFICATE" not in str(exc).upper() and "SSL" not in str(exc).upper():
            return f"failed: {type(exc).__name__}"
    args = ["/usr/bin/curl", "-sS", "--fail", "--max-time", "15", "-d", body[:500]]
    for k, v in head.items():
        args += ["-H", f"{k}: {v}"]
    out = subprocess.run(args + [url], capture_output=True, text=True, timeout=20)
    return "sent" if out.returncode == 0 else "failed: curl"


def watch_site(t: int, ok: bool, detail: str) -> tuple[str, str] | None:
    """The outside alert's state: down for 10 minutes -> a note, every 3 hours a reminder, back -> a note (only after a note).
    Returns (kind, result) when a note was tried ('down', 'still_down', 'back'; result 'sent' or why not), else None. With no
    alert.json there is nothing to try and nothing is recorded."""
    if ok:
        was, alerted = STATE["down_since"], STATE["alerted_t"]
        STATE["down_since"], STATE["alerted_t"] = None, None
        if alerted and was:
            r = alert("Ananta is reachable again", f"Seen from the worker Mac: the public page answers again after about "
                                                   f"{int((t - was) / 60)} minutes.")
            return None if r == "off" else ("back", r)
        return None
    if STATE["down_since"] is None:
        STATE["down_since"] = t
        return None
    down = t - STATE["down_since"]
    if down >= ALERT_AFTER_S and (STATE["alerted_t"] is None or t - STATE["alerted_t"] >= REMIND_S):
        first = STATE["alerted_t"] is None
        r = alert("Ananta: the main Mac or the site is down" if first else "Ananta: still down",
                  f"Seen from the worker Mac: the public page has not answered for {int(down / 60)} minutes ({detail[:80] or 'no answer'}). "
                  "Every paper book stands still meanwhile. If the Mac is asleep, plug it in and open the lid.")
        if r == "off":
            return None
        if r == "sent":
            STATE["alerted_t"] = t
        log(f"outside alert ({'first' if first else 'reminder'}): {r}")
        return ("down" if first else "still_down"), r
    return None


def site(con: sqlite3.Connection, t: int) -> int:
    t0 = time.time()
    try:
        get(SITE, timeout=15)
        ok, detail = 1, ""
        STATE["site_last_ok"] = t
    except Exception as exc:  # noqa: BLE001
        ok, detail = 0, str(exc)[:160]
    con.execute("INSERT INTO site VALUES (?,?,?,?)", (t, ok, int(1000 * (time.time() - t0)), detail))
    try:
        if ALERT_FILE.exists() and STATE.get("armed_day") != _day(t):          # each day's file says whether the alert was on that day
            con.execute("INSERT INTO alerts VALUES (?,?,?)", (t, "armed", "on"))
            STATE["armed_day"] = _day(t)
        a = watch_site(t, bool(ok), detail)
        if a:
            con.execute("INSERT INTO alerts VALUES (?,?,?)", (t, a[0], a[1]))
    except Exception as exc:  # noqa: BLE001  the alert never stops the recording
        log(f"outside alert error: {exc}")
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
          f"{hb.get('free_gb')} GB free · outside alert {'on' if ALERT_FILE.exists() else 'off'} · v{hb.get('version')}")
    return 0 if ok else 1


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "run":
        run()
    elif cmd == "once":
        print(json.dumps(round_once(), indent=1))
    elif cmd == "alert-test":                       # one test note to the phone, recorded in today's file (the main Mac's gate reads it)
        now = int(time.time())
        res = alert("Ananta: worker alert test", "The worker Mac can now tell you when the main Mac or the site has been down for "
                                                 "10 minutes. Nothing to do.")
        c = db(now)
        c.execute("INSERT INTO alerts VALUES (?,?,?)", (now, "test", res))
        c.commit()
        c.close()
        print(res)
        sys.exit(0 if res == "sent" else 1)
    else:
        sys.exit(status())
