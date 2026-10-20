"""SP1 holdout: the ONE confirmatory run of the frozen index playbook (registrations/sp1_v2.json, tests.holdout), approved by Madhav 19 Oct 2026.

  python -m india.sp1_holdout consistency   silver only (2023), no sealed read: the holdout builders must reproduce the gold universe ranks, the OC1
                                            breadth, the situation table and the SP1 outcomes exactly before the holdout is opened
  python -m india.sp1_holdout run           open the registered run (india.sealed.holdout_open), build 2024-01-01..2026-10-16 through the same code
                                            (scenario.build, sp1.outcomes), refit each test year on all earlier years, score, record, complete

The window, folders and approval live in india/sealed.py HOLDOUT_RUNS; every sealed query is logged in manifests/sealed_access.jsonl and the run
in manifests/holdout_runs.jsonl. Outputs of the run stay under the sealed tree (data) and in registrations/sp1_holdout_results.md (numbers).
Documented difference from the dev/validation build: gold/ca_flags ends in 2023, so no corporate-action exclusion applies to 2024+ breadth
(in 2015-2023 it removed 17 of 197,827 eligible stock-days).
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from india import ocstudy, paths, scenario, sealed, sp1

HERE = Path(__file__).parent
RUN = "sp1_holdout"


# ----------------------------------------------------------------------------------------------------------------------------- readers
class SilverReader:
    """Silver rows in a date window (used by the consistency mode; never touches the sealed tree)."""

    def __init__(self, start: str, end: str):
        self.start, self.end = pd.Timestamp(start).date(), pd.Timestamp(end).date()

    def q(self, folder: str, select: str, where: str = "", params: list | None = None, group_by: str = "") -> pd.DataFrame:
        base = paths.data_dir() / "silver" / folder
        files = [str(p) for p in sorted(base.glob("**/*.parquet"))]
        sql = (f"select {select} from read_parquet({files!r}, union_by_name=true) where cast(date as date) >= ? and cast(date as date) <= ?"
               + (f" and ({where})" if where else "") + (f" group by {group_by}" if group_by else ""))
        con = duckdb.connect()
        con.execute("set threads to 6")
        df = con.execute(sql, [self.start, self.end] + list(params or [])).df()
        con.close()
        return df


class HoldoutReader:
    """Silver rows from `silver_start` to 2023-12-31 plus the run's sealed rows (through the logged gateway)."""

    def __init__(self, ticket: dict, silver_start: str):
        self.t = ticket
        self.silver = SilverReader(silver_start, "2023-12-31")

    def q(self, folder, select, where="", params=None, group_by=""):
        a = self.silver.q(folder, select, where, params, group_by)
        b = sealed.holdout_query(self.t, folder, select, where, params, group_by)
        return pd.concat([a, b], ignore_index=True) if len(b) else a


# ----------------------------------------------------------------------------------------------------------------------------- calendar
def calendar_full() -> tuple[list[dt.date], set[dt.date]]:
    D = paths.data_dir()
    cal = pd.read_parquet(D / "silver/calendar/calendar.parquet")
    days = sorted(pd.to_datetime(cal.loc[cal["is_trading_day"], "date"]).dt.date)
    sp = json.loads((D / "manifests/special_sessions.json").read_text())["dates"]
    return days, {dt.date.fromisoformat(x) for x in sp}


# ----------------------------------------------------------------------------------------------------------------------------- universe
def universe_ranks(rd, start: str, first_day: dt.date) -> pd.DataFrame:
    """gold/universe rule (india/lab.py): series EQ, close > 0, no fund units; entity from the ISIN master; one row per entity-day (largest
    turnover); 60-session median turnover; at least 126 sessions and a close above Rs 10; rank 1 = most liquid. Ranks from first_day on."""
    D = paths.data_dir()
    cm = rd.q("cm_bhavcopy", "date, symbol, series, close, turnover, isin", "series = 'EQ' and close > 0")
    ent = pd.read_parquet(D / "silver/security_master/names.parquet", columns=["isin", "entity"]).drop_duplicates()
    con = duckdb.connect()
    con.register("cm", cm)
    con.register("ent", ent)
    df = con.execute("""
        with base0 as (select c.date::date as date, coalesce(e.entity, c.symbol) as sid, c.symbol, c.close as raw_close, c.turnover
                       from cm c left join (select distinct isin, entity from ent) e on e.isin = c.isin
                       where coalesce(c.isin, '') not like 'INF%' and c.symbol not in (select distinct symbol from cm where isin like 'INF%')
                       qualify row_number() over (partition by c.date, coalesce(e.entity, c.symbol) order by c.turnover desc) = 1),
             b as (select *, row_number() over (partition by sid order by date) as n from base0),
             m as (select *, quantile_cont(turnover, 0.5) over (partition by sid order by date rows between 59 preceding and current row) as med60 from b)
        select date, sid, symbol, med60, n as sessions, rank() over (partition by date order by med60 desc) as rank
        from m where n >= 126 and raw_close > 10""").df()
    con.close()
    df["date"] = pd.to_datetime(df["date"]).dt.date
    return df[df["date"] >= first_day]


def prev_ranks(u: pd.DataFrame, days: list[dt.date]) -> pd.DataFrame:
    """ocstudy.load_universe: rank <= 100 on the previous session, keyed by the session it applies to."""
    u = u[u["rank"] <= 100]
    nxt = {days[i - 1]: days[i] for i in range(1, len(days))}
    u = u.assign(day=u["date"].map(nxt)).dropna(subset=["day"]).rename(columns={"symbol": "u_symbol"})
    return u[["day", "sid", "u_symbol", "rank"]]


# ----------------------------------------------------------------------------------------------------------------------------- breadth
def breadth(rd, days, specials, ranks_prev: pd.DataFrame, first_day: dt.date, ca_block: set) -> pd.DataFrame:
    """OC v1 breadth (ocstudy.stock_pass): eligible top 50 (rank <= 50 on the previous session, linked, valid day, rvol baseline in at least 15 of
    the previous 20 regular sessions at every bar to 10:10, no ETF, no corporate-action block), share above their own 09:15 open per 5-minute bar."""
    D = paths.data_dir()
    link = ocstudy.load_link()
    rp = ranks_prev[~ranks_prev["u_symbol"].str.contains(ocstudy.ETF_RE)]
    lk = link[link["entity"].isin(set(rp["sid"]))]
    syms = sorted(lk["kite_symbol"].unique())
    mm = "(hour(ts) * 60 + minute(ts) - 555)"
    agg = rd.q("kite_5m", f"""symbol, date::date as date, count(*) filter (where {mm} % 5 = 0 and {mm} >= 0 and {mm} < 375) as nb,
                              count(*) filter (where {mm} = 0) as h0, count(*) filter (where raw_close is null) as nraw,
                              sum(coalesce(kite_volume, 0)) as dv,
                              {", ".join(f"sum(coalesce(kite_volume, 0)) filter (where {mm} >= 0 and {mm} <= {5 * j}) as cv{j}" for j in range(12))}""",
               "list_contains(?, symbol)", [syms], "symbol, date::date")
    early = rd.q("kite_5m", f"symbol, date::date as date, {mm} // 5 as j, raw_open as o, raw_close as c",
                 f"list_contains(?, symbol) and {mm} % 5 = 0 and {mm} >= 0 and {mm} < 60", [syms])
    for x in (agg, early):
        x["date"] = pd.to_datetime(x["date"]).dt.date
    # rvol baseline (ocstudy._cumvol_table / _rvol_baseline): valid regular stock-days, one symbol per entity by day volume
    cv = agg[(agg.nb >= 70) & (agg.h0 == 1) & (agg.nraw == 0) & ~agg["date"].isin(specials)]
    cv = cv.merge(lk, left_on="symbol", right_on="kite_symbol").sort_values("dv", ascending=False).drop_duplicates(["entity", "date"])
    regular = [d for d in days if d not in specials and d.year >= 2014 and d <= max(agg["date"])]
    base = {j: cv.pivot_table(index="date", columns="entity", values=f"cv{j}", aggfunc="first").reindex(regular).rolling(20, min_periods=15).median().shift(1)
            for j in range(12)}
    # per day: one symbol per entity (most 5-minute bars that day), valid day, eligibility
    ag = agg.merge(lk, left_on="symbol", right_on="kite_symbol")
    ag = ag.sort_values("nb", ascending=False).drop_duplicates(["entity", "date"])
    ag = ag[(ag.nb >= 70) & (ag.h0 >= 1) & (ag.nraw == 0)]
    ew = early.merge(ag[["symbol", "date", "entity"]], on=["symbol", "date"])
    rank_by_day = {d: g.set_index("sid")["rank"].to_dict() for d, g in rp.groupby("day")}
    out = []
    for d, g in ew.groupby("date"):
        if d < first_day or d in specials:
            continue
        ranks = rank_by_day.get(d, {})
        ents = sorted(e for e in g["entity"].unique() if ranks.get(e, 10**9) <= 50 and (d, e) not in ca_block)
        if not ents:
            out.append({"date": d, "names": 0, **{f"b{j}": np.nan for j in range(12)}})
            continue
        ok = []
        for e in ents:
            good = True
            for j in range(12):
                bt = base[j]
                v = bt.at[d, e] if (d in bt.index and e in bt.columns) else np.nan
                if not (v == v and v > 0):
                    good = False
                    break
            if good:
                ok.append(e)
        gg = g[g["entity"].isin(ok)]
        n = len(ok)
        if n < ocstudy.MIN_BREADTH_NAMES:
            out.append({"date": d, "names": n, **{f"b{j}": np.nan for j in range(12)}})
            continue
        c = gg.pivot_table(index="entity", columns="j", values="c", aggfunc="first").reindex(columns=range(12)).ffill(axis=1)
        o0 = gg[gg["j"] == 0].set_index("entity")["o"].reindex(c.index)
        B = (c.to_numpy() > o0.to_numpy()[:, None]).mean(0)
        out.append({"date": d, "names": n, **{f"b{j}": float(B[j]) for j in range(12)}})
    return pd.DataFrame(out)


# ----------------------------------------------------------------------------------------------------------------------------- inputs
def build_inputs(rd, days, specials, first_day: dt.date, ca_block: set, log) -> dict:
    D = paths.data_dir()
    log("universe ranks (full cash history from 1994, so 'at least 126 sessions' counts a renamed company's earlier sessions, as gold does)")
    rd_cm = HoldoutReader(rd.t, "1994-01-01") if isinstance(rd, HoldoutReader) else SilverReader("1994-01-01", str(rd.end))
    u = universe_ranks(rd_cm, "1994-01-01", first_day - dt.timedelta(days=60))
    rp = prev_ranks(u, days)
    log("breadth")
    br = breadth(rd, days, specials, rp, first_day, ca_block)
    log("index minutes")
    im = rd.q("kite_index/minute", "index_name, date::date as date, (hour(ts) * 60 + minute(ts) - 555) as m, open, high, low, close",
              "list_contains(?, index_name)", [["NIFTY 50", "NIFTY BANK", "INDIA VIX"]])
    index = ocstudy.index_arrays(im)
    log("index days, participant OI, lots, option chains")
    silver_day = pd.read_parquet(next(p for p in (D / "silver/kite_index/day").iterdir() if p.suffix == ".parquet"))
    idx_day = pd.concat([silver_day, rd.q("kite_index/day", "*")], ignore_index=True) if isinstance(rd, HoldoutReader) else silver_day
    po_s = pd.read_parquet(D / "silver/flows/participant_oi.parquet")
    po = pd.concat([po_s, rd.q("flows", "*")], ignore_index=True) if isinstance(rd, HoldoutReader) else po_s
    fo = rd.q("fo_bhavcopy", "date::date as date, symbol, expiry, coalesce(lot_size, lot_est) as lot",
              "instrument = 'FUTIDX' and list_contains(?, symbol)", [["NIFTY", "BANKNIFTY"]])
    fo["date"] = pd.to_datetime(fo["date"]).dt.date
    lots = ocstudy.lots_from_df(fo, days, (first_day.year, 2026))
    ch = rd.q("fo_greeks", "date::date as date, symbol, expiry, strike, opt_type, fwd, iv, coalesce(volume, 0) as volume",
              "list_contains(?, symbol)", [["NIFTY", "BANKNIFTY"]])
    ch["date"] = pd.to_datetime(ch["date"]).dt.date
    ch["expiry"] = pd.to_datetime(ch["expiry"]).dt.date
    return {"days": days, "specials": specials, "index": index, "breadth": br.set_index("date"), "participant_oi": po, "index_day": idx_day,
            "lots": lots, "chains": ch, "ranks": u, "breadth_df": br}


# ----------------------------------------------------------------------------------------------------------------------------- consistency
def consistency(log=print) -> dict:
    """On silver only: build 2023-06..2023-12 through the holdout path and compare with what the dev/validation pipeline produced."""
    D = paths.data_dir()
    days, specials = calendar_full()
    days23 = [d for d in days if d.year <= 2023]
    rd = SilverReader("2022-06-01", "2023-12-31")
    first = dt.date(2023, 6, 1)
    f = pd.read_parquet(D / "gold/ca_flags/ca_flags.parquet")
    f["date"] = pd.to_datetime(f["date"]).dt.date
    ca = ocstudy.load_ca_block(days23)
    inp = build_inputs(rd, days23, specials, first, ca, log)
    res = {}
    # (a) universe ranks
    g = pd.read_parquet(D / "gold/universe/u_liq_in.parquet", columns=["date", "sid", "rank"])
    g["date"] = pd.to_datetime(g["date"]).dt.date
    g = g[(g["date"] >= first) & (g["rank"] <= 100)]
    u = inp["ranks"]
    u = u[(u["date"] >= first) & (u["rank"] <= 100)]
    j = g.merge(u[["date", "sid", "rank"]], on=["date", "sid"], how="outer", suffixes=("_gold", "_holdout"))
    res["universe_rows"] = int(len(g))
    res["universe_mismatch"] = int(((j["rank_gold"] != j["rank_holdout"]) | j.isna().any(axis=1)).sum())
    # (b) breadth
    ob = pd.read_parquet(D / "gold/studies/OC1_breadth.parquet")
    ob["date"] = pd.to_datetime(ob["date"]).dt.date
    ob = ob[ob["date"] >= dt.date(2023, 7, 1)].set_index("date").sort_index()
    hb = inp["breadth_df"].set_index("date").reindex(ob.index)
    cols = ["names"] + [f"b{j}" for j in range(12)]
    diff = (ob[cols].fillna(-1) - hb[cols].fillna(-1)).abs().max(axis=1)
    res["breadth_days"] = int(len(ob))
    res["breadth_mismatch_days"] = int((diff > 1e-12).sum())
    # (c) states
    tmp = Path.home() / "ananta_runs/sp1_check"
    tmp.mkdir(parents=True, exist_ok=True)
    scenario.build(src=inp, out_file=tmp / "states_consistency.parquet", from_date=first)
    sh = pd.read_parquet(tmp / "states_consistency.parquet")
    sg = pd.read_parquet(D / "gold/scenario/index_states.parquet")
    for x in (sh, sg):
        x["date"] = pd.to_datetime(x["date"]).dt.date
    sg = sg[sg["date"] >= first]
    m = sg.merge(sh, on=["date", "index"], suffixes=("_g", "_h"))
    bad = []
    for col in sg.columns:
        if col in ("date", "index"):
            continue
        a, b = m[col + "_g"], m[col + "_h"]
        if a.dtype.kind == "f":
            eq = ((a - b).abs() <= 1e-12) | (a.isna() & b.isna())
        else:
            eq = (a.astype(str) == b.astype(str))
        if not eq.all():
            bad.append(f"{col}:{int((~eq).sum())}")
    res["states_rows"] = int(len(sg))
    res["states_matched_rows"] = int(len(m))
    res["states_column_mismatches"] = bad
    # (d) outcomes (states from June so the July previous-session tails match)
    inp2 = {**inp, "states": sh}
    oh = sp1.outcomes(lambda s: None, src=inp2, out_file=tmp / "outcomes_consistency.parquet")
    og = pd.read_parquet(D / "gold/studies/SP1_outcomes.parquet")
    for x in (oh, og):
        x["date"] = pd.to_datetime(x["date"]).dt.date
    lo = dt.date(2023, 7, 1)
    k = ["date", "index", "point", "action"]
    mo = og[og["date"] >= lo].merge(oh[oh["date"] >= lo], on=k, suffixes=("_g", "_h"), how="outer", indicator=True)
    res["outcome_rows"] = int((og["date"] >= lo).sum())
    res["outcome_unmatched"] = int((mo["_merge"] != "both").sum())
    both = mo[mo["_merge"] == "both"]
    obad = []
    for col in ("entry", "exit_px", "gross_bps", "cost_bps", "opt_net_rs"):
        a, b = both[col + "_g"], both[col + "_h"]
        eq = ((a - b).abs() <= 1e-9) | (a.isna() & b.isna())
        if not eq.all():
            obad.append(f"{col}:{int((~eq).sum())}")
    res["outcome_column_mismatches"] = obad
    res["PASS"] = (res["universe_mismatch"] == 0 and res["breadth_mismatch_days"] == 0 and not bad and res["states_matched_rows"] == res["states_rows"]
                   and res["outcome_unmatched"] == 0 and not obad)
    (D / "manifests/sp1_holdout_consistency.json").write_text(json.dumps(res, indent=1, default=str))
    return res


if __name__ == "__main__":
    paths.ensure()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "consistency"
    if cmd == "consistency":
        print(json.dumps(consistency(lambda s: print(f"[{dt.datetime.now():%H:%M:%S}] {s}", flush=True)), indent=1, default=str))
    else:
        raise SystemExit(__doc__)
