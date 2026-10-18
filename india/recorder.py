"""The option recorder: every evening, 1-minute candles for the live NIFTY and BANKNIFTY contracts near the money, plus the two
indices and India VIX, before the contracts expire and Kite forgets them. This is the only way to build intraday option history
from free sources (I0 registration; library O-01..O-04).

  python -m india.recorder run
What it fetches each day: for each index, the two nearest expiries; strikes within BAND steps of the at-the-money strike (NIFTY
step 50, BANKNIFTY step 100); calls and puts; the nearest two futures; the index and VIX at 1 minute. Kite serves up to 30 days of
1-minute candles per request, so a contract listed weeks ago gets its whole life on the first evening it is seen. Rows go to
bronze/kite_1m_fo/<expiry>/<tradingsymbol>.jsonl.gz, one line per fetch window, exactly as Kite answered; manifests/kite_1m_fo.jsonl
has one line per window. Re-fetching the same window on a later day is deliberate (the last window is still growing); the silver
step keeps the latest fetch per candle.
"""
from __future__ import annotations

import csv
import datetime as dt
import gzip
import io
import json
import sys
import time

from india import catalog, kite, paths

BAND = {"NIFTY": 20, "BANKNIFTY": 15}
STEP = {"NIFTY": 50, "BANKNIFTY": 100}
INDEX_TOKEN = {"NIFTY": "NIFTY 50", "BANKNIFTY": "NIFTY BANK"}
EXTRA_INDICES = ("INDIA VIX", "NIFTY 50", "NIFTY BANK", "NIFTY FIN SERVICE", "NIFTY MID SELECT")


def _nfo(k: kite.Kite) -> list[dict]:
    today = dt.date.today()
    p = paths.bronze("kite_instruments") / f"NFO_{today:%Y%m%d}.csv"
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(k.instruments("NFO"))
    return list(csv.DictReader(io.StringIO(p.read_text())))


def _nse_index_tokens(k: kite.Kite) -> dict[str, int]:
    today = dt.date.today()
    p = paths.bronze("kite_instruments") / f"NSE_{today:%Y%m%d}.csv"
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(k.instruments("NSE"))
    return {r["tradingsymbol"]: int(r["instrument_token"]) for r in csv.DictReader(io.StringIO(p.read_text())) if r.get("segment") == "INDICES"}


def _last_close(k: kite.Kite, token: int) -> float:
    today = dt.date.today()
    c = k.historical(token, "day", today - dt.timedelta(days=10), today)
    return float(c[-1][4])


def _fetch(k: kite.Kite, token: int, days_back: int) -> list[list]:
    today = dt.date.today()
    return k.historical(token, "minute", today - dt.timedelta(days=days_back), today)


def run(days_back: int = 29) -> dict:
    paths.ensure()
    k = kite.Kite()
    nfo = _nfo(k)
    idx = _nse_index_tokens(k)
    today = dt.date.today()
    picks: list[tuple[str, int, str]] = []  # (tradingsymbol, token, folder)
    for name in BAND:
        spot = _last_close(k, idx[INDEX_TOKEN[name]])
        atm = round(spot / STEP[name]) * STEP[name]
        rows = [r for r in nfo if r["name"] == name and r["expiry"] >= (today - dt.timedelta(days=1)).isoformat()]  # yesterday's expiry too: a contract may still be served for a few hours after it expires
        expiries = sorted({r["expiry"] for r in rows if r["instrument_type"] in ("CE", "PE")})[:3]
        for r in rows:
            if r["instrument_type"] in ("CE", "PE") and r["expiry"] in expiries and abs(float(r["strike"]) - atm) <= BAND[name] * STEP[name]:
                picks.append((r["tradingsymbol"], int(r["instrument_token"]), r["expiry"]))
        futs = sorted((r for r in rows if r["instrument_type"] == "FUT"), key=lambda r: r["expiry"])[:2]
        picks.extend((r["tradingsymbol"], int(r["instrument_token"]), r["expiry"]) for r in futs)
    for name in EXTRA_INDICES:
        if name in idx:
            picks.append((name, idx[name], "indices"))
    man = paths.manifest_dir() / "kite_1m_fo.jsonl"
    n = rows = 0
    t0 = time.time()
    stopped = ""
    for sym, tok, folder in picks:
        try:
            candles = _fetch(k, tok, days_back)
        except kite.NeedLogin as exc:
            stopped = str(exc)
            break
        except Exception as exc:  # one bad contract must not stop the evening
            with man.open("a") as fh:
                fh.write(json.dumps({"symbol": sym, "token": tok, "date": today.isoformat(), "status": f"error {type(exc).__name__}"}) + "\n")
            continue
        out = paths.bronze("kite_1m_fo") / folder / f"{sym}.jsonl.gz"
        out.parent.mkdir(parents=True, exist_ok=True)
        rec = {"symbol": sym, "token": tok, "interval": "minute", "start": (today - dt.timedelta(days=days_back)).isoformat(),
               "end": today.isoformat(), "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "n": len(candles), "status": "ok"}
        with gzip.open(out, "at") as gz:
            gz.write(json.dumps({**rec, "candles": candles}) + "\n")
        with man.open("a") as fh:
            fh.write(json.dumps(rec) + "\n")
        n += 1
        rows += len(candles)
    res = {"date": today.isoformat(), "contracts": len(picks), "fetched": n, "rows": rows, "calls": k.calls, "seconds": round(time.time() - t0), "stopped": stopped}
    catalog.heartbeat("recorder.run", not stopped, json.dumps(res))
    print(res, flush=True)
    return res


if __name__ == "__main__":
    run()
