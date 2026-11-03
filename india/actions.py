"""Corporate actions, two records, and the adjustment factors that come out of them.

Record B: NSE's corporate-actions API, one call per calendar year for every symbol (structured: symbol, series, ex-date,
record date, face value, subject text such as "Bonus 1:1" or "Face Value Split (Sub-Division) - From Rs 10/- Per Share To
Rs 2/- Per Share"). Reachable from 2000 on; thin before 2005. Saved as bronze/corporate_actions/ca_<year>.json.
Record A: the price itself. NSE does not adjust the previous-close column on an ex-date (checked on INFY 2015-06-15 and
RELIANCE 2017-09-07), so the gap prior close / ex-date open is the evidence; a gap over 20% is a candidate, snapped to the
nearest clean ratio (2, 3, 5, 10, 3:2, 5:4, 1:10 consolidation...) when within 4%.
The factors view joins both: AGREE (both say the same ratio), B_ONLY (an announced action with no visible gap, e.g. a
tiny bonus), A_ONLY (a gap with no announcement, to be looked at), and never a silent choice.

  python -m india.actions fetch 2000 2026
  python -m india.actions build
"""
from __future__ import annotations

import datetime as dt
import json
import re
import sys
from fractions import Fraction
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from india import nse, paths

API = "https://www.nseindia.com/api/corporates-corporateActions?index=equities&from_date=01-01-{y}&to_date=31-12-{y}"
CLEAN = sorted({float(Fraction(a + b, b)) for a in range(1, 11) for b in range(1, 11)} | {2, 2.5, 3, 4, 5, 10, 20, 25, 50, 100} |
               {1 / x for x in (2, 2.5, 3, 4, 5, 10, 20)})


def fetch(years: range | list[int]) -> list[dict]:
    f = nse.Fetcher(rate_s=1.5)
    f.s.headers.update({"Accept": "*/*"})
    out = []
    for y in years:
        st, body, secs = f.get(API.format(y=y))
        row = {"year": y, "status": st, "bytes": len(body), "seconds": secs, "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
        if st == 200 and body[:1] == b"[":
            p = paths.bronze("corporate_actions") / f"ca_{y}.json"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(body)
            row["rows"] = len(json.loads(body))
        with (paths.manifest_dir() / "corporate_actions.jsonl").open("a") as fh:
            fh.write(json.dumps(row) + "\n")
        print(row, flush=True)
        out.append(row)
    return out


_NUM = r"(\d+(?:\.\d+)?)"


def parse_subject(s: str) -> dict:
    """kind, ratio (price factor: old price / new price), amount (dividend per share) from NSE's subject text."""
    t = " ".join(s.lower().split())
    out: dict = {"kind": "OTHER", "ratio": None, "amount": None}
    # 3 Nov 2026 (big-falls review): "Bonus - 1:1" (a dash) and the abbreviated "Bon-2:1" were missed, so "Bonus - 1:1 And Face Value Split From
    # Rs. 10 To Rs. 2" was read as a split of 5 instead of 10, and "Fv Spl-Rs10tors5/Bon-2:1" as OTHER
    # "Bonus Issue 1 : 1", "Bonus Shares In The Ratio Of 1:1" too; bonus debentures (or preference shares) change no share count
    # bonus debentures, preference shares and NCRPS (non-convertible redeemable preference shares) are not equity: no factor
    m = None if re.search(r"\bbon(?:us)?\b\s*-?\s*(?:deb|pref|n\.?c\.?r\.?p|ncd|rps|red)", t) else re.search(r"\bbon(?:us)?\b[^0-9:/|]{0,28}?(\d+)\s*:\s*(\d+)", t)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        out.update(kind="BONUS", ratio=(a + b) / b if b else None)
    m = re.search(r"(?:spli?t|\bspl\b|sub-?division)[^0-9]*?(?:rs\.?|re\.?)?\s*" + _NUM + r"[^0-9]*?to\s*(?:face value)?\s*(?:rs\.?|re\.?)?\s*" + _NUM, t)
    if m:
        a, b = float(m.group(1)), float(m.group(2))
        if out["kind"] == "BONUS" and out["ratio"] and b:
            out.update(kind="BONUS+SPLIT", ratio=out["ratio"] * a / b)   # both on one ex-date: the gap is the product
        elif out["kind"] == "OTHER":
            out.update(kind="SPLIT", ratio=a / b if b else None)
    m = re.search(r"consolidat.*?(?:from|frm)\s*(?:rs\.?|re\.?)?\s*" + _NUM + r".*?to\s*(?:rs\.?|re\.?)?\s*" + _NUM, t)
    if m and out["kind"] == "OTHER":
        a, b = float(m.group(1)), float(m.group(2))
        out.update(kind="CONSOLIDATION", ratio=a / b if b else None)
    if out["kind"] == "OTHER" and re.search(r"\bright", t):
        m = re.search(r"right[s]?\s*(?:issue)?\s*(\d+)\s*:\s*(\d+)", t)
        out.update(kind="RIGHTS", ratio=None, note=f"{m.group(1)}:{m.group(2)}" if m else None)
    td = re.sub(r"sub-?division", "", t)   # "sub-division" is a split, not a dividend
    m = re.search(r"\bdiv[^0-9]{0,40}?(?:rs\.?|re\.?|₹)\s*" + _NUM, td)
    if m:
        out["amount"] = float(m.group(1))
        if out["kind"] == "OTHER":
            out["kind"] = "DIVIDEND"
    elif out["kind"] == "OTHER" and re.search(r"\bdiv", td):
        out["kind"] = "DIVIDEND"
    if out["kind"] == "OTHER" and ("buyback" in t or "buy back" in t):
        out["kind"] = "BUYBACK"
    if out["kind"] == "OTHER" and ("demerger" in t or "scheme of arrangement" in t or "amalgamation" in t):
        out["kind"] = "DEMERGER"
    return out


def build_b() -> dict:
    rows = []
    for p in sorted(paths.bronze("corporate_actions").glob("ca_*.json")):
        for r in json.loads(p.read_text()):
            ex = r.get("exDate", "")
            try:
                exd = dt.datetime.strptime(ex, "%d-%b-%Y").date()
            except ValueError:
                continue
            k = parse_subject(r.get("subject", ""))
            rows.append({"symbol": r.get("symbol", "").strip(), "series": r.get("series", "").strip(), "ex_date": exd, "record_date": r.get("recDate", ""),
                         "face_value": r.get("faceVal", ""), "isin": r.get("isin", ""), "subject": r.get("subject", "").strip(), **k, "source": p.name})
    df = pd.DataFrame(rows).drop_duplicates(subset=["symbol", "series", "ex_date", "subject"])
    out = paths.data_dir() / "silver" / "corporate_actions" / "record_b.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pandas(df, preserve_index=False), out)
    return {"rows": len(df), "kinds": df["kind"].value_counts().to_dict(), "path": str(out)}


def snap(x: float) -> float | None:
    best = min(CLEAN, key=lambda c: abs(c / x - 1))
    return best if abs(best / x - 1) <= 0.04 else None


def build_a(min_gap: float = 0.08) -> dict:
    """Candidates from the price itself on silver/ (dev and validation years): the ex-date gap (prior close / ex-date open) must
    snap to a clean ratio, and so must the persistent gap (median of the five closes before / median of the five closes from the
    ex-date on), to the same value. A one-day spike in an illiquid name fails the second test; a real split or bonus passes both."""
    import duckdb

    con = duckdb.connect()
    glob = str(paths.data_dir() / "silver" / "cm_bhavcopy" / "year=*" / "part.parquet")
    df = con.execute(f"""
        with eq as (select date, symbol, open, close, volume from read_parquet('{glob}') where series = 'EQ' and open > 0 and close > 0),
        w as (select *, lag(close) over (partition by symbol order by date) as prior_close,
                        lag(date) over (partition by symbol order by date) as prior_date,
                        median(close) over (partition by symbol order by date rows between 5 preceding and 1 preceding) as med_before,
                        median(close) over (partition by symbol order by date rows between current row and 4 following) as med_after
              from eq)
        select symbol, date as ex_date, prior_date, prior_close, open as ex_open, prior_close / open as gap, med_before / med_after as gap5, volume
        from w where prior_close is not null and abs(prior_close / open - 1) > {min_gap} and prior_date >= date - interval 10 day
        order by symbol, ex_date""").df()
    df["ratio"] = df["gap"].map(snap)
    df["ratio5"] = df["gap5"].map(lambda x: snap(x) if x and x > 0 else None)
    out = paths.data_dir() / "silver" / "corporate_actions" / "record_a.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pandas(df, preserve_index=False), out)
    return {"candidates": len(df), "snapped": int(df["ratio"].notna().sum()), "path": str(out)}


def build_factors() -> dict:
    """One row per (symbol, ex_date). Record B gives the ratio (every bonus, split and consolidation on that ex-date multiplied
    together) and Record A confirms it when the one-day gap or the five-day gap is within 10% of it. Without B, a gap counts only
    when both gaps snap to the same clean ratio of at least 1.3 or at most 0.77, so a penny stock's ordinary 10% day never
    becomes a split. Each B row takes the nearest A candidate within a day, the same day first."""
    import duckdb

    con = duckdb.connect()
    sd = paths.data_dir() / "silver" / "corporate_actions"
    df = con.execute(f"""
        with b0 as (select distinct symbol, ex_date, kind, ratio, subject from read_parquet('{sd / "record_b.parquet"}')
                    where kind in ('BONUS','SPLIT','CONSOLIDATION','BONUS+SPLIT') and ratio is not null and ratio > 0),
             b as (select symbol, ex_date, string_agg(kind, '+' order by kind) as kind, exp(sum(ln(ratio))) as ratio_b,
                          string_agg(subject, ' | ' order by kind) as subject from b0 group by 1, 2),
             a as (select symbol, ex_date, gap, gap5, ratio as ratio_a, ratio5 from read_parquet('{sd / "record_a.parquet"}')),
             ab as (select b.symbol, b.ex_date, b.kind, b.subject, b.ratio_b, a.ex_date as a_date, a.gap, a.gap5, a.ratio_a, a.ratio5,
                           row_number() over (partition by b.symbol, b.ex_date order by abs(datediff('day', a.ex_date, b.ex_date)), a.ex_date) as rn
                    from b left join a on a.symbol = b.symbol and abs(datediff('day', a.ex_date, b.ex_date)) <= 1),
             matched as (select * from ab where rn = 1),
             a_only as (select a.* from a left join b on a.symbol = b.symbol and abs(datediff('day', a.ex_date, b.ex_date)) <= 1 where b.symbol is null)
        select symbol, ex_date, kind, subject, gap, gap5, ratio_a, ratio_b,
               case when gap is not null and (abs(gap / ratio_b - 1) < 0.10 or abs(gap5 / ratio_b - 1) < 0.10) then 'AGREE'
                    when gap is null then 'B_ONLY' else 'DISAGREE' end as status, ratio_b as factor
        from matched
        union all
        select symbol, ex_date, null, null, gap, gap5, ratio_a, null, 'A_ONLY', ratio_a
        from a_only where ratio_a is not null and ratio_a = ratio5 and (ratio_a >= 1.3 or ratio_a <= 0.77)
        order by 1, 2""").df()
    df = confirm(df, con)
    df = manual(df, con)
    df = carry_entity(df, con)
    out = sd / "factors.parquet"
    pq.write_table(pa.Table.from_pandas(df, preserve_index=False), out)
    return {"rows": len(df), "status": df["status"].value_counts().to_dict(), "applied": df.groupby("status")["apply"].sum().astype(int).to_dict(),
            "ambiguous_inside_history": int((df["inside"] & ~df["apply"]).sum()), "path": str(out)}


def carry_entity(df: pd.DataFrame, con) -> pd.DataFrame:
    """3 Nov 2026 (big-falls review): factors are keyed by symbol, but the lab joins a company's symbols into one series (same entity through
    the ISIN). A split after a rename adjusted only the new symbol's rows, so the series showed a fake fall on the rename day (COFORGE
    2020-08-20 after its 2025 split, ANGELONE 2021, SHRIRAMFIN 2022, NAVA 2022 ...). Each applied factor is carried to the same company's other
    symbols that traded before its ex-date (status <status>+ENTITY, inside False: it changes levels on the old symbol only)."""
    glob = str(paths.data_dir() / "silver" / "cm_bhavcopy" / "year=*" / "part.parquet")
    names = str(paths.data_dir() / "silver" / "security_master" / "names.parquet")
    se = con.execute(f"""select c.symbol, e.entity, min(c.date) as first, max(c.date) as last from read_parquet('{glob}', union_by_name=true) c
                         join (select distinct isin, entity from read_parquet('{names}')) e on e.isin = c.isin where c.series = 'EQ' group by 1, 2""").df()
    se["first"], se["last"] = pd.to_datetime(se["first"]), pd.to_datetime(se["last"])
    f = df[df["apply"].astype(bool) & df["factor"].notna() & (df["factor"] > 0) & (df["factor"] != 1)].copy()
    f["ex_date"] = pd.to_datetime(f["ex_date"])
    m = f.merge(se[["symbol", "entity"]], on="symbol").merge(se.rename(columns={"symbol": "symbol_o"}), on="entity")
    # only a symbol that had stopped trading before the ex-date (a rename), never one trading alongside (a second line of the same company)
    m = m[(m["symbol_o"] != m["symbol"]) & (m["last"] < m["ex_date"])]
    have = df.assign(ex_date=pd.to_datetime(df["ex_date"]))[["symbol", "ex_date"]]
    rows = []
    for r in m.drop_duplicates(["symbol_o", "ex_date", "symbol"]).itertuples():
        h = have[have["symbol"] == r.symbol_o]
        if ((h["ex_date"] - r.ex_date).abs() <= pd.Timedelta(days=3)).any():
            continue
        rows.append({"symbol": r.symbol_o, "ex_date": r.ex_date, "kind": r.kind, "subject": r.subject, "status": f"{r.status}+ENTITY", "factor": r.factor,
                     "inside": False, "apply": True, "basis": f"carried from {r.symbol} (the same company's earlier symbol)"})
    if not rows:
        return df
    out = pd.concat([df, pd.DataFrame(rows)], ignore_index=True).sort_values(["symbol", "ex_date"]).reset_index(drop=True)
    out["ex_date"] = pd.to_datetime(out["ex_date"]).astype("datetime64[us]")
    return out


MANUAL = Path(__file__).parent / "registrations" / "ca_manual_v1.csv"


def manual(df: pd.DataFrame, con) -> pd.DataFrame:
    """The big-falls review of 3 Nov 2026 (Madhav's yes; registrations/ca_manual_v1.csv, each row with its evidence). A row replaces any automatic
    row of the same stock within 3 days of its ex-date:
      apply  the stated factor, applied (status MANUAL)
      price  a demerger: factor = last close before the ex-date / first close on or after it, any of the EQ, BE and BZ series (a demerged stock
             often trades in BE for a while), applied (status MANUAL_DEMERGER); it takes the ex-day's own move out with the demerger
      flag   not applied, marked inside the history (status MANUAL_FLAG), so gold/ca_flags lists it and the lab skips any window across it"""
    if not MANUAL.exists():
        return df
    m = pd.read_csv(MANUAL)
    m["ex_date"] = pd.to_datetime(m["ex_date"])
    glob = str(paths.data_dir() / "silver" / "cm_bhavcopy" / "year=*" / "part.parquet")
    rows = []
    for r in m.itertuples():
        before = con.execute(f"select close from read_parquet('{glob}', union_by_name=true) where symbol = ? and series in ('EQ','BE','BZ') and close > 0 "
                             "and date < ? and date >= ? order by date desc limit 1", [r.symbol, r.ex_date, r.ex_date - pd.Timedelta(days=20)]).fetchone()
        after = con.execute(f"select close from read_parquet('{glob}', union_by_name=true) where symbol = ? and series in ('EQ','BE','BZ') and close > 0 "
                            "and date >= ? and date <= ? order by date limit 1", [r.symbol, r.ex_date, r.ex_date + pd.Timedelta(days=20)]).fetchone()
        cb, ca = (before[0] if before else None), (after[0] if after else None)
        if r.decision == "apply":
            f, st, ap = float(r.factor), "MANUAL", True
        elif r.decision == "price":
            f = cb / ca if cb and ca else None
            st, ap = "MANUAL_DEMERGER", f is not None and f > 1
        else:
            f, st, ap = None, "MANUAL_FLAG", False
        rows.append({"symbol": r.symbol, "ex_date": r.ex_date, "kind": r.kind, "subject": r.evidence, "status": st, "factor": f, "close_before": cb,
                     "close_after": ca, "inside": True, "raw_gap_cc": (cb / ca) if cb and ca else None, "apply": bool(ap),
                     "basis": f"manual review 3 Nov 2026 ({r.decision}): {r.evidence}"})
    mm = pd.DataFrame(rows)
    df = df.copy()
    df["ex_date"] = pd.to_datetime(df["ex_date"])
    drop = pd.Series(False, index=df.index)
    for r in mm.itertuples():
        drop |= (df["symbol"] == r.symbol) & ((df["ex_date"] - r.ex_date).abs() <= pd.Timedelta(days=3))
    out = pd.concat([df[~drop], mm], ignore_index=True).sort_values(["symbol", "ex_date"]).reset_index(drop=True)
    out["ex_date"] = pd.to_datetime(out["ex_date"]).astype("datetime64[us]")    # the column's type as before the manual rows (timestamp[us])
    return out


def confirm(df: pd.DataFrame, con) -> pd.DataFrame:
    """Which factors are applied (18 Oct 2026 rule, from the integrity check: 63 of 514 A_ONLY factors made the adjusted series jump more than 30%).
    For each event, the raw close on the last session before the ex-date and on the first session on or after it (each within 15 days):
      inside = the stock traded on both sides; raw_gap = close before / close after.
      AGREE: applied. Outside the trading history: applied (it moves every row of that stock by the same amount, so no return changes).
      A_ONLY, B_ONLY, DISAGREE inside the history: applied only if raw_gap is within 15% of the factor; otherwise NOT applied and marked
      ambiguous: the lab skips any signal window that crosses an ambiguous event and the paper engine rejects a candidate with one in its lookback."""
    glob = str(paths.data_dir() / "silver" / "cm_bhavcopy" / "year=*" / "part.parquet")
    con.register("ev", df[["symbol", "ex_date"]].drop_duplicates())
    side = con.execute(f"""
        with eq as (select symbol, date, close from read_parquet('{glob}') where series = 'EQ' and close > 0)
        select ev.symbol, ev.ex_date,
               (select close from eq where eq.symbol = ev.symbol and eq.date < ev.ex_date and eq.date >= ev.ex_date - interval 15 day order by date desc limit 1) as close_before,
               (select close from eq where eq.symbol = ev.symbol and eq.date >= ev.ex_date and eq.date <= ev.ex_date + interval 15 day order by date limit 1) as close_after
        from ev""").df()
    df = df.merge(side, on=["symbol", "ex_date"], how="left")
    df["inside"] = df["close_before"].notna() & df["close_after"].notna()
    df["raw_gap_cc"] = df["close_before"] / df["close_after"]
    ok = (df["raw_gap_cc"] / df["factor"] - 1).abs() < 0.15
    df["apply"] = df["factor"].notna() & (df["factor"] > 0) & ((df["status"] == "AGREE") | ~df["inside"] | ok)
    df["basis"] = "not applied: price does not confirm (ambiguous)"
    df.loc[df["apply"] & (df["status"] == "AGREE"), "basis"] = "both records agree"
    df.loc[df["apply"] & ~df["inside"], "basis"] = "outside trading history (level only)"
    df.loc[df["apply"] & df["inside"] & (df["status"] != "AGREE"), "basis"] = "one record, price confirms within 15%"
    return df


if __name__ == "__main__":
    paths.ensure()
    what = sys.argv[1]
    if what == "fetch":
        fetch(range(int(sys.argv[2]), int(sys.argv[3]) + 1))
    elif what == "build":
        print(build_b(), flush=True)
        print(build_a(), flush=True)
        print(build_factors(), flush=True)
