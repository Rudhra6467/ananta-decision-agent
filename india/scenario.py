"""Situation (scenario) table for the Scenario Playbook (registrations/sp1_v1.json): what Ananta knows about each index-day at each decision
point, raw values only (bucketing happens inside each walk-forward fold, on its training years). No outcomes are computed here.

  python -m india.scenario build     gold/scenario/index_states.parquet (one row per session x index, 2015-2023, silver only)
  python -m india.scenario check     leak audit: every overnight value is dated before the session, every opening value uses closed bars

Columns (all known at the decision time named in the column):
  overnight (before 09:15): us_qqq_ret and us_qqq_date (SP1 v2's US feature: Tiingo QQQ, last US session before the Indian date), prev_close, sma50, sma200, trend, atr14_prev (daily, from index day bars), vix_prev, us_spx_ret, us_ndx_ret,
      us_date (the US session used), usdinr_chg, brent_chg, fx_date, oil_date (NOT used by SP1: FRED publishes them days late),
      fii_long_share (participant OI, previous session), event_scheduled and event_recent (scheduled calendar events today / in the previous 3
      sessions: scheduled_dates()), expiry (that index's option expiries)
  opening: gap (09:15 open vs prev_close); for D1 (09:30), D2 (09:45), D3 (10:15): move_Dk (close of the bar ending at Dk vs the 09:15 open),
      breadth_Dk (last closed 5-minute bar of the eligible top 50, OC v1 rules), agree_Dk (both indices moved >= 0.05% the same way),
      or15_w, or30_w (range width) and or15_atr / or30_atr (width over atr14_prev)
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from india import ocstudy, paths

IDX = {"NIFTY": "NIFTY 50", "BANKNIFTY": "NIFTY BANK"}
DEC = {"D1": 14, "D2": 29, "D3": 59}          # last 1-minute bar closing at the decision time (09:30, 09:45, 10:15)
BREADTH_BAR = {"D1": 2, "D2": 5, "D3": 11}    # last 5-minute bar closed by then (09:25, 09:40, 10:10)
SCHEDULED = {"rbi_policy", "union_budget", "election"}


def _daily(name: str, raw: pd.DataFrame | None = None) -> pd.DataFrame:
    """Daily bars with ATR14 and the 50/200-day averages. raw: rows supplied by a registered holdout run (silver + sealed), else silver to 2023."""
    D = paths.data_dir()
    if raw is None:
        f = next(p for p in (D / "silver/kite_index/day").iterdir() if p.suffix == ".parquet")
        d = pd.read_parquet(f)
    else:
        d = raw
    d = d[d["index_name"] == name].copy()
    d["date"] = pd.to_datetime(d["date"]).dt.date
    if raw is None:
        d = d[d["date"] <= dt.date(2023, 12, 31)]
    d = d.sort_values("date").drop_duplicates("date", keep="last").reset_index(drop=True)
    pc = d["close"].shift(1)
    tr = np.maximum(d["high"], pc) - np.minimum(d["low"], pc)
    d["atr14"] = tr.rolling(14).mean()
    d["sma50"] = d["close"].rolling(50).mean()
    d["sma200"] = d["close"].rolling(200).mean()
    return d


def _macro() -> pd.DataFrame:
    D = paths.data_dir()
    f = next(p for p in (D / "silver/macro").iterdir() if p.suffix == ".parquet")
    m = pd.read_parquet(f)
    m["date"] = pd.to_datetime(m["date"]).dt.date
    return m.pivot_table(index="date", columns="series", values="value", aggfunc="last").sort_index()


def _last_before(series: pd.Series, day: dt.date) -> tuple[float, float, dt.date | None]:
    """value change of the latest observation strictly before `day` vs the observation before it."""
    s = series.dropna()
    s = s[s.index < day]
    if len(s) < 2:
        return np.nan, np.nan, None
    return float(s.iloc[-1]), float(s.iloc[-1] / s.iloc[-2] - 1), s.index[-1]


def scheduled_dates() -> set[dt.date]:
    """Sessions with a scheduled event (SP1 review fix 4): a date on the published RBI MPC, Union Budget or election-counting calendar,
    known before the session. Sources: calendar_*.json rows (verified, or DUPLICATE of a verified era row) and verified era rows marked
    known_beforehand = scheduled; first tradable session = event date. Surprise and off-cycle moves are excluded."""
    D = paths.data_dir()
    ev = pd.read_parquet(D / "silver/events/events.parquet")
    ev["fts"] = pd.to_datetime(ev["first_tradable_session"]).dt.date
    ev["ed"] = pd.to_datetime(ev["event_date"]).dt.date
    ev = ev[ev["category"].isin(SCHEDULED) & (ev["fts"] == ev["ed"])]
    ok = ev["status"].isin(["OFFICIAL", "TWO_SOURCES"])
    cal = ev["batch"].str.startswith("calendar_")
    era_ok = set(zip(ev.loc[~cal & ok, "category"], ev.loc[~cal & ok, "ed"]))
    a = ev[cal & ok & (ev["known_beforehand"] == "scheduled")]
    b = ev[cal & (ev["status"] == "DUPLICATE") & (ev["known_beforehand"] == "scheduled")]
    b = b[[(c, d) in era_ok for c, d in zip(b["category"], b["ed"])]]
    c = ev[~cal & ok & (ev["known_beforehand"] == "scheduled")]
    return set(a["fts"]) | set(b["fts"]) | set(c["fts"])


def build(src: dict | None = None, out_file: Path | None = None, from_date: dt.date | None = None) -> dict:
    """src (optional, a registered holdout run): days, specials, index (ocstudy.index_arrays), breadth (date-indexed b0..b11), participant_oi
    rows, index_day rows. Without src: silver and gold, 2015-2023. Same code either way."""
    D = paths.data_dir()
    src = src or {}
    days, specials = (src["days"], src["specials"]) if "days" in src else ocstudy._calendar()
    index = src["index"] if "index" in src else ocstudy.load_index()
    breadth = src["breadth"] if "breadth" in src else pd.read_parquet(D / "gold/studies/OC1_breadth.parquet").set_index("date")
    macro = _macro()
    us = pd.read_parquet(D / "silver/us/us_close.parquet")
    qqq = us[us["symbol"] == "QQQ"].dropna(subset=["ret"]).set_index("date")["ret"].sort_index()
    fii = src["participant_oi"] if "participant_oi" in src else pd.read_parquet(D / "silver/flows/participant_oi.parquet")
    fii = fii[fii["client_type"] == "FII"].copy()
    fii["date"] = pd.to_datetime(fii["date"]).dt.date
    fii["fii_long_share"] = fii["future_index_long"] / (fii["future_index_long"] + fii["future_index_short"])
    fii = fii.set_index("date")["fii_long_share"].sort_index()
    sched = scheduled_dates()
    fts_all = sorted(sched)
    fc = pd.read_parquet(next(p for p in (D / "silver/fo_calendar").iterdir() if p.suffix == ".parquet"))
    fc = fc[fc["instrument"] == "OPTIDX"]
    fc["expiry"] = pd.to_datetime(fc["expiry"]).dt.date
    expiry = {s: set(fc.loc[fc["symbol"] == s, "expiry"]) for s in IDX}
    pos = {d: i for i, d in enumerate(days)}
    nf, nb = index["NIFTY 50"], index["NIFTY BANK"]
    fi = {d: i for i, d in enumerate(nf["dates"])}
    bi = {d: i for i, d in enumerate(nb["dates"])}
    daily = {sym: _daily(name, src.get("index_day")).set_index("date") for sym, name in IDX.items()}
    vix_d = _daily("INDIA VIX", src.get("index_day")).set_index("date")["close"]
    rows = []
    for d in days:
        if d.year < 2015 or d in specials or d not in fi or d not in bi or (from_date is not None and d < from_date):
            continue
        if not (nf["ok"][fi[d]] and nb["ok"][bi[d]]):
            continue
        i = pos[d]
        prev = days[i - 1]
        prev3 = set(days[max(0, i - 3):i])
        spx, spx_r, us_d = _last_before(macro["SP500"], d)
        _, ndx_r, _ = _last_before(macro["NASDAQCOM"], d)
        q_prev = qqq[qqq.index < d]
        qqq_r, qqq_d = (float(q_prev.iloc[-1]), q_prev.index[-1]) if len(q_prev) else (np.nan, None)
        _, fx_r, fx_d = _last_before(macro["DEXINUS"], d)
        _, oil_r, oil_d = _last_before(macro["DCOILBRENTEU"], d)
        f_prev = fii[fii.index < d]
        recent = any(x in prev3 for x in fts_all)
        mv = {}
        for sym, name in IDX.items():
            a = index[name]
            r = fi[d] if name == "NIFTY 50" else bi[d]
            mv[sym] = (a["open"][r], a["close"][r], a["high"][r], a["low"][r])
        for sym, name in IDX.items():
            dd = daily[sym]
            if prev not in dd.index:
                continue
            p = dd.loc[prev]
            o, c, h, l = mv[sym]
            row = {"date": d, "index": sym, "prev_date": prev, "prev_close": float(p["close"]), "sma50": float(p["sma50"]), "sma200": float(p["sma200"]),
                   "atr14_prev": float(p["atr14"]), "vix_prev": float(vix_d.get(prev, np.nan)),
                   "us_qqq_ret": qqq_r, "us_qqq_date": qqq_d, "us_spx_ret": spx_r, "us_ndx_ret": ndx_r, "us_date": us_d, "usdinr_chg": fx_r, "fx_date": fx_d, "brent_chg": oil_r, "oil_date": oil_d,
                   "fii_long_share": float(f_prev.iloc[-1]) if len(f_prev) else np.nan, "fii_date": f_prev.index[-1] if len(f_prev) else None,
                   "event_scheduled": d in sched, "event_recent": recent, "expiry": d in expiry[sym],
                   "open": float(o[0]), "gap": float(o[0] / p["close"] - 1)}
            row["trend"] = "up" if p["close"] > p["sma50"] and p["close"] > p["sma200"] else ("down" if p["close"] < p["sma50"] and p["close"] < p["sma200"] else "mixed")
            for k in (15, 30):
                w = float(h[:k].max() - l[:k].min())
                row[f"or{k}_w"] = w
                row[f"or{k}_atr"] = w / float(p["atr14"]) if p["atr14"] == p["atr14"] and p["atr14"] > 0 else np.nan
            for dk, bar in DEC.items():
                row[f"move_{dk}"] = float(c[bar] / o[0] - 1)
                bo = breadth.loc[d, f"b{BREADTH_BAR[dk]}"] if d in breadth.index else np.nan
                row[f"breadth_{dk}"] = float(bo) if bo == bo else np.nan
                m1 = mv["NIFTY"][1][bar] / mv["NIFTY"][0][0] - 1
                m2 = mv["BANKNIFTY"][1][bar] / mv["BANKNIFTY"][0][0] - 1
                row[f"agree_{dk}"] = bool((m1 >= 0.0005 and m2 >= 0.0005) or (m1 <= -0.0005 and m2 <= -0.0005))
            rows.append(row)
    st = pd.DataFrame(rows)
    if out_file is not None:
        out_file.parent.mkdir(parents=True, exist_ok=True)
        st.to_parquet(out_file)
        return {"rows": len(st), "days": int(st["date"].nunique()) if len(st) else 0, "file": str(out_file)}
    out = D / "gold/scenario"
    out.mkdir(parents=True, exist_ok=True)
    st.to_parquet(out / "index_states.parquet")
    res = {"rows": len(st), "days": int(st["date"].nunique()), "first": str(st["date"].min()), "last": str(st["date"].max()),
           "missing_share": {c: round(float(st[c].isna().mean()), 4) for c in st.columns if st[c].dtype.kind == "f"}}
    (D / "manifests/scenario_build.json").write_text(json.dumps(res, indent=1, default=str))
    return res


def check() -> dict:
    """Leak audit on the built table."""
    D = paths.data_dir()
    st = pd.read_parquet(D / "gold/scenario/index_states.parquet")
    out = {}
    for col in ("us_qqq_date", "us_date", "fx_date", "oil_date", "fii_date", "prev_date"):
        x = st.dropna(subset=[col])
        out[f"{col}_before_session"] = bool((pd.to_datetime(x[col]).dt.date < x["date"]).all())
    out["no_2024_or_later"] = bool((pd.to_datetime(st["date"]).dt.year <= 2023).all())
    out["breadth_bars_close_by_decision"] = all(5 * BREADTH_BAR[k] + 5 <= DEC[k] + 1 for k in DEC)
    out["PASS"] = all(v for v in out.values())
    return out


if __name__ == "__main__":
    paths.ensure()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "build"
    print(json.dumps(build() if cmd == "build" else check(), indent=1, default=str))
