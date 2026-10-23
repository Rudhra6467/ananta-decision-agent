"""Leak, mapping and workflow checks. Every check prints PASS or FAIL and the line goes into manifests/leakcheck.json; the evidence job runs them nightly.

  python -m india.leakcheck           all checks
Checks:
  sealed_files        lab / studies / exitlab / registry / paper / costs / greeks-input code never names the sealed folder; only india/sealed.py reads it
  kite_calls          india/kite.py sends GET plus only Kite's margin calculator (POST /margins/basket); no order path
  tables_pre_2024     gold lab tables stop before 2024-01-01
  feature_columns     the daily feature table holds no forward-looking columns (whitelist)
  parity              the paper engine's live features equal the lab's gold features on a past date (mapping between the two code paths)
  future_edit         changing every row after a date does not change the decision made on that date
  fill_after_signal   every paper trade enters on a session strictly after its signal date; no decision file was written after its fill
  stops_gap           in the harness, a stop is never filled better than the stop level or the open (unit check on synthetic bars)
  paper_review        live paper days (sealed purpose paper_review) are read only by india/missed.py, only through sealed.read_review, and only
                      with a constant start on or after 2026-10-16; no other module names the purpose
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

SAFE_FILES = ("lab.py", "studies.py", "exitlab.py", "registry.py", "paper.py", "costs.py", "tracker.py", "evidence.py", "reconstruct.py", "allocator.py")
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
    for f in ("lab.py", "studies.py", "exitlab.py", "registry.py", "costs.py", "conditions.py", "studies2.py", "istudies.py", "fstudies.py", "vstudies.py",
              "exitbook.py", "o4hist.py", "replay.py", "optreal.py", "selection.py", "hedge.py", "flowstudy.py", "morning.py", "sp1nightly.py", "sp3run.py", "sp3learn.py"):
        if (here / f).exists() and any("sealed" in s.lower() for s in _strings(here / f)):
            bad.append(f + " (mentions sealed)")
    # calibrate.py may read sealed rows, but every call must name the purpose "calibration" (a data-vs-market check, never a rule score)
    cal = here / "calibrate.py"
    if cal.exists():
        for n in ast.walk(ast.parse(cal.read_text())):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name) and n.func.value.id == "sealed":
                first = n.args[0].value if n.args and isinstance(n.args[0], ast.Constant) else None
                if first != "calibration":
                    bad.append(f"calibrate.py line {n.lineno} (sealed.{n.func.attr} purpose {first!r})")
    # sp1_holdout.py may open only its own registered run and may call only the holdout functions of the sealed module
    ho = here / "sp1_holdout.py"
    if ho.exists():
        for n in ast.walk(ast.parse(ho.read_text())):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name) and n.func.value.id == "sealed":
                if n.func.attr not in ("holdout_open", "holdout_query", "holdout_complete"):
                    bad.append(f"sp1_holdout.py line {n.lineno} (sealed.{n.func.attr})")
                if n.func.attr == "holdout_open":
                    first = n.args[0].value if n.args and isinstance(n.args[0], ast.Constant) else None
                    if first != "sp1_holdout":
                        bad.append(f"sp1_holdout.py line {n.lineno} (holdout_open {first!r})")
    # sp1paper.py (the live paper engine) may read the lookback rows and, after the holdout run completed, that run's own outputs; nothing else
    pp = here / "sp1paper.py"
    if pp.exists():
        allowed = {"read_cm": {"paper_lookback"}, "read_flows": {"paper_lookback"}, "holdout_outputs": {"sp1_holdout"}}
        for n in ast.walk(ast.parse(pp.read_text())):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name) and n.func.value.id == "sealed":
                first = n.args[0].value if n.args and isinstance(n.args[0], ast.Constant) else None
                if n.func.attr not in allowed or first not in allowed[n.func.attr]:
                    bad.append(f"sp1paper.py line {n.lineno} (sealed.{n.func.attr} {first!r})")
                if n.func.attr == "holdout_outputs":
                    second = n.args[1].value if len(n.args) > 1 and isinstance(n.args[1], ast.Constant) else None
                    if second not in ("paper_model", "paper_parity"):
                        bad.append(f"sp1paper.py line {n.lineno} (holdout_outputs purpose {second!r})")
        if any("sealed/" in x for x in _strings(pp)):
            bad.append("sp1paper.py (names a sealed path)")
    # sp3.py (the positional playbook study) may ask only for presence dates (the coverage rule); its holdout run will live in its own file
    s3 = here / "sp3.py"
    if s3.exists():
        for n in ast.walk(ast.parse(s3.read_text())):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name) and n.func.value.id == "sealed":
                if n.func.attr not in ("coverage", "coverage_summary"):
                    bad.append(f"sp3.py line {n.lineno} (sealed.{n.func.attr})")
            if isinstance(n, ast.ImportFrom) and (n.module or "").endswith("sealed"):
                bad.append(f"sp3.py line {n.lineno} (from {n.module} import ...)")
            if isinstance(n, ast.Attribute) and n.attr == "sealed_dir":
                bad.append(f"sp3.py line {n.lineno} (.sealed_dir)")
        # string constants only: the module name `sealed` must appear (sp3.py calls sealed.coverage), a path to the folder must not
        consts = [n.value for n in ast.walk(ast.parse(s3.read_text())) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
        if any(x.strip() in ("sealed", "sealed_dir") or "sealed/" in x or "/sealed" in x for x in consts):
            bad.append("sp3.py (names the sealed folder)")
    for f in ("sp1.py", "scenario.py", "ocstudy.py"):
        if (here / f).exists() and any(x in ("sealed", "sealed_dir") or "sealed/silver" in x or "sealed/gold" in x for x in _strings(here / f)):
            bad.append(f + " (mentions sealed)")
    return (not bad), ("clean" if not bad else "references in " + ", ".join(sorted(set(bad))))


REVIEW_MODULE = "missed.py"
REVIEW_MIN_START = "2026-10-16"   # the stock paper's first decision day (sealed.PAPER_REVIEW_START)


def _code_strings(tree: ast.AST) -> list[str]:
    """String constants that are not docstrings (prose may describe the purpose; code may not use it)."""
    doc = {id(n.body[0].value) for n in ast.walk(tree) if isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef))
           and n.body and isinstance(n.body[0], ast.Expr) and isinstance(getattr(n.body[0], "value", None), ast.Constant)}
    return [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in doc]


REVIEW_MODULES = {REVIEW_MODULE: ("paper_review", "read_review"),      # the missed-movers review (20 Oct 2026)
                  "others.py": ("others_review", "read_others")}       # the reference-traders review (22 Oct 2026)


def check_paper_review(here: Path | None = None) -> tuple[bool, str]:
    """Live paper days are read by the two review modules only (REVIEW_MODULES), each through its own sealed reader and purpose, and only with a
    start that is a constant (a literal, or a module-level name assigned once to a literal) on or after 2026-10-16. No other module may name
    either purpose or call either reader."""
    here = Path(here) if here else Path(__file__).parent
    bad = []
    purposes = {p for p, _ in REVIEW_MODULES.values()}
    readers = {r for _, r in REVIEW_MODULES.values()}
    for f in sorted(here.glob("*.py")):
        if f.name in ("sealed.py", "leakcheck.py") or f.name in REVIEW_MODULES:
            continue
        tree = ast.parse(f.read_text())
        for p in sorted(purposes):
            if any(p in s for s in _code_strings(tree)):
                bad.append(f"{f.name} (names the {p} purpose)")
        for r in sorted(readers):
            if any(isinstance(n, ast.Attribute) and n.attr == r for n in ast.walk(tree)):
                bad.append(f"{f.name} (calls {r})")
    for REVIEW_MODULE_, (own_purpose, own_reader) in REVIEW_MODULES.items():
        bad += _check_review_module(here / REVIEW_MODULE_, own_purpose, own_reader)
    note = (f"only {' and '.join(REVIEW_MODULES)} read live paper days, start constant on or after {REVIEW_MIN_START}" if not bad
            else "; ".join(sorted(set(bad))))
    return (not bad), note


def _check_review_module(m: Path, own_purpose: str, own_reader: str) -> list[str]:
    bad: list[str] = []
    REVIEW_MODULE = m.name
    if m.exists():
        tree = ast.parse(m.read_text())
        assigned: dict[str, list] = {}
        for n in ast.walk(tree):   # every binding of a name: assignments, loop and with targets, walrus, and parameters (which would shadow it)
            if isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del)):
                assigned.setdefault(n.id, []).append(n)
            elif isinstance(n, ast.arg):
                assigned.setdefault(n.arg, []).append(n)
            elif isinstance(n, ast.Global):
                for g in n.names:
                    assigned.setdefault(g, []).append(n)
        top = {t.id: n.value.value for n in tree.body if isinstance(n, ast.Assign) and isinstance(n.value, ast.Constant) for t in n.targets if isinstance(t, ast.Name)}
        calls = 0
        for n in ast.walk(tree):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name) and n.func.value.id == "sealed":
                if n.func.attr != own_reader:
                    bad.append(f"{REVIEW_MODULE} line {n.lineno} (sealed.{n.func.attr})")
                    continue
                calls += 1
                purpose = n.args[0].value if n.args and isinstance(n.args[0], ast.Constant) else None
                if purpose != own_purpose:
                    bad.append(f"{REVIEW_MODULE} line {n.lineno} ({own_reader} purpose {purpose!r})")
                node = n.args[1] if len(n.args) > 1 else next((k.value for k in n.keywords if k.arg == "since"), None)
                start = None
                if isinstance(node, ast.Constant):
                    start = node.value
                elif isinstance(node, ast.Name) and node.id in top and len(assigned.get(node.id, [])) == 1:
                    start = top[node.id]
                try:
                    ok_start = isinstance(start, str) and dt.date.fromisoformat(start) >= dt.date.fromisoformat(REVIEW_MIN_START)
                except ValueError:
                    ok_start = False
                if not ok_start:
                    bad.append(f"{REVIEW_MODULE} line {n.lineno} ({own_reader} start {start!r} is not a constant on or after {REVIEW_MIN_START})")
            if isinstance(n, ast.ImportFrom) and (n.module or "").endswith("sealed"):
                bad.append(f"{REVIEW_MODULE} line {n.lineno} (from {n.module} import ...)")
            if isinstance(n, ast.Attribute) and n.attr == "sealed_dir":
                bad.append(f"{REVIEW_MODULE} line {n.lineno} (.sealed_dir)")
        if any("sealed/" in s or "/sealed" in s or "cm_bhavcopy" in s or "kite_index" in s or "participant_oi" in s for s in _code_strings(tree)):
            bad.append(f"{REVIEW_MODULE} (names a sealed or price-data path)")
    return bad


def check_kite_calls() -> tuple[bool, str]:
    """india/kite.py sends GET, plus only Kite's margin calculator (POST /margins/basket, approved by Madhav 19 Oct 2026); no other POST, no PUT or DELETE,
    and no order path anywhere in the file."""
    src = (Path(__file__).parent / "kite.py").read_text()
    tree = ast.parse(src)
    bad = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in ("post", "put", "delete", "patch"):
            owner = n.func.value
            is_ntfy = isinstance(owner, ast.Name) and owner.id == "requests" and n.args and isinstance(n.args[0], ast.JoinedStr) and "ntfy.sh" in ast.unparse(n.args[0])
            in_calc = any(isinstance(f, ast.FunctionDef) and f.name == "post_calc" and f.lineno <= n.lineno <= f.end_lineno for f in ast.walk(tree))
            if not (is_ntfy or (n.func.attr == "post" and in_calc)):
                bad.append(f"line {n.lineno}: .{n.func.attr}(")
    calc = next((n for n in ast.walk(tree) if isinstance(n, ast.Assign) and any(getattr(t, "id", "") == "CALC_POSTS" for t in n.targets)), None)
    allowed = ast.literal_eval(calc.value) if calc else None
    if allowed != ("/margins/basket",):
        bad.append(f"CALC_POSTS is {allowed!r}")
    for word in ("/orders/", "/gtt", "place_order", "modify_order", "cancel_order"):
        if word in src:
            bad.append(f"mentions {word}")
    return (not bad), ("GET plus the margin calculator only" if not bad else "; ".join(bad))


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
    # RSI(14) of the REV campaign: the paper engine starts its recursion at the 400-day lookback, the lab at the first bar ever; they must agree closely
    if "rsi14" in live:
        bars = con.execute(f"select sid, date, c from read_parquet('{paths.gold() / 'bars/adj_daily.parquet'}') where date <= ? order by sid, date", [last]).df()
        sym_sid = dict(zip(live["symbol"], live["sid"]))
        lab_rsi = {}
        for sid, g in bars[bars["sid"].isin(set(m["symbol"].map(sym_sid)))].groupby("sid"):
            d = g["c"].diff()
            au = d.clip(lower=0).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean().iloc[-1]
            ad = (-d).clip(lower=0).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean().iloc[-1]
            lab_rsi[sid] = 100 - 100 / (1 + au / ad) if ad > 0 else 100.0
        m["rsi_lab"] = m["sid"].map(lab_rsi)
        dr = (m["rsi14"] - m["rsi_lab"]).abs().dropna()
        res["rsi14_within_0.5pt"] = round(float((dr < 0.5).mean()), 4)
        res["rsi14_side_of_30_agree"] = round(float(((m["rsi14"] < 30) == (m["rsi_lab"] < 30)).mean()), 4)
        ok &= res["rsi14_within_0.5pt"] > 0.98 and res["rsi14_side_of_30_agree"] > 0.995
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


CHECKS = {"sealed_files": check_sealed_files, "kite_calls": check_kite_calls, "tables_pre_2024": check_tables_pre_2024, "feature_columns": check_feature_columns, "parity": check_parity,
          "future_edit": check_future_edit, "fill_after_signal": check_fill_after_signal, "stops_gap": check_stops_gap, "paper_review": check_paper_review}


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
