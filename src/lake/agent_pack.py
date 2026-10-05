"""The lake -> agent hand-off (Madhav 2026-10-05: "the agent has to be sure of the added 120 coins ... integration and
coordination between the database and the agent").

The Jarvis service has no Parquet/DuckDB tools and must never read research files at decision time, so after each lake update
this writes a small, plain pack the agent reads with the standard library:

  ~/ananta_lake/agent/daily.sqlite    bars (coin, t, o, h, l, c, v, qv, tbv): complete UTC days for all 120 coins
                                      funding (coin, t, funding) and futures (coin, t, oi_value, top_ls, ls, taker_ls)
  ~/ananta_lake/agent/universe.json   one card per coin: tiers, what Ananta does with it (live watch / paper tier / research
                                      only), history and quality, costs, NDAX availability, futures coverage, current numbers,
                                      and the research verdicts that apply to its tiers

  python -m src.lake.cli pack        (the weekly lake job runs it after the update)
"""
from __future__ import annotations

import json
import math
import sqlite3
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

from src.lake import root

LAB10 = ["BTC", "ETH", "SOL", "ADA", "DOGE", "AVAX", "BCH", "LINK", "LTC", "XRP"]
T30_RENAMED = {"MATIC": "POL", "FTM": "S", "RNDR": "RENDER"}
MEASURED_HALF_SPREAD = {"BTC": 0.00178, "ETH": 0.00084, "SOL": 0.00289, "ADA": 0.00273, "DOGE": 0.00307,
                        "AVAX": 0.00370, "BCH": 0.00400, "LINK": 0.00341, "LTC": 0.00334, "XRP": 0.00251}
NDAX_FEE = 0.002
DAY = 86400

# What the reviews on the lake found, per tier (the results files hold the numbers; these lines are what the agent says).
RESEARCH = [
    {"id": "R15", "doc": "docs/research/REVIEW_15_RESULTS.md", "idea": "T3 trend portfolio",
     "LAB10": "PASS", "TOP30": "PASS", "ALL": "FAIL (only cut losses: -14% vs -66% holding, 2024-26)"},
    {"id": "R15", "doc": "docs/research/REVIEW_15_RESULTS.md", "idea": "H07 short dip trade",
     "LAB10": "INSUFFICIENT (too few events)", "TOP30": "PASS", "ALL": "FAIL"},
    {"id": "R15", "doc": "docs/research/REVIEW_15_RESULTS.md", "idea": "Madhav's reads M2a/M3a/M2a-G",
     "LAB10": "NOT SUPPORTED", "TOP30": "NOT SUPPORTED", "ALL": "NOT SUPPORTED"},
    {"id": "R15", "doc": "docs/research/REVIEW_15_RESULTS.md", "idea": "Madhav's read M1a (capitulation)",
     "LAB10": "INSUFFICIENT", "TOP30": "INSUFFICIENT", "ALL": "SUPPORTED, right on the bar (3 recent events)"},
    {"id": "R16", "doc": "docs/research/REVIEW_16_RESULTS.md", "idea": "Zones: new swing zones and the 200-day average hold more than random",
     "LAB10": "new swing PASS, 200-day just under the bar", "TOP30": "both PASS", "ALL": "both PASS (z 4.4)"},
    {"id": "R16", "doc": "docs/research/REVIEW_16_RESULTS.md", "idea": "Zones: overlapping (confluence) zones",
     "LAB10": "FAIL", "TOP30": "FAIL", "ALL": "FAIL (7-9 points better than random, under the 8-point bar)"},
    {"id": "R16", "doc": "docs/research/REVIEW_16_RESULTS.md", "idea": "Inside a zone: market allowed (BTC above its 50-day) separates held from broken",
     "LAB10": "PASS", "TOP30": "PASS", "ALL": "PASS"},
    {"id": "R17", "doc": "docs/research/REVIEW_17_RESULTS.md", "idea": "Relative strength vs BTC as a filter on T3",
     "LAB10": "hurts", "TOP30": "FAIL (hurts in both periods)", "ALL": "hurts"},
    {"id": "R17", "doc": "docs/research/REVIEW_17_RESULTS.md", "idea": "Market breadth as a filter on T3",
     "LAB10": "trade-off", "TOP30": "FAIL: much better 2024-26, much worse 2018-23", "ALL": "trade-off"},
    {"id": "R18", "doc": "docs/research/REVIEW_18_RESULTS.md", "idea": "Stops: structural (1 ATR under the 10-day low) vs tight 3%",
     "LAB10": "structural better", "TOP30": "structural better; the dip trade is best with no stop", "ALL": "structural better"},
    {"id": "R18", "doc": "docs/research/REVIEW_18_RESULTS.md", "idea": "25% disaster stop on T3",
     "LAB10": "no effect", "TOP30": "no effect", "ALL": "no effect (the BTC gate and the 20-day exit already protect); kept as a live guard"},
    {"id": "R20", "doc": "docs/research/REVIEW_20_RESULTS.md", "idea": "T3-B sizing (re-size only coins far from their share)",
     "LAB10": "PASS", "TOP30": "PASS", "ALL": "not tested"},
]


def _connect(p: Path) -> sqlite3.Connection:
    con = sqlite3.connect(str(p))
    con.executescript("""
        DROP TABLE IF EXISTS bars; DROP TABLE IF EXISTS funding; DROP TABLE IF EXISTS futures; DROP TABLE IF EXISTS meta;
        CREATE TABLE bars (coin TEXT, t INTEGER, o REAL, h REAL, l REAL, c REAL, v REAL, qv REAL, tbv REAL, PRIMARY KEY (coin, t));
        CREATE TABLE funding (coin TEXT, t INTEGER, funding REAL, PRIMARY KEY (coin, t));
        CREATE TABLE futures (coin TEXT, t INTEGER, oi_value REAL, top_ls REAL, ls REAL, taker_ls REAL, PRIMARY KEY (coin, t));
        CREATE TABLE meta (k TEXT PRIMARY KEY, v TEXT);""")
    return con


def _ndax() -> dict[str, str]:
    import requests

    try:
        d = requests.get("https://api.ndax.io:8443/AP/GetInstruments?OMSId=1", timeout=20).json()
        return {x["Product1Symbol"]: x["Symbol"] for x in d if x.get("Product2Symbol") == "CAD" and not x.get("IsDisable")}
    except Exception:  # noqa: BLE001
        return {}


def _ema(xs: list[float], n: int) -> list[float]:
    k, out, e = 2 / (n + 1), [], None
    for x in xs:
        e = x if e is None else x * k + e * (1 - k)
        out.append(e)
    return out


def _stats(rows: list[tuple]) -> dict:
    c = [r[5] for r in rows]
    h = [r[3] for r in rows]
    l = [r[4] for r in rows]
    qv = [r[7] or 0.0 for r in rows]
    n = len(c)
    ch = lambda k: round(100 * (c[-1] / c[-1 - k] - 1), 1) if n > k and c[-1 - k] > 0 else None   # noqa: E731
    tr = [max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1])) for i in range(max(1, n - 14), n)]
    e50 = _ema(c, 50)[-1] if n >= 50 else None
    s200 = sum(c[-200:]) / 200 if n >= 200 else None
    peak, mdd = 0.0, 0.0
    for x in c:
        peak = max(peak, x)
        mdd = max(mdd, 1 - x / peak if peak else 0)
    rets = [math.log(c[i] / c[i - 1]) for i in range(max(1, n - 365), n) if c[i - 1] > 0 and c[i] > 0]
    return {"last_close": c[-1], "last_day": datetime.fromtimestamp(rows[-1][1], timezone.utc).strftime("%Y-%m-%d"),
            "change_7d_pct": ch(7), "change_30d_pct": ch(30), "change_90d_pct": ch(90), "change_365d_pct": ch(365),
            "all_time_high": max(h), "from_ath_pct": round(100 * (c[-1] / max(h) - 1), 1),
            "atr14_pct": round(100 * statistics.mean(tr) / c[-1], 2) if tr and c[-1] else None,
            "above_50d": None if e50 is None else c[-1] > e50, "above_200d": None if s200 is None else c[-1] > s200,
            "median_daily_usd_volume_90d": round(statistics.median(qv[-90:])) if qv else None,
            "worst_fall_ever_pct": round(100 * mdd, 1),
            "volatility_1y_pct": round(100 * statistics.pstdev(rets) * math.sqrt(365), 1) if len(rets) > 30 else None}


def build(out: Path | None = None) -> dict:
    import pandas as pd

    from src.lake import futures as F
    from src.lake import research as L

    t0 = time.time()
    out = out or root() / "agent"
    out.mkdir(parents=True, exist_ok=True)
    u = json.loads((root() / "reports" / "universe_v1.json").read_text())
    table = {r["symbol"]: r for r in u.get("table", [])}
    chosen = u["chosen"]
    coins = [L.base(s) for s in chosen]
    top30 = coins[:30]
    ndax = _ndax()
    tmp = out / "daily.sqlite.tmp"
    if tmp.exists():
        tmp.unlink()
    con = _connect(tmp)
    cards, latest = {}, 0
    for rank, (sym, coin) in enumerate(zip(chosen, coins), 1):
        D = [r for r in L.daily(sym, until=2 ** 40) if r[0] >= L.BREAKS.get(sym, 0)]
        import duckdb

        p = L.clean_dir("1d") / f"symbol={sym}" / "**" / "*.parquet"
        extra = {int(t): (qv, tbv) for t, qv, tbv in duckdb.sql(
            f"SELECT t, qv, tbv FROM read_parquet('{p}', hive_partitioning=true) WHERE share >= {L.MIN_SHARE}").fetchall()}
        rows = [(coin, int(t), o, h, l, c, v, *extra.get(int(t), (None, None))) for t, o, h, l, c, v in D]
        con.executemany("INSERT OR REPLACE INTO bars VALUES (?,?,?,?,?,?,?,?,?)", rows)
        latest = max(latest, rows[-1][1]) if rows else latest
        fu, fm = F.load("funding_daily", coin), F.load("metrics_daily", coin)
        if fu is not None and len(fu):
            con.executemany("INSERT OR REPLACE INTO funding VALUES (?,?,?)", [(coin, int(t), float(x)) for t, x in zip(fu["t"], fu["funding"])])
        if fm is not None and len(fm):
            con.executemany("INSERT OR REPLACE INTO futures VALUES (?,?,?,?,?,?)",
                            [(coin, int(r.t), float(r.oi_value), float(r.top_ls), float(r.ls), float(r.taker_ls)) for r in fm.itertuples()])
        q = json.loads((root() / "reports" / "quality" / f"spot_1m_{sym}.json").read_text())
        tiers = ["ALL"] + (["TOP30"] if coin in top30 else []) + (["LAB10"] if coin in LAB10 else [])
        t30_name = T30_RENAMED.get(coin, coin) if coin in top30 and coin != "BCHABC" else None
        does = []
        if coin in LAB10:
            does.append("LIVE_WATCH: the Explorer, the decision chain, zones, your setups, the eye, the news check and the T3 book watch it live")
        if t30_name:
            does.append(f"PAPER_TIER_30: daily paper books T3-B and H07-T30 (as {t30_name})")
        if not does:
            does.append("RESEARCH_ONLY: full history in the lake; not watched live and not traded, even on paper")
        nd = ndax.get(coin) or ndax.get(T30_RENAMED.get(coin, ""))
        cards[coin] = {
            "coin": coin, "binance_symbol": sym, "rank_by_traded_value": rank, "tiers": tiers, "what_ananta_does": does,
            "paper_tier_name": t30_name,
            "history": {"first": q.get("first"), "last": q.get("last"), "days": len(rows),
                        "status": ("RENAMED" if coin in T30_RENAMED else "OLD_SYMBOL" if coin == "BCHABC" else
                                   "LISTED" if rows and rows[-1][1] >= latest - 3 * DAY else "DELISTED_OR_STOPPED"),
                        "renamed_to": T30_RENAMED.get(coin), "note": ("the 2018-2020 Bitcoin Cash ABC history; Bitcoin Cash is BCH"
                                                                       if coin == "BCHABC" else None),
                        "quality_grade": q.get("grade"), "missing_minutes_pct": q.get("missing_pct"),
                        "token_swaps_cut": [x["at"] for x in q.get("suspect_redenominations") or []],
                        "median_month_usd_traded": (table.get(sym) or {}).get("median_month_usd")},
            "costs": {"ndax_fee_per_side_pct": 100 * NDAX_FEE,
                      "half_spread_pct": round(100 * MEASURED_HALF_SPREAD.get(coin, 0.004), 3),
                      "half_spread_source": "measured" if coin in MEASURED_HALF_SPREAD else "assumed 0.40% (not measured)"},
            "ndax": {"listed_vs_cad": bool(nd), "symbol": nd},
            "futures": {"funding_from": None if fu is None or not len(fu) else datetime.fromtimestamp(int(fu["t"].min()), timezone.utc).strftime("%Y-%m-%d"),
                        "open_interest_from": None if fm is None or not len(fm) else datetime.fromtimestamp(int(fm["t"].min()), timezone.utc).strftime("%Y-%m-%d")},
            "now": _stats(rows) if len(rows) > 30 else {},
        }
    con.executemany("INSERT OR REPLACE INTO meta VALUES (?,?)", [("built_at", datetime.now(timezone.utc).isoformat(timespec="seconds")),
                                                                ("coins", str(len(cards)))])
    con.commit()
    con.close()
    tmp.replace(out / "daily.sqlite")
    pack = {"version": "agent_pack.v1", "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "source": "the research lake (Binance spot 1-minute candles, checked; futures context from Binance Data Vision)",
            "tiers": {"LAB10": LAB10, "TOP30": top30, "ALL": coins},
            "tier_meaning": {"LAB10": "watched live and paper-traded by every part of Ananta",
                             "TOP30": "the 30 most-traded coins: daily paper books for the ideas that passed on them (T3-B, H07)",
                             "ALL": "the full research universe (incl. delisted coins): history and research only"},
            "research": RESEARCH, "ndax_cad_coins": sorted(ndax), "cards": cards,
            "seconds": round(time.time() - t0)}
    (out / "universe.json").write_text(json.dumps(pack, indent=1, default=str))
    return {"coins": len(cards), "ndax": sum(c["ndax"]["listed_vs_cad"] for c in cards.values()), "seconds": pack["seconds"]}
