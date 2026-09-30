"""History replay of Rulebook v0 through the SAME engine the live Explorer uses (src/intelligence/explorer_engine).

    python -m src.research.explorer_replay run --db LAB5 --out DIR           # per-coin trades + scan counts
    python -m src.research.explorer_replay score --out DIR                   # scorecard.json + SCORECARD.md

Splits: DISCOVERY < 2024-01-01 <= CONFIRM < 2026-08-01. HOLDOUT (Aug-Sep 2026) is never loaded.
Portfolio caps (N4) are applied afterwards over all coins (documented approximation: a per-coin engine
does not know the other coins' slots).
"""
from __future__ import annotations

import argparse
import bisect
import json
import os
import pickle
import sqlite3
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

from src.intelligence import explorer_engine as xe

DISC_END = 1704067200
CONF_END = 1785542400
CRISES = {  # Rulebook R6
    "COVID_2020": ("2020-03-05", "2020-03-20"),
    "MAY_2021": ("2021-05-10", "2021-05-25"),
    "LUNA_3AC_2022": ("2022-05-05", "2022-06-20"),
    "FTX_2022": ("2022-11-05", "2022-11-15"),
    "AUG_2024": ("2024-08-01", "2024-08-08"),
    "OCT_2025": ("2025-10-09", "2025-10-12"),
}


def _ts(d: str) -> int:
    return int(time.mktime(time.strptime(d, "%Y-%m-%d")) - time.timezone)


def load_5m(db: str, coin: str) -> list[tuple]:
    con = sqlite3.connect(f"file:{os.path.expanduser(db)}?mode=ro", uri=True)
    try:
        return [tuple(r) for r in con.execute(
            "SELECT event_unix, open, high, low, close, volume FROM bars WHERE instrument=? AND event_unix < ? ORDER BY event_unix",
            (f"{coin}-USD-SPOT", CONF_END))]
    finally:
        con.close()


def resample(b5: list[tuple], step: int) -> list[tuple]:
    """Complete UTC buckets only (a bucket with a missing 5m bar is dropped, like live closed-bar rules)."""
    need = step // 300
    out, cur, key = [], [], None
    for bar in b5:
        k = bar[0] - bar[0] % step
        if k != key:
            if cur and len(cur) == need:
                out.append((key, cur[0][1], max(x[2] for x in cur), min(x[3] for x in cur), cur[-1][4], sum(x[5] for x in cur)))
            cur, key = [], k
        cur.append(bar)
    if cur and len(cur) == need:
        out.append((key, cur[0][1], max(x[2] for x in cur), min(x[3] for x in cur), cur[-1][4], sum(x[5] for x in cur)))
    return out


def event_stream(b5: list[tuple]) -> list[tuple]:
    """(close_t, tf_rank, tf, bar) sorted: all bars closing at T, the 5m bar first (execution before the scan)."""
    ev = []
    for rank, tf in enumerate(xe.ORDER_TF):
        bars = b5 if tf == "5m" else resample(b5, xe.TF_S[tf])
        step = xe.TF_S[tf]
        ev.extend((b[0] + step, rank, tf, b) for b in bars)
    ev.sort(key=lambda e: (e[0], e[1]))
    return ev


def btc_context(db: str) -> tuple[list[int], list[dict]]:
    b1h = resample(load_5m(db, "BTC"), 3600)
    s = xe.TfState("1h")
    ts, ctx = [], []
    for b in b1h:
        s.add(*b)
        if s.n < 60:
            continue
        c = b[4]
        e50, e50_5, e20, e20_3 = s.e50h[-1], s.ema_ago("50", 5), s.e20h[-1], s.ema_ago("20", 3)
        S1 = "BULL" if c > e50 and e50 > e50_5 else "BEAR" if c < e50 and e50 < e50_5 else "NEUTRAL"
        S2 = "UP" if c > e20 and e20 > e20_3 else "DOWN" if c < e20 and e20 < e20_3 else "FLAT"
        ts.append(b[0] + 3600)
        ctx.append({"btc_S1": S1, "btc_S2": S2, "btc_1h_ret": c / b[1] - 1})
    return ts, ctx


def run_coin(db: str, coin: str, out: str, rules: str = "C0") -> dict[str, Any]:
    t0 = time.time()
    b5 = load_5m(db, coin)
    if not b5:
        return {"coin": coin, "skipped": True}
    bts, bctx = btc_context(db) if coin != "BTC" else ([], [])

    def ctx(T: int) -> dict:
        i = bisect.bisect_right(bts, T) - 1
        return bctx[i] if i >= 0 and T - bts[i] <= 2 * 3600 else {}

    eng = xe.CoinEngine(coin, btc_ctx=ctx, rules=xe.RULESETS[rules])
    scans = skips = 0
    skip_kinds: dict[str, int] = {}
    ev = event_stream(b5)
    i, n = 0, len(ev)
    while i < n:
        T = ev[i][0]
        while i < n and ev[i][0] == T:
            eng.on_bar(ev[i][2], ev[i][3])
            i += 1
        if T % 900 == 0:
            rec = eng.scan(T)
            scans += 1
            if "skip" in rec:
                skips += 1
                k = rec["skip"].split(":")[0]
                skip_kinds[k] = skip_kinds.get(k, 0) + 1
    rows = eng.trade_rows()
    missed = [{"id": o.id, "setup": o.setup, "type": o.typ, "placed_t": o.placed_t, "shadow": o.shadow or ""} for o in eng.missed]
    Path(out, f"trades_{coin}.pkl").write_bytes(pickle.dumps({"rows": rows, "missed": missed}))
    return {"coin": coin, "rules": rules, "bars_5m": len(b5), "scans": scans, "skips": skips, "skip_kinds": skip_kinds,
            "closed_rows": len(rows), "real": sum(1 for r in rows if not r["shadow"]), "secs": round(time.time() - t0, 1)}


# ---------------------------------------------------------------------------
# Scorecard
# ---------------------------------------------------------------------------
def _agg(rows: list[dict], col: str = "ACTUAL_net") -> dict:
    x = [r[col] for r in rows if r.get(col) is not None]
    if not x:
        return {"n": 0}
    wins = sum(1 for v in x if v > 0)
    Rs = [r.get(col.replace("_net", "_R")) for r in rows if r.get(col.replace("_net", "_R")) is not None]
    return {"n": len(x), "win_rate": round(wins / len(x), 3), "mean_usd": round(sum(x) / len(x), 3),
            "total_usd": round(sum(x), 2), "mean_R": round(sum(Rs) / len(Rs), 3) if Rs else None}


def _group(rows, key) -> dict:
    g: dict[str, list] = {}
    for r in rows:
        g.setdefault(str(key(r)), []).append(r)
    return {k: _agg(v) for k, v in sorted(g.items())}


def portfolio(real: list[dict], start: float = 2000.0, max_open: int = 20, max_day: int = 30) -> dict:
    """Apply the N4 caps over all coins in entry order; realized equity and drawdown vs starting capital."""
    real = sorted(real, key=lambda r: r["entry_t"])
    open_exits: list[int] = []
    per_day: dict[int, int] = {}
    taken = []
    for r in real:
        t = r["entry_t"]
        open_exits = [x for x in open_exits if x > t]
        d = t // 86400
        if len(open_exits) >= max_open or per_day.get(d, 0) >= max_day:
            continue
        open_exits.append(r["ACTUAL_exit_t"])
        per_day[d] = per_day.get(d, 0) + 1
        taken.append(r)
    events = sorted((r["ACTUAL_exit_t"], r["ACTUAL_net"]) for r in taken)
    eq, peak, dd, curve = start, start, 0.0, []
    for t, v in events:
        eq += v
        peak = max(peak, eq)
        dd = max(dd, peak - eq)
        curve.append((t, eq))
    return {"taken": len(taken), "skipped_by_caps": len(real) - len(taken), "end_equity": round(eq, 2),
            "return_pct": round(100 * (eq - start) / start, 2), "max_dd_usd": round(dd, 2),
            "max_dd_pct_of_start": round(100 * dd / start, 2), "taken_ids": {r["id"] for r in taken}, "curve": curve}


def crisis(real_taken: list[dict], start: float = 2000.0) -> dict:
    out = {}
    for name, (a, b) in CRISES.items():
        lo, hi = _ts(a), _ts(b) + 86400
        inside = [r for r in real_taken if r["entry_t"] < hi and r["ACTUAL_exit_t"] > lo]
        if not inside:
            out[name] = {"trades": 0}
            continue
        act = sum(r["ACTUAL_net"] for r in inside)
        hold = sum(r["HOLD_net"] for r in inside if r.get("HOLD_net") is not None)
        x2 = sum(1 for r in inside if str(r["ACTUAL_bell"]).startswith("X2"))
        gaps = [r for r in inside if r["ACTUAL_bell"] == "X1_STOP_GAP"]
        out[name] = {"trades": len(inside), "net_with_bells_usd": round(act, 2), "net_held_to_cap_usd": round(hold, 2),
                     "bells_saved_usd": round(act - hold, 2), "x2_disaster_exits": x2, "gap_stop_exits": len(gaps),
                     "gap_stop_net_usd": round(sum(r["ACTUAL_net"] for r in gaps), 2),
                     "worst_trade_usd": round(min(r["ACTUAL_net"] for r in inside), 2)}
    return out


def score(out: str) -> dict:
    rows, missed = [], []
    for p in sorted(Path(out).glob("trades_*.pkl")):
        d = pickle.loads(p.read_bytes())
        rows += d["rows"]
        missed += d["missed"]
    split = lambda r: "DISCOVERY" if r["entry_t"] < DISC_END else "CONFIRM"  # noqa: E731
    res: dict[str, Any] = {"rulebook": xe.RULEBOOK, "engine": xe.ENGINE_VERSION}
    for sp in ("DISCOVERY", "CONFIRM"):
        R = [r for r in rows if split(r) == sp]
        real = [r for r in R if not r["shadow"]]
        rnd = [r for r in R if r["shadow"] == "RANDOM"]
        pf = portfolio(real)
        taken = [r for r in real if r["id"] in pf["taken_ids"]]
        res[sp] = {
            "all_real": _agg(real),
            "by_setup": _group(real, lambda r: r["setup"]),
            "by_type": _group(real, lambda r: r["type"]),
            "by_setup_type": _group(real, lambda r: f"{r['setup']}|{r['type']}"),
            "by_exit_bell": _group(real, lambda r: r["ACTUAL_bell"]),
            "random_baseline_by_type": _group(rnd, lambda r: r["type"]),
            "exit_comparison": {c: _agg(real, c) for c in ("ACTUAL_net", "AS_LONG_TERM_net", "AS_SHORT_TERM_net", "AS_INTRADAY_net", "HOLD_net")},
            "random_exit_comparison": {c: _agg(rnd, c) for c in ("ACTUAL_net", "AS_LONG_TERM_net", "AS_SHORT_TERM_net", "AS_INTRADAY_net", "HOLD_net")},
            "hold_by_type": {k: _agg([r for r in real if r["type"] == k], "HOLD_net") for k in xe.TYPES},
            "random_hold_by_type": {k: _agg([r for r in rnd if r["type"] == k], "HOLD_net") for k in xe.TYPES},
            "nets": {"real": [r["ACTUAL_net"] for r in real]},
            "by_S1": _group(real, lambda r: r.get("tag_S1")),
            "by_S3": _group(real, lambda r: r.get("tag_S3")),
            "by_btc_S1": _group(real, lambda r: r.get("tag_btc_S1")),
            "by_green_run_3plus": _group(real, lambda r: (r.get("tag_green_run_5m") or 0) >= 3),
            "by_expensive_coin": _group(real, lambda r: r.get("tag_expensive")),
            "by_coin": _group(real, lambda r: r["coin"]),
            "shadows": _group([r for r in R if r["shadow"]], lambda r: r["shadow"]),
            "missed_orders": sum(1 for m in missed if not m["shadow"] and (m["placed_t"] < DISC_END) == (sp == "DISCOVERY")),
            "portfolio": {k: v for k, v in pf.items() if k not in ("taken_ids", "curve")},
            "crisis": crisis(taken),
        }
    Path(out, "scorecard.json").write_text(json.dumps(res, indent=1, default=str))
    return res


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "score"])
    ap.add_argument("--db")
    ap.add_argument("--out", required=True)
    ap.add_argument("--coins", default=",".join(xe.COINS))
    ap.add_argument("--workers", type=int, default=5)
    ap.add_argument("--rules", default="C0", choices=list(xe.RULESETS))
    a = ap.parse_args(argv)
    out = Path(os.path.expanduser(a.out))
    out.mkdir(parents=True, exist_ok=True)
    if a.cmd == "run":
        coins = a.coins.split(",")
        with ProcessPoolExecutor(max_workers=a.workers) as ex:
            res = list(ex.map(run_coin, [a.db] * len(coins), coins, [str(out)] * len(coins), [a.rules] * len(coins)))
        (out / "run.json").write_text(json.dumps(res, indent=1))
        print(json.dumps(res, indent=1))
    else:
        r = score(str(out))
        print(json.dumps({sp: {"all_real": r[sp]["all_real"], "portfolio": r[sp]["portfolio"]} for sp in ("DISCOVERY", "CONFIRM")}, indent=1))


if __name__ == "__main__":
    main()
