"""Movers and their news: NC1's live side (Madhav, 25 Nov 2026: "what are the main influencing keywords, sometimes for market gainers or market
losers"). For a live paper session it takes the day's biggest gainers and losers from the missed-movers review (manifests/missed_<date>.json),
finds the company news each one had between the previous close and this close (bronze/announce_api, the same files the news read and the
reconstruction card use), reads it with the NC1 dictionary (india/newskinds.py), and adds what NC1 found on 2010-2023 for those kinds.

Read-only, live paper days only (from 16 Oct 2026). No book, rule, score or decision reads it; the India morning review prints its lines.

  python -m india.movernews day [YYYY-MM-DD]     the lines for a session (default: the newest missed-movers file with movers)
"""
from __future__ import annotations

import datetime as dt
import gzip
import json
import sys
from collections import Counter
from pathlib import Path

from india import newskinds, paths

FORWARD_START = dt.date(2026, 10, 16)
NC1_RESULTS = Path(__file__).parent / "registrations" / "nc1_results_v1.json"
WORDS = {"results": "results", "order_win": "an order win", "usfda_adverse": "a USFDA warning", "usfda_approval": "a USFDA approval",
         "rating_down": "a rating cut", "rating_up": "a rating raise", "fund_raising": "equity raising", "merger_acquisition": "a deal (merger or acquisition)",
         "holding_change": "a promoter or insider holding change", "management_exit": "a senior exit", "pledge_default": "a pledge or default",
         "regulatory_legal": "a penalty or court matter", "buyback": "a buyback", "dividend_bonus_split": "a dividend, bonus or split",
         "operations_up": "a new plant or launch", "disruption": "a fire, shutdown or strike", "analyst_meet": "an analyst meeting"}


def _holidays() -> set[dt.date]:
    try:
        d = json.loads((paths.manifest_dir() / "nse_holidays.json").read_text())
        return {dt.datetime.strptime(x["tradingDate"], "%d-%b-%Y").date() for x in d.get("CM", [])}
    except (OSError, ValueError, KeyError, TypeError):
        return set()


def previous_session(day: dt.date, holidays: set[dt.date] | None = None) -> dt.date:
    hol = _holidays() if holidays is None else holidays
    d = day - dt.timedelta(days=1)
    while d.weekday() >= 5 or d in hol:
        d -= dt.timedelta(days=1)
    return d


def _when(row: dict) -> dt.datetime | None:
    for k in ("exchdisstime", "an_dt"):
        try:
            return dt.datetime.strptime(str(row.get(k)), "%d-%b-%Y %H:%M:%S")
        except (TypeError, ValueError):
            continue
    return None


def news_for(day: dt.date, prev: dt.date, root: Path | None = None) -> dict[str, list[dict]]:
    """Company news by symbol, made public after the previous session's 15:30 and up to this session's 15:30 (IST), routine notices left out."""
    root = root or paths.bronze("announce_api")
    start, end = dt.datetime.combine(prev, dt.time(15, 30)), dt.datetime.combine(day, dt.time(15, 30))
    out: dict[str, list[dict]] = {}
    d = prev
    while d <= day:
        p = root / str(d.year) / f"{d:%Y%m%d}.json.gz"
        if p.exists():
            try:
                rows = json.loads(gzip.open(p).read())
            except (OSError, ValueError):
                rows = []
            for r in rows if isinstance(rows, list) else []:
                t = _when(r)
                if t is None or not (start < t <= end):
                    continue
                cat, text = r.get("desc"), r.get("attchmntText")
                if newskinds.routine(cat, text):
                    continue
                out.setdefault(str(r.get("symbol") or ""), []).append({"at": t.strftime("%H:%M"), "day": t.date().isoformat(),
                                                                       "kinds": newskinds.kinds(cat, text), "category": cat})
        d += dt.timedelta(days=1)
    return out


def _history() -> dict:
    try:
        return json.loads(NC1_RESULTS.read_text()).get("responsiveness", {})
    except (OSError, ValueError):
        return {}


def _missed(day: dt.date | None) -> dict | None:
    md = paths.manifest_dir()
    files = [md / f"missed_{day}.json"] if day else sorted(md.glob("missed_*.json"), reverse=True)
    for p in files:
        try:
            m = json.loads(p.read_text())
        except (OSError, ValueError):
            continue
        if m.get("movers"):
            return m
    return None


def report(day: dt.date | None = None, holidays: set[dt.date] | None = None, root: Path | None = None) -> dict:
    m = _missed(day)
    if not m:
        return {"day": str(day) if day else None, "lines": ["Movers and their news: no movers file for that session (a holiday, or not built yet)."]}
    d = dt.date.fromisoformat(str(m["date"])[:10])
    if d < FORWARD_START:
        return {"day": str(d), "lines": ["Movers and their news: only live paper days (from 16 Oct 2026) are read."]}
    news = news_for(d, previous_session(d, holidays), root)
    sides = {"up": [], "down": []}
    for mv in m["movers"]:
        if mv.get("side") in sides:
            sides[mv["side"]].append(mv)
    out = {"day": str(d), "sides": {}, "lines": []}
    parts = []
    for side, name in (("up", "gainers"), ("down", "losers")):
        mvs = sides[side]
        with_news = [(mv["symbol"], news.get(mv["symbol"]) or []) for mv in mvs]
        had = [(s, n) for s, n in with_news if n]
        kinds = Counter(k for _s, n in had for k in sorted({k for x in n for k in (x["kinds"] or ["other"])}))
        out["sides"][side] = {"movers": len(mvs), "with_news": len(had), "kinds": dict(kinds),
                              "examples": [{"symbol": s, "kinds": sorted({k for x in n for k in x["kinds"]}) or ["other news"]} for s, n in had[:6]]}
        ks = ", ".join(f"{WORDS.get(k, 'other news')} {c}" for k, c in kinds.most_common(4))
        parts.append(f"{len(had)} of {len(mvs)} {name} had company news" + (f" ({ks})" if ks else ""))
    out["lines"].append(f"Movers and their news ({d:%a %d %b}): " + "; ".join(parts) + ". The rest moved without news of their own.")
    ex = [f"{e['symbol']} ({', '.join(WORDS.get(k, k) for k in e['kinds'] if k in WORDS) or 'other news'})"
          for side in ("up", "down") for e in out["sides"][side]["examples"][:3]]
    if ex:
        out["lines"].append("With news: " + "; ".join(ex) + ".")
    h = _history()
    seen = {k for side in ("up", "down") for k in out["sides"][side]["kinds"] if k in WORDS}
    if h and seen:
        bits = []
        for k in sorted(seen, key=lambda k: -(h.get(f"A|{k}", {}).get("confirmed") or 0))[:2]:
            a = h.get(f"A|{k}") or {}
            if a.get("confirmed"):
                bits.append(f"a 2%+ opening jump with {WORDS[k]} went on to give back {abs(a['cont_mean']) * 100:.1f}% by the close on average"
                            if (a.get("cont_mean") or 0) < 0 else f"a 2%+ opening jump with {WORDS[k]} went on {a['cont_mean'] * 100:.1f}% by the close on average")
        nn = h.get("A|no_news") or {}
        if bits and nn.get("cont_mean") is not None:
            out["lines"].append("On history (NC1, 2010-2023, before costs): " + "; ".join(bits) +
                                f"; with no news it gave back {abs(nn['cont_mean']) * 100:.1f}%. A study, not a rule.")
    return out


def main(argv: list[str]) -> None:
    if len(argv) > 1 and argv[1] == "day":
        day = dt.date.fromisoformat(argv[2]) if len(argv) > 2 else None
        print("\n".join(report(day)["lines"]))
    else:
        print(__doc__)


if __name__ == "__main__":
    main(sys.argv)
