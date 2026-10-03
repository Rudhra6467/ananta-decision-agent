"""Review #9 (docs/repair_shop/REVIEW_9.md): the Explorer's history-replay trades split by the zone and market context at entry.

    python -m src.research.zone_splits --trades ~/ananta_runs/explorer_v0 --db .../lab5_5m.sqlite --out ~/ananta_runs/zones

Context comes from daily bars that closed before the entry's day only. No new replay: the trades and their RANDOM baseline come
from the existing rulebook v0 replay (same engine as the live Explorer).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import pickle
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

from src.research import reads as R
from src.research import zones as Z

DAY = 86400
SUPPORTED = {"AVERAGE-200", "CONFLUENCE", "SWING-NEW"}


class Context:
    """Zone maps per coin per day, built lazily and cached (SWING part refreshed every 5 days, as in review #6)."""

    def __init__(self, D: list[tuple], btc: list[tuple]):
        self.S = R.Series(D)
        self.A = Z.Arr(self.S)
        self.B = R.Series(btc)
        self.cache: dict[int, list[dict]] = {}
        self.swing: tuple[int, list[dict]] | None = None

    def zones(self, i: int) -> list[dict]:
        if i not in self.cache:
            if self.swing is None or not (0 <= i - self.swing[0] < Z.REFRESH):
                self.swing = (i, Z.swing_zones(self.A, i))
            self.cache[i] = Z.zone_map(self.A, i, self.swing[1])
        return self.cache[i]

    def at(self, t: int, price: float) -> dict | None:
        i = self.S.at(t - t % DAY)                       # the entry's day; zones use bars before it
        if i is None or i < 400 or math.isnan(self.A.atr[i - 1]):
            return None
        atr = float(self.A.atr[i - 1])
        sup = [z for z in self.zones(i) if z["bot"] <= price <= z["top"] + 0.5 * atr]
        bi = self.B.at(self.S.t[i - 1])
        g = bool(bi is not None and self.B.ema50[bi] is not None and self.B.c[bi] > self.B.ema50[bi])
        return {"Z": any(set(Z.groups(z)) & SUPPORTED for z in sup), "Zany": bool(sup), "G": g}


def welch(a: list[float], b: list[float]) -> float | None:
    if len(a) < 3 or len(b) < 3:
        return None
    va, vb = statistics.variance(a), statistics.variance(b)
    se = math.sqrt(va / len(a) + vb / len(b))
    return (statistics.mean(a) - statistics.mean(b)) / se if se > 0 else None


def _m(xs: list[float]) -> float | None:
    return round(statistics.mean(xs), 3) if xs else None


def split_report(rows: list[dict], key) -> dict:
    out = {}
    for sp, lo, hi in (("DISCOVERY", 0, R.DISC_END), ("CONFIRM", R.DISC_END, R.CONF_END)):
        rr = [r for r in rows if lo <= r["entry_t"] < hi and r["ctx"] is not None]
        real = [r for r in rr if not r["shadow"]]
        rnd = [r for r in rr if r["shadow"] == "RANDOM"]
        ri = [r["ACTUAL_net"] for r in real if key(r["ctx"])]
        ro = [r["ACTUAL_net"] for r in real if not key(r["ctx"])]
        qi = [r["ACTUAL_net"] for r in rnd if key(r["ctx"])]
        qo = [r["ACTUAL_net"] for r in rnd if not key(r["ctx"])]
        out[sp] = {"real_in": {"n": len(ri), "mean_usd": _m(ri), "win": round(sum(x > 0 for x in ri) / len(ri), 3) if ri else None},
                   "real_out": {"n": len(ro), "mean_usd": _m(ro)}, "random_in": {"n": len(qi), "mean_usd": _m(qi)},
                   "random_out": {"n": len(qo), "mean_usd": _m(qo)},
                   "t_vs_random_in": None if welch(ri, qi) is None else round(welch(ri, qi), 2),
                   "t_vs_real_out": None if welch(ri, ro) is None else round(welch(ri, ro), 2)}
    d, c = out["DISCOVERY"], out["CONFIRM"]
    ok_d = (d["real_in"]["mean_usd"] or -1) > 0 and (d["t_vs_random_in"] or 0) >= 2 and (d["t_vs_real_out"] or 0) >= 2
    ok_c = c["real_in"]["mean_usd"] is not None and c["real_out"]["mean_usd"] is not None and c["real_in"]["mean_usd"] > c["real_out"]["mean_usd"]
    out["status"] = "PASS" if ok_d and ok_c else "NOT_CONFIRMED" if ok_d else "FAIL"
    return out


SPLITS = {"Z": lambda c: c["Z"], "Zany": lambda c: c["Zany"], "G": lambda c: c["G"], "Z_and_G": lambda c: c["Z"] and c["G"]}


def review9(trades_dir: str, db: str, cache: Path) -> dict:
    btc = R.cached_daily(db, "BTC", cache, R.CONF_END)
    rows = []
    for p in sorted(Path(os.path.expanduser(trades_dir)).glob("trades_*.pkl")):
        coin = p.stem.split("_", 1)[1]
        d = pickle.loads(p.read_bytes())
        ctx = Context(R.cached_daily(db, coin, cache, R.CONF_END), btc)
        n = 0
        for r in d["rows"]:
            if r["shadow"] not in ("", "RANDOM") or r["entry_t"] >= R.CONF_END:
                continue
            rows.append({"coin": coin, "entry_t": r["entry_t"], "shadow": r["shadow"], "setup": r["setup"], "ACTUAL_net": r["ACTUAL_net"],
                         "ctx": ctx.at(r["entry_t"], r["entry"])})
            n += 1
        print(coin, n, file=sys.stderr)
    rep = {k: split_report(rows, f) for k, f in SPLITS.items()}
    by_setup = {}
    for s in sorted({r["setup"] for r in rows if not r["shadow"]}):
        by_setup[s] = split_report([r for r in rows if r["setup"] == s or r["shadow"] == "RANDOM"], SPLITS["Z"])
    rep["_by_setup_Z"] = by_setup
    rep["_counts"] = {"real": sum(1 for r in rows if not r["shadow"]), "random": sum(1 for r in rows if r["shadow"] == "RANDOM"),
                      "no_context": sum(1 for r in rows if r["ctx"] is None)}
    return rep


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trades", default="~/ananta_runs/explorer_v0")
    ap.add_argument("--db", required=True)
    ap.add_argument("--out", default="~/ananta_runs/zones")
    a = ap.parse_args(argv)
    out = Path(os.path.expanduser(a.out))
    out.mkdir(parents=True, exist_ok=True)
    rep = review9(a.trades, a.db, Path(os.path.expanduser("~/ananta_runs/reads")))
    rep["_meta"] = {"run": datetime.now(timezone.utc).isoformat(timespec="seconds"), "pre_registration": "docs/repair_shop/REVIEW_9.md"}
    (out / "review9_results.json").write_text(json.dumps(rep, indent=1))
    print(rep["_counts"])
    for k in SPLITS:
        v = rep[k]
        d, c = v["DISCOVERY"], v["CONFIRM"]
        print(f"{k:8} {v['status']:13} DISC in {d['real_in']} out {d['real_out']} rnd_in {d['random_in']} t_rnd {d['t_vs_random_in']} t_out {d['t_vs_real_out']}"
              f" | CONF in {c['real_in']['n']} {c['real_in']['mean_usd']} out {c['real_out']['n']} {c['real_out']['mean_usd']} rnd_in {c['random_in']['mean_usd']}")
    for s, v in rep["_by_setup_Z"].items():
        d, c = v["DISCOVERY"], v["CONFIRM"]
        print(f"  {s} Z {v['status']:13} DISC in {d['real_in']['n']} {d['real_in']['mean_usd']} out {d['real_out']['n']} {d['real_out']['mean_usd']} t_out {d['t_vs_real_out']}"
              f" | CONF in {c['real_in']['n']} {c['real_in']['mean_usd']} out {c['real_out']['n']} {c['real_out']['mean_usd']}")


if __name__ == "__main__":
    main()
