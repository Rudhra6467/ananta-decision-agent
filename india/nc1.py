"""NC1: news-confirmed moves, do they continue or fade? (Madhav, 25 Nov 2026: "Ananta can predict the live happening, which was let's say
5 minutes or 10 minutes or 15 minutes later ... we don't have to hurry in finding the moves. The proved moves are good enough ... what are the
most effective news for the Indian market ... what are the main influencing keywords, sometimes for market gainers or market losers").

A study, never a trading rule. The design is frozen in registrations/nc1_v1.json before any outcome was computed. Research years only
(2010-2023; the 5-minute part 2015-2023); nothing here reads 2024+ or the sealed folders.

  python -m india.nc1 counts      events per news kind, timing and year (counts only; no price is read)
  python -m india.nc1 run         the registered rows into the ledger, the descriptive tables, registrations/nc1_results_v1.md and .json

Part A (overnight): news made public between the previous close (15:30 IST) and 09:00 IST; the move is confirmed at the open (the open at least
2% from the previous close, beyond the Nifty's own gap); does it continue to the close, against gaps of the same size on days with no news?
Part B (in session): news made public 09:20-15:00 IST; the move is confirmed about 15 minutes later (at least 1% beyond the Nifty, on 5-minute
bars); does it continue to the close, against no-news moves of the same size at the same time of day?
"""
from __future__ import annotations

import datetime as dt
import json
import math
import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from india import newskinds, paths

SPEC = Path(__file__).parent / "registrations" / "nc1_v1.json"
RESULTS_MD = Path(__file__).parent / "registrations" / "nc1_results_v1.md"
RESULTS_JSON = Path(__file__).parent / "registrations" / "nc1_results_v1.json"
FIRST_DAY, LAST_RESEARCH_DAY = pd.Timestamp("2010-01-01"), pd.Timestamp("2023-12-29")
SPLIT_A, SPLIT_B = 2018, 2019          # A: dev 2010-2017, validation 2018-2023; B (5-minute bars from 2015): dev 2015-2018, validation 2019-2023
GAP_MIN, MOVE15_MIN, CAP = 0.02, 0.01, 0.5
OPEN_M, CLOSE_M, PRE_M = 9 * 60 + 15, 15 * 60 + 30, 9 * 60     # 09:15, 15:30, 09:00 IST in minutes
B_FROM, B_TO = 9 * 60 + 20, 15 * 60                              # in-session news 09:20-15:00
BUCKETS = [(9 * 60 + 20, 10 * 60 + 30), (10 * 60 + 30, 12 * 60), (12 * 60, 13 * 60 + 30), (13 * 60 + 30, 15 * 60 + 1)]
GRID = list(range(1, 69, 3))           # baseline reference bars for part B: every 15 minutes from the 09:20-09:25 bar to 14:55-15:00
GROUPS = list(newskinds.KINDS) + ["all_news"]


TMP = Path.home() / "ananta_runs" / "prelive" / "duckdb_tmp"


def _con() -> duckdb.DuckDBPyConnection:
    """25 Nov 2026: the first run's joins spilled 76 GB into the repo's .tmp folder and the disk fell to 13 GB free; it was stopped before any
    outcome. Now: a fixed temp folder outside the repos with an 8 GB cap (a query that needs more fails instead of filling the disk), 2 GB of
    memory and 2 threads, so the Mac's running jobs keep their room."""
    TMP.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute(f"SET temp_directory='{TMP}'")
    con.execute("SET max_temp_directory_size='8GB'")
    con.execute("SET memory_limit='2GB'")
    con.execute("SET threads=2")
    return con


def sessions() -> np.ndarray:
    d = _con().execute(f"SELECT DISTINCT date FROM read_parquet('{paths.gold()}/bars/adj_daily.parquet') "
                       f"WHERE date >= DATE '2009-12-01' AND date <= DATE '{LAST_RESEARCH_DAY.date()}' ORDER BY date").fetchdf()["date"]
    return pd.to_datetime(d).values.astype("datetime64[D]")


def announcements() -> pd.DataFrame:
    """2010-2023 announcements with their public time (the exchange dissemination time where kept, else the announcement time: the two agree
    within a minute where both exist), their timing class and session, and their news kinds."""
    a = _con().execute(f"""SELECT symbol, category, left(coalesce(text, ''), 400) AS text, coalesce(exchdisstime, an_dt) AS pt
        FROM read_parquet('{paths.data_dir()}/silver/announce/announcements.parquet')
        WHERE coalesce(exchdisstime, an_dt) >= TIMESTAMP '{FIRST_DAY}' AND coalesce(exchdisstime, an_dt) < TIMESTAMP '{LAST_RESEARCH_DAY.date()} 23:59:59'
          AND symbol IS NOT NULL""").fetchdf()
    a["pt"] = pd.to_datetime(a["pt"])
    u = a[["category", "text"]].drop_duplicates()
    u["routine"] = [newskinds.routine(c, t) for c, t in zip(u["category"], u["text"])]
    u["kinds"] = [newskinds.kinds(c, t) for c, t in zip(u["category"], u["text"])]
    a = a.merge(u, on=["category", "text"], how="left")
    sess = sessions()
    day = a["pt"].values.astype("datetime64[D]")
    m = (a["pt"].dt.hour * 60 + a["pt"].dt.minute + a["pt"].dt.second / 60.0).values
    i = np.searchsorted(sess, day)
    i_ok = np.minimum(i, len(sess) - 1)
    on_session = (i < len(sess)) & (sess[i_ok] == day)
    nxt = np.minimum(i + on_session.astype(int), len(sess) - 1)      # the next session after this day (or this day's own, if it is not one)
    cls = np.full(len(a), "edge", dtype=object)
    session = np.full(len(a), np.datetime64("NaT", "D"), dtype="datetime64[D]")
    a_before = on_session & (m <= PRE_M)
    a_after = on_session & (m > CLOSE_M)
    a_off = ~on_session & (i < len(sess))
    b_in = on_session & (m >= B_FROM) & (m <= B_TO)
    cls[a_before | a_after | a_off] = "A"
    session[a_before] = sess[i_ok][a_before]
    session[a_after] = sess[nxt][a_after]
    session[a_off] = sess[i_ok][a_off]
    cls[b_in] = "B"
    session[b_in] = sess[i_ok][b_in]
    edge = on_session & ~(a_before | a_after | b_in)                 # 09:00-09:20 and 15:00-15:30: kept as the day's news, never an event
    session[edge] = sess[i_ok][edge]
    a["cls"], a["session"], a["minute"] = cls, pd.to_datetime(session), m
    return a[a["session"].notna() & (a["session"] <= LAST_RESEARCH_DAY)]


def counts() -> dict:
    a = announcements()
    news = a[~a["routine"]]
    out = {"announcements": int(len(a)), "routine": int(a["routine"].sum()), "news": int(len(news)), "by_class": news["cls"].value_counts().to_dict(),
           "kinds": {}}
    ex = news.explode("kinds")
    for k in newskinds.KINDS:
        s = ex[ex["kinds"] == k]
        out["kinds"][k] = {"announcements": int(len(s)), "A_stock_days": int(s[s["cls"] == "A"][["symbol", "session"]].drop_duplicates().shape[0]),
                           "B_stock_days": int(s[(s["cls"] == "B") & (s["session"].dt.year >= 2015)][["symbol", "session"]].drop_duplicates().shape[0]),
                           "by_year": s.groupby(s["session"].dt.year).size().to_dict()}
    out["no_kind_news"] = int((news["kinds"].str.len() == 0).sum())
    return out


# ------------------------------------------------------------------------------------------------------------------------------ prices
def _daily() -> pd.DataFrame:
    """Top-500 stock-days with the adjusted open and close, the previous close and the close 4 sessions on (5 sessions from the open)."""
    g = paths.gold()
    df = _con().execute(f"""
        WITH b AS (SELECT sid, date, o, c, lag(c) OVER w AS c_prev, lead(c, 4) OVER w AS c_5
                   FROM read_parquet('{g}/bars/adj_daily.parquet') WHERE date <= DATE '{LAST_RESEARCH_DAY.date()}'
                   WINDOW w AS (PARTITION BY sid ORDER BY date))
        SELECT u.date, u.sid, u.symbol, b.o, b.c, b.c_prev, b.c_5
        FROM read_parquet('{g}/universe/u_liq_in.parquet') u JOIN b ON b.sid = u.sid AND b.date = u.date
        WHERE u.top500 AND u.date >= DATE '{FIRST_DAY.date()}' AND u.date <= DATE '{LAST_RESEARCH_DAY.date()}'""").fetchdf()
    df["date"] = pd.to_datetime(df["date"])
    ca = _con().execute(f"SELECT DISTINCT sid, CAST(date AS DATE) AS date FROM read_parquet('{g}/ca_flags/ca_flags.parquet')").fetchdf()
    ca["date"], ca["ca"] = pd.to_datetime(ca["date"]), True
    df = df.merge(ca, on=["sid", "date"], how="left")
    df = df[df["ca"].isna()].drop(columns="ca")
    ix = _con().execute(f"SELECT date, open, close FROM read_parquet('{paths.data_dir()}/silver/kite_index/day/day.parquet') "
                        f"WHERE index_name = 'NIFTY 50' ORDER BY date").fetchdf()
    ix["date"] = pd.to_datetime(ix["date"])
    ix["n_prev"], ix["n_5"] = ix["close"].shift(1), ix["close"].shift(-4)
    ix = ix.rename(columns={"open": "n_o", "close": "n_c"})
    return df.merge(ix, on="date", how="inner")


def part_a(a: pd.DataFrame) -> pd.DataFrame:
    """One row per top-500 stock-day: the overnight news kinds, the abnormal gap, and the continuation to the close and over 5 sessions."""
    d = _daily()
    d["gap"] = (d["o"] / d["c_prev"] - 1) - (d["n_o"] / d["n_prev"] - 1)
    sgn = np.sign(d["gap"])
    d["cont"] = sgn * ((d["c"] / d["o"] - 1) - (d["n_c"] / d["n_o"] - 1))
    d["cont5"] = sgn * ((d["c_5"] / d["o"] - 1) - (d["n_5"] / d["n_o"] - 1))
    d["day_ret"] = (d["c"] / d["c_prev"] - 1) - (d["n_c"] / d["n_prev"] - 1)
    for col in ("gap", "cont", "cont5", "day_ret"):
        d.loc[d[col].abs() > CAP, col] = np.nan
    news = a[~a["routine"]]
    ov = news[news["cls"] == "A"]
    tags = ov.explode("kinds").dropna(subset=["kinds"]).groupby(["symbol", "session"])["kinds"].agg(lambda s: sorted(set(s))).rename("kinds")
    anynews = ov.groupby(["symbol", "session"]).size().rename("n_news")
    # the whole day's news (overnight before the open, and in session): for the no-news baseline and the movers' map
    day_tags = news.explode("kinds").dropna(subset=["kinds"]).groupby(["symbol", "session"])["kinds"].agg(lambda s: sorted(set(s))).rename("day_kinds")
    day_any = news.groupby(["symbol", "session"]).size().rename("day_news")
    t = pd.concat([tags, anynews, day_tags, day_any], axis=1).reset_index().rename(columns={"session": "date"})
    d = d.merge(t, on=["symbol", "date"], how="left")
    for col in ("n_news", "day_news"):
        d[col] = d[col].fillna(0).astype(int)
    for col in ("kinds", "day_kinds"):
        d[col] = d[col].apply(lambda x: x if isinstance(x, list) else [])
    return d


def part_b(a: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """News events in session (first news of the stock-day) with the 15-minute move and the continuation to the close; and the no-news
    baseline moves at the GRID bars of stock-days with no news at all. One pass over the bars, no self-joins (25 Nov 2026: the first form
    joined the bar table to itself and spilled 76 GB before it was stopped; nothing was computed or seen)."""
    con = _con()
    bars = f"read_parquet('{paths.data_dir()}/silver/kite_5m/year=*/part.parquet', union_by_name=true)"
    kx = f"CAST(round((hour(ts) * 60 + minute(ts) - {OPEN_M}) / 5.0) AS INTEGER)"
    span = f"date >= DATE '2015-01-01' AND date <= DATE '{LAST_RESEARCH_DAY.date()}'"
    # the Nifty: one row per session, its close at every bar and its last close
    ncols = ", ".join(f"max(close) FILTER (WHERE {kx} = {k}) AS n{k}" for k in range(75))
    nw = con.execute(f"""SELECT date, {ncols}, max({kx}) AS nkl, arg_max(close, ts) AS ncl
                         FROM read_parquet('{paths.data_dir()}/silver/kite_index/5minute/year=*/part.parquet', union_by_name=true)
                         WHERE index_name = 'NIFTY 50' AND {span} GROUP BY date HAVING max({kx}) >= 72""").fetchdf()
    nw["date"] = pd.to_datetime(nw["date"])
    nw = nw.set_index("date")
    # the news events: the first in-session news of each stock-day, 2015-2023
    insess = a[(a["cls"] == "B") & ~a["routine"] & (a["session"] >= pd.Timestamp("2015-01-01"))].sort_values("pt")
    first = insess.groupby(["symbol", "session"]).head(1).copy()
    first["k0"] = np.floor((first["minute"] - (OPEN_M + 5)) / 5).astype(int)
    first = first[first["k0"] >= 0]
    ev = first[["symbol", "session", "k0", "minute", "kinds"]].rename(columns={"session": "date"}).reset_index(drop=True)
    keys = ev[["symbol", "date"]].drop_duplicates().copy()
    keys["date"] = keys["date"].dt.date
    con.register("ev_keys", keys)
    long = con.execute(f"""SELECT b.symbol, b.date, {kx} AS k, b.kite_close AS p, b.ts FROM {bars} b
                           SEMI JOIN ev_keys e ON e.symbol = b.symbol AND e.date = b.date
                           WHERE {span} AND b.kite_close > 0""").fetchdf()
    long["date"] = pd.to_datetime(long["date"])
    last = long.sort_values("ts").groupby(["symbol", "date"]).agg(kl=("k", "max"), pl=("p", "last")).reset_index()
    last = last[last["kl"] >= 72]
    pk = long.drop_duplicates(["symbol", "date", "k"], keep="last").set_index(["symbol", "date", "k"])["p"]
    ev["p0"] = pk.reindex(list(zip(ev["symbol"], ev["date"], ev["k0"]))).values
    ev["p1"] = pk.reindex(list(zip(ev["symbol"], ev["date"], ev["k0"] + 3))).values
    ev = ev.merge(last[["symbol", "date", "pl"]], on=["symbol", "date"], how="inner")
    nd = nw.reindex(ev["date"])
    nmat = nd[[f"n{k}" for k in range(75)]].to_numpy(dtype=float)
    rows = np.arange(len(ev))
    k0v, k1v = ev["k0"].to_numpy(), ev["k0"].to_numpy() + 3
    ev["m0"] = np.where(k0v < 75, nmat[rows, np.clip(k0v, 0, 74)], np.nan)
    ev["m1"] = np.where(k1v < 75, nmat[rows, np.clip(k1v, 0, 74)], np.nan)
    ev["ml"] = nd["ncl"].to_numpy(dtype=float)
    ev = ev.dropna(subset=["p0", "p1", "pl", "m0", "m1", "ml"])
    del long, pk
    # the no-news baseline: every stock-day's closes at the GRID bars and 15 minutes after them, in one grouped pass
    need = sorted(set(GRID) | {g + 3 for g in GRID})
    scols = ", ".join(f"max(kite_close) FILTER (WHERE {kx} = {k}) AS c{k}" for k in need)
    wide = con.execute(f"""SELECT symbol, date, {scols}, max({kx}) AS kl, arg_max(kite_close, ts) AS cl FROM {bars}
                           WHERE {span} AND kite_close > 0 GROUP BY symbol, date HAVING max({kx}) >= 72""").fetchdf()
    wide["date"] = pd.to_datetime(wide["date"])
    newsdays = a[~a["routine"] & (a["session"] >= pd.Timestamp("2015-01-01"))][["symbol", "session"]].drop_duplicates()
    newsdays = newsdays.rename(columns={"session": "date"}).assign(news=True)
    wide = wide.merge(newsdays, on=["symbol", "date"], how="left")
    wide = wide[wide["news"].isna()].drop(columns="news")
    nwd = nw.reindex(wide["date"])
    parts, total = [], 0
    for k0 in GRID:
        p0, p1, pl = wide[f"c{k0}"].values, wide[f"c{k0 + 3}"].values, wide["cl"].values
        m0, m1, ml = nwd[f"n{k0}"].values, nwd[f"n{k0 + 3}"].values, nwd["ncl"].values
        ok = ~(np.isnan(p0) | np.isnan(p1) | np.isnan(m0) | np.isnan(m1) | np.isnan(ml))
        total += int(ok.sum())
        mv = (p1 / p0 - 1) - (m1 / m0 - 1)
        sel = ok & (np.abs(mv) >= MOVE15_MIN)
        parts.append(pd.DataFrame({"symbol": wide["symbol"].values[sel], "date": wide["date"].values[sel], "k0": k0, "p0": p0[sel], "p1": p1[sel],
                                   "pl": pl[sel], "m0": m0[sel], "m1": m1[sel], "ml": ml[sel]}))
    base = pd.concat(parts, ignore_index=True)
    base.attrs["grid_moves_total"] = int(total)
    for df in (ev, base):
        df["move15"] = (df["p1"] / df["p0"] - 1) - (df["m1"] / df["m0"] - 1)
        df["cont"] = np.sign(df["move15"]) * ((df["pl"] / df["p1"] - 1) - (df["ml"] / df["m1"] - 1))
        for col in ("move15", "cont"):
            df.loc[df[col].abs() > CAP, col] = np.nan
        df["bucket"] = np.digitize(OPEN_M + 5 + 5 * df["k0"], [b[1] for b in BUCKETS[:-1]])
    return ev, base


# ------------------------------------------------------------------------------------------------------------------------------ statistics
def _stat(q: pd.Series) -> tuple[float, float, int]:
    q = q.dropna()
    if len(q) < 3:
        return float("nan"), float("nan"), int(len(q))
    se = q.std(ddof=1) / math.sqrt(len(q))
    return float(q.mean()), (float(q.mean() / se) if se else float("nan")), int(len(q))


def _rows_a(d: pd.DataFrame) -> dict[str, pd.Series]:
    d = d[d["gap"].abs() >= GAP_MIN].dropna(subset=["cont"]).copy()
    d["q"], d["dir"] = d["date"].dt.to_period("Q"), np.sign(d["gap"])
    base = d[d["day_news"] == 0].groupby(["q", "dir"])["cont"].mean().rename("base")     # gaps on days with no news at all
    d = d.join(base, on=["q", "dir"])
    d["excess"] = d["cont"] - d["base"]
    out = {}
    for gname in GROUPS:
        sel = d[d["n_news"] > 0] if gname == "all_news" else d[d["kinds"].apply(lambda k: gname in k)]
        out[f"A|{gname}|cont"] = sel.groupby("q")["cont"].mean()
        out[f"A|{gname}|edge"] = sel.groupby("q")["excess"].mean()
    return out


def _rows_b(ev: pd.DataFrame, base: pd.DataFrame) -> dict[str, pd.Series]:
    ev = ev[ev["move15"].abs() >= MOVE15_MIN].dropna(subset=["cont"]).copy()
    for df in (ev, base):
        df["q"], df["dir"] = df["date"].dt.to_period("Q"), np.sign(df["move15"])
    b = base.dropna(subset=["cont"]).groupby(["q", "bucket", "dir"])["cont"].mean().rename("base")
    ev = ev.join(b, on=["q", "bucket", "dir"])
    ev["excess"] = ev["cont"] - ev["base"]
    out = {}
    for gname in GROUPS:
        sel = ev if gname == "all_news" else ev[ev["kinds"].apply(lambda k: gname in k)]
        out[f"B|{gname}|cont"] = sel.groupby("q")["cont"].mean()
        out[f"B|{gname}|edge"] = sel.groupby("q")["excess"].mean()
    return out


def variants() -> list[str]:
    return [f"{p}|{g}|{m}" for p in ("A", "B") for g in GROUPS for m in ("cont", "edge")]


def main(argv: list[str]) -> None:
    cmd = argv[1] if len(argv) > 1 else "counts"
    if cmd == "counts":
        print(json.dumps(counts(), indent=1, default=str))
    elif cmd == "run":
        from india import nc1_run
        nc1_run.run()
    else:
        print(__doc__)


if __name__ == "__main__":
    main(sys.argv)
