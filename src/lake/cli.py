"""Run the lake steps from the Terminal (low priority, so the live system is never slowed):

    nice -n 10 python -m src.lake.cli all BTC ETH SOL ADA AVAX      download, build and check these coins
    python -m src.lake.cli pull BTC | build BTC | bars BTC | check BTC one step (bars = 5m, 15m, 1h, 4h, daily from the 1-minute base)
    python -m src.lake.cli universe 120                                choose the coins by the written rule (reports/universe_v1.json)
    python -m src.lake.cli review15                                    re-test T3, H07 and the setups on LAB10 / TOP30 / ALL
    python -m src.lake.cli status                                      what the lake holds

Coins are given as BTC (traded against USDT on Binance) or as a full symbol (BTCUSDT).
"""
from __future__ import annotations

import json
import sys
import time

from src.lake import bars, quality, root, universe
from src.lake import binance_vision as bv


def sym(x: str) -> str:
    x = x.upper()
    return x if x.endswith(("USDT", "USDC", "BUSD", "BTC")) and len(x) > 4 else x + "USDT"


def status() -> dict:
    import duckdb

    out = {"root": str(root()), "symbols": []}
    rep = root() / "reports" / "quality"
    for p in sorted(rep.glob("*.json")) if rep.exists() else []:
        q = json.loads(p.read_text())
        out["symbols"].append({k: q.get(k) for k in ("symbol", "interval", "rows", "first", "last", "missing_pct", "broken_candles", "grade")})
    clean = root() / "clean"
    out["clean_mb"] = round(sum(p.stat().st_size for p in clean.rglob("*.parquet")) / 1e6, 1) if clean.exists() else 0
    raw = root() / "raw"
    out["raw_mb"] = round(sum(p.stat().st_size for p in raw.rglob("*.zip")) / 1e6, 1) if raw.exists() else 0
    del duckdb
    return out


def main(argv: list[str]) -> None:
    cmd, coins = (argv[0] if argv else "status"), [sym(c) for c in argv[1:]]
    if cmd == "status":
        print(json.dumps(status(), indent=1))
        return
    if cmd == "review15":                                     # python -m src.lake.cli review15   (docs/research/REVIEW_15.md)
        from src.lake import research

        u = json.loads((root() / "reports" / "universe_v1.json").read_text())
        chosen = u["chosen"]
        base = [research.base(s) for s in chosen]
        tiers = {"LAB10": [c for c in research.LAB10], "TOP30": base[:30], "ALL": base}
        rep = research.review15(chosen, tiers)
        print(json.dumps({t: {"coins": len(v["coins"]), "T3": v["T3"]["PASS"], "H07": v["H07"]["H07"]["status"], "H07-G": v["H07"]["H07-G"]["status"],
                              "setups": {k: x["status"] for k, x in v["setups"].items()}} for t, v in rep["tiers"].items()}, indent=1))
        return
    if cmd == "universe":                                     # python -m src.lake.cli universe [top]
        c = universe.candidates()
        u = universe.rank(c, top=int(argv[1]) if len(argv) > 1 else 120)
        print(json.dumps({k: u[k] for k in ("candidates", "eligible", "chosen")}))
        return
    for s in coins:
        t0 = time.time()
        r: dict = {"symbol": s}
        if cmd in ("pull", "all"):
            r["pull"] = bv.pull(s)
        if cmd in ("build", "all"):
            r["build"] = bv.build(s)
        if cmd in ("bars", "all"):
            r["bars"] = bars.build(s)["candles"]
        if cmd in ("check", "all"):
            q = quality.check(s)
            r["check"] = {k: q.get(k) for k in ("rows", "first", "last", "missing_pct", "gaps", "broken_candles", "jumps_30pct", "grade")}
        r["seconds"] = round(time.time() - t0, 1)
        print(json.dumps(r), flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
