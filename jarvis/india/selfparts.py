"""The India-side parts of Ananta's book about itself (6 Nov 2026): where India's data lives and the pre-open read, read from the India
data folder by this India-app module only (the firewall's allowlist names India's own files; jarvis/selfknow.py imports this when the
market is India). Read-only: nothing here writes."""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

INDIA = Path(os.getenv("ANANTA_INDIA_DATA", os.path.expanduser("~/ananta_data/india")))
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()


def _day(d) -> str:
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", str(d or ""))
    return f"{int(m.group(3))} {MONTHS[int(m.group(2)) - 1]}" if m else str(d or "")


def _json(p: Path):
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return None


def preopen() -> dict:
    files = sorted((INDIA / "paper" / "preopen").glob("*.json")) if (INDIA / "paper" / "preopen").exists() else []
    base = ("Every weekday at 09:09 IST (10:39 pm Toronto the evening before), since Friday 6 Nov, Ananta reads NSE's pre-open indicative "
            "prices for the Nifty, Bank Nifty and the ten heaviest stocks, and the morning answers use them as the first sight of the gap.")
    if not files:
        return {"words": base + " It has not run yet; the first read is Friday 6 Nov."}
    d = _json(files[-1]) or {}
    ok = not d.get("error") and any((v or {}).get("last") for v in (d.get("indexes") or {}).values())
    return {"words": base + f" Last read: {_day(files[-1].stem)}, {'with prices' if ok else 'empty (no prices came back)'}.", "last": files[-1].stem,
            "ok": ok}



def india_database() -> dict:
    """Where India's data lives: folders on the Mac, with file counts and the newest file (read-only)."""
    places = {
        "bronze/": "the raw lake: every file as downloaded from NSE and Zerodha (daily prices since 1994, futures and options since 2000, indices, intraday bars, filings, flows)",
        "silver/": "the cleaned tables built from bronze (one per kind)", "gold/": "the study-ready tables (returns, features, the 20-session windows)",
        "india.duckdb": "the query database over silver and gold that the studies and the fact map read",
        "readmodel/": "the read model: the one JSON the app and the Ask answer from (rebuilt after each run)",
        "paper/": "the paper books: your holdings' ratings, the managed book, the practice picks, the options line, the pre-open reads",
        "manifests/": "each job's run record (what it read, what it wrote, errors), the voice check and the trials",
        "ask/": "every conversation (one JSONL file per thread), your flags' pending picks, the oversight nudges, the Ask's own notes",
        "reports/": "the daily reports", "sealed/": "2024 onwards, kept sealed from research", "mf_cache/": "mutual-fund data cache",
    }
    out = {}
    for name, w in places.items():
        p = INDIA / name.rstrip("/")
        try:
            if p.is_dir():
                files = [x for x in p.rglob("*") if x.is_file()]
                newest = max((x.stat().st_mtime for x in files), default=0)
                out[name] = f"{w} ({len(files):,} files, newest {time.strftime('%d %b %H:%M', time.localtime(newest))})" if files else f"{w} (empty)"
            elif p.exists():
                out[name] = f"{w} (updated {time.strftime('%d %b %H:%M', time.localtime(p.stat().st_mtime))})"
        except OSError:
            out[name] = w
    return {"words": ("India's data is files on the Mac under ananta_data/india, written only by the India jobs (the lake, the studies, the paper books) "
                      "and the India service (conversations, flags). Your Zerodha account is read only; nothing here places an order."),
            "places": out, "chat_history": "ask/ (one file per conversation)"}


