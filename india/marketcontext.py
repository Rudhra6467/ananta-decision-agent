"""The market-context feed (Madhav, 26 Oct 2026: "the market-context feed: rupee-dollar, FII flows, global cues ... can't read why a gap opened or why
the rupee's moving"). One small file, manifests/market_context.json, that says what the rupee, the dollar, crude, US yields, the US indices, the
two fear gauges and the institutions' flows did, each with its own as-of date and how late its source is.

  python -m india.marketcontext refresh   macro pull + silver (FRED, polite: 2 s apart), then build
  python -m india.marketcontext build     build manifests/market_context.json from what is already on disk

What it is for: EXPLAINING. Tested 26 Oct (XO1, FX1, FII1, DII1, TWT-H43): none of these predicts the Nifty. The words field says so every time, and nothing
here feeds a rule, a size or a pick.

Sources and their lag (said in words per series):
  rupee, same day   the Kite USDINR front-month future the recorder saves (bronze/kite_1m_fo/cds, live days only; the last candle of each session)
  rupee, FRED       DEXINUS: about a week behind; kept for the longer view
  dollar index, Brent, WTI, US 10-year and 2-year, S&P 500, Nasdaq, US VIX   FRED (silver/macro): each reading carries its own lag in days (Brent has run about a week behind)
  India VIX         the paper_context index reader (technicals.latest_index): the newest close
  FII / DII cash    the evening capture (manifests/fii_dii_cash.jsonl: NSE provisional, NSDL): the newest session
  GIFT Nifty        no free source
FRED's raw series stay on the Mac (their terms); this file holds derived readings only.
"""
from __future__ import annotations

import datetime as dt
import glob
import gzip
import json
import re
import sys

import pandas as pd

from india import paths

RULES = "marketcontext-v1-2026-10-26"
TESTED = ("Tested 26 Oct (studies XO1, FX1, FII1, DII1 and the crude card TWT-H43): none of these readings predicts what the Nifty does next. "
          "Use them to explain a move, never to trade.")
MACRO = {   # series id: (label, unit word, decimals, lag note)
    "DTWEXBGS": ("broad dollar index", "", 2, "FRED"),
    "DCOILBRENTEU": ("Brent crude", "dollars a barrel", 2, "FRED"),
    "DCOILWTICO": ("WTI crude", "dollars a barrel", 2, "FRED"),
    "DGS10": ("US 10-year yield", "%", 2, "FRED"),
    "DGS2": ("US 2-year yield", "%", 2, "FRED"),
    "SP500": ("S&P 500", "", 0, "FRED"),
    "NASDAQCOM": ("Nasdaq composite", "", 0, "FRED"),
    "VIXCLS": ("US VIX (fear gauge)", "", 2, "FRED"),
    "DEXINUS": ("USD/INR, FRED", "rupees per dollar", 2, "FRED"),
}
YIELD_SERIES = {"DGS10", "DGS2"}


def _out():
    return paths.manifest_dir() / "market_context.json"


def _pc(x: float | None) -> str:
    return "n/a" if x is None else f"{x * 100:+.1f}%"


def _dw(d) -> str:
    try:
        x = dt.date.fromisoformat(str(d)[:10])
        return f"{x:%a} {x.day} {x:%b}"
    except (TypeError, ValueError):
        return str(d)


def _reading(label: str, s: pd.Series, nd: int, lag: str, today: dt.date, unit: str = "", yield_pts: bool = False) -> dict:
    """The last value, the change against the previous observation and against five observations back, with its as-of date and lag in days."""
    s = s.dropna()
    if len(s) < 7:
        return {"label": label, "status": "too_short"}
    last, prev, five = float(s.iloc[-1]), float(s.iloc[-2]), float(s.iloc[-6])
    asof = pd.Timestamp(s.index[-1]).date()
    if yield_pts:
        ch1, ch5 = last - prev, last - five          # yields: moves are in percentage points
    else:
        ch1, ch5 = last / prev - 1, last / five - 1
    return {"label": label, "status": "ok", "as_of": str(asof), "lag_days": (today - asof).days, "value": round(last, nd), "unit": unit,
            "change_1": round(ch1, 4), "change_5": round(ch5, 4), "change_kind": "points" if yield_pts else "percent", "source": lag}


def _words(r: dict) -> str:
    if r.get("status") != "ok":
        return f"{r.get('label')}: no reading ({r.get('why') or r.get('status')})."
    if r["change_kind"] == "points":
        mv = f"{r['change_1']:+.2f} points on the day, {r['change_5']:+.2f} over five readings"
    else:
        mv = f"{_pc(r['change_1'])} on the day, {_pc(r['change_5'])} over five readings"
    val = f"{r['value']:,.{2 if abs(r['value']) < 1000 else 0}f}"
    lagw = "" if r.get("lag_days") is None else (", the latest FRED has" if r["lag_days"] <= 1 else f", {r['lag_days']} days behind today")
    return f"{r['label']} {val}{(' ' + r['unit']) if r['unit'] and r['unit'] != '%' else ('%' if r['unit'] == '%' else '')} on {_dw(r['as_of'])} ({mv}; {r['source']}{lagw})."


def macro_readings(today: dt.date | None = None) -> dict:
    today = today or dt.date.today()
    f = paths.data_dir() / "silver" / "macro" / "macro.parquet"
    if not f.exists():
        return {k: {"label": v[0], "status": "missing", "why": "macro table not built"} for k, v in MACRO.items()}
    m = pd.read_parquet(f)
    m["date"] = pd.to_datetime(m["date"])
    out = {}
    for sid, (label, unit, nd, lag) in MACRO.items():
        s = m[m["series"] == sid].drop_duplicates("date", keep="last").set_index("date")["value"].sort_index()
        out[sid] = _reading(label, s, nd, lag, today, unit, yield_pts=sid in YIELD_SERIES)
    return out


def _front_usdinr() -> tuple[str | None, list[list]]:
    """The newest USDINR monthly future's candles from the recorder's bronze files: one line per fetch (a growing window), the last line is the newest.
    Front month = the monthly contract (USDINR26OCTFUT) with the nearest expiry folder that has not passed, falling back to the newest file."""
    root = paths.bronze("kite_1m_fo") / "cds"
    cands = []
    for p in glob.glob(str(root / "*" / "USDINR*FUT.jsonl.gz")):
        name = p.rsplit("/", 1)[-1][: -len(".jsonl.gz")]
        if re.fullmatch(r"USDINR\d\d[A-Z]{3}FUT", name):
            cands.append((p.rsplit("/", 2)[-2], name, p))
    if not cands:
        return None, []
    cands.sort()
    today = dt.date.today().isoformat()
    live = [c for c in cands if c[0] >= today] or cands[-1:]
    folder, name, p = live[0]
    last = None
    with gzip.open(p, "rt") as fh:
        for line in fh:
            if line.strip():
                last = line
    j = json.loads(last) if last else {}
    return name, j.get("candles") or []


def rupee_same_day() -> dict:
    name, candles = _front_usdinr()
    if not candles:
        return {"label": "USD/INR, same day (Kite future)", "status": "missing", "why": "no USDINR futures candles recorded"}
    df = pd.DataFrame(candles, columns=["t", "o", "h", "l", "c", "v"])
    df["day"] = df["t"].str[:10]
    d = df.groupby("day").agg(close=("c", "last"), last_t=("t", "last")).reset_index()
    d = d[d["close"] > 0]
    if len(d) < 7:
        return {"label": "USD/INR, same day (Kite future)", "status": "too_short"}
    last, prev, five = float(d["close"].iloc[-1]), float(d["close"].iloc[-2]), float(d["close"].iloc[-6])
    asof = dt.date.fromisoformat(d["day"].iloc[-1])
    return {"label": "USD/INR, same day (Kite future)", "status": "ok", "contract": name, "as_of": str(asof), "last_candle": d["last_t"].iloc[-1],
            "lag_days": (dt.date.today() - asof).days, "value": round(last, 3), "unit": "rupees per dollar", "change_1": round(last / prev - 1, 4),
            "change_5": round(last / five - 1, 4), "change_kind": "percent",
            "source": f"Kite {name} future, last candle of each session (the future trades a little above spot, so read the move, not the level)"}


def india_vix() -> dict:
    try:
        from india import technicals
        v = technicals.latest_index(["INDIA VIX"]).get("INDIA VIX")
    except Exception as e:  # noqa: BLE001
        return {"label": "India VIX (fear gauge)", "status": "missing", "why": f"{type(e).__name__}: {e}"[:100]}
    if not v:
        return {"label": "India VIX (fear gauge)", "status": "missing", "why": "no rows"}
    asof = dt.date.fromisoformat(v["date"])
    return {"label": "India VIX (fear gauge)", "status": "ok", "as_of": v["date"], "lag_days": (dt.date.today() - asof).days, "value": round(v["close"], 2),
            "unit": "", "change_1": round(v["d1"], 4), "change_5": None, "change_kind": "percent", "source": "the newest daily close in Ananta's index data"}


def opening_gaps() -> dict:
    """Each index's newest session: the open against the previous close (the gap) and where it closed (26 Oct: Ask said "the facts record no
    gap and no opening price"). Daily rows through the paper_context reader; the open is Kite's first traded index value."""
    from india import technicals      # the logged paper_context reader, as for the VIX
    out = {}
    try:
        since = (dt.date.today() - dt.timedelta(days=20)).isoformat()
        df = technicals.index_rows(["NIFTY 50", "NIFTY BANK"], since).sort_values(["index_name", "date"])
    except Exception as e:  # noqa: BLE001
        return {"status": "missing", "why": f"{type(e).__name__}: {e}"[:100]}
    for nm, g in df.groupby("index_name"):
        g = g.dropna(subset=["close"])
        if len(g) < 2 or g["open"].iloc[-1] != g["open"].iloc[-1]:
            continue
        o, c, pc = float(g["open"].iloc[-1]), float(g["close"].iloc[-1]), float(g["close"].iloc[-2])
        out[nm] = {"date": str(pd.Timestamp(g["date"].iloc[-1]).date()), "prev_close": round(pc, 2), "open": round(o, 2), "close": round(c, 2),
                   "gap": round(o / pc - 1, 4), "open_to_close": round(c / o - 1, 4), "day": round(c / pc - 1, 4)}
    if not out:
        return {"status": "missing", "why": "no rows with an open"}
    return {"status": "ok", "rows": out, "as_of": max(v["date"] for v in out.values()),
            "source": "Ananta's daily index data (open = the first traded value; Kite)",
            "tested": "GP1 (26 Oct): a Nifty or Bank Nifty gap of 1% or more did not predict the rest of the day or week (inconclusive or rejected); on stocks a "
                      "2% gap-down was followed by a rebound in 2000-2017 that had nearly gone by 2021-2023 and cannot be bought at the open price"}


def valuation_latest() -> dict:
    """The Nifty 50, Nifty 500 and Bank Nifty P/E, P/B and dividend yield (NSE, published after each close) and where today sits in the pre-2024
    history (india/valuation.latest; 27 Oct, Madhav's yes: "my facts hold no PE or PB figure")."""
    try:
        from india import valuation
        rows = valuation.latest()
    except Exception as e:  # noqa: BLE001
        return {"status": "missing", "why": f"{type(e).__name__}: {e}"[:100]}
    if not rows:
        return {"status": "missing", "why": "no rows"}
    return {"status": "ok", "rows": rows, "as_of": max(v["date"] for v in rows.values()),
            "source": "NSE index P/E, P/B and dividend yield (niftyindices.com), published after each close; percentiles against 2024-free history only",
            "meaning": "pe_pctile 10 = today's P/E is higher than only 10% of past days on the same basis (cheap against that history); since 31 Mar 2021 "
                       "NSE uses consolidated earnings, so P/E and yield are compared with 2021-2023 only (a short history); P/B with 1999-2023",
            "tested": "the Nifty valuation study (VL1) is registered separately; until its result, a cheap or dear reading is context, not a signal"}


def flows_latest() -> dict:
    """The newest session's FII and DII cash (NSE provisional) and FPI exchange cash (NSDL), from the evening capture manifest."""
    f = paths.manifest_dir() / "fii_dii_cash.jsonl"
    if not f.exists():
        return {"status": "missing", "why": "no capture manifest"}
    best = {}
    for line in f.read_text().splitlines()[-400:]:
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if r.get("status") != 200:
            continue
        for row in r.get("rows") or []:
            cat, d = row.get("category"), str(row.get("date"))
            if cat in ("FII", "DII", "FPI_equity_exchange") and (cat not in best or d >= best[cat]["date"]):
                best[cat] = {"date": d, "buy_cr": row.get("buy_cr"), "sell_cr": row.get("sell_cr"), "net_cr": row.get("net_cr"), "source": r.get("source")}
    if not best:
        return {"status": "missing", "why": "no rows"}
    days = sorted({v["date"] for v in best.values()})
    return {"status": "ok", "as_of": days[-1], "lag_days": (dt.date.today() - dt.date.fromisoformat(days[-1])).days, "rows": best,
            "source": "NSE provisional FII/DII cash and NSDL FPI exchange cash, captured each evening; crore rupees, net = bought minus sold"}


def build() -> dict:
    paths.ensure()
    today = dt.date.today()
    macro = macro_readings(today)
    rupee = rupee_same_day()
    vix = india_vix()
    flows = flows_latest()
    gaps = opening_gaps()
    val = valuation_latest()
    lines = []
    if val.get("status") == "ok":
        bits = []
        for nm, v in val["rows"].items():
            if v.get("pe") is None:
                continue
            def ordn(x):
                n = int(x)
                return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"
            bits.append(f"{nm} P/E {v['pe']:.1f}" + (f" (higher than {v['pe_pctile']:.0f}% of 2021-2023 days, {ordn(v['pe_pctile'])} percentile)" if v.get("pe_pctile") is not None else "")
                        + (f", P/B {v['pb']:.2f}" if v.get("pb") is not None else "") + (f" ({ordn(v['pb_pctile'])} percentile since {v['pb_pctile_basis'][5:9]})" if v.get("pb_pctile") is not None and v.get("pb_pctile_basis") else "")
                        + (f", dividend yield {v['div_yield']:.2f}%" if v.get("div_yield") is not None else ""))
        if bits:
            lines.append(f"Valuation on {_dw(val['as_of'])}: " + "; ".join(bits) + ".")
    if gaps.get("status") == "ok":
        for nm, g in gaps["rows"].items():
            kind = "gap-up" if g["gap"] >= 0.0025 else "gap-down" if g["gap"] <= -0.0025 else "flat open"
            lines.append(f"{nm} on {_dw(g['date'])}: opened {g['open']:,.2f} against the previous close {g['prev_close']:,.2f} ({_pc(g['gap'])}, a {kind}), "
                         f"closed {g['close']:,.2f} ({_pc(g['open_to_close'])} from the open, {_pc(g['day'])} on the day).")
    if rupee.get("status") == "ok":
        w = "weaker (more rupees per dollar)" if rupee["change_1"] > 0 else "stronger"
        lines.append(f"The rupee, same day: USD/INR {rupee['value']:.2f} on {_dw(rupee['as_of'])} ({_pc(rupee['change_1'])} on the day, {w}; {_pc(rupee['change_5'])} over five sessions).")
    for sid in ("DTWEXBGS", "DCOILBRENTEU", "DGS10", "SP500", "NASDAQCOM", "VIXCLS"):
        lines.append(_words(macro[sid]))
    if vix.get("status") == "ok":
        lines.append(f"India VIX {vix['value']:.2f} on {_dw(vix['as_of'])} ({_pc(vix['change_1'])} on the day).")
    if flows.get("status") == "ok":
        r = flows["rows"]
        bits = [f"{k} {v['net_cr']:+,.0f} crore" for k, v in (("FII", r.get("FII")), ("DII", r.get("DII"))) if v]
        lines.append(f"Institutions on {_dw(flows['as_of'])} (cash, net): " + ", ".join(bits) + ".")
    lines.append("GIFT Nifty: no free source, so the pre-open signal is not available.")
    explains = []
    if rupee.get("status") == "ok" and abs(rupee["change_1"]) >= 0.003:
        explains.append(f"The rupee moved {_pc(rupee['change_1'])} against the dollar on {_dw(rupee['as_of'])}: a large day for the currency.")
    sp, nq = macro.get("SP500", {}), macro.get("NASDAQCOM", {})
    if sp.get("status") == "ok" and abs(sp["change_1"]) >= 0.01:
        explains.append(f"The S&P 500 moved {_pc(sp['change_1'])} on {_dw(sp['as_of'])}: a global cue that can show up as a gap at the Indian open.")
    if macro.get("DCOILBRENTEU", {}).get("status") == "ok" and abs(macro["DCOILBRENTEU"]["change_1"]) >= 0.02:
        explains.append(f"Brent moved {_pc(macro['DCOILBRENTEU']['change_1'])}: India imports most of its oil, so crude moves its import bill and the rupee.")
    if not explains:
        explains.append("No single reading made an unusually large move on its latest day.")
    out = {"rules": RULES, "built_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "status": "ok",
           "rupee_same_day": rupee, "macro": macro, "india_vix": vix, "flows": flows, "opening_gaps": gaps, "valuation": val,
           "gift_nifty": {"status": "missing", "why": "no free source"},
           "words": " ".join(lines), "explains": explains, "tested": TESTED,
           "how_to_say_it": ("Give each reading with its as-of date; the macro series are FRED and lag the Indian open by a day or more, so say 'as of' and never "
                             "present them as live. The rupee same-day reading is the Kite future's last candle. A reading explains a move, it does not predict one: say the "
                             "tested line when asked what to do about it. GIFT Nifty is not available.")}
    _out().write_text(json.dumps(out, indent=1, default=str))
    return out


def section() -> dict:
    """For the read model: the file as built (rebuilt when older than six hours)."""
    p = _out()
    j = None
    if p.exists():
        try:
            j = json.loads(p.read_text())
        except ValueError:
            j = None
    stale = j is None or (dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(j["built_at"])).total_seconds() > 6 * 3600
    if stale:
        j = build()
    return j


def refresh() -> dict:
    from india import catalog, macro

    macro.pull()
    s = macro.silver()
    catalog.heartbeat("macro.silver", True, "")
    return {"macro": s, "context": build()["words"][:200]}


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "build"
    if cmd == "refresh":
        print(json.dumps(refresh(), default=str))
    else:
        j = build()
        print(j["words"])
        print(j["explains"])
