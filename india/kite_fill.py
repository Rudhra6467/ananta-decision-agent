"""Background stock-candle fills from Kite (25 Oct 2026 audit: stock minute history and 5-minute gaps), polite to the live jobs.

  python -m india.kite_fill            the plan below, resumable (windows already in the manifests are skipped)
  python -m india.kite_fill status     windows and rows fetched so far per step -> manifests/kite_fill.json

The plan, in order:
  1. 1-minute candles for the Nifty 50, the last 60 days (proves the path)
  2. 5-minute candles 2015 onward for every Nifty Total Market stock (Nifty 500 plus about 250 smaller names; fills names the Nifty 500
     backfill never had, e.g. PC Jeweller, and brings every series up to date)
  3. 1-minute candles for the Nifty 50, 2015 to 60 days ago
  4. 1-minute candles for the rest of the Nifty 100, 2015 onward
Rules: 2 requests a second (Kite allows 3; the live jobs keep the rest), no request while an India job other than the web app is running, and
none inside the live jobs' Kite windows (Toronto): 12:20-13:10 (noon recorder) and 18:50-02:45 (evening job, token expiry, sign-in, paper,
spreads, the SP1 opening window, nightly). If the token is dead the step stops and the driver waits for the next automatic sign-in.
Read-only data calls only (india/kite.py allows no order call). Bronze stays as Kite answered: bronze/kite_minute/<SYM>.jsonl.gz and
bronze/kite_5m/<SYM>.jsonl.gz; silver for stock minutes is not built yet (2024+ rows would go under sealed/silver, as for the 5-minute series).
"""
from __future__ import annotations

import csv
import datetime as dt
import io
import json
import subprocess
import sys
import time
from zoneinfo import ZoneInfo

from india import kite_backfill, paths

TOR = ZoneInfo("America/Toronto")
RATE = 2.0
# Toronto clock. 18:50-02:45 covers the evening job, the token's expiry (06:00 IST = 20:30 EDT / 19:30 EST: a request on a dead token would make
# india/kite.py sign in again, outside the schedule), the 21:40 sign-in, paper, spreads, the SP1 opening window and the nightly build.
QUIET = [((12, 20), (13, 10)), ((18, 50), (24, 0)), ((0, 0), (2, 45))]
SERVICES = ("com.ananta.india.web",)
START = dt.date(2015, 1, 1)


def in_quiet(now: dt.datetime) -> bool:
    """True inside a live job's Kite window (Toronto clock)."""
    hm = (now.hour, now.minute)
    return any(a <= hm < b for a, b in QUIET)


def india_job_running(text: str | None = None) -> bool:
    """True when `launchctl list` shows a running India job (a PID in the first column), the web app excepted."""
    if text is None:
        try:
            text = subprocess.run(["launchctl", "list"], capture_output=True, text=True, timeout=20).stdout
        except Exception:
            return False
    for line in text.splitlines():
        parts = line.split("\t")
        if len(parts) == 3 and parts[2].startswith("com.ananta.india.") and parts[2] not in SERVICES and parts[0].strip() not in ("-", ""):
            return True
    return False


class Guard:
    def __init__(self, log=print):
        self.log = log
        self._checked = 0.0
        self._busy = False

    def __call__(self) -> bool:
        while True:
            now = dt.datetime.now(TOR)
            if time.time() - self._checked > 60:
                self._busy = india_job_running()
                self._checked = time.time()
            if not in_quiet(now) and not self._busy:
                return True
            time.sleep(60)
            self._checked = 0.0


def _list(name: str) -> list[str]:
    lst = sorted(paths.bronze("indices").glob(f"{name}_*.csv"))
    if not lst:
        return []
    return [r["Symbol"].strip() for r in csv.DictReader(io.StringIO(lst[-1].read_text(encoding="utf-8", errors="replace"))) if r.get("Symbol")]


def plan(today: dt.date | None = None) -> list[dict]:
    today = today or dt.date.today()
    n50 = _list("nifty50")
    n100 = [s for s in _list("nifty100") if s not in set(n50)]
    total = _list("niftytotalmarket") or _list("nifty500")
    recent = today - dt.timedelta(days=60)
    return [
        {"step": "1 minute, Nifty 50, last 60 days", "interval": "minute", "symbols": n50, "start": recent, "end": today},
        {"step": "2 five-minute, Nifty Total Market, 2015 on", "interval": "5minute", "symbols": total, "start": START, "end": today},
        {"step": "3 minute, Nifty 50, 2015 to 60 days ago", "interval": "minute", "symbols": n50, "start": START, "end": recent - dt.timedelta(days=1)},
        {"step": "4 minute, rest of the Nifty 100, 2015 on", "interval": "minute", "symbols": n100, "start": START, "end": today},
    ]


def _status_path():
    return paths.manifest_dir() / "kite_fill.json"


def main(log=print) -> None:
    paths.ensure()
    g = Guard(log)
    state = json.loads(_status_path().read_text()) if _status_path().exists() else {}
    for p in plan():
        while True:
            g()
            try:
                res = kite_backfill.run("-", p["interval"], p["start"], p["end"], rate=RATE, guard=g, symbols=p["symbols"])
            except Exception as e:  # one bad answer must not end a long fill; wait and resume (finished windows are skipped)
                res = {"stopped": f"{type(e).__name__}: {str(e)[:200]}"}
            state[p["step"]] = {**{k: v for k, v in res.items()}, "at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                                "symbols": len(p["symbols"]), "from": str(p["start"]), "to": str(p["end"])}
            _status_path().write_text(json.dumps(state, indent=1, default=str))
            stop = str(res.get("stopped", ""))
            if not stop:
                break
            log(f"{p['step']}: stopped ({stop}); waiting 30 minutes")
            time.sleep(1800)   # a dead token is renewed only by the scheduled automatic sign-in (21:40 Toronto); this driver never signs in


if __name__ == "__main__":
    if sys.argv[1:2] == ["status"]:
        print(_status_path().read_text() if _status_path().exists() else "{}")
    else:
        main()
