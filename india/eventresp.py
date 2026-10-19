"""Market response to registered events (Market Brain layer 2), measured from the lake only. HISTORICAL OBSERVATION, not a rule score.

  python -m india.eventresp build     gold/event_response/response.parquet (long: event x instrument x window) and manifests/event_response.json
  python -m india.eventresp report    registrations/event_response.md: per event, the index, VIX, sector and macro reaction table

Windows, relative to the event's first tradable session t0 (close-to-close against the close before t0 unless noted):
  pre5 (t0-6 .. t0-1), gap (open t0 / close t0-1), m5 / m15 / m30 (09:20 / 09:30 / 09:45 against the close t0-1; index minutes from 2015),
  d0 (close t0), d1, d3, d5, d10, d20 and d60, d120, d250 (permanence). Sectors also relative to Nifty 50. Macro (FRED, US-dated) uses the last
  value on or before each IST date, so a US close on date D counts as known before the IST open of D+1. Breadth: share of the liquidity top 500
  (as of t0-1) that closed up on t0.
Only OFFICIAL / TWO_SOURCES events with t0 before 2024 are measured: holdout-era reactions stay sealed until the one-time holdout run.
Date sanity (a check, not evidence): the percentile of Nifty's |d0| and |gap| against the previous 250 sessions; a 'surprise' event on a quiet
day is listed for a second look at its date.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from india import paths

D = paths.data_dir()
WIN_D = {"d0": 0, "d1": 1, "d3": 3, "d5": 5, "d10": 10, "d20": 20, "d60": 60, "d120": 120, "d250": 250}
CORE = ["NIFTY 50", "NIFTY BANK", "INDIA VIX", "NIFTY MIDCAP 100", "NIFTY SMLCAP 100"]
SECTORS = ["NIFTY IT", "NIFTY AUTO", "NIFTY FMCG", "NIFTY PHARMA", "NIFTY METAL", "NIFTY ENERGY", "NIFTY OIL AND GAS", "NIFTY REALTY", "NIFTY PSU BANK",
           "NIFTY PVT BANK", "NIFTY FIN SERVICE", "NIFTY MEDIA", "NIFTY INFRA", "NIFTY CONSUMPTION", "NIFTY CPSE", "NIFTY PSE", "NIFTY COMMODITIES",
           "NIFTY HEALTHCARE", "NIFTY CONSR DURBL", "NIFTY IND DEFENCE", "NIFTY CAPITAL MKT"]
MACRO = {"USDINR": "DEXINUS", "BRENT": "DCOILBRENTEU", "US10Y": "DGS10", "USVIX": "VIXCLS", "SP500": "SP500", "NASDAQ": "NASDAQCOM"}
LEVEL_DIFF = {"US10Y"}  # changes in percentage points, not returns


def _events() -> pd.DataFrame:
    ev = pd.read_parquet(D / "silver/events/events.parquet")
    ev = ev[ev["status"].isin(["OFFICIAL", "TWO_SOURCES"]) & ev["era"].isin(["dev", "validation"])].copy()
    ev["t0"] = pd.to_datetime(ev["first_tradable_session"])
    return ev[ev["t0"] < "2024-01-01"]


def build() -> dict:
    ev = _events()
    day = pd.read_parquet(D / "silver/kite_index/day/day.parquet")
    day["date"] = pd.to_datetime(day["date"])
    day = day[day["index_name"].isin(CORE + SECTORS)].drop_duplicates(["index_name", "date"], keep="last")
    C = day.pivot(index="date", columns="index_name", values="close").sort_index()
    O = day.pivot(index="date", columns="index_name", values="open").reindex(C.index)
    mins = duckdb.connect().execute(
        f"select index_name, ts, close from read_parquet('{D}/silver/kite_index/minute/year=*/part.parquet') "
        f"where index_name in ('NIFTY 50','NIFTY BANK','INDIA VIX') and strftime(ts, '%H:%M') in ('09:19','09:29','09:44')").df()
    mins["date"] = pd.to_datetime(mins["ts"]).dt.normalize()
    mins["slot"] = pd.to_datetime(mins["ts"]).dt.strftime("%H:%M").map({"09:19": "m5", "09:29": "m15", "09:44": "m30"})
    mac = pd.read_parquet(next(p for p in (D / "silver/macro").iterdir() if p.suffix == ".parquet"))
    mac["date"] = pd.to_datetime(mac["date"])
    M = mac[mac["series"].isin(MACRO.values())].pivot_table(index="date", columns="series", values="value").sort_index().ffill()
    u = pd.read_parquet(D / "gold/universe/u_liq_in.parquet", columns=["date", "symbol", "top500"])
    u["date"] = pd.to_datetime(u["date"])
    cm_files = str(D / "silver/cm_bhavcopy/year=*/part.parquet")
    con = duckdb.connect()
    rows, sanity = [], []
    idx = C.index
    for e in ev.itertuples():
        i = idx.searchsorted(e.t0)
        if i >= len(idx) or idx[i] != e.t0 or i < 6:
            sanity.append({"event_id": e.event_id, "problem": "t0 not in the index calendar"})
            continue
        prev = idx[i - 1]

        def put(inst, kind, win, val, rel=None, res="daily"):
            if val is not None and val == val:
                rows.append({"event_id": e.event_id, "t0": e.t0, "instrument": inst, "kind": kind, "window": win, "value": float(val),
                             "rel_nifty": None if rel is None or rel != rel else float(rel), "resolution": res})
        for inst in [c for c in CORE + SECTORS if c in C]:
            kind = "index" if inst in CORE else "sector"
            c0 = C[inst].iloc[i - 1]
            if not c0 == c0:
                continue
            put(inst, kind, "pre5", c0 / C[inst].iloc[i - 6] - 1)
            put(inst, kind, "gap", O[inst].iloc[i] / c0 - 1, (O[inst].iloc[i] / c0 - 1) - (O["NIFTY 50"].iloc[i] / C["NIFTY 50"].iloc[i - 1] - 1) if kind == "sector" else None)
            for w, n in WIN_D.items():
                if i + n < len(idx):
                    r = C[inst].iloc[i + n] / c0 - 1
                    rn = C["NIFTY 50"].iloc[i + n] / C["NIFTY 50"].iloc[i - 1] - 1
                    put(inst, kind, w, r, r - rn if kind == "sector" else None)
        mm = mins[mins["date"] == e.t0]
        for r in mm.itertuples():
            c0 = C[r.index_name].iloc[i - 1]
            put(r.index_name, "index", r.slot, r.close / c0 - 1, res="minute")
        for name, s in MACRO.items():
            if s not in M:
                continue
            ser = M[s]
            base = ser.asof(prev)
            for w, n in {"d0": 0, "d1": 1, "d5": 5, "d20": 20}.items():
                if i + n < len(idx):
                    v = ser.asof(idx[i + n])
                    put(name, "macro", w, (v - base) if name in LEVEL_DIFF else (v / base - 1 if base else None))
        top = u[(u["date"] == prev) & u["top500"]]["symbol"]
        if len(top):
            b = con.execute(f"select symbol, close, prev_close from read_parquet('{cm_files}') where date = ? and series = 'EQ'", [e.t0.date()]).df()
            b = b[b["symbol"].isin(set(top)) & (b["prev_close"] > 0)]
            if len(b):
                put("BREADTH_TOP500", "breadth", "d0", float((b["close"] > b["prev_close"]).mean()))
        # date sanity: how unusual was Nifty's day
        n50 = C["NIFTY 50"]
        r = n50.pct_change()
        g = (O["NIFTY 50"] / n50.shift(1) - 1)
        hist = r.iloc[max(0, i - 250):i].abs().dropna()
        ghist = g.iloc[max(0, i - 250):i].abs().dropna()
        pr = float((hist < abs(r.iloc[i])).mean()) if len(hist) else None
        pg = float((ghist < abs(g.iloc[i])).mean()) if len(ghist) else None
        quiet = pr is not None and pr < 0.6 and (pg or 0) < 0.6
        sanity.append({"event_id": e.event_id, "t0": str(e.t0.date()), "nifty_d0_pctile": pr, "nifty_gap_pctile": pg, "known_beforehand": e.known_beforehand,
                       "second_look": bool(quiet and e.known_beforehand == "surprise")})
    con.close()
    df = pd.DataFrame(rows)
    out = D / "gold" / "event_response"
    out.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out / "response.parquet")
    s = pd.DataFrame(sanity)
    s.to_parquet(out / "date_sanity.parquet")
    summ = {"at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "events_measured": int(df["event_id"].nunique()) if len(df) else 0,
            "rows": len(df), "minute_windows": int((df["resolution"] == "minute").sum()) if len(df) else 0,
            "second_look": s[s.get("second_look", False) == True]["event_id"].tolist() if len(s) and "second_look" in s else [],
            "problems": s[s.get("problem").notna()]["event_id"].tolist() if len(s) and "problem" in s else []}
    (paths.manifest_dir() / "event_response.json").write_text(json.dumps(summ, indent=1, default=str))
    return summ


def report() -> None:
    df = pd.read_parquet(D / "gold/event_response/response.parquet")
    ev = pd.read_parquet(D / "silver/events/events.parquet").set_index("event_id")
    san = pd.read_parquet(D / "gold/event_response/date_sanity.parquet").set_index("event_id")
    L = ["# Event responses (historical observation, measured from the lake)", "",
         "Generated by `python -m india.eventresp report`. Returns against the close before the first tradable session. Sectors: return minus Nifty 50. "
         "This describes what happened; it is not evidence that the event caused it (confounders are listed per event). 2024+ events are not measured "
         "here (holdout).", ""]
    for eid, x in df.groupby("event_id", sort=False):
        e = ev.loc[eid]
        L += [f"## {e['first_tradable_session']}: {e['title']} ({e['category']}, {e['known_beforehand'] or 'unknown'})", "",
              f"Public {e['public_time_ist'] or 'time unknown'}; {e['timing_note'] or ''}. Confounders: {', '.join(json.loads(e['confounders'])) or 'none named'}; "
              f"same session: {len(json.loads(e['same_session_events']))} other registered event(s). Date check: Nifty move percentile "
              f"{san.loc[eid, 'nifty_d0_pctile'] if eid in san.index else '?'}.", ""]
        core = x[x["kind"].isin(["index"])].pivot_table(index="instrument", columns="window", values="value")
        cols = [c for c in ("pre5", "gap", "m5", "m15", "m30", "d0", "d1", "d5", "d20", "d60", "d250") if c in core]
        if len(core):
            L += [(core[cols] * 100).round(2).to_markdown(), ""]
        sec = x[x["kind"] == "sector"].pivot_table(index="instrument", columns="window", values="rel_nifty")
        if len(sec) and "d5" in sec:
            s5 = (sec["d5"] * 100).round(2).sort_values()
            L += [f"Sectors vs Nifty, 5 sessions: weakest {', '.join(f'{k} {v:+.1f}%' for k, v in s5.head(3).items())}; strongest "
                  f"{', '.join(f'{k} {v:+.1f}%' for k, v in s5.tail(3)[::-1].items())}", ""]
        mac = x[x["kind"] == "macro"].pivot_table(index="instrument", columns="window", values="value")
        if len(mac):
            L += ["Macro over the same windows (US10Y in percentage points, others as returns): " + "; ".join(
                f"{k} d5 {v:+.3f}" if k == "US10Y" else f"{k} d5 {v * 100:+.1f}%" for k, v in mac.get("d5", pd.Series(dtype=float)).dropna().items()), ""]
    Path(__file__).resolve().parent.joinpath("registrations", "event_response.md").write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    paths.ensure()
    if (sys.argv[1] if len(sys.argv) > 1 else "build") == "build":
        print(json.dumps(build(), indent=1, default=str))
    else:
        report()
