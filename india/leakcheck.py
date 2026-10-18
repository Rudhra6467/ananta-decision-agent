"""Leak, mapping and workflow checks. Every check prints PASS or FAIL and the line goes into manifests/leakcheck.json; the evidence job runs them nightly.

  python -m india.leakcheck           all checks
Checks:
  sealed_files        lab / studies / exitlab / registry / paper / costs / greeks-input code never names the sealed folder; only india/sealed.py reads it
  tables_pre_2024     gold lab tables stop before 2024-01-01
  feature_columns     the daily feature table holds no forward-looking columns (whitelist)
  parity              the paper engine's live features equal the lab's gold features on a past date (mapping between the two code paths)
  future_edit         changing every row after a date does not change the decision made on that date
  fill_after_signal   every paper trade enters on a session strictly after its signal date; no decision file was written after its fill
  stops_gap           in the harness, a stop is never filled better than the stop level or the open (unit check on synthetic bars)
"""
from __future__ import annotations

import ast
import datetime as dt
import json
import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from india import exitlab, paths

SAFE_FILES = ("lab.py", "studies.py", "exitlab.py", "registry.py", "paper.py", "costs.py", "tracker.py", "evidence.py")
FEATURE_WHITELIST = {"date", "sid", "symbol", "liq_rank", "o", "h", "l", "c", "volume", "turnover", "ret_1", "ret_5", "ret_20", "ret_60", "gap_pct", "range_pct", "atr14", "atr_pct",
                     "rv20", "vol_ratio20", "dist_sma20", "dist_sma50", "dist_sma200", "breakout20", "breakdown20", "pos20", "deliv_pct"}


def _strings(path: Path) -> list[str]:
    tree = ast.parse(path.read_text())
    doc_nodes = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)) and n.body and isinstance(n.body[0], ast.Expr) and isinstance(getattr(n.body[0], "value", None), ast.Constant):
            doc_nodes.add(id(n.body[0].value))
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in doc_nodes:
            out.append(n.value)
        if isinstance(n, ast.Attribute):
            out.append(n.attr)
        if isinstance(n, ast.Name):
            out.append(n.id)
    return out


def check_sealed_files() -> tuple[bool, str]:
    bad = []
    here = Path(__file__).parent
    for f in SAFE_FILES:
        # a path or identifier (no spaces, or a slash) naming the sealed folder is a reference; prose such as "2024+ sealed" in a status note is not
        if any(s != "sealed" and any("sealed" in tok.lower() and ("/" in tok or "_" in tok or tok == s) for tok in s.split()) for s in _strings(here / f)):
            bad.append(f)
    # paper.py and the leak check may import the sealed module by name; nothing else should reference the folder helpers
    for f in ("lab.py", "studies.py", "exitlab.py", "registry.py", "costs.py"):
        if any("sealed" in s.lower() for s in _strings(here / f)):
            bad.append(f + " (mentions sealed)")
    return (not bad), ("clean" if not bad else "references in " + ", ".join(sorted(set(bad))))


def check_tables_pre_2024() -> tuple[bool, str]:
    con = duckdb.connect()
    last = {}
    for name in ("features/daily.parquet", "bars/adj_daily.parquet", "universe/u_liq_in.parquet"):
        last[name] = str(con.execute(f"select max(date) from read_parquet('{paths.gold() / name}')").fetchone()[0])
    ok = all(v < "2024-01-01" for v in last.values())
    return ok, json.dumps(last)


def check_feature_columns() -> tuple[bool, str]:
    con = duckdb.connect()
    cols = {r[0] for r in con.execute(f"describe select * from read_parquet('{paths.gold() / 'features/daily.parquet'}')").fetchall()}
    extra = cols - FEATURE_WHITELIST
    return (not extra), ("columns ok" if not extra else f"unexpected columns {sorted(extra)}")


def _silver_raw(until: str) -> pd.DataFrame:
    root = paths.data_dir()
    files = [str(p) for p in (root / "silver/cm_bhavcopy").glob("year=*/part.parquet")]
    since = (pd.Timestamp(until) - pd.Timedelta(days=400)).date()
    con = duckdb.connect()
    return con.execute(f"select date, symbol, series, open, high, low, close, prev_close, volume, turnover, isin from read_parquet({files!r}) where series = 'EQ' and close > 0 and date >= ? and date <= ?",
                       [since, pd.Timestamp(until).date()]).df()


def check_parity(asof: str = "2023-06-30") -> tuple[bool, str]:
    from india import paper
    raw = _silver_raw(asof)
    last = raw["date"].max()
    df = paper.load_adjusted(raw=raw)
    live = paper.features(df, pd.Timestamp(last))
    con = duckdb.connect()
    gold = con.execute(f"select symbol, liq_rank, atr14, dist_sma20, dist_sma200, vol_ratio20, breakout20 from read_parquet('{paths.gold() / 'features/daily.parquet'}') where date = ?", [last]).df()
    m = live.merge(gold, on="symbol", suffixes=("", "_gold"))
    if len(m) < 100:
        return False, f"only {len(m)} stocks matched on {last}"
    res = {"asof": str(last), "matched": int(len(m)), "live_n": int(len(live)), "gold_n": int(len(gold))}
    ok = True
    for c in ("atr14", "dist_sma20", "dist_sma200", "vol_ratio20"):
        d = (m[c] - m[c + "_gold"]).abs() / (m[c + "_gold"].abs() + 1e-9)
        res[c + "_within_1e-6"] = round(float((d < 1e-6).mean()), 4)
        ok &= float((d < 1e-6).mean()) > 0.985
    res["breakout_agree"] = round(float((m["breakout20"] == m["breakout20_gold"]).mean()), 4)
    res["liq_rank_agree_pm3"] = round(float(((m["liq_rank"] - m["liq_rank_gold"]).abs() <= 3).mean()), 4)
    ok &= res["breakout_agree"] > 0.99 and res["liq_rank_agree_pm3"] > 0.95
    return ok, json.dumps(res)


def check_future_edit(asof: str = "2023-06-30") -> tuple[bool, str]:
    from india import paper
    extra = _silver_raw("2023-12-29")
    extra = extra[extra["date"] >= pd.Timestamp(asof) - pd.Timedelta(days=400)]
    base = paper.decide(state={"trades": {}, "decisions": {}}, raw=extra, write=False, asof=asof)
    edited = extra.copy()
    fut = edited["date"] > pd.Timestamp(asof)
    rng = np.random.default_rng(3)
    for c in ("open", "high", "low", "close", "volume", "turnover"):
        edited[c] = edited[c].astype(float)
        edited.loc[fut, c] = edited.loc[fut, c] * rng.uniform(0.2, 5, fut.sum())
    cut = extra[extra["date"] <= pd.Timestamp(asof)]
    again = paper.decide(state={"trades": {}, "decisions": {}}, raw=edited, write=False, asof=asof)
    trunc = paper.decide(state={"trades": {}, "decisions": {}}, raw=cut, write=False, asof=asof)
    a, b, c = (x["body"]["signals"] for x in (base, again, trunc))
    same = a == b == c
    return same, f"{len(a)} signals on {asof}; edited future {'identical' if a == b else 'DIFFERENT'}; truncated {'identical' if a == c else 'DIFFERENT'}"


def check_fill_after_signal() -> tuple[bool, str]:
    p = paths.data_dir() / "paper" / "state.json"
    if not p.exists():
        return True, "no paper trades yet"
    st = json.loads(p.read_text())
    bad = [t["id"] for t in st["trades"].values() if t.get("entry_date") and t["entry_date"] <= t["signal_date"]]
    late = []
    for d, meta in st["decisions"].items():
        f = paths.data_dir() / "paper" / "decisions" / f"{d}.json"
        if meta.get("filled_on") and f.exists():
            decided = json.loads(f.read_text())["decided_at"]
            # decided_at is UTC; the fill session opens 03:45 UTC on its date (09:15 IST), so the decision file must be earlier than that
            if decided >= f"{meta['filled_on']}T03:45:00":
                late.append(d)
    return (not bad and not late), f"{len(bad)} entries on or before signal date; {len(late)} decisions written after the fill session opened"


def check_stops_gap() -> tuple[bool, str]:
    o = np.array([100.0, 90.0, 95.0]); h = np.array([101.0, 92.0, 96.0]); l = np.array([99.0, 88.0, 94.0]); c = np.array([100.0, 91.0, 95.0])
    k, px, why, _ = exitlab._exit(exitlab.Policy("hold", "hold", 5), o, h, l, c, 100.0, 5.0)
    gap_ok = why == "stop" and px == 90.0  # gapped through 95: fill at the open 90, not the stop level
    o2 = np.array([100.0, 99.0]); h2 = np.array([101.0, 100.0]); l2 = np.array([99.0, 94.0]); c2 = np.array([100.0, 96.0])
    k2, px2, why2, _ = exitlab._exit(exitlab.Policy("hold", "hold", 5), o2, h2, l2, c2, 100.0, 5.0)
    touch_ok = why2 == "stop" and px2 == 95.0
    both = exitlab._exit(exitlab.Policy("target", "target", 1), np.array([100.0, 100.0]), np.array([101.0, 106.0]), np.array([99.0, 94.0]), np.array([100.0, 100.0]), 100.0, 5.0)
    both_ok = both[2] == "stop"  # stop and target in the same bar: the unfavourable reading
    return (gap_ok and touch_ok and both_ok), f"gap {gap_ok}, touch {touch_ok}, same-bar stop+target {both_ok}"


CHECKS = {"sealed_files": check_sealed_files, "tables_pre_2024": check_tables_pre_2024, "feature_columns": check_feature_columns, "parity": check_parity,
          "future_edit": check_future_edit, "fill_after_signal": check_fill_after_signal, "stops_gap": check_stops_gap}


def run() -> dict:
    paths.ensure()
    out = {}
    for name, fn in CHECKS.items():
        try:
            ok, note = fn()
        except Exception as e:
            ok, note = False, f"error {type(e).__name__}: {e}"
        out[name] = {"ok": bool(ok), "note": note}
        print(("PASS " if ok else "FAIL ") + name + " — " + note, flush=True)
    out["_at"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    (paths.manifest_dir() / "leakcheck.json").write_text(json.dumps(out, indent=1))
    return out


if __name__ == "__main__":
    r = run()
    sys.exit(0 if all(v["ok"] for k, v in r.items() if not k.startswith("_")) else 1)
