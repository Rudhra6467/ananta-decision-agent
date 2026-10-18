"""Lineage: every hypothesis traced to the data it needs (checked, not assumed), the code that tests it, the study runs and their results, the limits
of those results, and the paper records that follow the idea in the live market.

  python -m india.lineage versions     snapshot every dataset (files, bytes, rows, first/last date, fingerprint) -> catalog dataset_versions, manifests/dataset_versions.jsonl
  python -m india.lineage deps         every data item checked against the lake: present / partial / stale / missing, and every study's blockers
  python -m india.lineage build        all of the above plus the lineage tables (catalog lineage_study, lineage_hypothesis) and manifests/lineage.json
  python -m india.lineage show E02     one study end to end

Rules: a data item counts as present only if its files exist and cover the dates the item promises; a READY flag set by hand that the lake contradicts is
reported as MISMATCH. A study whose data is missing is BLOCKED and says by what; nothing is filled in with a stand-in unless the stand-in is itself a
labelled data item (D26). Dataset fingerprints are a hash over file names, sizes and modification times, so a rebuilt file gets a new version.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import duckdb
import pandas as pd

from india import catalog, paths, sealed, tracker

REPO = Path(__file__).resolve().parent.parent

# dataset name -> (folder under the data root, glob, date column or None)
DATASETS = {
    "silver/cm_bhavcopy": ("silver/cm_bhavcopy", "year=*/part.parquet", "date"),
    "silver/delivery": ("silver/delivery", "year=*/part.parquet", "date"),
    "silver/corporate_actions": ("silver/corporate_actions", "*.parquet", "ex_date"),
    "silver/security_master": ("silver/security_master", "*.parquet", None),
    "silver/calendar": ("silver/calendar", "calendar.parquet", "date"),
    "silver/kite_5m": ("silver/kite_5m", "year=*/part.parquet", "date"),
    "silver/kite_day": ("silver/kite_day", "kite_day.parquet", "date"),
    "silver/kite_index/day": ("silver/kite_index/day", "day.parquet", "date"),
    "silver/kite_index/5minute": ("silver/kite_index/5minute", "year=*/part.parquet", "date"),
    "silver/kite_index/minute": ("silver/kite_index/minute", "year=*/part.parquet", "date"),
    "silver/fo_bhavcopy": ("silver/fo_bhavcopy", "year=*/part.parquet", "date"),
    "silver/fo_calendar": ("silver/fo_calendar", "expiries.parquet", None),
    "silver/fo_greeks": ("silver/fo_greeks", "year=*/part.parquet", "date"),
    "silver/macro": ("silver/macro", "macro.parquet", "date"),
    "gold/bars": ("gold/bars", "adj_daily.parquet", "date"),
    "gold/features": ("gold/features", "daily.parquet", "date"),
    "gold/universe": ("gold/universe", "u_liq_in.parquet", "date"),
    "gold/hypothesis_map": ("gold/hypothesis_map", "hypothesis_map.parquet", None),
    "bronze/kite_1m_fo": ("bronze/kite_1m_fo", "**/*.jsonl.gz", None),
    "bronze/pr_zip": ("bronze/pr_zip", "**/*", None),
    "bronze/results_index": ("bronze/results_index", "**/*", None),
    "bronze/xbrl": ("bronze/xbrl", "**/*", None),
    "bronze/flows": ("bronze/flows", "**/*", None),
    "bronze/ledger": ("bronze/ledger", "*.json", None),
}

# data item -> what the lake must show for it to count as present: datasets, first date the item promises (or None), and whether it must be current
DMAP = {
    "D01": (["silver/cm_bhavcopy"], "1994-12-31", True), "D02": (["silver/delivery"], "2003-12-31", True), "D03": (["silver/corporate_actions"], None, False),
    "D04": (["silver/kite_5m"], "2015-12-31", True), "D05": (["silver/security_master"], None, False), "D06": (["silver/calendar"], "1994-12-31", False),
    "D07": (["gold/universe"], "2000-12-31", False), "D09": (["gold/features"], "2000-12-31", False),
    "D10": (["silver/kite_index/minute", "silver/kite_index/5minute"], "2015-12-31", True), "D11": (["silver/kite_index/day"], "2003-12-31", True),
    "D12": (["silver/fo_bhavcopy", "silver/fo_calendar"], "2001-12-31", True), "D13": (["silver/fo_greeks"], "2001-12-31", True),
    "D14": (["bronze/kite_1m_fo"], None, True), "D16": (["bronze/ledger"], None, False), "D17": (["bronze/flows"], None, False),
    "D18": (["bronze/pr_zip"], None, False), "D20": (["bronze/results_index", "bronze/xbrl"], None, False), "D22": (["silver/macro"], None, False),
    "D23": (["gold/hypothesis_map"], None, False), "D29": (["silver/kite_index/day"], None, False),
}
# inputs a study can run without: the part that needs them is skipped and the result says so
OPTIONAL = {"C09": ["D30"], "V06": ["D19"], "F05": ["D14"]}
# gold research tables end at the sealed line on purpose; "current" for them means 2023-12-29
RESEARCH_END = "2023-12-29"

# code each study family runs on (the files whose versions are stamped with a result)
CODE = {"E": ["india/studies.py", "india/exitlab.py", "india/lab.py", "india/costs.py", "india/registry.py"],
        "C": ["india/cstudies.py", "india/exitlab.py", "india/lab.py", "india/costs.py", "india/registry.py"],
        "F": ["india/fstudies.py", "india/fo.py", "india/greeks.py", "india/costs.py", "india/registry.py"],
        "I": ["india/istudies.py", "india/kite_index.py", "india/registry.py"],
        "P": ["india/studies.py", "india/exitlab.py", "india/lab.py"], "R": ["india/optpaper.py", "india/recorder.py"],
        "V": ["india/vstudies.py"], "S": ["india/lab.py", "india/exitlab.py", "india/costs.py", "india/registry.py"], "K": [], "G": []}

# which paper record follows each study in the live market
PAPER = {
    "E01": "stock book: every trade carries the same 2 ATR stop; stop-outs by policy in paper/state.json and baseline.parquet",
    "E02": "stock book: 18 exit policies + random exit on every candidate (exec and baseline)", "E03": "stock book: policy set in exitlab (turn-warning exits are lab-only until a family passes)",
    "E07": "stock book: swing_low_* policies", "E08": "decision context: nifty_vs_sma50/200 recorded with every decision; baseline sliced by it",
    "C05": "decision context: vix_close and vix_vs_sma50", "C08": "decision context: breadth200_liq / breadth50_liq",
    "E04": "baseline journal features ret_20, dist_sma50", "E05": "baseline journal feature dist_sma20 (PULL depth)", "E10": "executed stock book open drawdown (marks)",
    "F02": "options book O-03 (paper/options_trades.jsonl)", "F05": "options book O-04, 8 variants", "I05": "options book O-04 spot side", "R02": "options book O-04 / O-03",
}

LIMITS = {
    "E": "8,000 signals sampled per entry set; long only; 60-session horizon; overlapping holds handled by quarter-block t; spread is an estimate by liquidity rank; "
         "prices adjusted for splits and bonuses, not dividends; dev 2000-2017, validation 2018-2023, holdout not read",
    "E08": "few independent weak-market episodes (2008-09, 2011-12, 2020, 2022); gate measured at the signal close",
    "C": "index and sector maps use the current Nifty 500 industry list (not point in time): sector studies carry survivorship in the sector labels",
    "F": "end-of-day settlement prices only; Greeks are Black-76 estimates with a flat 6.5% rate; option bid-ask before 18 Oct 2026 not available (D26)",
    "I": "index minutes from 2015 only; spot side only (option side needs the recorder)",
    "R": "recorder started 18 Oct 2026: no history; fills are next-minute open plus a labelled half-spread estimate",
    "V": "fundamentals from Aug 2018 (XBRL) unless D20b is approved; filing timestamps used as point in time",
}


def _git(*args: str) -> str:
    try:
        return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True, timeout=20).stdout.rstrip("\n")  # keep leading spaces: porcelain status columns
    except Exception:
        return ""


def code_version(files: list[str] | None = None) -> dict:
    head = _git("rev-parse", "--short=12", "HEAD").strip()
    dirty = [x[3:] for x in _git("status", "--porcelain", "--", "india").splitlines() if x.strip()]
    out = {"git": head, "dirty": dirty}
    if files:
        out["files"] = {f: (_git("hash-object", f)[:12] if (REPO / f).exists() else "missing") for f in files}
    return out


def _files(name: str) -> list[Path]:
    folder, pat, _ = DATASETS[name]
    base = paths.data_dir() / folder
    return sorted(p for p in base.glob(pat) if p.is_file()) if base.exists() else []


def fingerprint(name: str) -> dict:
    fs = _files(name)
    h = hashlib.sha256()
    size = 0
    for p in fs:
        st = p.stat()
        size += st.st_size
        h.update(f"{p.relative_to(paths.data_dir())}|{st.st_size}|{st.st_mtime_ns}\n".encode())
    newest = max((p.stat().st_mtime for p in fs), default=None)
    return {"dataset": name, "files": len(fs), "bytes": size, "fingerprint": h.hexdigest()[:16] if fs else None,
            "newest_file": dt.datetime.fromtimestamp(newest, dt.timezone.utc).isoformat(timespec="seconds") if newest else None}


def datasets_for(study: str) -> list[str]:
    needs = next((x[4] for x in tracker.STUDIES if x[0] == study), [])
    return sorted({n for d in needs for n in DMAP.get(d, ([], None, False))[0]})


def stamp(datasets: list[str] | None = None, files: list[str] | None = None) -> dict:
    """Cheap provenance for a registry row: code version and dataset fingerprints (no row reads)."""
    return {"code": code_version(files), "data": {n: fingerprint(n)["fingerprint"] for n in (datasets or [])}, "stamped_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}


def _scan(files: list[Path], datecol: str | None) -> dict:
    pq = [str(p) for p in files if p.suffix == ".parquet"]
    if not pq:
        return {}
    con = duckdb.connect()
    try:
        if datecol:
            r = con.execute(f"select count(*), min({datecol}), max({datecol}) from read_parquet({pq!r}, union_by_name=true)").fetchone()
            return {"rows": int(r[0]), "first": str(r[1])[:10] if r[1] is not None else None, "last": str(r[2])[:10] if r[2] is not None else None}
        r = con.execute(f"select count(*) from read_parquet({pq!r}, union_by_name=true)").fetchone()
        return {"rows": int(r[0])}
    finally:
        con.close()


def versions(write: bool = True) -> list[dict]:
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    out = []
    for name, (folder, pat, datecol) in DATASETS.items():
        fp = fingerprint(name)
        row = {**fp, **_scan(_files(name), datecol), "snapshot_at": now}
        if folder.startswith("silver/"):
            sm = sealed.metadata(folder, pat, datecol)
            row.update({"sealed_files": sm.get("files", 0), "sealed_rows": sm.get("rows"), "sealed_last": sm.get("last"), "sealed_fingerprint": sm.get("fingerprint")})
        out.append(row)
    if write:
        with (paths.manifest_dir() / "dataset_versions.jsonl").open("a") as fh:
            for r in out:
                fh.write(json.dumps(r, default=str) + "\n")
        df = pd.DataFrame(out)
        con = catalog.connect()
        con.register("dv", df)
        con.execute("create table if not exists dataset_versions as select * from dv where false")
        cols = [r[1] for r in con.execute("pragma table_info('dataset_versions')").fetchall()]
        for c in df.columns:
            if c not in cols:
                con.execute(f'alter table dataset_versions add column "{c}" varchar')
        con.execute(f"insert into dataset_versions ({', '.join(chr(34) + c + chr(34) for c in df.columns)}) select * from dv")
        con.close()
    return out


def _latest_versions() -> dict:
    p = paths.manifest_dir() / "dataset_versions.jsonl"
    if not p.exists():
        return {r["dataset"]: r for r in versions()}
    last = {}
    for line in p.read_text().splitlines():
        r = json.loads(line)
        last[r["dataset"]] = r
    return last


def _expected_session() -> str:
    """The latest session the lake should hold: the newest cash-file date (fetched every evening), checked against the weekday calendar."""
    v = _latest_versions().get("silver/cm_bhavcopy", {})
    cm_last = max(x for x in (v.get("last"), v.get("sealed_last")) if x) if v else None
    return cm_last or ""


def deps() -> tuple[list[dict], list[dict]]:
    vers = _latest_versions()
    ref = _expected_session()
    today = dt.date.today()
    last_weekday = today - dt.timedelta(days=1)
    while last_weekday.weekday() >= 5:
        last_weekday -= dt.timedelta(days=1)
    cm_gap = (last_weekday - dt.date.fromisoformat(ref)).days if ref else None
    data, studies = tracker.evaluate()
    items = []
    for d in data:
        rec = {"id": d["id"], "item": d["item"], "manual_state": d["state"], "datasets": "", "first": None, "last": None, "auto_state": "NOT_CHECKED", "note": ""}
        if d["id"] in DMAP:
            names, promise_first, current = DMAP[d["id"]]
            rec["datasets"] = ",".join(names)
            states, notes = [], []
            for n in names:
                v = vers.get(n, {})
                files = (v.get("files") or 0) + (v.get("sealed_files") or 0)
                first = v.get("first")
                last = max([x for x in (v.get("last"), v.get("sealed_last")) if x], default=None)
                rec["first"] = min([x for x in (rec["first"], first) if x], default=None)
                rec["last"] = max([x for x in (rec["last"], last) if x], default=None)
                if files == 0:
                    states.append("MISSING"); notes.append(f"{n}: no files"); continue
                if promise_first and first and first > promise_first:
                    states.append("PARTIAL"); notes.append(f"{n}: starts {first}, promised by {promise_first}")
                elif current and last and n.startswith("silver/") and ref and last < ref:
                    states.append("STALE"); notes.append(f"{n}: last {last}, lake session {ref}")
                elif n.startswith("gold/") and last and last < RESEARCH_END:
                    states.append("STALE"); notes.append(f"{n}: last {last}, research end {RESEARCH_END}")
                else:
                    states.append("PRESENT")
            order = ["MISSING", "STALE", "PARTIAL", "PRESENT"]
            rec["auto_state"] = min(states, key=order.index)
            rec["note"] = "; ".join(notes)
            if rec["auto_state"] == "PRESENT" and d["state"] != "READY":
                # files exist but the item is not finished (a pull still running, history still accumulating, a piece still to source)
                rec["auto_state"] = "PARTIAL"
                rec["note"] = (rec["note"] + "; " if rec["note"] else "") + f"{d['state'].lower()}: {d['live'] or d['note']}"
            if d["state"] == "READY" and rec["auto_state"] in ("MISSING", "STALE"):
                rec["auto_state"] = "MISMATCH:" + rec["auto_state"]
        if d["id"] == "D01" and cm_gap is not None and cm_gap > 4:
            rec["note"] = (rec["note"] + "; " if rec["note"] else "") + f"cash file {cm_gap} days behind the last weekday"
        items.append(rec)
    by = {r["id"]: r for r in items}
    out = []
    for sid, ph, fam, q, needs, exit_focus, _ in tracker.STUDIES:
        block = []
        for n in OPTIONAL.get(sid, []):
            r = by.get(n)
            if r and not (r["auto_state"] in ("PRESENT", "PARTIAL") or r["manual_state"] == "READY"):
                block.append(f"{n} partial (optional input missing: runs without it, marked in the result)")
        needs = [n for n in needs if n not in OPTIONAL.get(sid, [])]
        for n in needs:
            r = by.get(n)
            if r is None:
                continue  # a study dependency (E/G): handled by the tracker
            ok = r["auto_state"] in ("PRESENT", "PARTIAL") if r["auto_state"] != "NOT_CHECKED" else r["manual_state"] == "READY"
            if not ok:
                block.append(f"{n} {r['auto_state'] if r['auto_state'] != 'NOT_CHECKED' else r['manual_state']}")
            elif r["auto_state"] == "PARTIAL":
                block.append(f"{n} partial (runs with a coverage note)")
        hard = [b for b in block if "partial" not in b]
        out.append({"study": sid, "phase": ph, "family": fam, "needs": ",".join(needs), "runnable": not hard and not any(n.startswith(("E", "G")) and n not in ("E01", "E02", "E03", "E07") for n in needs),
                    "blockers": "; ".join(block), "exit_focus": exit_focus})
    return items, out


def _registry() -> tuple[dict, dict]:
    p = paths.manifest_dir() / "test_ledger.jsonl"
    regs, res = {}, {}
    if not p.exists():
        return regs, res
    for line in p.read_text().splitlines():
        r = json.loads(line)
        base = r["study"].split("-")[0]
        if r.get("kind") == "registration":
            regs.setdefault(base, []).append(r)
        elif r.get("kind") == "result":
            res.setdefault(base, {})[(r["study"], r["variant"])] = r  # latest row per study run and variant
    return regs, res


def _paper_counts() -> dict:
    d = paths.data_dir() / "paper"
    out = {"decisions": len(list((d / "decisions").glob("????-??-??.json"))) if (d / "decisions").exists() else 0}
    st = d / "state.json"
    out["exec_trades"] = len(json.loads(st.read_text())["trades"]) if st.exists() else 0
    bp = d / "baseline.parquet"
    out["baseline_rows"] = int(duckdb.sql(f"select count(*) from read_parquet('{bp}')").fetchone()[0]) if bp.exists() else 0
    op = d / "options_trades.jsonl"
    out["options_rows"] = sum(1 for _ in op.open()) if op.exists() else 0
    return out


def build() -> dict:
    vers = versions()
    items, studs = deps()
    regs, res = _registry()
    pc = _paper_counts()
    code_all = code_version()
    rows = []
    for s in studs:
        sid = s["study"]
        fam = sid[0]
        files = CODE.get(fam, [])
        rr = list(res.get(sid, {}).values())
        verdicts = pd.Series([r["verdict"] for r in rr]).value_counts().to_dict() if rr else {}
        best = max(rr, key=lambda r: abs(r["dev"][1] or 0) if r["dev"][1] == r["dev"][1] else 0, default=None)
        reg = regs.get(sid, [])
        rows.append({**s, "code_files": ",".join(files), "code_blobs": json.dumps(code_version(files)["files"]) if files else "{}", "git": code_all["git"],
                     "registrations": len(reg), "registered_at": reg[-1]["at"] if reg else None, "registration_stamp": json.dumps(reg[-1].get("stamp")) if reg and reg[-1].get("stamp") else None,
                     "results": len(rr), "verdicts": json.dumps(verdicts),
                     "strongest": None if not best else f"{best['study']}/{best['variant']}: dev {best['dev'][0]:+.4f} (t {best['dev'][1]:+.2f}), val {best['val'][0]:+.4f} (t {best['val'][1]:+.2f}), {best['verdict']}",
                     "limits": LIMITS.get(sid, LIMITS.get(fam, "")), "paper_link": PAPER.get(sid, "none yet"),
                     "state": "RESULTS" if rr else ("RUNNABLE" if s["runnable"] else "BLOCKED")})
    study_df = pd.DataFrame(rows)
    hm = pd.read_parquet(paths.gold() / "hypothesis_map/hypothesis_map.parquet")
    dstate = {r["id"]: (r["auto_state"] if r["auto_state"] != "NOT_CHECKED" else r["manual_state"]) for r in items}
    sidx = study_df.set_index("study")
    hrows = []
    for _, h in hm.iterrows():
        lots = [x for x in str(h["data_lots"] or "").split() if x.startswith("D")]
        st = sidx.loc[h["study"]] if h["study"] in sidx.index else None
        hrows.append({"hypothesis": h["id"], "teacher": h["teacher"], "family": h["family"], "map_status": h["status"], "study": h["study"],
                      "data": " ".join(f"{x}:{dstate.get(x, '?')}" for x in lots), "data_ok": all(dstate.get(x, "?") in ("PRESENT", "PARTIAL", "READY") for x in lots),
                      "study_state": None if st is None else st["state"], "verdicts": None if st is None else st["verdicts"], "paper_link": None if st is None else st["paper_link"]})
    hyp_df = pd.DataFrame(hrows)
    con = catalog.connect()
    for name, df in (("lineage_study", study_df), ("lineage_hypothesis", hyp_df), ("data_check", pd.DataFrame(items))):
        con.register("x", df)
        con.execute(f"create or replace table {name} as select * from x")
        con.unregister("x")
    con.close()
    summary = {"built_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "git": code_all, "paper": pc,
               "datasets": len(vers), "data_items": pd.Series([r["auto_state"].split(":")[0] for r in items]).value_counts().to_dict(),
               "mismatches": [r["id"] + " " + r["auto_state"] + " " + r["note"] for r in items if r["auto_state"].startswith("MISMATCH")],
               "studies": study_df["state"].value_counts().to_dict(), "hypotheses": len(hyp_df), "hypotheses_data_ok": int(hyp_df["data_ok"].sum()),
               "hypotheses_without_study": int((hyp_df["study_state"].isna()).sum())}
    (paths.manifest_dir() / "lineage.json").write_text(json.dumps(summary, indent=1, default=str))
    return summary


def show(sid: str) -> None:
    con = catalog.connect(read_only=True)
    r = con.execute("select * from lineage_study where study = ?", [sid]).df()
    h = con.execute("select hypothesis, teacher, map_status, data, data_ok from lineage_hypothesis where study = ?", [sid]).df()
    con.close()
    if r.empty:
        print("unknown study (run build first)")
        return
    for k, v in r.iloc[0].items():
        print(f"{k:>20}: {v}")
    print("\nhypotheses:")
    print(h.to_string(index=False) if not h.empty else "  none mapped")


if __name__ == "__main__":
    paths.ensure()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "build"
    if cmd == "versions":
        for r in versions():
            print(json.dumps(r, default=str))
    elif cmd == "deps":
        items, studs = deps()
        for r in items:
            print(f"{r['id']:>5} {r['manual_state']:<11} {r['auto_state']:<16} {r['first'] or '':<10} {r['last'] or '':<10} {r['item'][:60]}  {r['note']}")
        print()
        for s in studs:
            print(f"{s['study']:>4} {'RUNNABLE' if s['runnable'] else 'BLOCKED ':<8} {s['blockers']}")
    elif cmd == "show":
        show(sys.argv[2])
    else:
        print(json.dumps(build(), indent=1, default=str))
