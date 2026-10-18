"""Data and book integrity checks: duplicates, survivorship, stale prices, instrument mappings, corporate actions, calendar coverage, and whether paper
fills are possible. Complements india/leakcheck.py (look-ahead). Every run writes manifests/integrity.json and a line per check to the evidence log.

  python -m india.integrity            run every check
  python -m india.integrity dup_keys   one check

A check returns ok, a one-line note and the numbers behind it. A failure is a finding to fix or explain, not a reason to stop other work.
Rows dated 2024+ are read only through india.sealed (purpose integrity) and only key, date and price-equality columns; no returns are computed from them.
"""
from __future__ import annotations

import datetime as dt
import json
import sys

import duckdb
import pandas as pd

from india import catalog, paths, sealed


def _pq(folder: str) -> str:
    return str(paths.data_dir() / folder / "**" / "*.parquet")


def _gold(name: str) -> str:
    return str(paths.gold() / name)


def check_dup_keys() -> tuple[bool, str, dict]:
    keys = {"silver/cm_bhavcopy": "date, symbol, series", "silver/delivery": "date, symbol, series",
            "silver/fo_bhavcopy": "date, instrument, symbol, expiry, strike, opt_type", "silver/kite_index/day": "index_name, date", "silver/fo_greeks": "date, symbol, expiry, strike, opt_type"}
    gold = {"features/daily.parquet": "date, sid", "bars/adj_daily.parquet": "date, sid", "universe/u_liq_in.parquet": "date, sid"}
    con = duckdb.connect()
    out = {}
    for folder, k in keys.items():
        out[folder] = int(con.execute(f"select count(*) from (select {k} from read_parquet('{_pq(folder)}', union_by_name=true) group by {k} having count(*) > 1)").fetchone()[0])
        s = sealed.read_cols("integrity", folder, [c.strip() for c in k.split(",")], "2024-01-01")
        out["sealed/" + folder] = int(s.duplicated().sum())
    for name, k in gold.items():
        out["gold/" + name] = int(con.execute(f"select count(*) from (select {k} from read_parquet('{_gold(name)}') group by {k} having count(*) > 1)").fetchone()[0])
    con.close()
    bad = {k: v for k, v in out.items() if v}
    return (not bad), ("no duplicate keys" if not bad else f"duplicate keys in {bad}"), out


def check_survivorship() -> tuple[bool, str, dict]:
    """The research universe must contain stocks that later stopped trading; a universe built from today's list would not."""
    con = duckdb.connect()
    df = con.execute(f"""
        with last as (select sid, max(date) as last from read_parquet('{_gold('bars/adj_daily.parquet')}') group by sid),
             u as (select year(date) as y, sid from read_parquet('{_gold('universe/u_liq_in.parquet')}') where top250 group by 1, 2)
        select y, count(*) as members, sum(case when last.last < date '2023-06-30' then 1 else 0 end) as later_stopped
        from u join last using (sid) group by y order by y""").df()
    con.close()
    early = df[df["y"] <= 2015]
    ok = bool(len(early)) and bool((early["later_stopped"] > 0).all())
    share = (df["later_stopped"] / df["members"]).round(3)
    return ok, f"top-250 members that later stopped trading: {int(df['later_stopped'].sum())} stock-years; share by year {share.min():.1%}-{share.max():.1%}", \
        {"by_year": dict(zip(df["y"].astype(int).astype(str), zip(df["members"].astype(int), df["later_stopped"].astype(int))))}


def check_stale_prices() -> tuple[bool, str, dict]:
    """Liquid stocks (top 500) whose adjusted close is unchanged for 5+ sessions while volume is positive: a frozen feed, not a market."""
    con = duckdb.connect()
    r = con.execute(f"""
        with b as (select b.sid, b.date, b.c, b.volume, case when b.c = lag(b.c) over (partition by b.sid order by b.date) then 0 else 1 end as brk
                   from read_parquet('{_gold('bars/adj_daily.parquet')}') b),
             g as (select *, sum(brk) over (partition by sid order by date) as grp from b),
             runs as (select sid, grp, count(*) as n, min(volume) as minvol, min(date) as start from g group by sid, grp having count(*) >= 5),
             liq as (select sid, date from read_parquet('{_gold('universe/u_liq_in.parquet')}') where top500)
        select count(*), count(distinct runs.sid) from runs join liq on runs.sid = liq.sid and runs.start = liq.date where runs.minvol > 0""").fetchone()
    con.close()
    # the latest sealed sessions: a re-published file would repeat yesterday's closes for most stocks
    s = sealed.read_cols("integrity", "silver/cm_bhavcopy", ["date", "symbol", "close", "prev_close", "volume"], (dt.date.today() - dt.timedelta(days=20)).isoformat(), "series = 'EQ'")
    last_days = {}
    for d, g in s.groupby("date"):
        g = g[g["volume"] > 0]
        last_days[str(d)[:10]] = round(float((g["close"] == g["prev_close"]).mean()), 4) if len(g) else None
    worst = max((v for v in last_days.values() if v is not None), default=0)
    # every frozen run must be flagged for the exit harness (gold/ca_flags, status FROZEN), so no study trades through one
    fl = paths.gold() / "ca_flags" / "ca_flags.parquet"
    flagged = 0
    if fl.exists():
        f = pd.read_parquet(fl)
        flagged = int((f["status"] == "FROZEN").sum() // 2)
    ok = flagged >= r[0] and worst < 0.2
    return ok, (f"{r[0]} frozen runs (5+ unchanged closes with volume) in liquid stocks across {r[1]} stocks, {flagged} runs flagged and skipped by the lab; "
                f"recent sessions unchanged-close share max {worst:.1%}"), {"frozen_runs": int(r[0]), "stocks": int(r[1]), "flagged": flagged, "recent_unchanged_share": last_days}


def check_mappings() -> tuple[bool, str, dict]:
    """Recent cash rows map to an ISIN and a company entity; an ISIN maps to one entity; one entity does not trade under two symbols on one day;
    every stock future on the latest day has a cash row; Kite closes agree with the exchange file on the spot-check list."""
    since = (dt.date.today() - dt.timedelta(days=30)).isoformat()
    cm = sealed.read_cols("integrity", "silver/cm_bhavcopy", ["date", "symbol", "isin"], since, "series = 'EQ'")
    names = pd.read_parquet(paths.data_dir() / "silver/security_master/names.parquet")
    isin_ent = names[["isin", "entity"]].drop_duplicates()
    multi = int(isin_ent.groupby("isin")["entity"].nunique().gt(1).sum())
    m = cm.merge(isin_ent.drop_duplicates("isin"), on="isin", how="left")
    no_isin = int(m["isin"].isna().sum())
    no_ent = float(m["entity"].isna().mean()) if len(m) else 0.0
    two_sym = int(m.dropna(subset=["entity"]).groupby(["date", "entity"])["symbol"].nunique().gt(1).sum())
    fo = sealed.read_cols("integrity", "silver/fo_bhavcopy", ["date", "symbol", "instrument"], since, "instrument in ('FUTSTK', 'STF')")
    fo_missing = []
    if len(fo) and len(cm):
        d = fo["date"].max()
        fs = set(fo.loc[fo["date"] == d, "symbol"])
        cs = set(cm.loc[cm["date"] == d, "symbol"])
        fo_missing = sorted(fs - cs)
    q = sorted((paths.data_dir() / "silver/quality").glob("spot_checks_*.parquet"))
    spot = None
    if q:
        sq = pd.read_parquet(q[-1])
        spot = {"file": q[-1].name, "rows": int(len(sq)),
                "within_tol": round(float(sq["within_tol"].mean()), 4) if "within_tol" in sq else None,
                "kite_missing": int(sq["kite_missing"].sum()) if "kite_missing" in sq else None}
        if spot["within_tol"] is None:
            spot = None  # a spot-check file of another kind (no tolerance column): not a mapping test
    ok = no_isin == 0 and multi == 0 and two_sym == 0 and not fo_missing and no_ent < 0.02 and (spot is None or spot["within_tol"] >= 0.98)
    return ok, (f"30 days: {no_isin} rows without ISIN, {no_ent:.2%} without an entity, {two_sym} entity-days on two symbols, {multi} ISINs on two entities, "
                f"{len(fo_missing)} stock futures without a cash row; Kite spot check {spot}"), \
        {"no_isin": no_isin, "no_entity_share": no_ent, "entity_two_symbols": two_sym, "isin_multi_entity": multi, "fo_without_cash": fo_missing[:20], "spot": spot}


def check_corporate_actions() -> tuple[bool, str, dict]:
    """On ex-dates the adjusted series should not jump; large raw falls with no recorded action are candidates for a missing split or bonus."""
    con = duckdb.connect()
    fx = str(paths.data_dir() / "silver/corporate_actions/factors.parquet")
    feat = _gold("features/daily.parquet")
    r = con.execute(f"""
        with f as (select symbol, ex_date from read_parquet('{fx}') where factor is not null and factor > 0 and factor <> 1)
        select count(*), sum(case when abs(d.ret_1) > 0.3 then 1 else 0 end) from f join read_parquet('{feat}') d on d.symbol = f.symbol and d.date = f.ex_date""").fetchone()
    miss = con.execute(f"""
        with f as (select symbol, ex_date from read_parquet('{fx}') where factor is not null and factor > 0)
        select year(d.date) as y, count(*) as n from read_parquet('{feat}') d
        where d.ret_1 < -0.45 and d.liq_rank <= 500 and not exists (select 1 from f where f.symbol = d.symbol and abs(datediff('day', f.ex_date, d.date)) <= 3)
        group by 1 order by 1""").df()
    con.close()
    n, bad = int(r[0] or 0), int(r[1] or 0)
    share = bad / n if n else 0.0
    return share < 0.02, f"{n} ex-dates in the features table; {bad} ({share:.2%}) still jump more than 30% after adjustment; {int(miss['n'].sum())} liquid-stock falls over 45% with no action within 3 days", \
        {"ex_dates": n, "jump_after_adjust": bad, "unexplained_falls_by_year": dict(zip(miss["y"].astype(str), miss["n"].astype(int)))}


def check_calendar() -> tuple[bool, str, dict]:
    con = duckdb.connect()
    cal = con.execute(f"select date from read_parquet('{paths.data_dir() / 'silver/calendar/calendar.parquet'}') where is_trading_day").df()["date"]
    cm = con.execute(f"select distinct date from read_parquet('{_pq('silver/cm_bhavcopy')}')").df()["date"]
    con.close()
    cm_s = sealed.read_cols("integrity", "silver/cm_bhavcopy", ["distinct date"], "2024-01-01")
    have = set(pd.to_datetime(cm)) | set(pd.to_datetime(cm_s.iloc[:, 0])) if len(cm_s) else set(pd.to_datetime(cm))
    cal = set(pd.to_datetime(cal))
    lo = max(min(have), min(cal))
    missing = sorted(d for d in cal if d >= lo and d not in have)
    extra = sorted(d for d in have if d >= lo and d not in cal)
    return (not missing and not extra), f"{len(cal)} calendar trading days; {len(missing)} without a cash file; {len(extra)} cash files on non-trading days", \
        {"missing": [str(d.date()) for d in missing[:30]], "extra": [str(d.date()) for d in extra[:30]]}


def check_fills() -> tuple[bool, str, dict]:
    """Paper fills must be prices that traded: the entry is the session's open (inside its low-high), an exit inside the exit bar's range, costs charged on every close;
    the baseline book must agree with the executed book for the same trade id; option rows must carry fees and positive prices."""
    p = paths.data_dir() / "paper"
    out = {"exec_checked": 0, "entry_outside_bar": 0, "exit_outside_bar": 0, "no_cost": 0, "baseline_mismatch": 0, "baseline_checked": 0, "options_checked": 0, "options_bad": 0}
    st = json.loads((p / "state.json").read_text()) if (p / "state.json").exists() else {"trades": {}}
    ex = [t for t in st["trades"].values() if t.get("status") in ("open", "closed")]
    for t in ex:
        out["exec_checked"] += 1
        if "bar_low_raw" in t and not (t["bar_low_raw"] - 1e-6 <= t["entry_raw"] <= t["bar_high_raw"] + 1e-6):
            out["entry_outside_bar"] += 1
        if t.get("status") == "closed":
            if "exit_bar_low_adj" in t and not (t["exit_bar_low_adj"] - 1e-6 <= t["exit_adj"] <= t["exit_bar_high_adj"] + 1e-6):
                out["exit_outside_bar"] += 1
            if not t.get("cost_inr") or t["cost_inr"] <= 0:
                out["no_cost"] += 1
    if (p / "baseline.parquet").exists() and ex:
        b = pd.read_parquet(p / "baseline.parquet").set_index("id")
        for t in ex:
            if t["id"] in b.index:
                out["baseline_checked"] += 1
                r = b.loc[t["id"]]
                if abs(float(r["entry_adj"]) - t["entry_adj"]) > 1e-6 * t["entry_adj"] or (t["status"] == "closed" and r["status"] == "closed" and abs(float(r["net_inr"]) - t["net_inr"]) > 0.01):
                    out["baseline_mismatch"] += 1
    op = p / "options_trades.jsonl"
    if op.exists():
        for line in op.read_text().splitlines():
            r = json.loads(line)
            if r.get("kind") == "skip":
                continue
            out["options_checked"] += 1
            prices = [v for k, v in r.items() if k in ("ce_in", "pe_in", "credit") and isinstance(v, (int, float))]
            if r.get("fees_inr", 0) <= 0 or any(x <= 0 for x in prices) or abs(r["gross_inr"] - r["fees_inr"] - r["net_inr"]) > 0.01:
                out["options_bad"] += 1
    bad = out["entry_outside_bar"] + out["exit_outside_bar"] + out["no_cost"] + out["baseline_mismatch"] + out["options_bad"]
    note = (f"exec {out['exec_checked']} trades, baseline cross-checked {out['baseline_checked']}, options {out['options_checked']}: {bad} problems"
            if out["exec_checked"] or out["options_checked"] else "no filled paper trades yet (first stock fill is the 19 Oct open)")
    return bad == 0, note, out


CHECKS = {"dup_keys": check_dup_keys, "survivorship": check_survivorship, "stale_prices": check_stale_prices, "mappings": check_mappings,
          "corporate_actions": check_corporate_actions, "calendar": check_calendar, "fills": check_fills}


def run(only: str | None = None) -> dict:
    paths.ensure()
    out = {}
    for name, fn in CHECKS.items():
        if only and name != only:
            continue
        t0 = dt.datetime.now()
        try:
            ok, note, metrics = fn()
        except Exception as e:
            ok, note, metrics = False, f"error {type(e).__name__}: {e}", {}
        out[name] = {"ok": bool(ok), "note": note, "metrics": metrics, "secs": round((dt.datetime.now() - t0).total_seconds(), 1)}
        print(("PASS " if ok else "FAIL ") + name + " — " + note, flush=True)
    out["_at"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    if not only:
        (paths.manifest_dir() / "integrity.json").write_text(json.dumps(out, indent=1, default=str))
    return out


if __name__ == "__main__":
    r = run(sys.argv[1] if len(sys.argv) > 1 else None)
    sys.exit(0 if all(v["ok"] for k, v in r.items() if not k.startswith("_")) else 1)
