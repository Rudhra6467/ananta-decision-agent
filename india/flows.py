"""Who holds what in index and stock derivatives: NSE participant-wise open interest (Client, DII, FII, Pro), daily from 2012 (D17a).

  python -m india.flows fetch [from_year]     bronze/flows/participant_oi/<year>/fao_participant_oi_<ddmmyyyy>.csv  (polite, resumable, manifest flows_participant_oi.jsonl)
  python -m india.flows build                 silver/flows/participant_oi.parquet (2024+ under sealed/silver)

The file for day d is published after the close of d: a study may use it from the next session. This is derivatives positioning, not cash-market FII/DII
buying and selling (D17 proper still has no free history found); the two are labelled apart.
"""
from __future__ import annotations

import datetime as dt
import io
import json
import re
import sys

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from india import nse, paths

URL = "https://nsearchives.nseindia.com/content/nsccl/fao_participant_oi_{d:%d%m%Y}.csv"


def _days(from_year: int) -> list[dt.date]:
    cal = pd.read_parquet(paths.data_dir() / "silver/calendar/calendar.parquet")
    cal = cal[cal["is_trading_day"]]
    d = pd.to_datetime(cal["date"]).dt.date
    days = sorted(x for x in d if x.year >= from_year)
    # the calendar silver ends where the cash files end; add the weekdays since, in case the calendar lags
    last = days[-1] if days else dt.date(from_year, 1, 1)
    x = last + dt.timedelta(days=1)
    while x < dt.date.today():
        if x.weekday() < 5:
            days.append(x)
        x += dt.timedelta(days=1)
    return days


def fetch(from_year: int = 2012) -> dict:
    paths.ensure()
    man = paths.manifest_dir() / "flows_participant_oi.jsonl"
    done = set()
    if man.exists():
        for line in man.read_text().splitlines():
            r = json.loads(line)
            if r.get("status") in (200, 404):
                done.add(r["date"])
    f = nse.Fetcher(rate_s=1.0)
    n = ok = 0
    for d in _days(from_year):
        if d.isoformat() in done:
            continue
        st, body, secs = f.get(URL.format(d=d))
        row = {"date": d.isoformat(), "status": st, "bytes": len(body), "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
        if st == 200 and b"Participant" in body[:200]:
            out = paths.bronze("flows") / "participant_oi" / str(d.year) / f"fao_participant_oi_{d:%d%m%Y}.csv"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(body)
            row["path"] = str(out.relative_to(paths.data_dir()))
            ok += 1
        elif st == 200:
            row["status"] = 204  # a page that is not the file (holiday placeholder)
        with man.open("a") as fh:
            fh.write(json.dumps(row) + "\n")
        n += 1
        if n % 250 == 0:
            print(f"participant_oi {d} fetched={n} files={ok}", flush=True)
    return {"fetched": n, "files": ok}


def _parse(p) -> pd.DataFrame:
    """The date comes from the file name (fao_participant_oi_DDMMYYYY.csv, the date we asked NSE for) and is checked against the title line.
    Formats drift: from 2019 some titles are wrapped in doubled quotes and written "Jan 01,2021" (no space), and some headers carry a stray
    tab ("Future Stock Short\\t"). Before the 19 Oct fix those files were skipped silently (2019 partly, 2020-2023 almost entirely)."""
    txt = p.read_text(errors="ignore").splitlines()
    fd = pd.to_datetime(re.search(r"(\d{8})\.csv$", p.name).group(1), format="%d%m%Y")
    m = re.search(r"as on ([A-Za-z]+ ?\d{1,2}, ?\d{4})", txt[0].replace('"', ""))
    if m:
        td = pd.to_datetime(m.group(1).replace(",", ", ").replace("  ", " "), errors="coerce")
        if td is not pd.NaT and td == td and td != fd:
            raise ValueError(f"title date {td.date()} differs from file date {fd.date()}")
    df = pd.read_csv(io.StringIO("\n".join(txt[1:])))
    df.columns = [re.sub(r"\s+", " ", str(c)).strip() for c in df.columns]
    df = df[df["Client Type"].astype(str).str.strip().isin(["Client", "DII", "FII", "Pro", "TOTAL"])].copy()
    df["Client Type"] = df["Client Type"].astype(str).str.strip()
    for c in df.columns[1:]:
        # some files write numbers in Indian grouping ("2,38,483.00"): strip the commas
        df[c] = pd.to_numeric(df[c].astype(str).str.replace(",", "").str.strip(), errors="coerce")
    df = df.loc[:, [c for c in df.columns if not c.startswith("Unnamed")]]
    df.insert(0, "date", fd)
    return df


def build() -> dict:
    files = sorted((paths.bronze("flows") / "participant_oi").glob("*/*.csv"))
    frames, failed = [], []
    for p in files:
        try:
            frames.append(_parse(p))
        except Exception as e:  # counted and reported, never skipped silently
            failed.append(f"{p.name}: {type(e).__name__}: {str(e)[:80]}")
    if not frames:
        return {"rows": 0, "failed": failed[:20]}
    df = pd.concat(frames, ignore_index=True).rename(columns={"Client Type": "client_type"})
    df.columns = [c.lower().replace(" ", "_") for c in df.columns]
    hold = pd.Timestamp(paths.HOLDOUT_START)
    for part, sub in (("silver", df[df["date"] < hold]), ("sealed/silver", df[df["date"] >= hold])):
        t = paths.data_dir() / part / "flows" / "participant_oi.parquet"
        t.parent.mkdir(parents=True, exist_ok=True)
        pq.write_table(pa.Table.from_pandas(sub.reset_index(drop=True), preserve_index=False), t)
    per_year = df.groupby(df["date"].dt.year)["date"].nunique().to_dict()
    return {"rows": len(df), "days": int(df["date"].nunique()), "first": str(df["date"].min().date()), "last": str(df["date"].max().date()), "columns": list(df.columns)[:8],
            "files": len(files), "failed": len(failed), "failed_examples": failed[:10], "days_per_year": per_year}


if __name__ == "__main__":
    paths.ensure()
    if sys.argv[1] == "fetch":
        print(fetch(int(sys.argv[2]) if len(sys.argv) > 2 else 2012))
    else:
        print(json.dumps(build(), indent=1, default=str))
