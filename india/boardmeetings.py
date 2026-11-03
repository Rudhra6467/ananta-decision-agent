"""NSE's board-meetings calendar (data audit step 3, 3 Nov 2026): the meetings companies have told the exchange about, with the time they told it.

  python -m india.boardmeetings ahead            the next 60 days as known tonight -> bronze/board_meetings/ahead/<yyyymmdd>.json.gz
  python -m india.boardmeetings history [year]   one request per month from `year` (default 2010) to last month, resumable
                                                 -> bronze/board_meetings/history/<yyyymm>.json.gz; manifest manifests/board_meetings.jsonl
  python -m india.boardmeetings build            silver/board_meetings/meetings.parquet (meetings dated 2024+ under sealed/silver)

Point in time: a study may use a meeting from its intimation time (bm_timestamp, `intimated_at`), never from the meeting date. The nightly
snapshots also keep when Ananta first saw each meeting. Read-only public data; nothing trades from it.
"""
from __future__ import annotations

import datetime as dt
import gzip
import json
import sys

import pandas as pd

from india import nse, paths

URL = "https://www.nseindia.com/api/corporate-board-meetings?index=equities&from_date={a:%d-%m-%Y}&to_date={b:%d-%m-%Y}"
AHEAD_DAYS = 60
RESULTS_WORDS = ("result", "financial")


def _man():
    return paths.manifest_dir() / "board_meetings.jsonl"


def _get(f: "nse.Fetcher", a: dt.date, b: dt.date) -> tuple[int, list | None]:
    st, body, _ = f.get(URL.format(a=a, b=b))
    if st != 200:
        return st, None
    try:
        data = json.loads(body)
    except ValueError:
        return 520, None   # an HTML page instead of JSON: retried next time
    return 200, data if isinstance(data, list) else []


def _write(path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wb") as fh:
        fh.write(json.dumps(data).encode())


def _log(row: dict) -> None:
    with _man().open("a") as fh:
        fh.write(json.dumps(row) + "\n")


def ahead(today: dt.date | None = None) -> dict:
    """Tonight's view of the meetings from 3 days back to 60 days ahead."""
    paths.ensure()
    today = today or dt.date.today()
    st, data = _get(nse.Fetcher(rate_s=1.0), today - dt.timedelta(days=3), today + dt.timedelta(days=AHEAD_DAYS))
    row = {"kind": "ahead", "date": today.isoformat(), "status": st, "rows": len(data) if data is not None else None,
           "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
    if data is not None:
        _write(paths.bronze("board_meetings") / "ahead" / f"{today:%Y%m%d}.json.gz", {"fetched_at": row["fetched_at"], "rows": data})
    _log(row)
    return row


def history(from_year: int = 2010) -> dict:
    """Month by month to the end of last month; a month already fetched is skipped (the current month comes from `ahead`)."""
    paths.ensure()
    done = set()
    if _man().exists():
        for line in _man().read_text().splitlines():
            r = json.loads(line)
            if r.get("kind") == "history" and r.get("status") == 200:
                done.add(r["month"])
    f = nse.Fetcher(rate_s=1.5)
    first_this_month = dt.date.today().replace(day=1)
    m, n, rows = dt.date(from_year, 1, 1), 0, 0
    while m < first_this_month:
        nxt = (m + dt.timedelta(days=32)).replace(day=1)
        key = f"{m:%Y-%m}"
        if key not in done:
            st, data = _get(f, m, nxt - dt.timedelta(days=1))
            if data is not None:
                _write(paths.bronze("board_meetings") / "history" / f"{m:%Y%m}.json.gz", data)
                rows += len(data)
            _log({"kind": "history", "month": key, "status": st, "rows": len(data) if data is not None else None,
                  "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")})
            n += 1
        m = nxt
    return {"months_fetched": n, "rows": rows}


def _frame(data: list, first_seen=None) -> pd.DataFrame:
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    keep = {"bm_symbol": "symbol", "sm_isin": "isin", "sm_name": "company", "bm_date": "meeting_date", "bm_purpose": "purpose", "bm_desc": "text",
            "bm_timestamp": "intimated_at"}
    df = df[[c for c in keep if c in df]].rename(columns=keep)
    df["meeting_date"] = pd.to_datetime(df["meeting_date"], format="%d-%b-%Y", errors="coerce")
    df["intimated_at"] = pd.to_datetime(df["intimated_at"], format="%d-%b-%Y %H:%M:%S", errors="coerce")
    df["text"] = df["text"].astype(str).str[:400]
    df["first_seen"] = pd.Timestamp(first_seen).tz_convert(None) if first_seen else pd.NaT
    return df


def is_results(purpose) -> bool:
    p = str(purpose or "").lower()
    return any(w in p for w in RESULTS_WORDS)


def table() -> pd.DataFrame:
    """Every meeting seen in the history months and the nightly snapshots, one row per company, meeting day and purpose, with the earliest
    intimation time and the night Ananta first saw it (NaT for history-only rows)."""
    frames = []
    for p in sorted(paths.bronze("board_meetings").glob("history/*.json.gz")):
        frames.append(_frame(json.loads(gzip.open(p).read())))
    for p in sorted(paths.bronze("board_meetings").glob("ahead/*.json.gz")):
        x = json.loads(gzip.open(p).read())
        frames.append(_frame(x.get("rows") or [], x.get("fetched_at")))
    frames = [f for f in frames if not f.empty]
    if not frames:
        return pd.DataFrame(columns=["symbol", "isin", "company", "meeting_date", "purpose", "text", "intimated_at", "first_seen", "is_results"])
    df = pd.concat(frames, ignore_index=True)
    df = df[df["meeting_date"].notna()]
    df["is_results"] = df["purpose"].map(is_results)
    key = ["symbol", "meeting_date", "purpose"]
    first = df.groupby(key, dropna=False).agg(intimated_at=("intimated_at", "min"), first_seen=("first_seen", "min")).reset_index()
    rest = df.sort_values("intimated_at").drop_duplicates(key, keep="first").drop(columns=["intimated_at", "first_seen"])
    return rest.merge(first, on=key, how="left").sort_values(["meeting_date", "symbol"]).reset_index(drop=True)


def build() -> dict:
    import pyarrow as pa
    import pyarrow.parquet as pq
    df = table()
    hold = pd.Timestamp(paths.HOLDOUT_START)
    out = {}
    for part, sub in (("silver", df[df["meeting_date"] < hold]), ("sealed/silver", df[df["meeting_date"] >= hold])):
        p = paths.data_dir() / part / "board_meetings" / "meetings.parquet"
        p.parent.mkdir(parents=True, exist_ok=True)
        pq.write_table(pa.Table.from_pandas(sub.reset_index(drop=True), preserve_index=False), p)
        out[part] = int(len(sub))
    out["results_meetings"] = int(df["is_results"].sum()) if len(df) else 0
    return out


def results_ahead(days: list[dt.date]) -> tuple[dict, str | None]:
    """({iso day: [symbols]}, snapshot day) of results meetings on the given days, from the newest nightly snapshot (live use: the desk)."""
    snaps = sorted(paths.bronze("board_meetings").glob("ahead/*.json.gz"))
    if not snaps:
        return {}, None
    x = json.loads(gzip.open(snaps[-1]).read())
    df = _frame(x.get("rows") or [])
    if df.empty:
        return {d.isoformat(): [] for d in days}, snaps[-1].name[:8]
    df = df[df["purpose"].map(is_results)]
    return {d.isoformat(): sorted(set(df.loc[df["meeting_date"] == pd.Timestamp(d), "symbol"].dropna())) for d in days}, snaps[-1].name[:8]


if __name__ == "__main__":
    paths.ensure()
    w = sys.argv[1] if len(sys.argv) > 1 else "build"
    if w == "ahead":
        print(ahead())
    elif w == "history":
        print(history(int(sys.argv[2]) if len(sys.argv) > 2 else 2010))
    else:
        print(json.dumps(build(), default=str))
