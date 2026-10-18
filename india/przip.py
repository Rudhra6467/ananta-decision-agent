"""NSE daily PR zips (bronze/pr_zip, 2010 on) into silver: announcements, board meetings, corporate actions (book closure), and price-band hits.

  python -m india.przip build        silver/pr/{announcements,board_meetings,bc_actions,band_hits}.parquet  (2024+ under sealed/silver/pr)

Point in time: everything in a day's file is known after that day's close (the files are stamped about 16:30-17:00 IST), so a row's available_from is the
next session. Announcement text is kept on this Mac only (D18); studies use the category and the date.
Categories come from the subject words NSE uses (first matching rule wins); "other" keeps the rest visible.
"""
from __future__ import annotations

import datetime as dt
import io
import re
import sys
import zipfile

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from india import paths

CATS = [("results", r"financial result|unaudited|audited result"), ("dividend", r"dividend"), ("bonus_split", r"bonus|split|sub-division"),
        ("buyback", r"buy[- ]?back"), ("fund_raising", r"fund raising|preferential|qip|rights issue|allotment"), ("merger", r"amalgamation|merger|demerger|scheme of arrangement|acquisition"),
        ("rating", r"credit rating"), ("analyst_meet", r"analyst|investor meet|con\. call|conference call|investor presentation"),
        ("legal", r"litigation|penalty|sebi order|court|tribunal|show cause|adjudication"),
        ("order_win", r"bagging|bagged|receipt of (an |the )?orders?|orders? received|new orders?|award(ed)? of|letter of award|contract (award|win|receipt)"),
        ("management", r"resignation|appointment|cessation|director|ceo|cfo|kmp"),
        ("pledge", r"pledge|encumbrance"), ("insider_trading", r"insider trading|sast|takeover|acquisition of shares"), ("nav", r"declaration of nav"),
        ("share_cert", r"share certificate"), ("agm", r"general meeting|agm|egm|postal ballot"), ("legal", r"litigation|penalty|sebi order|court|tribunal")]


def _cat(text: str) -> str:
    t = text.lower()
    for name, pat in CATS:
        if re.search(pat, t):
            return name
    return "other"


_AN = re.compile(r"^(.*?)\s{2,}([A-Z0-9&\-\.]+)\s*:\s*(.*)$")


def _member(z: zipfile.ZipFile, prefix: str, ext: str) -> str | None:
    for n in z.namelist():
        if n.lower().startswith(prefix.lower()) and n.lower().endswith(ext):
            return n
    return None


def _read_txt(z, name) -> list[str]:
    return z.read(name).decode("latin-1", errors="ignore").splitlines()[1:]


def parse(path, file_date: dt.date) -> dict[str, list[dict]]:
    out = {"announcements": [], "board_meetings": [], "bc_actions": [], "band_hits": []}
    try:
        z = zipfile.ZipFile(path)
    except zipfile.BadZipFile:
        return out
    n = _member(z, "An", ".txt")
    if n:
        for line in _read_txt(z, n):
            m = _AN.match(line.strip())
            if not m:
                continue
            name, sym, rest = m.groups()
            subj = rest.split(f" {sym} :")[0].split(f"{sym} :")[0].strip()
            out["announcements"].append({"date": file_date, "symbol": sym, "company": name.strip(), "subject": subj[:200], "category": _cat(subj), "text": rest[:2000]})
    n = _member(z, "Bm", ".txt")
    if n:
        for line in _read_txt(z, n):
            parts = [p.strip() for p in line.split(" : ", 2)]
            if len(parts) < 3:
                continue
            m = re.match(r"^(.*?)\s{2,}([A-Z0-9&\-\.]+)$", parts[0])
            if not m:
                continue
            bm = pd.to_datetime(parts[1], format="%d-%b-%Y", errors="coerce")
            out["board_meetings"].append({"date": file_date, "symbol": m.group(2), "company": m.group(1).strip(), "meeting_date": bm.date() if pd.notna(bm) else None,
                                          "purpose": parts[2][:300], "category": _cat(parts[2])})
    n = _member(z, "Bc", ".csv")
    if n:
        try:
            bc = pd.read_csv(io.BytesIO(z.read(n)), dtype=str, encoding="latin-1", on_bad_lines="skip")
            bc.columns = [c.strip().upper() for c in bc.columns]
            for d in bc.to_dict("records"):
                ex = pd.to_datetime(str(d.get("EX_DT", "")).strip(), format="%d/%m/%Y", errors="coerce")
                out["bc_actions"].append({"date": file_date, "series": str(d.get("SERIES", "")).strip(), "symbol": str(d.get("SYMBOL", "")).strip(),
                                          "ex_date": ex.date() if pd.notna(ex) else None, "purpose": str(d.get("PURPOSE", "")).strip()})
        except Exception:
            pass
    n = _member(z, "bh", ".csv")
    if n:
        try:
            bh = pd.read_csv(io.BytesIO(z.read(n)), dtype=str, encoding="latin-1", on_bad_lines="skip", index_col=False)
            bh.columns = [c.strip().upper() for c in bh.columns]
            sc = "SERIES" if "SERIES" in bh.columns else "SR"
            side_col = next((c for c in bh.columns if c.replace("_", "/") == "HIGH/LOW"), None)
            for d in bh.to_dict("records"):  # records, not itertuples: "HIGH/LOW" is not a valid tuple field name and would be renamed
                out["band_hits"].append({"date": file_date, "symbol": str(d.get("SYMBOL", "")).strip(), "series": str(d.get(sc, "")).strip(),
                                         "side": str(d.get(side_col, "")).strip() if side_col else ""})
        except Exception:
            pass
    return out


def build() -> dict:
    import json
    man = paths.manifest_dir() / "pr_zip.jsonl"
    rows = {}
    for line in man.read_text().splitlines():
        r = json.loads(line)
        if r.get("status") == 200 and r.get("path"):
            rows[r["date"]] = r["path"]
    acc = {"announcements": [], "board_meetings": [], "bc_actions": [], "band_hits": []}
    for d, p in sorted(rows.items()):
        res = parse(paths.data_dir() / p, dt.date.fromisoformat(d))
        for k, v in res.items():
            acc[k].extend(v)
    out = {}
    hold = dt.date.fromisoformat(paths.HOLDOUT_START)
    for k, v in acc.items():
        df = pd.DataFrame(v)
        if df.empty:
            out[k] = 0
            continue
        for part, sub in (("silver", df[df["date"] < hold]), ("sealed/silver", df[df["date"] >= hold])):
            t = paths.data_dir() / part / "pr" / f"{k}.parquet"
            t.parent.mkdir(parents=True, exist_ok=True)
            pq.write_table(pa.Table.from_pandas(sub.reset_index(drop=True), preserve_index=False), t, compression="zstd")
        out[k] = {"rows": len(df), "first": str(df["date"].min()), "last": str(df["date"].max()),
                  "categories": df["category"].value_counts().head(12).to_dict() if "category" in df else None}
    return out


if __name__ == "__main__":
    paths.ensure()
    import json
    print(json.dumps(build(), indent=1, default=str))
