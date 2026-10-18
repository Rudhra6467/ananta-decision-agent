"""Workflow replay: the live paper engine run day by day over a past window of the VALIDATION years (never the sealed years), into a scratch folder,
then checked against the research harness. This is the reproducible end-to-end example: fetch -> decide (journal) -> fill -> step -> exit -> costs ->
baseline book -> filters, with every step checked.

  python -m india.replay 2023-05-01 2023-09-29      (default window)

Checks written to manifests/replay.json:
  decisions_before_fill   every decision file's data_through is earlier than its fill session
  fill_is_next_open       every executed entry is the official open of the first session after the signal (recomputed independently from silver)
  caps_respected          chosen signals per day never exceed the caps; every rejection carries a reason
  baseline_matches_exec   the baseline book holds the same trade (same entry, same exit, same net) for every executed trade id
  fills_inside_bar        entry inside the fill bar's low-high; exits inside the exit bar's range
  costs_charged           every closed trade paid costs
  lab_parity              the same entries run through india.exitlab (the research harness, gold tables) give the same exit day, reason and net return
"""
from __future__ import annotations

import datetime as dt
import json
import shutil
import sys
import tempfile
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from india import exitlab, paper, paths


def _raw(start: str, end: str) -> pd.DataFrame:
    files = [str(p) for p in (paths.data_dir() / "silver/cm_bhavcopy").glob("year=*/part.parquet")]
    since = (pd.Timestamp(start) - pd.Timedelta(days=paper.LOOKBACK_CAL_DAYS)).date()
    con = duckdb.connect()
    df = con.execute(f"select date, symbol, series, open, high, low, close, prev_close, volume, turnover, isin from read_parquet({files!r}) "
                     f"where series = 'EQ' and close > 0 and date >= ? and date <= ?", [since, pd.Timestamp(end).date()]).df()
    con.close()
    assert pd.to_datetime(df["date"]).max() < pd.Timestamp(paths.HOLDOUT_START), "replay must stay out of the holdout years"
    return df


def run(start: str = "2023-05-01", end: str = "2023-09-29", keep: bool = False) -> dict:
    tmp = Path(tempfile.mkdtemp(prefix="ananta_replay_"))
    (tmp / "decisions").mkdir()
    orig_pdir = paper.pdir
    paper.pdir = lambda: tmp
    t0 = dt.datetime.now()
    try:
        raw = _raw(start, end)
        full = paper.load_adjusted(raw=raw, since=(pd.Timestamp(start) - pd.Timedelta(days=paper.LOOKBACK_CAL_DAYS)).strftime("%Y-%m-%d"))
        sessions = sorted(d for d in full["date"].unique() if pd.Timestamp(start) <= d <= pd.Timestamp(end))
        state = {"trades": {}, "decisions": {}, "version": paper.RULES_VERSION}
        for d in sessions:
            upto = full[full["date"] <= d]
            paper.settle(state, upto)
            paper.decide(state, raw=raw, asof=pd.Timestamp(d).strftime("%Y-%m-%d"))
        base = paper.baseline(full)
        checks = _checks(state, full, raw, tmp)
        out = {"window": [start, end], "sessions": len(sessions), "decisions": len(state["decisions"]), "exec_trades": len(state["trades"]),
               "closed": sum(1 for t in state["trades"].values() if t["status"] == "closed"), "baseline": base, "checks": checks,
               "seconds": round((dt.datetime.now() - t0).total_seconds())}
        out["ok"] = all(v["ok"] for v in checks.values())
        (paths.manifest_dir() / "replay.json").write_text(json.dumps(out, indent=1, default=str))
        if keep:
            out["folder"] = str(tmp)
        return out
    finally:
        paper.pdir = orig_pdir
        if not keep:
            shutil.rmtree(tmp, ignore_errors=True)


def _checks(state: dict, full: pd.DataFrame, raw: pd.DataFrame, folder: Path) -> dict:
    res = {}
    trades = pd.DataFrame(state["trades"].values())
    ex = trades[trades["status"].isin(["open", "closed"])].copy()
    sessions = np.array(sorted(full["date"].unique()))
    # decisions before fill
    late = []
    for key, meta in state["decisions"].items():
        if meta.get("filled_on") and meta["filled_on"] <= key:
            late.append(key)
    res["decisions_before_fill"] = {"ok": not late, "note": f"{len(state['decisions'])} decisions, {len(late)} filled on or before their data date"}
    # fill is the next session's official open, recomputed from silver raw rows
    raw2 = raw.copy()
    raw2["date"] = pd.to_datetime(raw2["date"])
    names = pd.read_parquet(paths.data_dir() / "silver/security_master/names.parquet", columns=["isin", "entity"]).drop_duplicates("isin")
    raw2 = raw2.merge(names, on="isin", how="left")
    raw2["sid"] = raw2["entity"].fillna(raw2["symbol"])
    opens = raw2.sort_values("turnover", ascending=False).drop_duplicates(["sid", "date"]).set_index(["sid", "date"])["open"]
    bad_day = bad_px = 0
    for t in ex.itertuples():
        nxt = sessions[np.searchsorted(sessions, np.datetime64(pd.Timestamp(t.signal_date)), side="right")]
        if pd.Timestamp(t.entry_date) != pd.Timestamp(nxt):
            bad_day += 1
        o = opens.get((t.sid, pd.Timestamp(t.entry_date)))
        if o is None or abs(float(o) - t.entry_raw) > 1e-6 * max(1.0, float(o)):
            bad_px += 1
    res["fill_is_next_open"] = {"ok": bad_day == 0 and bad_px == 0, "note": f"{len(ex)} entries: {bad_day} not on the next session, {bad_px} not at the official open"}
    # caps and reasons
    cfg = paper.settings.load()["stock"]
    over, no_reason, reasons = [], 0, {}
    for p in sorted(folder.joinpath("decisions").glob("????-??-??.json")):
        body = json.loads(p.read_text())
        for camp, cap in cfg["caps"].items():
            if sum(1 for s in body["signals"] if s["campaign"] == camp) > cap:
                over.append(p.stem)
        for j in body["journal"]:
            if j["status"] == "rejected":
                if not j["reason"]:
                    no_reason += 1
                reasons[j["reason"]] = reasons.get(j["reason"], 0) + 1
    res["caps_respected"] = {"ok": not over and no_reason == 0, "note": f"{len(over)} days over a cap, {no_reason} rejections without a reason; reasons {reasons}"}
    # baseline matches the executed book
    b = pd.read_parquet(folder / "baseline.parquet").set_index("id")
    mism = 0
    for t in ex.itertuples():
        if t.id not in b.index:
            mism += 1
            continue
        r = b.loc[t.id]
        if abs(float(r["entry_adj"]) - t.entry_adj) > 1e-9 * t.entry_adj or r["status"] != t.status or (t.status == "closed" and abs(float(r["net_inr"]) - t.net_inr) > 0.01):
            mism += 1
    res["baseline_matches_exec"] = {"ok": mism == 0, "note": f"{len(ex)} executed trades, {mism} differ from the baseline row with the same id; baseline rows {len(b)}"}
    # fills inside the bar, costs charged
    cl = ex[ex["status"] == "closed"]
    out_in = int(((ex["entry_raw"] < ex["bar_low_raw"] - 1e-6) | (ex["entry_raw"] > ex["bar_high_raw"] + 1e-6)).sum())
    out_ex = int(((cl["exit_adj"] < cl["exit_bar_low_adj"] - 1e-6) | (cl["exit_adj"] > cl["exit_bar_high_adj"] + 1e-6)).sum())
    res["fills_inside_bar"] = {"ok": out_in == 0 and out_ex == 0, "note": f"entries outside the bar {out_in}, exits outside the bar {out_ex} (of {len(cl)} closed)"}
    res["costs_charged"] = {"ok": bool((cl["cost_inr"] > 0).all()), "note": f"{len(cl)} closed trades, median cost Rs {cl['cost_inr'].median():.0f}, {int((cl['cost_inr'] <= 0).sum())} without costs"}
    # lab parity: the research harness on the same entries
    res["lab_parity"] = _lab_parity(cl)
    return res


def _lab_parity(cl: pd.DataFrame) -> dict:
    if cl.empty:
        return {"ok": False, "note": "no closed trades to compare"}
    feats = pd.read_parquet(paths.gold() / "features" / "daily.parquet", columns=["sid", "date", "atr14", "liq_rank"])
    feats["date"] = pd.to_datetime(feats["date"])
    ent = cl[["sid", "signal_date"]].drop_duplicates()
    ent["signal_date"] = pd.to_datetime(ent["signal_date"])
    bars = exitlab.load_bars(sids=ent["sid"].unique())
    pols = [p for p in exitlab.DEFAULT_POLICIES]
    lab = exitlab.simulate(ent, bars, feats, pols, random_draws=1)
    lab = lab[lab["policy"] != "random_exit"]
    lab["signal_date"] = pd.to_datetime(lab["signal_date"]).dt.strftime("%Y-%m-%d")
    m = cl.merge(lab, left_on=["sid", "signal_date", "policy"], right_on=["sid", "signal_date", "policy"], suffixes=("_paper", "_lab"))
    if m.empty:
        return {"ok": False, "note": f"no overlap: {len(cl)} paper trades; lab rows {len(lab)} (signals outside the top 500 have no lab features)"}
    same_days = float((m["hold_days_paper"] == m["hold_days_lab"]).mean())
    same_reason = float((m["exit_reason"] == m["reason"]).mean())
    diff = (m["net_ret_paper"] - m["net_ret_lab"]).abs()
    ok = same_days >= 0.99 and same_reason >= 0.99 and float(diff.quantile(0.99)) < 0.002
    worst = m.loc[diff.idxmax(), ["sid", "signal_date", "policy", "net_ret_paper", "net_ret_lab", "hold_days_paper", "hold_days_lab", "exit_reason", "reason"]].to_dict()
    return {"ok": ok, "note": f"{len(m)} trades in both: same exit day {same_days:.1%}, same reason {same_reason:.1%}, net-return difference median {diff.median()*100:.3f}% p99 {diff.quantile(0.99)*100:.3f}%",
            "worst": worst}


if __name__ == "__main__":
    paths.ensure()
    a = sys.argv[1:] or ["2023-05-01", "2023-09-29"]
    r = run(a[0], a[1], keep="--keep" in a)
    for k, v in r["checks"].items():
        print(("PASS " if v["ok"] else "FAIL ") + k + " — " + v["note"], flush=True)
    print(json.dumps({k: v for k, v in r.items() if k != "checks"}, indent=1, default=str))
    sys.exit(0 if r["ok"] else 1)
