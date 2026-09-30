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


if __name__ == "__main__":
    main()
