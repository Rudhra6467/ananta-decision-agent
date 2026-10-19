"""Real bid-ask for index options: the evidence that replaces the 0.4% half-spread guess in every options study (limitation 2, 19 Oct).

  python -m india.spreads sample        waits for 09:14 IST, then every minute until 15:31 IST snapshots the five-level order book of the
                                        near-the-money calls and puts (two nearest expiries) of NIFTY, BANKNIFTY, FINNIFTY, MIDCPNIFTY, and the
                                        far strikes the hedges use; stops cleanly when the Kite token is missing or expires
  python -m india.spreads once          one snapshot now (a market-hours probe)
  python -m india.spreads build         bronze snapshots -> silver/option_spreads (one row per contract per snapshot)
  python -m india.spreads table         measured half-spread by index, premium bucket, moneyness and time of day, next to the study assumption

GET /quote only (read side; india.kite has no order method). Up to 500 instruments a request, one request a minute: far inside Kite's limits.
Bronze: bronze/kite_depth/date=YYYY-MM-DD/HHMM.jsonl.gz, Kite's answer as given plus our snapshot time. Personal-use market data: raw rows
never leave the Mac (bronze is not synced); only the derived half-spread table is used by the studies.

Token timing: the token expires at 06:00 IST every day. A Toronto-morning sign-in expires the same Toronto evening (20:30 EDT / 19:30 EST), before
the next IST session opens (23:45 EDT / 22:45 EST). Depth capture therefore needs a sign-in after 20:30 EDT (19:30 EST) the evening before.
"""
from __future__ import annotations

import csv
import datetime as dt
import gzip
import io
import json
import sys
import time

import pandas as pd

from india import kite, paths

IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
NAMES = {"NIFTY": ("NSE:NIFTY 50", 50, 12), "BANKNIFTY": ("NSE:NIFTY BANK", 100, 10), "FINNIFTY": ("NSE:NIFTY FIN SERVICE", 50, 8),
         "MIDCPNIFTY": ("NSE:NIFTY MID SELECT", 25, 8)}          # (index quote key, strike step, strikes each side)
HEDGE_PCT = (0.97, 1.03, 0.95, 1.05)                               # the O-03/F02 hedge distances, both sides
START, END = dt.time(9, 14), dt.time(15, 31)
STUDY_HS_PCT, STUDY_HS_MIN = 0.004, 0.05


def _bronze_day(d: dt.date):
    p = paths.bronze("kite_depth") / f"date={d}"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _nfo(k: kite.Kite) -> list[dict]:
    today = dt.datetime.now(IST).date()
    p = paths.bronze("kite_instruments") / f"NFO_{today:%Y%m%d}.csv"
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(k.instruments("NFO"))
    return list(csv.DictReader(io.StringIO(p.read_text())))


def universe(k: kite.Kite) -> tuple[list[str], dict]:
    """The instruments to snapshot today, chosen from the index levels now: ATM +/- n strikes and the hedge strikes, two nearest expiries."""
    nfo = [r for r in _nfo(k) if r["segment"] == "NFO-OPT" and r["name"] in NAMES]
    spot = k.get("/quote/ltp", {"i": [v[0] for v in NAMES.values()]})
    today = dt.datetime.now(IST).date()
    keys, meta = [], {}
    for name, (ix, step, n) in NAMES.items():
        if ix not in spot:
            continue
        s = float(spot[ix]["last_price"])
        rows = [r for r in nfo if r["name"] == name and dt.date.fromisoformat(r["expiry"]) >= today]
        exps = sorted({r["expiry"] for r in rows})[:2]
        atm = round(s / step) * step
        want = {atm + i * step for i in range(-n, n + 1)} | {round(s * h / step) * step for h in HEDGE_PCT}
        for r in rows:
            if r["expiry"] in exps and float(r["strike"]) in want:
                key = f"NFO:{r['tradingsymbol']}"
                keys.append(key)
                meta[key] = {"name": name, "expiry": r["expiry"], "strike": float(r["strike"]), "type": r["instrument_type"], "lot": int(r["lot_size"]),
                             "spot_at_pick": s}
    return keys, meta


def snapshot(k: kite.Kite, keys: list[str], meta: dict) -> int:
    now = dt.datetime.now(IST)
    out = []
    for i in range(0, len(keys), 500):
        part = keys[i:i + 500] + ([v[0] for v in NAMES.values()] if i == 0 else [])
        q = k.get("/quote", {"i": part})
        for key, v in q.items():
            out.append({"snap": now.isoformat(timespec="seconds"), "key": key, **meta.get(key, {}), "q": v})
    p = _bronze_day(now.date()) / f"{now:%H%M}.jsonl.gz"
    with gzip.open(p, "at") as fh:
        for r in out:
            fh.write(json.dumps(r) + "\n")
    return len(out)


def sample(interval_s: int = 60) -> dict:
    try:
        k = kite.Kite(rate_per_s=1.0)
    except kite.NeedLogin as e:
        kite._ntfy("Option spreads not captured tonight: Kite sign-in needed after 20:30 Toronto (06:00 IST) for the IST session")
        return {"ok": False, "why": str(e)}
    while dt.datetime.now(IST).time() < START:
        time.sleep(20)
    if dt.datetime.now(IST).weekday() >= 5:
        return {"ok": True, "why": "weekend"}
    keys, meta = universe(k)
    n_snap, n_rows, fails = 0, 0, 0
    while dt.datetime.now(IST).time() <= END:
        t0 = time.time()
        try:
            n_rows += snapshot(k, keys, meta)
            n_snap += 1
        except kite.NeedLogin as e:
            return {"ok": False, "why": str(e), "snapshots": n_snap, "rows": n_rows}
        except Exception as e:  # a dropped answer costs one minute, not the day
            fails += 1
            print(f"snapshot failed: {type(e).__name__}: {e}", flush=True)
        if n_snap and n_snap % 60 == 0:  # re-centre the strikes each hour as the index moves
            try:
                keys, meta = universe(k)
            except Exception:
                pass
        time.sleep(max(1.0, interval_s - (time.time() - t0)))
    res = {"ok": True, "snapshots": n_snap, "rows": n_rows, "failed": fails, "instruments": len(keys)}
    with open(paths.manifest_dir() / "kite_depth.jsonl", "a") as fh:
        fh.write(json.dumps({"date": str(dt.datetime.now(IST).date()), **res}) + "\n")
    return res


def build() -> pd.DataFrame:
    rows = []
    for f in sorted(paths.bronze("kite_depth").glob("date=*/*.jsonl.gz")):
        with gzip.open(f, "rt") as fh:
            for line in fh:
                r = json.loads(line)
                q = r["q"]
                if "name" not in r:
                    continue
                d = q.get("depth") or {}
                b = (d.get("buy") or [{}])[0]
                a = (d.get("sell") or [{}])[0]
                bid, ask = float(b.get("price") or 0), float(a.get("price") or 0)
                rows.append({"snap": r["snap"], "name": r["name"], "expiry": r["expiry"], "strike": r["strike"], "type": r["type"], "lot": r["lot"],
                             "ltp": q.get("last_price"), "bid": bid, "ask": ask, "bid_qty": b.get("quantity"), "ask_qty": a.get("quantity"),
                             "bid5_qty": sum(x.get("quantity") or 0 for x in d.get("buy") or []), "ask5_qty": sum(x.get("quantity") or 0 for x in d.get("sell") or []),
                             "oi": q.get("oi"), "volume": q.get("volume"), "spot": r.get("spot_at_pick")})
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["snap"] = pd.to_datetime(df["snap"])
    t = df["snap"].dt.tz_convert(IST).dt.time
    df = df[(t >= dt.time(9, 15)) & (t <= dt.time(15, 30))].copy()  # probes outside the session (closed books) are kept in bronze, never measured
    ok = (df["bid"] > 0) & (df["ask"] > df["bid"])
    df["two_sided"] = ok
    df["mid"] = (df["bid"] + df["ask"]) / 2
    df["half_spread"] = (df["ask"] - df["bid"]).where(ok) / 2
    df["half_spread_pct"] = df["half_spread"] / df["mid"]
    df["moneyness"] = (df["strike"] / df["spot"] - 1).abs()
    df["dte"] = (pd.to_datetime(df["expiry"]) - df["snap"].dt.tz_localize(None).dt.normalize()).dt.days
    out = paths.data_dir() / "silver" / "option_spreads"
    out.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out / "spreads.parquet")
    return df


def table() -> pd.DataFrame:
    p = paths.data_dir() / "silver" / "option_spreads" / "spreads.parquet"
    if not p.exists():
        print("no spreads recorded yet: needs a Kite sign-in after 20:30 Toronto so the IST session is covered", flush=True)
        return pd.DataFrame()
    df = pd.read_parquet(p)
    df = df[df["two_sided"]]
    df["premium"] = pd.cut(df["mid"], [0, 2, 5, 20, 50, 150, 1e9], labels=["<2", "2-5", "5-20", "20-50", "50-150", "150+"])
    df["hour"] = df["snap"].dt.hour
    df["study_hs"] = (STUDY_HS_PCT * df["mid"]).clip(lower=STUDY_HS_MIN)
    g = df.groupby(["name", "premium"], observed=True).agg(n=("half_spread", "size"), hs_median=("half_spread", "median"), hs_p90=("half_spread", lambda x: x.quantile(0.9)),
                                                          hs_pct_median=("half_spread_pct", "median"), study_hs_median=("study_hs", "median")).reset_index()
    g["measured_over_study"] = g["hs_median"] / g["study_hs_median"]
    print(g.to_string(index=False), flush=True)
    g.to_csv(paths.data_dir() / "reports" / "option_spreads_table.csv", index=False)
    return g


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "table"
    if cmd == "sample":
        print(json.dumps(sample()), flush=True)
    elif cmd == "once":
        k = kite.Kite(rate_per_s=1.0)
        keys, meta = universe(k)
        print(json.dumps({"instruments": len(keys), "rows": snapshot(k, keys, meta)}), flush=True)
    elif cmd == "build":
        print(len(build()), "rows", flush=True)
    else:
        table()
