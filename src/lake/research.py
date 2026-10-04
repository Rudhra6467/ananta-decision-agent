"""Re-testing what passed on the full universe (review #15, docs/research/REVIEW_15.md, written before any run).

The same engines as the original reviews, fed from the lake instead of the 10-coin research database:
  T3        the trend portfolio (review #4 simulator) against equal-weight buy-and-hold of the same coins
  H07       the short dip trade against ordinary uptrend days with the same exit (review #14)
  setups    Madhav's reads M1a, M2a, M3a and the retest with the market allowed (M2a-G) against each coin's drift (reviews #5, #8)
Daily candles come from the lake's 1d files (days with at least 97% of their minutes), cut at 2026-08-01 so the holdout stays sealed.
Coins outside the lab 10 pay a 0.40% half-spread on top of NDAX's 0.20% fee (the pessimistic default), so thin coins cannot flatter a result.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from src.lake import root
from src.lake.binance_vision import clean_dir

MIN_SHARE = 0.97
LAB10 = ["BTC", "ETH", "SOL", "ADA", "DOGE", "AVAX", "BCH", "LINK", "LTC", "XRP"]


def base(symbol: str) -> str:
    return symbol[:-4] if symbol.endswith("USDT") else symbol


def daily(symbol: str, until: int | None = None, con=None) -> list[tuple]:
    """(t, o, h, l, c, v) per UTC day from the lake, complete days only, before `until` (default: the holdout start)."""
    import duckdb

    from src.research import reads as R

    until = until or R.CONF_END
    p = clean_dir("1d") / f"symbol={symbol}" / "**" / "*.parquet"
    con = con or duckdb.connect()
    rows = con.execute(f"SELECT t, o, h, l, c, v FROM read_parquet('{p}', hive_partitioning=true) WHERE share >= {MIN_SHARE} AND t < {until} ORDER BY t").fetchall()
    return [tuple(r) for r in rows]


def load(symbols: list[str]) -> dict[str, list[tuple]]:
    out = {}
    for s in symbols:
        D = daily(s)
        if len(D) >= 120:
            out[base(s)] = D
    return out


def t3(D: dict[str, list[tuple]]) -> dict:
    import pandas as pd

    from src.research import portfolio_trend as P

    data = {}
    for c, bars in D.items():
        df = pd.DataFrame(bars, columns=["t", "o", "h", "l", "c", "v"])
        df.index = pd.to_datetime(df["t"], unit="s")
        data[c] = df[["o", "c"]]
    days = pd.date_range(min(v.index.min() for v in data.values()), max(v.index.max() for v in data.values()), freq="D")
    sig = P.signals(data, days)
    out = {}
    for s in ("BH", "T3"):
        sim = P.simulate(data, days, sig[s], sig["_avail"])
        eq, exp = sim["equity"], sim["exposure"]
        eq = eq[eq.index >= eq.index[0] + pd.Timedelta(days=50)]
        disc, conf = eq[eq.index < P.DISC_END], eq[eq.index >= P.DISC_END]
        out[s] = {"ALL": P.metrics(eq, exp), "DISCOVERY": P.metrics(disc, exp), "CONFIRM": P.metrics(conf, exp), "trades": sim["trades"],
                  "costs_paid_pct_of_start": round(100 * sim["costs"], 2)}
    checks = {}
    for sp in ("DISCOVERY", "CONFIRM"):
        a, b = out["T3"][sp], out["BH"][sp]
        checks[sp] = {"return>0": a["total_return_pct"] > 0, "dd<BH": a["max_dd_pct"] < b["max_dd_pct"], "mar>BH": (a["mar"] or -9) > (b["mar"] or -9)}
    out["checks"] = checks
    out["PASS"] = all(all(v.values()) for v in checks.values())
    out["coins"] = len(D)
    return out


def h07(D: dict[str, list[tuple]]) -> dict:
    from src.research import teachers2

    return teachers2.review14("", Path("/tmp"), D=D)


def setups(D: dict[str, list[tuple]]) -> dict:
    from src.research import reads as R

    keep = lambda name, coin, S, B: R.review8_filter(name, coin, S, B) if "-" in name else None   # noqa: E731
    return R.history(D, ["M1a", "M2a", "M3a", "M2a-G"], keep_for=keep)


def review15(symbols: list[str], tiers: dict[str, list[str]] | None = None, out: Path | None = None) -> dict:
    """Every test on each tier of coins (the lab 10 as a check that the lake agrees with the old database, then the wider tiers)."""
    t0 = time.time()
    D_all = load(symbols)
    tiers = tiers or {"LAB10": [c for c in LAB10 if c in D_all], "ALL": list(D_all)}
    rep: dict = {"version": "review15.v1", "pre_registration": "docs/research/REVIEW_15.md", "coins_loaded": len(D_all), "tiers": {}}
    for name, coins in tiers.items():
        D = {c: D_all[c] for c in coins if c in D_all}
        if "BTC" not in D:
            continue
        rep["tiers"][name] = {"coins": sorted(D), "T3": t3(D), "H07": h07(D), "setups": setups(D)}
    rep["seconds"] = round(time.time() - t0)
    out = out or root() / "reports"
    out.mkdir(parents=True, exist_ok=True)
    (out / "review15_results.json").write_text(json.dumps(rep, indent=1, default=str))
    return rep
