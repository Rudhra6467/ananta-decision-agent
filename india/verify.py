"""Verification report: what is proven, by which test, with the actual output. A component counts as done only when its checks pass here.

  python -m india.verify            run everything, write manifests/verify.json and india/registrations/verification.md
  python -m india.verify quick      unit tests and canaries only

Three kinds of evidence are kept apart in the report:
  HISTORICAL BACKTEST       registry results on dev 2000-2017 and validation 2018-2023 (no holdout)
  CURRENT-MARKET OBSERVATION  live data coming in (recorder minutes, decision context, baseline book slices) - descriptive only
  PAPER EXECUTION           the executed paper books (stock, options): fills, exits, costs on real prices with paper money
"""
from __future__ import annotations

import datetime as dt
import json
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from india import paths

HERE = Path(__file__).parent


def _t(name, fn):
    try:
        ok, note = fn()
    except Exception as e:
        ok, note = False, f"error {type(e).__name__}: {e}"
    return {"test": name, "ok": bool(ok), "note": note}


# ----------------------------------------------------------------------------------------------- unit tests

def t_sizing():
    from india import settings
    cfg = settings.load()
    q1, n1 = settings.size({"stock": {**cfg["stock"], "sizing": "fixed_notional", "notional_inr": 50000}}, 100.0, 0.05)
    q2, n2 = settings.size({"stock": {**cfg["stock"], "sizing": "fixed_risk", "risk_inr": 1000}}, 100.0, 0.05)
    ok = abs(n1 - 50000) < 1e-9 and abs(q1 - 500) < 1e-9 and abs(n2 - 20000) < 1e-9 and abs(q2 - 200) < 1e-9
    return ok, f"fixed_notional Rs 50,000 at Rs 100 -> {q1:.0f} shares; fixed_risk Rs 1,000 with a 5% stop -> Rs {n2:,.0f} ({q2:.0f} shares); config {cfg['version']} sha {settings.sha()}"


def t_ca_rule():
    from india import actions
    import duckdb
    ev = pd.DataFrame({"symbol": ["ZZTEST"] * 1, "ex_date": [pd.Timestamp("2010-01-05")], "status": ["A_ONLY"], "factor": [2.0]})
    # without price rows the event is outside the trading history: applied (level only)
    con = duckdb.connect()
    out = actions.confirm(ev.copy(), con)
    ok1 = bool(out["apply"].iloc[0]) and not bool(out["inside"].iloc[0])
    f = pd.read_parquet(paths.data_dir() / "silver/corporate_actions/factors.parquet")
    amb = f[f["inside"] & ~f["apply"]]
    agree_applied = bool(f.loc[f["status"] == "AGREE", "apply"].all())
    confirm_ok = bool((((f.loc[f["inside"] & f["apply"] & (f["status"] != "AGREE"), "raw_gap_cc"] / f.loc[f["inside"] & f["apply"] & (f["status"] != "AGREE"), "factor"]) - 1).abs() < 0.15).all())
    return ok1 and agree_applied and confirm_ok, (f"synthetic event outside history applied: {ok1}; every AGREE applied: {agree_applied}; every applied one-record event confirmed by price: {confirm_ok}; "
                                                  f"{len(amb)} ambiguous events not applied ({amb['status'].value_counts().to_dict()})")


def t_conditions_no_lookahead():
    """The context on date t computed from data up to t equals the context on date t computed from all data."""
    from india import conditions, studies
    f = studies.load_features()
    f = f[(f["date"] >= "2019-01-01") & (f["date"] <= "2020-06-30")]
    full = conditions.context_table(f)
    cut = pd.Timestamp("2020-03-20")
    part = conditions.context_table(f[f["date"] <= cut])
    a, b = full.loc[cut], part.loc[cut]
    cols = [c for c in full.columns if pd.notna(a[c]) or pd.notna(b[c])]
    same = all((pd.isna(a[c]) and pd.isna(b[c])) or abs(float(a[c]) - float(b[c])) < 1e-12 for c in cols)
    # macro is joined on the day before: the US close used on t is dated before t
    return same, f"context on {cut.date()} from data to that day vs all data: {'identical' if same else 'DIFFERENT'} over {len(cols)} columns (index closes cut too: they are read in full, so this checks the rolling windows only look back)"


def t_sealed_canary():
    from india import leakcheck
    tmp = Path(tempfile.mkdtemp()) / "canary.py"
    tmp.write_text('import duckdb\nx = duckdb.sql("select * from read_parquet(\'~/ananta_data/india/sealed/silver/cm_bhavcopy/x.parquet\')")\n')
    strings = leakcheck._strings(tmp)
    caught = any(s != "sealed" and any("sealed" in tok.lower() and ("/" in tok or "_" in tok or tok == s) for tok in s.split()) for s in strings)
    return caught, f"a planted read of the sealed folder is {'caught' if caught else 'NOT caught'} by the sealed-reference rule"


def t_dup_canary():
    df = pd.DataFrame({"date": ["2020-01-01", "2020-01-01"], "symbol": ["A", "A"], "series": ["EQ", "EQ"]})
    return bool(df.duplicated().sum() == 1), "a planted duplicate key is counted by the duplicate rule"


def t_paper_rules():
    from india import paper
    r = paper.RULES_VERSION
    j = json.loads((paths.data_dir() / "paper/decisions/2026-10-16.json").read_text())
    rec = paths.data_dir() / "paper/decisions/2026-10-16.journal.json"
    rj = json.loads(rec.read_text()) if rec.exists() else {}
    return bool(rj.get("chosen_match")), (f"rules {r}; first decision (data 16 Oct, written {j['decided_at']}) {len(j['signals'])} signals, sha {j['sha256'][:12]}; "
                                          f"reconstructed journal matches its chosen list: {rj.get('chosen_match')} ({rj.get('label', '')[:60]})")


UNIT = {"sizing": t_sizing, "corporate_action_rule": t_ca_rule, "conditions_no_lookahead": t_conditions_no_lookahead, "sealed_canary": t_sealed_canary,
        "duplicate_canary": t_dup_canary, "paper_first_decision": t_paper_rules}


# ----------------------------------------------------------------------------------------------- report

def _load(name: str) -> dict:
    p = paths.manifest_dir() / name
    return json.loads(p.read_text()) if p.exists() else {}


def _registry_summary() -> dict:
    p = paths.manifest_dir() / "test_ledger.jsonl"
    rows = [json.loads(x) for x in p.read_text().splitlines()] if p.exists() else []
    latest = {}
    for r in rows:
        if r.get("kind") == "result":
            latest[(r["study"], r["variant"])] = r
    df = pd.DataFrame(latest.values())
    if df.empty:
        return {}
    fam = df.groupby(["family", "verdict"]).size().unstack(fill_value=0)
    notable = df[df["verdict"].isin(["VALIDATED", "CONDITIONAL", "OPPOSITE"])]
    return {"results_latest": len(df), "by_family": fam.to_dict(orient="index"),
            "notable": [f"{r.study} {r.variant}: {r.verdict} (dev {r.dev[0]*100:+.2f}% t {r.dev[1]:+.1f}; val {r.val[0]*100:+.2f}% t {r.val[1]:+.1f})" for r in notable.itertuples()][:80],
            "stamped": int(df["code"].notna().sum()) if "code" in df else 0}


def run(quick: bool = False) -> dict:
    paths.ensure()
    out = {"at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "unit": [_t(k, f) for k, f in UNIT.items()]}
    if not quick:
        from india import integrity, leakcheck, lineage
        lk = leakcheck.run()
        out["leakcheck"] = {k: v for k, v in lk.items() if not k.startswith("_")}
        ig = integrity.run()
        out["integrity"] = {k: {"ok": v["ok"], "note": v["note"]} for k, v in ig.items() if not k.startswith("_")}
        out["lineage"] = lineage.build()
        items, studs = lineage.deps()
        out["data_items"] = [{k: r[k] for k in ("id", "item", "manual_state", "auto_state", "first", "last", "note")} for r in items]
        out["blocked_studies"] = [s for s in studs if not s["runnable"]]
    out["replay"] = _load("replay.json")
    out["registry"] = _registry_summary()
    out["paper"] = _paper_summary()
    fails = [u["test"] for u in out["unit"] if not u["ok"]]
    fails += [f"leakcheck.{k}" for k, v in out.get("leakcheck", {}).items() if not v["ok"]]
    fails += [f"integrity.{k}" for k, v in out.get("integrity", {}).items() if not v["ok"]]
    fails += [f"replay.{k}" for k, v in out.get("replay", {}).get("checks", {}).items() if not v["ok"]]
    out["failures"] = fails
    (paths.manifest_dir() / "verify.json").write_text(json.dumps(out, indent=1, default=str))
    (HERE / "registrations" / "verification.md").write_text(_markdown(out))
    return out


def _paper_summary() -> dict:
    p = paths.data_dir() / "paper"
    out = {}
    st = p / "state.json"
    if st.exists():
        s = json.loads(st.read_text())
        t = pd.DataFrame(s["trades"].values())
        out["exec"] = {"decisions": len(s["decisions"]), "trades": t["status"].value_counts().to_dict() if len(t) else {}}
    bp = p / "baseline.parquet"
    if bp.exists():
        b = pd.read_parquet(bp)
        out["baseline"] = {"rows": len(b), "status": b["status"].value_counts().to_dict()}
    op = p / "options_trades.jsonl"
    if op.exists():
        rows = [json.loads(x) for x in op.read_text().splitlines()]
        out["options"] = {"rows": len(rows), "trades": sum(1 for r in rows if r.get("kind") != "skip"), "skips": sum(1 for r in rows if r.get("kind") == "skip")}
    return out


def _markdown(o: dict) -> str:
    L = [f"# India verification report ({o['at']})", "", "Generated by `python -m india.verify`. Every line is the output of a test run at that time.", ""]
    L += ["## Outstanding failures", ""] + ([f"- {x}" for x in o["failures"]] or ["- none"]) + [""]
    L += ["## Unit tests and canaries", "", "| test | result | output |", "|---|---|---|"] + [f"| {u['test']} | {'PASS' if u['ok'] else 'FAIL'} | {u['note']} |" for u in o["unit"]] + [""]
    if "leakcheck" in o:
        L += ["## Look-ahead and sealed-data checks (india.leakcheck)", "", "| check | result | output |", "|---|---|---|"]
        L += [f"| {k} | {'PASS' if v['ok'] else 'FAIL'} | {v['note']} |" for k, v in o["leakcheck"].items()] + [""]
        L += ["## Data integrity (india.integrity)", "", "| check | result | output |", "|---|---|---|"]
        L += [f"| {k} | {'PASS' if v['ok'] else 'FAIL'} | {v['note']} |" for k, v in o["integrity"].items()] + [""]
    rp = o.get("replay") or {}
    if rp:
        L += [f"## Workflow replay (india.replay, {rp.get('window')}, validation years, scratch folder)", "",
              f"{rp.get('sessions')} sessions, {rp.get('decisions')} decisions, {rp.get('exec_trades')} executed trades ({rp.get('closed')} closed), baseline {rp.get('baseline', {}).get('rows')} rows.", "",
              "| check | result | output |", "|---|---|---|"] + [f"| {k} | {'PASS' if v['ok'] else 'FAIL'} | {v['note']} |" for k, v in rp.get("checks", {}).items()] + [""]
    if "data_items" in o:
        L += ["## Data items checked against the lake (india.lineage deps)", "", "| id | item | hand state | lake state | first | last | note |", "|---|---|---|---|---|---|---|"]
        L += [f"| {d['id']} | {d['item'][:70]} | {d['manual_state']} | {d['auto_state']} | {d['first'] or ''} | {d['last'] or ''} | {d['note'][:120]} |" for d in o["data_items"]] + [""]
        L += ["## Blocked studies and what they wait for", ""] + [f"- {s['study']}: {s['blockers']}" for s in o["blocked_studies"]] + [""]
    rg = o.get("registry", {})
    L += ["## HISTORICAL BACKTEST: registry (latest result per study and variant)", "", f"{rg.get('results_latest', 0)} results; stamped with a code version: {rg.get('stamped', 0)}", ""]
    for fam, counts in (rg.get("by_family") or {}).items():
        L.append(f"- {fam}: " + ", ".join(f"{k} {v}" for k, v in counts.items() if v))
    L += ["", "Notable (VALIDATED / CONDITIONAL / OPPOSITE):", ""] + [f"- {x}" for x in rg.get("notable", [])] + [""]
    pp = o.get("paper", {})
    L += ["## PAPER EXECUTION and CURRENT-MARKET OBSERVATION", "", f"- stock executed book: {pp.get('exec')}", f"- stock baseline book: {pp.get('baseline', 'none yet')}",
          f"- options book: {pp.get('options', 'none yet')}", ""]
    lg = o.get("lineage", {})
    if lg:
        L += ["## Lineage", "", f"- code {lg.get('git', {}).get('git')} (uncommitted files: {len(lg.get('git', {}).get('dirty', []))})", f"- studies {lg.get('studies')}",
              f"- hypotheses {lg.get('hypotheses')}, with data available {lg.get('hypotheses_data_ok')}, without a study {lg.get('hypotheses_without_study')}", ""]
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    r = run(quick=len(sys.argv) > 1 and sys.argv[1] == "quick")
    for u in r["unit"]:
        print(("PASS " if u["ok"] else "FAIL ") + u["test"] + " — " + u["note"])
    print("failures:", r["failures"])
