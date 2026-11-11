"""Review 42's forward test on live paper, recording only (docs/research/REVIEW_42_FORWARD.md, written 11 Nov 2026 before any forward data
existed). After a coin's rarest 15-minute drops (its frozen worst 0.05%), a resting buy half the coin's drop size below the price, resting
60 minutes, sold 4 hours after the fill: once at Binance's one-minute prices, and once at NDAX's own recorded quotes (the worker Mac's
minute bid and ask), which decide. Nothing here trades or reaches a book. It prints counts only: the record is read once, at 30
independent days with an NDAX fill (no early looks).

    ~/ananta_venvs/lake/bin/python -m src.research.review42_forward       # weekly, after the Sunday lake update (scripts/lake_weekly.sh)
"""
from __future__ import annotations

import calendar
import json
import sqlite3
import time
from pathlib import Path

import numpy as np

from src.research import review41 as R

OUT = Path.home() / "ananta_runs" / "review42_forward"
WORKER = Path.home() / "ananta_worker_data"
FROM = calendar.timegm((2026, 11, 12, 0, 0, 0))        # 2026-11-12 00:00 UTC: the first forward minute
CUT_IDX, DEPTH, HOLD, WINDOW, THROUGH = 2, 0.5, 240, 3600, 0.999
PIT_MONTH = "2026-09"                                   # the last month the lake had a PIT30 list for on 11 Nov 2026 (frozen)
GOAL = 30
NDAX_SLACK = 600                                        # an NDAX quote counts for a moment if it is within 10 minutes after it


def universe(reg: dict | None = None) -> list[str]:
    """NDAX30, frozen: the PIT30 list of 2026-09 restricted to the coins NDAX listed on 11 Nov 2026 (written once to universe.json)."""
    f = OUT / "universe.json"
    if f.exists():
        return json.loads(f.read_text())["symbols"]
    reg = reg or json.loads(R.REGISTRY.read_text())
    pit = json.loads((R.LAKE / "reports" / "pit_top30.json").read_text())["months"][PIT_MONTH]
    syms = [s for s in pit if s.endswith("USDT") and not R._excluded(s[:-4]) and (reg.get("coins", {}).get(s[:-4]) or {}).get("ndax")]
    OUT.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps({"symbols": syms, "from": f"pit_top30 {PIT_MONTH} and NDAX-listed in universe_live.json", "frozen": "2026-11-11"}, indent=1))
    return syms


def ndax_quotes(coin: str, lo: int, hi: int) -> tuple[np.ndarray, np.ndarray, np.ndarray] | None:
    """The worker's NDAX (t, bid, ask) for one coin over [lo, hi), from its daily files; None if a needed day's file is missing."""
    ts, bids, asks = [], [], []
    for day in range(lo // R.DAY, (hi - 1) // R.DAY + 1):
        f = WORKER / f"l1_{time.strftime('%Y-%m-%d', time.gmtime(day * R.DAY))}.sqlite"
        if not f.exists():
            return None
        con = sqlite3.connect(f"file:{f}?mode=ro", uri=True)
        rows = con.execute("SELECT t, bid, ask FROM ndax WHERE coin=? AND bid > 0 AND ask >= bid AND t >= ? AND t < ? ORDER BY t", (coin, lo, hi)).fetchall()
        con.close()
        for t, b, a in rows:
            ts.append(t)
            bids.append(b)
            asks.append(a)
    return np.asarray(ts, dtype=np.int64), np.asarray(bids, dtype=np.float64), np.asarray(asks, dtype=np.float64)


def _first_at_or_after(t: np.ndarray, when: int, slack: int = NDAX_SLACK) -> int:
    i = int(np.searchsorted(t, when))
    return i if i < t.size and t[i] - when <= slack else -1


def ndax_side(coin: str, d: int, depth: float, newest_day: int) -> dict:
    """The same order on NDAX's own quotes: placed at NDAX's mid at the detection minute, filled when NDAX's ask trades through it by
    0.1% within 60 minutes, sold at NDAX's bid 4 hours after the fill (fee 0.20% each way)."""
    hi = d + WINDOW + HOLD * 60 + NDAX_SLACK + 60
    q = ndax_quotes(coin, d - 120, hi)
    if q is None:
        return {"status": "no data"} if (hi - 1) // R.DAY < newest_day else {"status": "waiting"}
    t, bid, ask = q
    i = _first_at_or_after(t, d + 59, 120)                # the quote at the close of the detection minute, where the order is placed
    if i < 0:
        return {"status": "no quote at detection"}
    placed = int(t[i])
    mid = (bid[i] + ask[i]) / 2
    limit = mid * (1 - depth)
    w = np.flatnonzero((t > placed) & (t <= placed + WINDOW) & (ask <= limit * THROUGH))
    if not w.size:
        return {"status": "not filled", "mid": mid, "limit": limit}
    f = int(w[0])
    x = _first_at_or_after(t, int(t[f]) + HOLD * 60)
    if x < 0:
        return {"status": "no quote at exit", "mid": mid, "limit": limit, "fill_t": int(t[f])}
    return {"status": "filled", "mid": mid, "limit": limit, "fill_t": int(t[f]), "exit_t": int(t[x]), "exit_bid": float(bid[x]),
            "net": float(bid[x] / limit - 1 - 2 * R.NDAX_FEE)}


def newest_worker_day() -> int:
    days = [calendar.timegm(time.strptime(p.stem[3:], "%Y-%m-%d")) // R.DAY for p in WORKER.glob("l1_*.sqlite")]
    return max(days) if days else 0


def run() -> dict:
    from src.research import review42 as Q

    OUT.mkdir(parents=True, exist_ok=True)
    log = OUT / "sightings.jsonl"
    done = {json.loads(x)["key"] for x in log.read_text().splitlines() if x.strip()} if log.exists() else set()
    cut = json.loads((R.OUT / "review41_cutoffs.json").read_text())
    reg = json.loads(R.REGISTRY.read_text())
    con = R._con()
    newest = newest_worker_day()
    added = 0
    for s in universe(reg):
        rec = cut["coins"].get(s) or {}
        cu = (rec["cuts"] if rec.get("own") else cut["pooled"])[CUT_IDX]
        depth = DEPTH * abs(cu)
        p = R.ONE_MIN / f"symbol={s}" / "**" / "*.parquet"
        try:
            r = con.execute(f"SELECT t, o, l, c FROM read_parquet('{p}', hive_partitioning=true) WHERE t >= {FROM - 900} ORDER BY t").fetchnumpy()
        except Exception:  # noqa: BLE001  a coin the lake does not hold
            continue
        t = np.asarray(r["t"], dtype=np.int64)
        if not t.size:
            continue
        o, low, c = (np.asarray(r[k], dtype=np.float64) for k in ("o", "l", "c"))
        x = R.r15(t, c)
        last = -(10 ** 12)
        for i in np.flatnonzero(np.isfinite(x) & (x <= cu) & (t >= FROM)):
            if t[i] - last < R.GAP:
                continue
            last = int(t[i])
            key = f"{s}:{int(t[i])}"
            if key in done:
                continue
            if t[i] + WINDOW + HOLD * 60 + 60 > t[-1]:
                continue                                   # its window is not over in the lake yet: next week
            got = Q.trade(t, o, low, c, int(i), depth, HOLD)
            nd = ndax_side(s[:-4], int(t[i]), depth, newest)
            if nd.get("status") == "waiting":
                continue                                   # the worker's quotes for those days are not here yet
            row = {"key": key, "coin": s[:-4], "detected": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime(int(t[i]))), "r15": float(x[i]),
                   "cut": cu, "depth": depth,
                   "binance": ({"filled": True, "gross": got[0], "fill_t": int(t[got[1]])} if got else {"filled": False}),
                   "ndax": nd, "recorded": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())}
            with log.open("a") as f:
                f.write(json.dumps(row) + "\n")
            done.add(key)
            added += 1
    rows = [json.loads(x) for x in log.read_text().splitlines() if x.strip()] if log.exists() else []
    nd_days = {r["detected"][:10] for r in rows if (r.get("ndax") or {}).get("status") == "filled"}
    status = {"sightings": len(rows), "binance_fills": sum(1 for r in rows if r["binance"]["filled"]),
              "ndax_fills": sum(1 for r in rows if (r.get("ndax") or {}).get("status") == "filled"),
              "independent_days_with_an_ndax_fill": len(nd_days), "goal": GOAL, "read_at_goal_only": True,
              "added_this_run": added, "updated": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())}
    (OUT / "status.json").write_text(json.dumps(status, indent=1))
    print(json.dumps(status))                              # counts only: no returns are totalled before the goal
    return status


if __name__ == "__main__":
    run()
