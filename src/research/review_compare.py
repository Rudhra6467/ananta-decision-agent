"""Compare repair-shop variants with the control by the pre-registered rule (docs/repair_shop/REVIEW_1.md).

    python -m src.research.review_compare --dir ~/ananta_runs/review1 --control C0 --variants P1a,P1b,P2,P3,V1c
"""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path

SPLITS = ("DISCOVERY", "CONFIRM")


def welch_t(a: list[float], b: list[float]) -> float:
    """t of mean(a) - mean(b), Welch (unequal variances)."""
    if len(a) < 2 or len(b) < 2:
        return 0.0
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    va = sum((x - ma) ** 2 for x in a) / (len(a) - 1)
    vb = sum((x - mb) ** 2 for x in b) / (len(b) - 1)
    se = math.sqrt(va / len(a) + vb / len(b))
    return (ma - mb) / se if se > 0 else 0.0


def crisis_total(sc: dict) -> float:
    return sum(v.get("net_with_bells_usd", 0.0) for sp in SPLITS for v in sc[sp]["crisis"].values())


def compare(d: Path, control: str, variants: list[str]) -> dict:
    sc = {v: json.loads((d / v / "scorecard.json").read_text()) for v in [control] + variants}
    c = sc[control]
    out = {"control": control, "rule": "both splits: mean net > control with Welch t >= 2.0, and crisis loss not >20% worse", "variants": {}}
    c_crisis = crisis_total(c)
    for v in variants:
        s = sc[v]
        row = {}
        ok = True
        for sp in SPLITS:
            a, b = s[sp]["nets"]["real"], c[sp]["nets"]["real"]
            t = welch_t(a, b)
            ma = sum(a) / len(a) if a else 0.0
            mb = sum(b) / len(b) if b else 0.0
            passed = ma > mb and t >= 2.0
            ok &= passed
            row[sp] = {"n": len(a), "mean_usd": round(ma, 3), "control_mean_usd": round(mb, 3), "welch_t": round(t, 2),
                       "pass": passed, "account_return_pct": s[sp]["portfolio"]["return_pct"],
                       "win_rate": s[sp]["all_real"].get("win_rate")}
        vc = crisis_total(s)
        crisis_ok = vc >= c_crisis - 0.20 * abs(c_crisis)
        row["crisis_total_usd"] = round(vc, 2)
        row["control_crisis_total_usd"] = round(c_crisis, 2)
        row["crisis_ok"] = crisis_ok
        row["PASS"] = bool(ok and crisis_ok)
        out["variants"][v] = row
    # HOLD: setups vs random entries (is the hold edge from the setups or from drift?)
    out["hold_vs_random"] = {sp: {"real_hold": c[sp]["hold_by_type"], "random_hold": c[sp]["random_hold_by_type"]} for sp in SPLITS}
    return out


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--control", default="C0")
    ap.add_argument("--variants", default="P1a,P1b,P2,P3,V1c")
    a = ap.parse_args(argv)
    d = Path(os.path.expanduser(a.dir))
    r = compare(d, a.control, a.variants.split(","))
    (d / "review_compare.json").write_text(json.dumps(r, indent=1))
    print(json.dumps(r, indent=1))


# ---------------------------------------------------------------------------
# Review #3 rule (docs/repair_shop/REVIEW_3.md)
# ---------------------------------------------------------------------------
def _rows(run_dir: Path) -> list[dict]:
    import pickle

    rows = []
    for p in sorted(run_dir.glob("trades_*.pkl")):
        rows += pickle.loads(p.read_bytes())["rows"]
    return rows


def review3(r3_dir: Path, c0_scorecard: Path, variants=("R3a", "R3b", "R3c", "R3all")) -> dict:
    disc_end = 1704067200
    c0 = json.loads(c0_scorecard.read_text())["DISCOVERY"]["nets"]["real"]
    out = {"rule": "DISCOVERY: mean > 0; beats random SHORT_TERM (same run) by Welch t>=2; beats C0 by Welch t>=2",
           "c0_mean": round(sum(c0) / len(c0), 3), "variants": {}}
    for v in variants:
        rows = _rows(r3_dir / v)
        res = {}
        for sp, keep in (("DISCOVERY", lambda r: r["entry_t"] < disc_end), ("CONFIRM_in_sample", lambda r: r["entry_t"] >= disc_end)):
            real = [r["ACTUAL_net"] for r in rows if not r["shadow"] and keep(r)]
            rnd = [r["ACTUAL_net"] for r in rows if r["shadow"] == "RANDOM" and r["type"] == "SHORT_TERM" and keep(r)]
            m = sum(real) / len(real) if real else float("nan")
            res[sp] = {"n": len(real), "mean_usd": round(m, 3), "win_rate": round(sum(1 for x in real if x > 0) / len(real), 3) if real else None,
                       "random_st_n": len(rnd), "random_st_mean_usd": round(sum(rnd) / len(rnd), 3) if rnd else None,
                       "t_vs_random": round(welch_t(real, rnd), 2), "t_vs_c0": round(welch_t(real, c0), 2) if sp == "DISCOVERY" else None}
        d = res["DISCOVERY"]
        res["PASS"] = bool(d["n"] and d["mean_usd"] > 0 and d["t_vs_random"] >= 2 and d["t_vs_c0"] >= 2)
        out["variants"][v] = res
    return out


if __name__ == "__main__":
    if os.getenv("REVIEW3"):
        r = review3(Path(os.path.expanduser(os.environ["REVIEW3"])), Path(os.path.expanduser(os.environ["C0_SCORECARD"])))
        print(json.dumps(r, indent=1))
    else:
        main()
