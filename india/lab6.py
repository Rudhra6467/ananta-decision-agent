"""Lab 6 (2 Nov 2026; Madhav 19:05 Toronto: "Yes , set it up."): RS1, relative strength against the Nifty on Indian stocks. The spec
(india/registrations/rs1_v1.json) was written and committed before any outcome was read; `run` registers the study with the spec's frozen k,
computes, and records every variant in the ledger. Research rows only: the stock panel stops at 2023 here; nothing dated 2024 or later and no
sealed folder.

  python -m india.lab6 check      signal counts per period only (no means, no t, no verdicts): a code check before the run
  python -m india.lab6 run        register, compute, record; manifests/lab6_rs1.json and registrations/rs1_results_v1.md
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

from india import paths, registry
from india import teachers_stock as ts
from india.lab3 import _clean

REG_DIR = Path(__file__).resolve().parent / "registrations"
CUT = pd.Timestamp("2024-01-01")
SPLIT = 2018
COLS = ["sid", "symbol", "date", "liq_rank", "rs_ret126", "rs_ret63", "net20", "net60", "dist_sma50", "nifty_below_both"]


def spec() -> dict:
    return json.loads((REG_DIR / "rs1_v1.json").read_text())


def frame() -> pd.DataFrame:
    P = pd.read_parquet(paths.gold() / "teachers" / "stock_panel.parquet", columns=COLS)
    P["date"] = pd.to_datetime(P["date"])
    P = P[(P["date"] < CUT) & (P["liq_rank"] <= 250)].reset_index(drop=True)
    for v in ("rs_ret126", "rs_ret63"):
        P[f"pct_{v}"] = P.groupby("date")[v].rank(pct=True)
    P["nifty_down"] = P["nifty_below_both"].fillna(False).astype(bool)
    return P


def plan(P: pd.DataFrame) -> dict:
    """variant -> (rows, signal mask, outcome column), exactly as the spec's definitions."""
    top126 = P["pct_rs_ret126"] >= 0.90
    out = {
        "top10|rs126|net20": (P, top126, "net20"),
        "top10|rs63|net20": (P, P["pct_rs_ret63"] >= 0.90, "net20"),
        "top10|rs126|net60": (P, top126, "net60"),
        "top10|rs126_nochase|net20": (P, top126 & (P["dist_sma50"] <= 0.08), "net20"),
        "bottom10|rs126|net20": (P, P["pct_rs_ret126"] <= 0.10, "net20"),
    }
    D = P[P["nifty_down"]]
    out["top10|rs126|net20|nifty_down"] = (D, D["pct_rs_ret126"] >= 0.90, "net20")
    return out


def _counts(d: pd.DataFrame, on: pd.Series, col: str) -> dict:
    x = d[on.fillna(False).astype(bool)].dropna(subset=[col])
    y = x["date"].dt.year
    return {"signals_dev": int((y < SPLIT).sum()), "signals_val": int((y >= SPLIT).sum()), "sessions": int(x["date"].nunique())}


def check() -> dict:
    P = frame()
    return {k: _counts(d, on, col) for k, (d, on, col) in plan(P).items()}


def run(rerun_reason: str | None = None) -> dict:
    s = spec()
    k = int(s["bar"]["union_k"])
    if abs(registry.threshold(k) - float(s["bar"]["z"])) > 0.01:
        raise ValueError(f"RS1: the spec's z {s['bar']['z']} does not match k {k}")
    reg = registry.register("RS1", family=s["family"], title=s["title"], hypothesis=s["hypothesis"], variants=list(s["variants"]),
                            note="spec india/registrations/rs1_v1.json (written and committed before the run)", bar_families=s["bar"].get("bar_families"),
                            union_k=k, rerun_reason=rerun_reason)
    P = frame()
    rows = []
    for var, (d, on, col) in plan(P).items():
        expect = s["variants"][var]
        r = ts.level(d, on, col)
        extra = {**r["extra"], **_counts(d, on, col)}
        line = registry.record(reg, var, tuple(r["dev"]), tuple(r["val"]), extra=_clean(extra), expect=expect)
        rows.append({"variant": var, "expect": expect, "verdict": line["verdict"], "z": line["z"], "dev": _clean(list(line["dev"])),
                     "val": _clean(list(line["val"])), "extra": _clean(line["extra"])})
    out = {"study": "RS1", "registered_at": reg["at"], "k": k, "rows": rows}
    (paths.manifest_dir() / "lab6_rs1.json").write_text(json.dumps(out, indent=1, default=str))
    _page(out)
    registry.mirror_to_catalog()
    return out


def _pct(x) -> str:
    return "n/a" if x is None or x != x else f"{100 * x:+.2f}%"


def _t(x) -> str:
    return "n/a" if x is None or x != x else f"{x:.2f}"


def _page(out: dict) -> None:
    L = ["# RS1 results: relative strength against the Nifty (2000-2023)", "",
         f"Registered {out['registered_at']}; k {out['k']}, bar z {registry.threshold(out['k']):.2f}. Spec: `india/registrations/rs1_v1.json`.", "",
         "| variant | verdict | 2000-17 vs average stock (t) | 2018-23 vs average stock (t) | signals |", "|---|---|---|---|---|"]
    for r in out["rows"]:
        d, v, e = r["dev"], r["val"], r["extra"]
        L.append(f"| {r['variant']} | {r['verdict']} | {_pct(d[0])} ({_t(d[1])}) | {_pct(v[0])} ({_t(v[1])}) | {e.get('signals_dev')} / {e.get('signals_val')} |")
    (REG_DIR / "rs1_results_v1.md").write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    cmd = (sys.argv[1:] or ["check"])[0]
    print(json.dumps(check() if cmd == "check" else run(), indent=1, default=str))
