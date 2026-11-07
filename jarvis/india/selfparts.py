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





# ------------------------------------------------------------------------------------------------------------ the self-scan, India half
# 6 Nov 2026 (Madhav, 17:13: "how Ananta is scanning the market, it also scans itself ... and tells us if it finds any issue"): the bugs of
# the last two weeks were of four kinds: wrong order or day; two places disagreeing; a number stuck at zero; Ananta not seeing its own
# facts. Each check below is one of those, written from a bug that already happened. Read-only; every finding is a self-check item.

STUCK_NIGHTS = 4


def _cards(n: int = 6) -> list[dict]:
    d = INDIA / "paper" / "reconstruction"
    out = []
    for p in sorted(d.glob("????-??-??.json"))[-n:]:
        c = _json(p)
        if isinstance(c, dict):
            out.append(c)
    return out


def scan(now: float | None = None) -> list[dict]:
    items: list[dict] = []
    now = now or time.time()
    try:
        sess = sorted(p.stem for p in (INDIA / "paper" / "decisions").glob("????-??-??.json"))
        newest = sess[-1] if sess else ""
        cards = _cards()
        card = cards[-1] if cards else {}
        day = str(card.get("day") or "")
        # 1. order and day: the card is behind the paper book (the India card of 4 Nov had described the wrong day)
        if newest and day and day < newest and now - time.mktime(time.strptime(newest, "%Y-%m-%d")) > 36 * 3600:
            items.append({"market": "india", "severity": "medium", "source": "self-scan",
                          "what": f"the newest reconstruction card is about {_day(day)} while the paper book has {_day(newest)}: the card is a session behind"})
        # 2. two places disagreeing: the card's last line against the queue of drafts (5 Nov: "nothing waits for you" while 3 drafts waited)
        try:
            from jarvis.india import views

            waiting = len(views.drafts().get("drafts") or [])
        except Exception:  # noqa: BLE001
            waiting = None
        head = str(card.get("headline") or "")
        m = re.search(r"(\d+) drafts? waits? for your yes", head)
        said = int(m.group(1)) if m else (0 if "nothing waits for you" in head else None)
        if waiting is not None and said is not None and said != waiting:
            items.append({"market": "india", "severity": "medium", "source": "self-scan",
                          "what": f"the card of {_day(day)} says {said} draft{'s' if said != 1 else ''} wait for Madhav but the queue holds {waiting}: two places disagree"})
        # 3. a section that could not build (the card still writes, with status 'error' in that part)
        bad = [k for k in ("market", "people", "ananta", "not_done", "reviews") if (card.get(k) or {}).get("status") == "error"]
        if bad:
            items.append({"market": "india", "severity": "medium", "source": "self-scan",
                          "what": f"the card of {_day(day)} could not build its {', '.join(bad)} part{'s' if len(bad) > 1 else ''} ({(card.get(bad[0]) or {}).get('error', '')[:80]})"})
        # 4. a number stuck at zero: the day's movers or the chosen picks, several nights running (a card that looks alive but reads nothing)
        if len(cards) >= STUCK_NIGHTS:
            last = cards[-STUCK_NIGHTS:]
            movers = [((c.get("not_done") or {}).get("summary") or {}).get("up", {}).get("movers", 0) or 0 for c in last]
            chosen = [len((c.get("ananta") or {}).get("chosen") or []) for c in last]
            for name, vals in (("the day's biggest movers", movers), ("Ananta's picks", chosen)):
                if all(v == 0 for v in vals):
                    items.append({"market": "india", "severity": "medium", "source": "self-scan",
                                  "what": f"{name} read 0 on the last {STUCK_NIGHTS} cards ({_day(last[0].get('day'))} to {_day(day)}): a number stuck at zero"})
        # 5. the read model behind the book (every answer reads it; 2 Nov: 'Monday's session is happening' after the close)
        rm = _json(INDIA / "readmodel" / "latest.json") or {}
        through = str(rm.get("data_through") or "")
        if newest and through and through < newest and now - time.mktime(time.strptime(newest, "%Y-%m-%d")) > 36 * 3600:
            items.append({"market": "india", "severity": "high", "source": "self-scan",
                          "what": f"the read model every answer uses stops at {_day(through)} while the paper book has {_day(newest)}: the answers are a session behind"})
        # 6. waiting too long: a draft older than 7 days (the three of 2 Nov waited 4 days before anyone counted them)
        try:
            from jarvis.india import views

            old = [d for d in views.drafts().get("drafts") or [] if d.get("day") and now - time.mktime(time.strptime(d["day"], "%Y-%m-%d")) > 7 * 86400]
        except Exception:  # noqa: BLE001
            old = []
        if old:
            items.append({"market": "india", "severity": "low", "source": "self-scan",
                          "what": f"{len(old)} research draft{'s' if len(old) != 1 else ''} ha{'ve' if len(old) != 1 else 's'} waited for Madhav's yes or skip for more than a week (oldest {_day(old[0]['day'])})"})
    except Exception as exc:  # noqa: BLE001  the scan never breaks the check
        items.append({"market": "india", "severity": "low", "source": "self-scan", "what": f"the India self-scan could not run ({type(exc).__name__})"})
    return items


def morning_review(full: bool = False) -> dict:
    """7 Nov 2026 (Madhav's yes): the India morning review's findings (the records repo's reviews folder), for the voice."""
    from jarvis import selfknow
    from jarvis.india import views

    return selfknow.review_page(views.REG / "reviews") if full else selfknow.review_page(views.REG / "reviews", per_section=4, cap=1300)
