"""Review #21: E3 (Explorer engine replay on the lake) and B3 (review #11 on the lake). docs/research/REVIEW_21.md

  python -m src.research.review21 replay [--workers 4]   # E3: replay every TOP30/ALL coin, trades in ~/ananta_runs/review21
  python -m src.research.review21 score                  # E3 + B3 verdicts -> ~/ananta_lake/reports/review21_results.json
"""
from __future__ import annotations

import json
import os
import pickle
import statistics
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

OUT = Path(os.path.expanduser("~/ananta_runs/review21"))


def lake_5m(_db: str, coin: str) -> list[tuple]:
    import duckdb

    from src.lake.binance_vision import clean_dir
    from src.research import explorer_replay as ER

    p = clean_dir("5m") / f"symbol={coin}USDT" / "**" / "*.parquet"
    return [tuple(r) for r in duckdb.sql(f"SELECT t, o, h, l, c, v FROM read_parquet('{p}', hive_partitioning=true) "
                                         f"WHERE t < {ER.CONF_END} ORDER BY t").fetchall()]


def _one(coin: str) -> dict:
    from src.research import explorer_replay as ER

    ER.load_5m = lake_5m                                    # same engine, lake candles
    if (OUT / f"trades_{coin}.pkl").exists():
        return {"coin": coin, "cached": True}
    return ER.run_coin("lake", coin, str(OUT))


def coins_all() -> list[str]:
    from src.lake import research as L
    from src.lake import root

    u = json.loads((root() / "reports" / "universe_v1.json").read_text())["chosen"]
    return [L.base(s) for s in u]


def replay(workers: int = 4) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    cs = coins_all()
    cs = ["BTC"] + [c for c in cs if c != "BTC"]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for r in pool.map(_one, cs):
            print(json.dumps(r), flush=True)


def _mk(rows):
    out = []
    for r in sorted(rows, key=lambda x: x["entry_t"]):
        if out and r["entry_t"] - out[-1][0]["entry_t"] <= 3 * 86400:
            out[-1].append(r)
        else:
            out.append([r])
    return out


def e3_verdict(coins: list[str]) -> dict:
    from src.research import explorer_replay as ER

    rows = []
    for c in coins:
        p = OUT / f"trades_{c}.pkl"
        if p.exists():
            rows += pickle.loads(p.read_bytes())["rows"]
    res = {}
    for sp in ("DISCOVERY", "CONFIRM"):
        R = [r for r in rows if (r["entry_t"] < ER.DISC_END) == (sp == "DISCOVERY") and r.get("ACTUAL_net") is not None]
        e3 = [r for r in R if not r["shadow"] and r["setup"] == "E3"]
        rnd = {}
        for r in R:
            if r["shadow"] == "RANDOM":
                rnd.setdefault(r["type"], []).append(r["ACTUAL_net"])
        base = {k: statistics.mean(v) for k, v in rnd.items() if v}
        for r in e3:
            r["x"] = r["ACTUAL_net"] - base.get(r["type"], 0.0)
        mk = _mk(e3)
        xs = [statistics.mean(r["x"] for r in m) for m in mk]
        sd = statistics.stdev(xs) if len(xs) > 2 else None
        res[sp] = {"trades": len(e3), "market_events": len(mk), "mean_net_usd": round(statistics.mean(r["ACTUAL_net"] for r in e3), 3) if e3 else None,
                   "win_rate": round(sum(r["ACTUAL_net"] > 0 for r in e3) / len(e3), 3) if e3 else None,
                   "random_by_type_usd": {k: round(v, 3) for k, v in base.items()},
                   "mean_excess_usd": round(statistics.mean(xs), 3) if xs else None,
                   "z": round(statistics.mean(xs) / (sd / len(xs) ** 0.5), 2) if sd else None,
                   "types": {t: sum(r["type"] == t for r in e3) for t in {r["type"] for r in e3}}}
    d, c = res["DISCOVERY"], res["CONFIRM"]
    ok_d = d["market_events"] >= 30 and (d["mean_excess_usd"] or -1) > 0 and (d["z"] or 0) >= 2.5
    res["status"] = "PASS" if ok_d and (c["mean_excess_usd"] or -1) > 0 else "NOT_CONFIRMED" if ok_d else (
        "INSUFFICIENT" if d["market_events"] < 30 else "FAIL")
    return res


def score() -> dict:
    from src.lake import research as L
    from src.lake import root
    from src.research import zones as Z

    allc = coins_all()
    tiers = {"LAB10": list(L.LAB10), "TOP30": allc[:30], "ALL": allc}
    u = json.loads((root() / "reports" / "universe_v1.json").read_text())["chosen"]
    D_all = L.load(u)
    rep = {"version": "review21.v1", "pre_registration": "docs/research/REVIEW_21.md", "tiers": {}}
    for name, cs in tiers.items():
        D = {c: D_all[c] for c in cs if c in D_all}
        b = Z.review11(D)
        rep["tiers"][name] = {"E3": e3_verdict(cs), "B": {k: v for k, v in b.items() if k in ("A1", "B1", "B2", "B3")}}
    (root() / "reports" / "review21_results.json").write_text(json.dumps(rep, indent=1, default=str))
    for name, t in rep["tiers"].items():
        e = t["E3"]
        print("==", name, "E3", e["status"], {sp: (e[sp]["trades"], e[sp]["market_events"], e[sp]["mean_net_usd"], e[sp]["mean_excess_usd"], e[sp]["z"]) for sp in ("DISCOVERY", "CONFIRM")})
        for k, v in t["B"].items():
            print("  ", k, v.get("status"), {sp: (v[sp].get("market_events"), v[sp].get("mean_excess20_pct"), v[sp].get("z")) for sp in ("DISCOVERY", "CONFIRM") if sp in v})
    return rep


if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "replay":
        replay(int(a[a.index("--workers") + 1]) if "--workers" in a else 4)
    else:
        score()
