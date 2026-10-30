"""Sensitivity re-run of the daily-bar studies with the unexplained price jumps taken out (Phase 2.2 of the 29 Oct 2026 audit).

The data audit (india.datacheck) found about 1,440 one-day moves over 40% in the liquid names of gold/bars, most of them splits and bonuses
the corporate-action record does not know (thin before 2006). The exit harness skips windows that cross a move over 50%, the signal side
(features) does not. This module answers one question without touching the real lake or ledger: do the key verdicts change when those days
are excluded?

  python -m india.sensitivity build       makes a shadow lake at ~/ananta_data/india_nojump: every folder a symlink to the real one, except
                                          gold/features and gold/bars (filtered copies), manifests/test_ledger.jsonl and india.duckdb (copies)
  python -m india.sensitivity jumps       lists the excluded (sid, date) pairs -> manifests/sensitivity_jumps.json (real manifests, read-only)
  python -m india.sensitivity compare     verdicts in the real ledger against the shadow ledger for the studies named in STUDIES

Run the studies themselves with INDIA_DATA_DIR=~/ananta_data/india_nojump, e.g.
  INDIA_DATA_DIR=~/ananta_data/india_nojump python -m india.studies e02
  INDIA_DATA_DIR=~/ananta_data/india_nojump python -m india.studies2 conditions
Nothing here writes to the real ledger; the shadow lake is a scratch copy and can be deleted.

Exclusion rule: a jump is |close / previous close - 1| > 0.4 with no corporate-action flag within 2 sessions. For that stock every row from
90 calendar days before to 90 calendar days after the jump is removed from features and from bars. The removed block leaves a gap of more
than 10 days, which the exit harness already treats as "skip this window".
"""
from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

import pandas as pd

from india import paths

SHADOW = Path(os.path.expanduser("~/ananta_data/india_nojump"))
JUMP = 0.40
PAD_DAYS = 90
STUDIES = ["E04-ANY", "E04-BRK", "E04-PULL", "P01-ANY", "P01-BRK", "P01-PULL", "GP1", "V01", "T-TWT-H10", "T-TWT-H12", "T-TWT-H18", "E02-ANY", "E02-BRK", "E02-PULL"]


def jumps() -> pd.DataFrame:
    """(sid, date, ratio) of unexplained jumps in the real bars."""
    b = pd.read_parquet(paths.gold() / "bars" / "adj_daily.parquet", columns=["sid", "date", "c"])
    b["date"] = pd.to_datetime(b["date"])
    b = b.sort_values(["sid", "date"])
    b["ratio"] = b["c"] / b.groupby("sid")["c"].shift(1)
    j = b[(b["ratio"] - 1).abs() > JUMP][["sid", "date", "ratio"]].copy()
    caf = paths.gold() / "ca_flags" / "ca_flags.parquet"
    if caf.exists():
        f = pd.read_parquet(caf, columns=["sid", "date"])
        f["date"] = pd.to_datetime(f["date"])
        keys = set()
        for sid, d in zip(f["sid"], f["date"]):
            for k in range(-2, 3):
                keys.add((sid, d + pd.Timedelta(days=k)))
        j = j[[(s, d) not in keys for s, d in zip(j["sid"], j["date"])]]
    return j.reset_index(drop=True)


def _mask(df: pd.DataFrame, j: pd.DataFrame) -> pd.Series:
    """True for rows to keep."""
    keep = pd.Series(True, index=df.index)
    d = pd.to_datetime(df["date"])
    for sid, g in j.groupby("sid"):
        idx = df.index[df["sid"] == sid]
        if not len(idx):
            continue
        dd = d.loc[idx]
        drop = pd.Series(False, index=idx)
        for jd in g["date"]:
            drop |= (dd >= jd - pd.Timedelta(days=PAD_DAYS)) & (dd <= jd + pd.Timedelta(days=PAD_DAYS))
        keep.loc[idx[drop.values]] = False
    return keep


def build() -> dict:
    real = paths.data_dir()
    if SHADOW.exists():
        shutil.rmtree(SHADOW)
    SHADOW.mkdir(parents=True)
    for p in real.iterdir():
        if p.name in ("gold", "manifests", "india.duckdb"):
            continue
        os.symlink(p, SHADOW / p.name)
    (SHADOW / "gold").mkdir()
    for p in (real / "gold").iterdir():
        if p.name in ("features", "bars", "studies"):
            continue
        os.symlink(p, SHADOW / "gold" / p.name)
    (SHADOW / "gold" / "studies").mkdir()  # the studies write their trade tables here; the shadow starts empty so nothing real is reused
    (SHADOW / "manifests").mkdir()
    for p in (real / "manifests").iterdir():
        if p.name == "test_ledger.jsonl":
            shutil.copy2(p, SHADOW / "manifests" / p.name)  # same k per family, so the same bar; the shadow rows append here only
        else:
            os.symlink(p, SHADOW / "manifests" / p.name)
    shutil.copy2(real / "india.duckdb", SHADOW / "india.duckdb")
    j = jumps()
    out = {"jumps": int(len(j)), "stocks": int(j["sid"].nunique()),
           "ledger_lines": len((real / "manifests" / "test_ledger.jsonl").read_text().splitlines())}
    for name, cols in (("features", None), ("bars", None)):
        src = real / "gold" / name / ("daily.parquet" if name == "features" else "adj_daily.parquet")
        df = pd.read_parquet(src)
        keep = _mask(df, j)
        (SHADOW / "gold" / name).mkdir()
        df[keep].to_parquet(SHADOW / "gold" / name / src.name, index=False)
        out[name] = {"rows": int(len(df)), "kept": int(keep.sum()), "removed_share": round(float(1 - keep.mean()), 5)}
    (SHADOW / "SHADOW_LAKE.txt").write_text("Scratch copy for india.sensitivity (29 Oct 2026). Delete freely. " + json.dumps(out))
    return out


def _t(x) -> float:
    """t-stat from a ledger dev/val entry, stored as [mean, t, dates] or {"mean", "t", "dates"}."""
    v = x.get("t") if isinstance(x, dict) else x[1]
    return round(float(v), 2) if v == v else float("nan")


def _ledger(p: Path) -> dict:
    rows = [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
    last = {}
    for r in rows:
        if r.get("kind") == "result" and r["study"] in STUDIES:
            last[(r["study"], r["variant"])] = r
    return last


def compare() -> dict:
    real = _ledger(paths.manifest_dir() / "test_ledger.jsonl")
    shadow_rows = [json.loads(x) for x in (SHADOW / "manifests" / "test_ledger.jsonl").read_text().splitlines() if x.strip()]
    meta = (SHADOW / "SHADOW_LAKE.txt").read_text()
    n_real = int(json.loads(meta[meta.index("{"):])["ledger_lines"])  # the copied lines; the real ledger may have grown since
    shadow = {}
    for r in shadow_rows[n_real:]:  # only the rows the shadow runs appended
        if r.get("kind") == "result" and r["study"] in STUDIES:
            shadow[(r["study"], r["variant"])] = r
    out = {"compared": 0, "same": 0, "changed": [], "not_rerun": sorted({s for s, _ in real} - {s for s, _ in shadow})}
    for k, r in real.items():
        s = shadow.get(k)
        if not s:
            continue
        out["compared"] += 1
        if r["verdict"] == s["verdict"]:
            out["same"] += 1
        else:
            out["changed"].append({"study": k[0], "variant": k[1], "before": r["verdict"], "after": s["verdict"],
                                   "dev_t": [_t(r["dev"]), _t(s["dev"])], "val_t": [_t(r["val"]), _t(s["val"])]})
    # verdict-level summary per study
    per = {}
    for k, r in real.items():
        s = shadow.get(k)
        if s:
            per.setdefault(k[0], {"same": 0, "changed": 0})["same" if r["verdict"] == s["verdict"] else "changed"] += 1
    out["per_study"] = per
    (paths.manifest_dir() / "sensitivity_compare.json").write_text(json.dumps(out, indent=1))
    return out


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "jumps"
    if cmd == "build":
        print(json.dumps(build(), indent=1))
    elif cmd == "jumps":
        j = jumps()
        (paths.manifest_dir() / "sensitivity_jumps.json").write_text(json.dumps({"n": int(len(j)), "rule": f"|ratio-1| > {JUMP}, no CA flag within 2 sessions",
                                                                                  "rows": [{"sid": s, "date": str(d.date()), "ratio": round(float(r), 3)} for s, d, r in zip(j["sid"], j["date"], j["ratio"])]}, indent=1))
        print(len(j), "jumps in", j["sid"].nunique(), "stocks")
    elif cmd == "compare":
        print(json.dumps(compare(), indent=1))
