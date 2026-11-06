"""Ananta scans itself (6 Nov 2026, Madhav: "how Ananta is scanning the market, it also scans itself every now and then and tells us if it
finds any issue"). The 15-minute self-check (jarvis/selfcheck.py) already asks whether every part RAN; this asks whether the parts AGREE.
Every check here is written from a bug that already happened, in one of four kinds: wrong order or day; two places disagreeing; a number
stuck at zero; Ananta not seeing its own facts. Read-only. The India half lives in jarvis/india/selfparts.py (the firewall's allowlist is
per file); this module holds the crypto half and joins the two. A HIGH item is pushed to Madhav's phone once a day (selfcheck.refresh);
HIGH and MEDIUM items reach him once per conversation through the Ask's nudge; all of them answer "is anything off with you?"."""
from __future__ import annotations

import calendar
import json
import os
import sqlite3
import time
from pathlib import Path

HOME = Path.home()
CRYPTO_DB = Path(os.getenv("JARVIS_DB", str(HOME / "code" / "ananta-decision-agent" / "jarvis.sqlite")))
STUCK_NIGHTS = 3
DAY = 86400


def _day_words(d: str) -> str:
    try:
        return time.strftime("%-d %b", time.strptime(str(d)[:10], "%Y-%m-%d"))
    except ValueError:
        return str(d)


def crypto(db: Path = CRYPTO_DB, now: float | None = None) -> list[dict]:
    items: list[dict] = []
    now = now or time.time()
    try:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=2)
    except sqlite3.Error as exc:
        return [{"market": "crypto", "severity": "low", "source": "self-scan", "what": f"the crypto self-scan could not open the database ({type(exc).__name__})"}]
    try:
        try:
            rows = con.execute("SELECT day, t, card FROM rx_cards ORDER BY day DESC LIMIT 6").fetchall()
        except sqlite3.Error:
            rows = []
        cards = []
        for day, t, card in rows:
            try:
                c = json.loads(card or "{}")
            except ValueError:
                continue
            c["_day"], c["_t"] = day, int(t or 0)
            cards.append(c)
        v2 = [c for c in cards if c.get("about_day")]                    # cards made after the 6 Nov fix say which day they describe
        if v2:
            c = v2[0]
            about = str(c["about_day"])
            # 1. order and day: the card must describe the day before the morning it was made (the 13 cards before 6 Nov did not)
            try:
                want = time.strftime("%Y-%m-%d", time.gmtime(calendar.timegm(time.strptime(c["_day"], "%Y-%m-%d")) - DAY))
            except ValueError:
                want = about
            if about != want:
                items.append({"market": "crypto", "severity": "medium", "source": "self-scan",
                              "what": f"the reconstruction card of {_day_words(c['_day'])} describes {_day_words(about)}, not the day before it: the window is wrong again"})
            # 2. two places disagreeing: the card's count of the brain's decisions against the table it was read from
            try:
                t0 = calendar.timegm(time.strptime(about, "%Y-%m-%d"))
                n_db = con.execute("SELECT count(*) FROM brain_decisions WHERE t >= ? AND t < ?", (t0, t0 + DAY)).fetchone()[0]
            except sqlite3.Error:
                n_db = None
            n_card = ((c.get("ananta") or {}).get("brain") or {}).get("n")
            if n_db is not None and n_card is not None and int(n_card) != int(n_db):
                items.append({"market": "crypto", "severity": "medium", "source": "self-scan",
                              "what": f"the card of {_day_words(c['_day'])} counts {n_card} brain decisions for {_day_words(about)} but the brain's table holds {n_db}: two places disagree"})
            # 3. a number stuck at zero, several nights running (the brain decides most days; 0 on every card was the bug nobody saw)
            if len(v2) >= STUCK_NIGHTS:
                last = v2[:STUCK_NIGHTS]
                ns = [((x.get("ananta") or {}).get("brain") or {}).get("n") or 0 for x in last]
                if all(n == 0 for n in ns):
                    items.append({"market": "crypto", "severity": "medium", "source": "self-scan",
                                  "what": f"the brain's decisions read 0 on the last {STUCK_NIGHTS} reconstruction cards: a number stuck at zero"})
            # 4. the value line and the wakes count are on the card (v2 shape)
            if "value" not in c or "wakes" not in c:
                items.append({"market": "crypto", "severity": "low", "source": "self-scan",
                              "what": f"the card of {_day_words(c['_day'])} is missing its {'value line' if 'value' not in c else 'wakes count'}"})
        # 5. waiting too long: an OPEN queue row older than 7 days
        try:
            old = con.execute("SELECT day, key FROM rx_queue WHERE state='OPEN' AND t < ? ORDER BY t", (int(now) - 7 * DAY,)).fetchall()
        except sqlite3.Error:
            old = []
        if old:
            items.append({"market": "crypto", "severity": "low", "source": "self-scan",
                          "what": f"{len(old)} reconstruction question{'s' if len(old) != 1 else ''} ha{'ve' if len(old) != 1 else 's'} waited for Madhav's decision for more than a week (oldest {_day_words(old[0][0])})"})
        # 6. Ananta not seeing its own facts: the self-check file itself is stale (the loop that writes it has stopped)
        p = Path(os.getenv("ANANTA_SELFCHECK", str(HOME / "ananta_data" / "selfcheck.json")))
        try:
            age = now - p.stat().st_mtime
            if age > 3600:
                items.append({"market": "both", "severity": "high", "source": "self-scan",
                              "what": f"the self-check has not been written for {int(age // 60)} minutes: the 15-minute loop that watches everything has stopped"})
        except OSError:
            pass
    finally:
        con.close()
    return items


def scan(now: float | None = None) -> list[dict]:
    """Both halves, own-market items unmixed; never raises."""
    out: list[dict] = []
    try:
        out += crypto(now=now)
    except Exception as exc:  # noqa: BLE001
        out.append({"market": "crypto", "severity": "low", "source": "self-scan", "what": f"the crypto self-scan could not run ({type(exc).__name__})"})
    try:
        from jarvis.india import selfparts

        out += selfparts.scan(now=now)
    except Exception as exc:  # noqa: BLE001
        out.append({"market": "india", "severity": "low", "source": "self-scan", "what": f"the India self-scan could not run ({type(exc).__name__})"})
    return out
