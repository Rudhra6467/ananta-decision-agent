"""DII1: domestic mutual fund cash flows (the largest part of DII; SEBI Mutual Funds Trends, filled 26 Oct 2026 by india/fiidii.py mfhistory)
against the Nifty, the same design as FII1 (india/xstudies.py), plus "domestic funds buying while foreign ones sell". Madhav's yes of 26 Oct
2026 12:19 Toronto. The spec (india/registrations/dii1_v1.json) was written before the run; `run` registers the study with the spec's frozen k,
computes, and records every variant in the ledger. Research rows only: nothing dated 2024 or later is used (silver/flows holds only rows
before 2024; the index panel comes from india.teachers_stock, cut at 2024-01-01).

  python -m india.diistudy check      event counts per period only (no means, no t, no verdicts): a code check before the run
  python -m india.diistudy run        register, compute, record; manifests/diistudy_dii1.json and registrations/dii1_results_v1.md
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from india import paths, registry
from india import teachers_stock as ts

REG_DIR = Path(__file__).resolve().parent / "registrations"
CUT = pd.Timestamp("2024-01-01")
SPLIT = ts.SPLIT
STUDY = "DII1"
WIN, MINP = 756, 500


def spec() -> dict:
    return json.loads((REG_DIR / "dii1_v1.json").read_text())


def _clean(x):
    if isinstance(x, dict):
        return {str(k): _clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_clean(v) for v in x]
    if isinstance(x, (np.floating, float)):
        return None if (x != x or math.isinf(x)) else float(x)
    if isinstance(x, np.integer):
        return int(x)
    if isinstance(x, np.bool_):
        return bool(x)
    return x


def _flows(category: str) -> pd.Series:
    fl = pd.read_parquet(paths.data_dir() / "silver/flows/fii_dii_cash.parquet")
    fl["date"] = pd.to_datetime(fl["date"])
    return fl[(fl["category"] == category) & (fl["date"] < CUT)].groupby("date")["net_cr"].sum().sort_index()


def _place(flow: pd.Series, sessions: pd.DatetimeIndex, after: bool) -> pd.Series:
    """Put each flow row on a Nifty session: the first session AFTER its date (after=True: trading-date rows, published later) or on/after it
    (after=False: NSDL reporting-date rows, as FII1). Rows landing on the same session are summed."""
    sess = sessions.values
    pos = np.searchsorted(sess, flow.index.values, side="right" if after else "left")
    keep = pos < len(sess)
    return pd.Series(flow.values[keep], index=pd.DatetimeIndex(sess[pos[keep]])).groupby(level=0).sum().reindex(sessions)


def frame() -> pd.DataFrame:
    piv = ts.index_panel()
    n = piv["NIFTY 50"].dropna()
    n = n[n.index < CUT]
    mf = _place(_flows("MF_equity"), n.index, after=True)
    fpi = _place(_flows("FPI_equity"), n.index, after=False)
    M = pd.DataFrame(index=n.index)
    M["date"] = n.index
    M["net1"] = mf
    M["net5"] = mf.rolling(5, min_periods=4).sum()
    M["fpi1"] = fpi
    for col in ("net1", "net5", "fpi1"):
        M[f"{col}_lo"] = M[col].rolling(WIN, min_periods=MINP).quantile(0.1)
        M[f"{col}_hi"] = M[col].rolling(WIN, min_periods=MINP).quantile(0.9)
    M["ok1"] = M["net1"].notna() & M["net1_lo"].notna()
    M["ok5"] = M["net5"].notna() & M["net5_lo"].notna()
    M["okx"] = M["ok1"] & M["fpi1"].notna() & M["fpi1_lo"].notna()
    M["neg1"] = (M["net1"] <= M["net1_lo"]) & M["ok1"]
    M["pos1"] = (M["net1"] >= M["net1_hi"]) & M["ok1"]
    M["neg5"] = (M["net5"] <= M["net5_lo"]) & M["ok5"]
    M["pos5"] = (M["net5"] >= M["net5_hi"]) & M["ok5"]
    M["diibuy_fiisell"] = (M["net1"] >= M["net1_hi"]) & (M["fpi1"] <= M["fpi1_lo"]) & M["okx"]
    for k in (1, 5, 20):
        M[f"nfwd{k}"] = ts._fwd_close(n, k)
    M["ret0"] = n.pct_change()
    return M


PLAN = [("neg5", "nfwd1", 1, "ok5"), ("neg5", "nfwd5", 5, "ok5"), ("neg5", "nfwd20", 20, "ok5"), ("neg1", "nfwd1", 1, "ok1"), ("neg1", "nfwd5", 5, "ok1"),
        ("pos5", "nfwd5", 5, "ok5"), ("pos5", "nfwd20", 20, "ok5"), ("pos1", "nfwd1", 1, "ok1"),
        ("diibuy_fiisell", "nfwd5", 5, "okx"), ("diibuy_fiisell", "nfwd20", 20, "okx")]


def _period_counts(M: pd.DataFrame, ev: str) -> dict:
    o = M[ev].fillna(False).astype(bool)
    y = M.index.year
    return {"events_dev": int((o & (y < SPLIT)).sum()), "events_val": int((o & (y >= SPLIT)).sum())}


def results(counts_only: bool = False) -> dict:
    M = frame()
    out = {}
    for ev, col, h, ok in PLAN:
        key = f"{ev}|{col}"
        cnt = {**_period_counts(M, ev), "base_sessions": int(M[ok].sum()), "first_base_session": str(M.index[M[ok]].min().date()) if M[ok].any() else None}
        if counts_only:
            out[key] = cnt
            continue
        r = ts.msplit(M, M[ev], col, h=h, base=M[ok])
        r["extra"] = {**r["extra"], **cnt}
        out[key] = r
    return out


def describe() -> dict:
    """Descriptive only: how the MF flow (in trailing-SD units) lines up with the previous, same and next session's Nifty return, and with the
    same session's FPI flow, by year."""
    M = frame()
    z = M["net1"] / M["net1"].rolling(252, min_periods=200).std().shift(1)
    D = pd.DataFrame({"r": M["ret0"], "z": z, "r_prev": M["ret0"].shift(1), "r_next": M["ret0"].shift(-1), "fpi": M["fpi1"], "y": M.index.year}).dropna()
    rows = {}
    for y, g in D.groupby("y"):
        if len(g) < 100:
            continue
        rows[int(y)] = {"corr_same_day": round(float(g["r"].corr(g["z"])), 3), "corr_flow_vs_previous_day_return": round(float(g["r_prev"].corr(g["z"])), 3),
                        "corr_flow_vs_next_day_return": round(float(g["r_next"].corr(g["z"])), 3), "corr_with_fpi_same_session": round(float(g["fpi"].corr(g["z"])), 3),
                        "days": int(len(g))}
    return {"by_year": rows, "note": "descriptive only; the MF row is placed on the session after its trading date, so 'same day' here is the publication session"}


def run() -> dict:
    s = spec()
    k = int(s["bar"]["union_k"])
    if abs(registry.threshold(k) - float(s["bar"]["z"])) > 0.01:
        raise ValueError(f"{STUDY}: the spec's z {s['bar']['z']} does not match k {k}")
    reg = registry.register(STUDY, family=s["family"], title=s["title"], hypothesis=s["hypothesis"], variants=list(s["variants"]),
                            note="spec india/registrations/dii1_v1.json (written before the run)", bar_families=s["bar"].get("bar_families"), union_k=k)
    res = results()
    rows = []
    for var, expect in s["variants"].items():
        r = res.get(var)
        if r is None:
            line = registry.record(reg, var, (float("nan"), float("nan"), 0), (float("nan"), float("nan"), 0), extra={"missing": True}, expect=expect)
        else:
            line = registry.record(reg, var, tuple(r["dev"]), tuple(r["val"]), extra=_clean(r.get("extra", {})), expect=expect)
        rows.append({"variant": var, "expect": expect, "verdict": line["verdict"], "z": line["z"], "dev": _clean(list(line["dev"])),
                     "val": _clean(list(line["val"])), "extra": _clean(line["extra"])})
    out = {"study": STUDY, "registered_at": reg["at"], "k": k, "rows": rows, "descriptive": describe()}
    (paths.manifest_dir() / "diistudy_dii1.json").write_text(json.dumps(out, indent=1, default=str))
    table(out)
    return out


TAKEAWAY: list[str] = [      # written after the run of 26 Oct 2026, from the numbers below
    "**Domestic mutual fund flows do not predict the Nifty's next 1, 5 or 20 sessions, and \"funds buying while foreigners sell\" is no cushion signal. "
    "All 10 versions are REJECTED (bar z 3.05; no |t| above 1.7).**",
    "- **Sharp fund outflow days (298 in 2007-17, 209 in 2018-23) and 5-session spells (290 / 222):** the Nifty did no worse afterwards (every |t| under 1.4).",
    "- **Sharp inflow days (409 / 219) and spells (439 / 215):** no better afterwards.",
    "- **Funds in their top tenth on a day foreigners are in their bottom tenth (123 / 106 days):** over 5 and 20 sessions the Nifty did slightly worse "
    "in 2007-17 and better in 2018-23 (+1.0% and +1.6%, t 1.6 and 1.2): the two periods disagree and neither is significant.",
    "- **Descriptive:** fund flows are the mirror of foreign flows (same-session correlation about -0.28 on average, -0.35 to -0.62 every year since "
    "2016). They track the day of the trade's own Nifty move (correlation up to 0.47 before 2019, slightly negative since, as funds have taken "
    "to buying the dips) and carry nothing about the next session (about 0.01).",
    "- **Data:** SEBI's Mutual Funds Trends, daily from January 2005, 262 months, each month equal to the page's own total; the mutual funds are "
    "the largest part of DII, insurers and banks are not in it. Rows used from the session after the trading day.",
    "- **What Ananta does with this:** nothing changes in the paper rules. 'DIIs are buying' is context, as 'FIIs are selling' is (FII1).",
]


def _f(x, pct: bool = True) -> str:
    if x is None or (isinstance(x, float) and x != x):
        return "n/a"
    return f"{100 * x:+.2f}%" if pct else f"{x:+.2f}"


def table(out: dict) -> Path:
    s = spec()
    L = [f"# {STUDY} results: {s['title']}", "", f"Registered {out['registered_at']} (spec `dii1_v1.json`, written before the run); family {s['family']}, "
         f"k = {out['k']}, z = {registry.threshold(out['k']):.2f}. Development to 2017, validation 2018-2023; nothing from 2024 on.", ""]
    if TAKEAWAY:
        L += ["## In plain words", ""] + TAKEAWAY + ["", "## The rows", ""]
    L += ["Verdicts: VALIDATED and CONDITIONAL would be passes; OPPOSITE means significantly the other way round in development and the same way in "
          "2018-23; INCONCLUSIVE means too few independent blocks (16 needed per period) or a reading below the bar.", "",
          "| variant | expected | verdict | dev mean | dev t | dev blocks | val mean | val t | val blocks | events dev / val |", "|---|---|---|---|---|---|---|---|---|---|"]
    for r in out["rows"]:
        e = r["extra"] or {}
        d, v = r["dev"], r["val"]
        L.append(f"| {r['variant']} | {'+' if r['expect'] > 0 else '-'} | {r['verdict']} | {_f(d[0])} | {_f(d[1], False)} | {d[2]} | {_f(v[0])} | {_f(v[1], False)} | {v[2]} | "
                 f"{e.get('events_dev', 'n/a')} / {e.get('events_val', 'n/a')} |")
    h = out.get("descriptive") or {}
    if h.get("by_year"):
        L += ["", "## Descriptive: how mutual fund flows line up with the Nifty and with foreign flows", "",
              "| year | corr same session | corr with previous session's return | corr with next session's return | corr with FPI same session | days |",
              "|---|---|---|---|---|---|"]
        for y, v in sorted(h["by_year"].items()):
            L.append(f"| {y} | {v['corr_same_day']} | {v['corr_flow_vs_previous_day_return']} | {v['corr_flow_vs_next_day_return']} | {v['corr_with_fpi_same_session']} | {v['days']} |")
    p = REG_DIR / "dii1_results_v1.md"
    p.write_text("\n".join(L) + "\n")
    return p


if __name__ == "__main__":
    paths.ensure()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    if cmd == "check":
        print(json.dumps(results(counts_only=True), indent=1))
    elif cmd == "run":
        o = run()
        for r in o["rows"]:
            print(r["variant"], r["verdict"], r["dev"], r["val"], (r["extra"] or {}).get("events_dev"), (r["extra"] or {}).get("events_val"))
    elif cmd == "table":
        p = table(json.loads((paths.manifest_dir() / "diistudy_dii1.json").read_text()))
        print(p)
    else:
        print(__doc__)
