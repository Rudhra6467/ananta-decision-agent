"""W500 v1 (data audit step 4; Madhav, 3 Nov 2026: "yes to all your recommendations and next steps"): do the narrow-universe results carry to the
next band of stocks? The frozen OC1, IB1 and GP1 rules, unchanged, on stocks just outside each study's own universe. Research years only.

  python -m india.w500 freeze     write registrations/w500_v1.json (the variants, bands, pass rule and code hashes) BEFORE any number is computed
  python -m india.w500 run        register W500, compute, record every variant; manifests/w500.json and registrations/w500_results_v1.md

Pass rule ("carries"): the same sign as the original, with t >= 2.0 in both periods, on the new band alone. The ledger's own verdict (family W500,
k = 11, the registry's standard bar) is recorded beside it. OC1 uses its frozen X2 m values from the OC1 run (not refitted on the new band).
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

from india import paths, registry

HERE = Path(__file__).parent
SPEC = HERE / "registrations" / "w500_v1.json"
RESULTS = HERE / "registrations" / "w500_results_v1.md"
CODE = ["india/ocstudy.py", "india/lab4.py", "india/gaplab.py", "india/w500.py"]
APPROVED = "Madhav, 3 Nov 2026 (chat: 'yes to all your recommendations and next steps', after the draft registrations/w500_v1_draft.md)"
BANDS = {"OC1": (100, 250), "IB1": (50, 150), "GP1": (250, 500)}
OC1_VARIANTS = [f"k{k}|{e}|{x}" for k in (15, 30) for e in ("E1", "E2") for x in ("X1", "X2")]
VARIANTS = ([f"OC1|STOCKS|{v}|vs_base" for v in OC1_VARIANTS] + ["IB1|STK|orb15|net", "IB1|STK|orb30|net"] + ["GP1|STK|gapdown2|open|hold1"])
T_MIN = 2.0


def _sha(rel: str) -> str:
    return hashlib.sha256((HERE.parent / rel).read_bytes()).hexdigest()[:16]


def freeze() -> dict:
    if SPEC.exists():
        raise SystemExit("w500_v1.json exists: the spec is frozen once")
    s = {"study": "W500", "family": "W500", "frozen_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "approved": APPROVED,
         "title": "W500: do the narrow-universe results (OC1, IB1, GP1) carry to the next band of stocks?",
         "hypothesis": "each VALIDATED stock variant of OC1 (top 100), IB1 (top 50) and GP1 (top 250), with its frozen rule, costs and periods, has the "
                       "same sign with t >= 2.0 in both periods on the next band of stocks alone",
         "bands": {k: {"ranks_above": lo, "ranks_to": hi} for k, (lo, hi) in BANDS.items()},
         "variants": {v: 1 for v in VARIANTS}, "pass_rule": {"carries": f"same sign as the original and t >= {T_MIN} in development and in validation"},
         "bar": {"union_k": len(VARIANTS), "z": round(registry.threshold(len(VARIANTS)), 3)},
         "periods": "each study's own: OC1 and IB1 2015-2017 / 2018-2023, GP1 2000-2017 / 2018-2023; nothing from 2024",
         "fixed_choices": ["universe chosen exactly as in each study (OC1 and IB1: the previous session's rank; GP1: the stock panel's rank)",
                           "OC1 breadth stays the eligible top 50 (it is a market-state filter, not the traded universe)",
                           "OC1 X2 uses the m values frozen in the OC1 run (manifests/oc_v1_results.json m_stocks), not refitted",
                           "costs as in each study, by the stock's own liquidity rank where the study does that",
                           "a failure is a finding about how wide the edge is, not a rejection of the original"],
         "code_sha": {c: _sha(c) for c in CODE}}
    SPEC.write_text(json.dumps(s, indent=1))
    return s


def _oc1() -> dict:
    from india import ocstudy as oc
    m = json.loads((paths.manifest_dir() / "oc_v1_results.json").read_text())["m_stocks"]
    m_s = {(int(k.split("|")[0]), k.split("|")[1]): {("dev" if kk == "dev" else int(kk)): vv for kk, vv in v.items()} for k, v in m.items()}
    oc.STOCK_BAND = BANDS["OC1"]
    days, specials = oc._calendar()
    index = oc.load_index()
    st1, _, c1 = oc.stock_pass(index, days, specials, None, print)
    st1 = oc.stock_costs(st1)
    st2, _, _ = oc.stock_pass(index, days, specials, m_s, print)
    st2 = oc.stock_costs(st2)
    stt = pd.concat([st1, st2], ignore_index=True)
    sx = pd.concat([stt[stt["X"] == "X1"], oc.x2_select(stt)])
    out = {}
    for v in OC1_VARIANTS:
        k, E, X = v.split("|")
        sel = (sx["k"] == int(k[1:])) & (sx["E"] == E) & (sx["X"] == X)
        tf, tb = sx[sel & (sx["version"] == "FILTERED")], sx[sel & (sx["version"] == "BASELINE")]
        s = oc.vs_base(tf, tb, ["date", "entity"]).rename(columns={"diff": "net"})
        base = oc.day_series(tb, "STOCKS")
        filt = oc.day_series(tf, "STOCKS")
        out[f"OC1|STOCKS|{v}|vs_base"] = {"dev": oc.tstat(s.loc[s["year"] <= oc.DEV_LAST, "net"]), "val": oc.tstat(s.loc[s["year"] > oc.DEV_LAST, "net"]),
                                          "extra": {"unit": "net bps per trade, filtered minus baseline (per-day mean)", "counts": c1,
                                                    "filtered_net": {"dev": oc.tstat(filt.loc[filt["year"] <= oc.DEV_LAST, "net"]), "val": oc.tstat(filt.loc[filt["year"] > oc.DEV_LAST, "net"])},
                                                    "baseline_net": {"dev": oc.tstat(base.loc[base["year"] <= oc.DEV_LAST, "net"]), "val": oc.tstat(base.loc[base["year"] > oc.DEV_LAST, "net"])}}}
    oc.STOCK_BAND = (0, 100)
    return out


def _ib1() -> dict:
    from india import lab4
    lab4.STOCK_BAND = BANDS["IB1"]
    lab4._STK.clear()
    out = {}
    for kind in ("orb15", "orb30"):
        T, Ct = lab4._stock_ib(kind)
        r = lab4._ib_row(T, Ct)
        r["extra"]["trades"] = int(len(T))
        out[f"IB1|STK|{kind}|net"] = r
    lab4.STOCK_BAND = (0, 50)
    lab4._STK.clear()
    return out


def _gp1() -> dict:
    from india import gaplab
    gaplab.STOCK_BAND = BANDS["GP1"]
    r = gaplab.gp1_results()["STK|gapdown2|open|hold1"]
    gaplab.STOCK_BAND = (0, 250)
    return {"GP1|STK|gapdown2|open|hold1": r}


def carries(dev, val, expect: int = 1) -> bool:
    try:
        return all(float(x[1]) * expect >= T_MIN for x in (dev, val))
    except (TypeError, ValueError):
        return False


def run() -> dict:
    s = json.loads(SPEC.read_text())
    if not s.get("approved"):
        raise SystemExit("W500 is not approved")
    for c, h in s["code_sha"].items():
        if c != "india/w500.py" and _sha(c) != h:
            raise SystemExit(f"{c} changed since the freeze")
    k = int(s["bar"]["union_k"])
    reg = registry.register("W500", family=s["family"], title=s["title"], hypothesis=s["hypothesis"], variants=list(s["variants"]),
                            note=f"spec india/registrations/w500_v1.json frozen {s['frozen_at']} ({s['approved']})", union_k=k)
    res = {**_gp1(), **_ib1(), **_oc1()}
    from india.gaplab import _clean
    rows = []
    for var, expect in s["variants"].items():
        r = res.get(var)
        if r is None:
            ok = False
            line = registry.record(reg, var, (float("nan"), float("nan"), 0), (float("nan"), float("nan"), 0), extra={"missing": True}, expect=expect)
        else:
            ok = carries(r["dev"], r["val"], expect)
            ex = _clean({**(r.get("extra") or {}), "carries": ok, "band": BANDS[var.split("|")[0]]})
            line = registry.record(reg, var, tuple(r["dev"]), tuple(r["val"]), extra=ex, expect=expect)
        rows.append({"variant": var, "verdict": line["verdict"], "z": line["z"], "dev": _clean(list(line["dev"])), "val": _clean(list(line["val"])), "carries": ok})
    out = {"study": "W500", "registered_at": reg["at"], "k": k, "rows": rows}
    (paths.manifest_dir() / "w500.json").write_text(json.dumps(out, indent=1, default=str))
    registry.mirror_to_catalog()
    page(out)
    return out


TAKEAWAY = [   # 3 Nov 2026, after the run
    "- Every one of these is a RELATIVE result, and each one carries: the effect is not confined to the most traded names. None of them is a "
    "way to make money by itself.",
    "- OC1: on ranks 101-250 the filtered trades still lose about 25-33 bps per trade after costs in both periods (the baseline loses about "
    "24-29). 'vs_base' is positive because the filters skip many losing trades. The protocol tells you when NOT to trade a stock at the open; "
    "it does not find trades that pay.",
    "- IB1: on ranks 51-150 the breakout trades lose about 0.10-0.14% per trade after costs, against about 0.25% for random intraday entries. "
    "Better than random, but still a loss.",
    "- GP1: buying the open after a 2% gap-down earns on paper on ranks 251-500 too (about +2.0% dev, +0.3% val per trade after costs). The "
    "GP1 results page already says it cannot be traded as defined (the gap is known only once the open prints) and that the edge has faded; "
    "a wider universe does not change that.",
    "- So: no rule, book or paper position changes. The finding goes into each study's write-up as 'holds beyond the most traded names'.",
]


def _orig() -> dict:
    o = {}
    for r in registry._rows():
        if r.get("kind") == "result" and r.get("study") in ("OC1", "IB1", "GP1"):
            o[f"{r['study']}|{r['variant']}"] = r
    return o


def page(out: dict) -> Path:
    orig = _orig()
    L = ["# W500 v1 results: do the narrow-universe results carry to the next band of stocks?", "",
         f"Frozen spec registrations/w500_v1.json ({APPROVED}). Bands: OC1 ranks 101-250, IB1 ranks 51-150, GP1 ranks 251-500. HISTORICAL BACKTEST, "
         f"research years only. 'Carries' = same sign and t >= {T_MIN} in both periods on the new band; the ledger verdict uses k = {out['k']}.", "",
         "| variant | original dev t | original val t | new band dev mean | t | new band val mean | t | carries | ledger verdict |", "|---|---|---|---|---|---|---|---|---|"]
    for r in out["rows"]:
        o = orig.get(r["variant"]) or {}
        f = lambda x: "" if x is None else (f"{x:+.4f}" if abs(x) < 1 else f"{x:+.2f}")
        L.append(f"| {r['variant'].replace('|', ' · ')} | {o.get('dev', [None, None])[1] or 0:+.1f} | {o.get('val', [None, None])[1] or 0:+.1f} | "
                 f"{f(r['dev'][0])} | {(r['dev'][1] or 0):+.1f} | {f(r['val'][0])} | {(r['val'][1] or 0):+.1f} | {'yes' if r['carries'] else 'no'} | {r['verdict']} |")
    n = sum(1 for r in out["rows"] if r["carries"])
    L += ["", f"{n} of {len(out['rows'])} variants carry to the next band.", "", "## What 'carries' does and does not mean (written after the run, from the ledger extras)", ""] + TAKEAWAY + [""]
    RESULTS.write_text("\n".join(L))
    return RESULTS


if __name__ == "__main__":
    paths.ensure()
    w = sys.argv[1] if len(sys.argv) > 1 else ""
    if w == "freeze":
        print(json.dumps(freeze(), indent=1))
    elif w == "run":
        print(json.dumps(run(), indent=1, default=str))
    else:
        print(__doc__)
