"""Review #29 (docs/research/REVIEW_29.md, approved by Madhav in chat 2026-10-15 06:33 Toronto; sha256 below): H07 on a
point-in-time tier A, both dial states, Universe Rule v2 costs, against random twins; the holdout stays sealed.

  python -m src.research.review29 fetch      download, build and quality-check (as review #22) every coin ever in tier A that the
                                             lake has no daily candles for (the registration's download step)
  python -m src.research.review29 coverage   the stop rule first: do the coins with clean daily candles cover 99% of tier A's
                                             traded value in every month 2018-01 .. 2026-07? (no trade is simulated)
  python -m src.research.review29            the run; refuses when the registration changed or coverage fails
                                             -> docs/research/review29.json (REVIEW_29_RESULTS.md is written from it)

Operational choices fixed here, before any result (the registration leaves them open): tier A in a month for the coverage gate =
average daily traded value in that month >= $20M (monthly_values.json); a coin-month counts as covered when at least 90% of its
trading days have a complete candle (>= 97% of the minutes; Binance's own daily candles count as complete) and the coin passed the
token-swap check (see COIN_MONTH_MIN for the one change made after the first coverage pass); the token-swap check is the lake's
own minute-level report (cut at BREAKS / ENDS) for a coin with minute data, and the same 10x rule on daily closes for a coin held
only as Binance's daily candles (fixed after the third coverage pass, still before any trade: the daily rule had been applied to
minute coins too and flagged LUNA's real May 2022 collapse, which the minute-level check already handles); a re-used ticker's new
token is its own coin and a listing day's partial candle does not count against its month (both fixed after the 4th coverage pass,
before any trade: see SUCCESSORS and LISTING_DAY); "the two largest bursts" = the two
bursts with the most trades (ties: the larger total excess); the paired twin exits on the same day as its trade; a coin that no
longer trades (not LISTED in today's registry) pays Kraken's 0.40% fee plus twice its tier's half-spread floor at the signal.
"""
from __future__ import annotations

import calendar
import glob
import hashlib
import json
import math
import os
import random
import statistics
import sys
from pathlib import Path

DAY = 86400
START_T = 1514764800                     # 2018-01-01
SPLIT_T = 1704067200                     # 2024-01-01
END_T = 1785542400                       # 2026-08-01: the holdout starts here and is never loaded
TIER_A = 20e6
FLOOR = {"A": 0.0020, "B": 0.0040, "C": 0.0080}
KRAKEN_FEE = 0.0040
HOLD = 10
COVERAGE_MIN = 0.99
# Changed before any trade was simulated (Oct 15, after the first coverage pass only): that pass weighted each coin-month by its share
# of complete days, so one exchange-wide incomplete day (a Binance maintenance day: 29 of 30 days complete for every coin) failed
# whole months at 96.7%, which measures exchange uptime, not whether the coins have data. The gate is per coin, as REVIEW_29.md
# words it ("the coins with clean daily candles"): a coin-month counts when at least 90% of its trading days have a complete candle.
COIN_MONTH_MIN = 0.90
# Fixed after the 4th coverage pass (after downloading the 76 missing coins), still before any trade was simulated. That pass fell
# short in two months only, both from how this code counted, not from missing data:
#  - 2022-09 (98.69%): LUNA 2.0, the new token Binance listed under the re-used ticker LUNAUSDT on 2022-05-31, was tier A, but the
#    ENDS cut (review #22) keeps only Terra classic under that ticker. A re-used ticker's rows from the swap on are their own coin
#    (SUCCESSORS), checked on their own with the same 10x rule (1,523 complete days, no suspect).
#  - 2023-03 (98.89%): ARB listed on 2023-03-24 and its first candle held 94.4% of the minutes (< 97%): a listing day is partial
#    by construction, so an incomplete FIRST candle of a coin is left out of its month's count (LISTING_DAY).
SUCCESSORS = {"LUNAUSDT": "LUNA2"}
COST_AS = {"LUNA": "LUNC", "LUNA2": "LUNA"}   # the live coin each name pays: Terra classic trades today as LUNC, LUNA 2.0 as LUNA
LISTING_DAY = True
MIN_DAYS, Z_DISC, Z_CONF, SHRINK = 30, 2.5, 2.0, 50
BURST_GAP = 10 * DAY
REG_SHA = "c7b52bb866fe0d82acfcfb529b79c8f28fb2a3d9c63209f6a7501b2a62a8ebd8"
ROOT = Path(__file__).resolve().parents[2]
SEED = 29


def _lake() -> Path:
    from src.lake import root

    return root()


def registration_ok() -> bool:
    return hashlib.sha256((ROOT / "docs" / "research" / "REVIEW_29.md").read_bytes()).hexdigest() == REG_SHA


def months() -> list[str]:
    out, y, m = [], 2018, 1
    while (y, m) <= (2026, 7):
        out.append(f"{y:04d}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def _mdays(mon: str) -> int:
    y, m = map(int, mon.split("-"))
    return calendar.monthrange(y, m)[1]


def _month(t: int) -> str:
    import time

    return time.strftime("%Y-%m", time.gmtime(t))


def _rows(symbol: str, con, after_end: bool = False) -> list[tuple]:
    """Every daily row before the holdout (complete or not): (t, o, h, l, c, v, qv, share), inside the coin's safe window
    (after_end: the rows of a re-used ticker from its swap on, the successor coin of SUCCESSORS)."""
    from src.lake import research as L
    from src.lake.binance_vision import clean_dir

    d = clean_dir("1d") / f"symbol={symbol}"
    if not glob.glob(str(d / "**" / "*.parquet"), recursive=True):
        return []
    src = f"read_parquet('{d}/**/*.parquet', hive_partitioning=true, union_by_name=true)"
    cols = {r[0] for r in con.execute(f"DESCRIBE SELECT * FROM {src}").fetchall()}
    # coins built from minute data carry share (the minutes present); coins held as Binance's own daily candles (lake_extend)
    # are complete by construction (share 1.0)
    share = "COALESCE(share, 1.0)" if "share" in cols else "1.0"
    rows = con.execute(f"SELECT t, o, h, l, c, v, qv, {share} FROM {src} WHERE t < {END_T} ORDER BY t").fetchall()
    if after_end:
        return [tuple(r) for r in rows if r[0] >= L.ENDS.get(symbol, 1 << 62)] if symbol in SUCCESSORS else []
    return [tuple(r) for r in rows if L.BREAKS.get(symbol, 0) <= r[0] < L.ENDS.get(symbol, 1 << 62)]


def swap_unchecked(symbol: str, rows: list[tuple]) -> list:
    """The lake's token-swap check. A coin with minute data has its minute-level quality report (src/lake/quality.py, as review #22);
    a coin the lake holds only as Binance's daily candles gets the same 10x rule on its daily closes (it has no minute report)."""
    from src.lake import root
    from src.lake import research as L

    if (root() / "reports" / "quality" / f"spot_1m_{symbol}.json").exists():
        return L.unhandled_suspects(symbol)
    return daily_suspects(rows)


def daily_suspects(rows: list[tuple]) -> list[int]:
    """The lake's token-swap rule (src/lake/quality.py: a close 10x above or under the one before) on the daily candles, so the coins
    the lake holds only as daily candles get the same check; days already cut by BREAKS / ENDS are not in `rows`."""
    out, prev = [], None
    for r in rows:
        if prev and r[4] and (r[4] / prev >= 10 or r[4] / prev <= 0.1):
            out.append(int(r[0]))
        prev = r[4] or prev
    return out


def tier_months() -> dict:
    """{month: {symbol: traded value that month}} for the coins in tier A that month (average daily traded value >= $20M)."""
    mv = json.loads((_lake() / "reports" / "monthly_values.json").read_text())
    syms = [r["symbol"] for r in json.loads((_lake() / "reports" / "universe_v1.json").read_text())["table"]]
    return {m: {s: mv.get(s, {}).get(m, 0.0) for s in syms if mv.get(s, {}).get(m, 0.0) / _mdays(m) >= TIER_A} for m in months()}


def fetch() -> None:
    """The registration's download step, as review #22 did it (src.lake.cli all: minute files checked against Binance's checksums,
    built, daily bars, the quality check with the token-swap test) for every coin ever in tier A with no daily candles in the lake."""
    from src.lake import cli

    tier = tier_months()
    d1 = _lake() / "clean" / "binance" / "spot" / "1d"
    missing = sorted({s for v in tier.values() for s in v if not (d1 / f"symbol={s}").exists()})
    print("downloading", len(missing), missing, flush=True)
    cli.main(["all"] + missing)


def coverage(con=None) -> dict:
    """The stop rule: tier A's traded value per month, and how much of it has clean, swap-checked daily candles."""
    import duckdb

    from src.lake import research as L

    con = con or duckdb.connect()
    ms = months()
    tier = tier_months()
    ever = sorted({s for m in ms for s in tier[m]})
    per: dict = {}
    for s in ever:
        rows = _rows(s, con)
        bad = swap_unchecked(s, rows)
        segs = [] if bad else [rows]
        nxt = _rows(s, con, after_end=True)                     # a re-used ticker's new token (SUCCESSORS), checked on its own
        if nxt and not daily_suspects(nxt):
            segs.append(nxt)
        by: dict = {}
        for seg in segs:
            for k, r in enumerate(seg):
                if LISTING_DAY and k == 0 and (r[7] or 0) < L.MIN_SHARE:
                    continue                                    # the listing day: partial by construction
                mm = by.setdefault(_month(r[0]), [0, 0])
                mm[0] += 1
                mm[1] += 1 if (r[7] or 0) >= L.MIN_SHARE else 0
        per[s] = {"swap_unchecked": bool(bad), "months": by}
    out = {}
    for m in ms:
        tot = sum(tier[m].values())
        cov, missing = 0.0, []
        for s, v in tier[m].items():
            tr, ok = (per[s]["months"].get(m) or [0, 0])
            share = ok / tr if tr else 0.0
            covered = share >= COIN_MONTH_MIN                  # the coin has clean candles for this month (coin-level, see COIN_MONTH_MIN)
            cov += v if covered else 0.0
            if not covered:
                missing.append({"symbol": s, "value_usd": round(v), "complete_days_share": round(share, 3),
                                "swap_unchecked": per[s]["swap_unchecked"]})
        missing.sort(key=lambda x: -x["value_usd"])
        out[m] = {"tier_a_coins": len(tier[m]), "value_usd": round(tot), "covered": round(cov / tot, 4) if tot else 1.0, "short": missing[:5]}
    worst = min(out.values(), key=lambda x: x["covered"])
    return {"months": out, "coins_ever_tier_a": len(ever), "min_covered": worst["covered"],
            "pass": all(x["covered"] >= COVERAGE_MIN for x in out.values()),
            "rule": f"every month 2018-01..2026-07 needs >= {COVERAGE_MIN:.0%} of tier A's traded value with clean, swap-checked candles"}


# ---------------------------------------------------------------------------
# the run
# ---------------------------------------------------------------------------
def _net(entry: float, exit_px: float, k: float) -> float:
    return 100 * (exit_px / entry * (1 - k) ** 2 - 1)


def _cost_fn(reg: dict):
    """Each side: the coin's live Universe Rule v2 cost (registry.cost); a coin no longer LISTED: Kraken's fee + twice its floor."""
    from jarvis.service import registry
    from src.intelligence.explorer_engine import HALF_SPREAD

    coins = reg.get("coins") or {}

    def cost(coin: str, tier_sig: str) -> float:
        coin = COST_AS.get(coin, coin)
        if coin in HALF_SPREAD or (coins.get(coin) or {}).get("status") == "LISTED":
            return registry.cost(coin, reg)
        return KRAKEN_FEE + 2 * FLOOR[tier_sig]
    return cost


def _tiers(D: list[tuple]) -> list[str | None]:
    """Point-in-time tier on each day: the median quote volume of the 30 complete days before it (as review #26, on quote volume)."""
    out: list[str | None] = [None] * len(D)
    for i in range(30, len(D)):
        med = sorted((D[k][6] or 0.0) for k in range(i - 30, i))[15]
        out[i] = "A" if med >= TIER_A else "B" if med >= 1e6 else "C"
    return out


def _dial_at(btc: list[tuple]):
    """The dial v1 decided on each Bitcoin close (review #25); a day without a Bitcoin candle takes the last close before it."""
    import bisect

    from src.research import review25 as R25

    w = R25.targets([b[:5] for b in btc], "GATE50_200")
    ts = [b[0] for b in btc]

    def at(t: int) -> str:
        k = bisect.bisect_right(ts, t) - 1
        return "OPEN" if k >= 0 and w[k] > 0 else "CLOSED"
    return at


def h07(coin: str, D: list[tuple], B, tiers: list, dial, cost) -> list[dict]:
    """Every H07 trade on one coin exactly as live (watch_engine._fires; next open; out at the open after RSI(10) closes over 40,
    or after 10 days; no stop; one at a time), kept when the coin was tier A on the signal day."""
    from jarvis.service import watch_engine as W
    from src.research import reads as R

    spec = W.DAILY["H07"]
    S = B if coin == "BTC" else R.Series(D)
    r10 = R.rsi(S.c, 10)
    out, busy = [], -1
    for i in range(210, len(D) - 1):
        if D[i][0] < START_T or i <= busy:
            continue
        ok, _, _ = W._fires(spec, S, B, i, r10)
        if not ok:
            continue
        k = i + 1
        exit_i = None
        for d in range(k, len(D)):
            if d == k + spec["days"]:
                exit_i = d
                break
            if r10[d] is not None and r10[d] > spec["rsi_exit"] and d + 1 < len(D):
                exit_i = d + 1
                break
        if exit_i is None:
            continue                                         # still open when the data ends (the holdout is never loaded)
        busy = exit_i
        if tiers[i] != "A":
            continue
        c1 = cost(coin, "A")
        out.append({"coin": coin, "t": D[i][0], "entry_t": D[k][0], "exit_t": D[exit_i][0], "state": dial(D[i][0]), "cost": c1,
                    "net": _net(D[k][1], D[exit_i][1], c1), "net2": _net(D[k][1], D[exit_i][1], 2 * c1)})
    return out


def baseline(data: dict, tiers: dict, dial, cost, rng: random.Random, stress: float = 1.0, n_per: int = 4000) -> dict:
    """Random days of point-in-time tier-A coins in the same dial state, held 10 days (next open to the open 10 days on)."""
    pools: dict = {}
    for coin, D in data.items():
        tr = tiers[coin]
        for i in range(30, len(D) - 1 - HOLD):
            if tr[i] == "A" and D[i][0] >= START_T:
                pools.setdefault((dial(D[i][0]), "DISCOVERY" if D[i][0] < SPLIT_T else "CONFIRM"), []).append((coin, i))
    out = {}
    for key, sel in sorted(pools.items()):
        vals = []
        for coin, i in (rng.choice(sel) for _ in range(min(n_per, 3 * len(sel)))):
            D = data[coin]
            vals.append(_net(D[i + 1][1], D[i + 1 + HOLD][1], stress * cost(coin, "A")))
        out[key] = {"mean_net_pct": statistics.mean(vals), "n": len(vals), "pool": len(sel)}
    return out


def _bursts(xs: list[dict], b: float) -> float | None:
    """Mean excess after dropping the two bursts with the most trades (trades within 10 days of each other form one burst)."""
    if not xs:
        return None
    xs = sorted(xs, key=lambda t: t["t"])
    groups, cur = [], [xs[0]]
    for t in xs[1:]:
        if t["t"] - cur[-1]["t"] <= BURST_GAP:
            cur.append(t)
        else:
            groups.append(cur)
            cur = [t]
    groups.append(cur)
    groups.sort(key=lambda g: (len(g), sum(t["net"] - b for t in g)), reverse=True)
    rest = [t for g in groups[2:] for t in g]
    return round(statistics.mean(t["net"] - b for t in rest), 2) if rest else None


def _period(xs: list[dict], b: float, b2: float, twin: list[float]) -> dict:
    ex = [t["net"] - b for t in xs]
    md = len({t["exit_t"] // DAY for t in xs})
    sd = statistics.pstdev(ex) if len(ex) > 1 else 0.0
    z = statistics.mean(ex) / (sd / math.sqrt(md)) if sd and md else 0.0
    tz = (statistics.mean(twin) / (statistics.pstdev(twin) / math.sqrt(len(twin)))) if len(twin) > 1 and statistics.pstdev(twin) else 0.0
    return {"trades": len(xs), "market_days": md, "mean_net_pct": round(statistics.mean(t["net"] for t in xs), 2) if xs else None,
            "baseline_pct": round(b, 2), "mean_excess_pct": round(statistics.mean(ex), 2) if ex else None, "z": round(z, 2),
            "stress_mean_net_pct": round(statistics.mean(t["net2"] for t in xs), 2) if xs else None, "stress_baseline_pct": round(b2, 2),
            "excess_without_two_largest_bursts_pct": _bursts(xs, b),
            "paired_twin": {"pairs": len(twin), "mean_minus_twin_pct": round(statistics.mean(twin), 2) if twin else None, "z": round(tz, 2)}}


def verdict(cell: dict) -> str:
    d, c = cell["DISCOVERY"], cell["CONFIRM"]
    if d["market_days"] < MIN_DAYS:
        return "INSUFFICIENT"
    if not ((d["mean_excess_pct"] or 0) > 0 and (d["mean_net_pct"] or 0) > 0 and (c["mean_excess_pct"] or 0) > 0 and (c["mean_net_pct"] or 0) > 0):
        return "FAIL"
    marks = (d["z"] >= Z_DISC and c["z"] >= Z_CONF and (d["stress_mean_net_pct"] or 0) > 0 and (c["stress_mean_net_pct"] or 0) > 0
             and (d["excess_without_two_largest_bursts_pct"] or 0) > 0 and (c["excess_without_two_largest_bursts_pct"] or 0) > 0)
    return "PASS" if marks else "WEAKENED"


def main() -> dict:
    import duckdb

    from src.lake import research as L
    from src.research import reads as R

    if not registration_ok():
        raise SystemExit("REVIEW_29.md changed after approval: refusing to run (a change is a new review)")
    con = duckdb.connect()
    cov = coverage(con)
    out: dict = {"review": 29, "registration_sha256": REG_SHA, "approved": "Madhav in chat, 2026-10-15 06:33 Toronto: '1. approved'",
                 "coverage": {k: v for k, v in cov.items() if k != "months"}, "coverage_months": cov["months"], "seed": SEED}
    if not cov["pass"]:
        out["stopped"] = "coverage short of 99% in at least one month: no result computed (the stop rule)"
        return out
    syms = [r["symbol"] for r in json.loads((_lake() / "reports" / "universe_v1.json").read_text())["table"]]
    data, skipped = {}, []
    for s in syms:
        allrows = _rows(s, con)
        if swap_unchecked(s, allrows):
            skipped.append(s)
            continue
        rows = [r[:7] for r in allrows if (r[7] or 0) >= L.MIN_SHARE]
        if len(rows) >= 240:
            data[L.base(s)] = rows
        nxt = _rows(s, con, after_end=True)                     # a re-used ticker's new token (SUCCESSORS), its own coin
        if nxt:
            if daily_suspects(nxt):
                skipped.append(SUCCESSORS[s])
            elif sum(1 for r in nxt if (r[7] or 0) >= L.MIN_SHARE) >= 240:
                data[SUCCESSORS[s]] = [r[:7] for r in nxt if (r[7] or 0) >= L.MIN_SHARE]
    if "BTC" not in data:
        raise SystemExit("BTC missing")
    reg = json.loads((Path.home() / "code" / "ananta-decision-agent" / "universe_live.json").read_text())
    cost = _cost_fn(reg)
    B = R.Series(data["BTC"])
    dial = _dial_at(data["BTC"])
    tiers = {c: _tiers(D) for c, D in data.items()}
    trades = []
    for k, (coin, D) in enumerate(sorted(data.items())):
        trades += h07(coin, D, B, tiers[coin], dial, cost)
        if k % 50 == 0:
            print(f"  {k}/{len(data)} coins, {len(trades)} tier-A H07 trades", file=sys.stderr, flush=True)
    base = baseline(data, tiers, dial, cost, random.Random(SEED))
    base2 = baseline(data, tiers, dial, cost, random.Random(SEED), stress=2.0)
    idx = {c: {b[0]: i for i, b in enumerate(D)} for c, D in data.items()}
    day_a: dict = {}
    for c, D in data.items():
        for i, tr in enumerate(tiers[c]):
            if tr == "A":
                day_a.setdefault(D[i][0], []).append(c)
    rng = random.Random(SEED + 1)
    for t in trades:                                             # the paired twin (reported only): a random tier-A coin, same days
        pool = sorted(c for c in day_a.get(t["t"], []) if c != t["coin"] and t["entry_t"] in idx[c] and t["exit_t"] in idx[c])
        if pool:
            c2 = rng.choice(pool)
            D2 = data[c2]
            t["twin"] = c2
            t["twin_net"] = _net(D2[idx[c2][t["entry_t"]]][1], D2[idx[c2][t["exit_t"]]][1], cost(c2, "A"))
    cells = []
    for state in ("CLOSED", "OPEN"):
        cell: dict = {"rule": "H07", "tier": "A", "state": state, "role": "primary" if state == "CLOSED" else "secondary"}
        pooled, n = [], 0
        for period in ("DISCOVERY", "CONFIRM"):
            xs = [t for t in trades if t["state"] == state and (t["t"] < SPLIT_T) == (period == "DISCOVERY")]
            b = base[(state, period)]["mean_net_pct"]
            b2 = base2[(state, period)]["mean_net_pct"]
            twin = [t["net"] - t["twin_net"] for t in xs if "twin_net" in t]
            cell[period] = _period(xs, b, b2, twin)
            pooled += [t["net"] - b for t in xs]
            n += cell[period]["market_days"]
        cell["verdict"] = verdict(cell)
        cell["expected_excess_pct"] = (round(statistics.mean(pooled) * n / (n + SHRINK), 2)
                                       if cell["verdict"] in ("PASS", "WEAKENED") and pooled else 0.0)
        cells.append(cell)
    out.update(coins_loaded=len(data), coins_skipped_swap_unchecked=skipped, tier_a_h07_trades=len(trades), cells=cells,
               baseline={f"{k[0]}|{k[1]}": {kk: round(vv, 3) if isinstance(vv, float) else vv for kk, vv in v.items()} for k, v in base.items()},
               holdout="2026-08-01 to 2026-12-14: not loaded (every candle read is before 2026-08-01)")
    return out


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "fetch":
        fetch()
    elif len(sys.argv) > 1 and sys.argv[1] == "coverage":
        c = coverage()
        print(json.dumps({k: v for k, v in c.items() if k != "months"}, indent=1))
        short = {m: x for m, x in c["months"].items() if x["covered"] < COVERAGE_MIN}
        print(json.dumps(short, indent=1)[:6000])
    else:
        res = main()
        (ROOT / "docs" / "research" / "review29.json").write_text(json.dumps(res, indent=1))
        print(json.dumps({"stopped": res.get("stopped"), "cells": [{k: c[k] for k in ("state", "verdict", "expected_excess_pct")}
                                                                  for c in res.get("cells", [])]}, indent=1))
