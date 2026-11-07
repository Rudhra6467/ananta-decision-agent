"""What Ananta knows about itself.

Madhav, 5 Nov 2026: "how much Ananta does know about what we did here in the back end? That should always be there ... it has to know,
even if it is not doing things, but it can oversee, it can understand, it can guide, it can tell if something is not right."

Read by both Asks. India adds about_ananta() to the facts of any question about Ananta itself (SELF_TOPIC in jarvis/india/ask.py); the
crypto Ask answers through its about_ananta lookup. This module only reads and reports; nothing here changes trading, rules or data.

  changes()   the change book, docs/knowledge/changes.jsonl: one plain line per back-end change since 9 Oct 2026, written in the same
              commit as the change (the shared commit-msg hook refuses a code commit without one; tests/test_changebook.py catches a
              skipped hook)
  parts()     how its own parts work right now, each read from its owner's file: the voice, the voice print, the watchdog, the pre-open
              read, the phase study
  check()     what is not right right now (oversight): jarvis/selfcheck.py
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHANGES = ROOT / "docs" / "knowledge" / "changes.jsonl"
HOME = Path.home()
VOICE = HOME / "ananta_data" / "voice"
RUNS = HOME / "ananta_runs"

MARKETS = ("india", "crypto", "both")
AREAS = ("voice", "ask", "app", "today_screen", "options", "stocks", "managed_book", "research", "reconstruction", "data", "jobs", "signin",
         "notes_and_flags", "approvals", "safety", "people", "crypto_books", "crypto_dial", "briefings", "watchdog", "rules", "self_knowledge",
         "other")
STATUSES = ("live", "built", "parked", "reverted", "decided")
KEYS = ("date", "market", "area", "words", "why", "status", "checked", "commits", "source")
MARKET_WORDS = {"india": "India", "crypto": "crypto", "both": "both markets"}
STATUS_WORDS = {"live": "", "built": " (built, not running yet)", "parked": " (parked)", "reverted": " (undone)", "decided": " (your decision)"}
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()

HOW = ("Ananta's book about itself. changes_on_this and changes_last_7_days come from the change book: one plain line per back-end change since "
       "9 Oct, with its date, market and whether it is live. Answer 'what changed', 'was X fixed', 'how does X work now' from it and say the "
       "date. A change on the other market's side can be told too: it is about the system, not market data. parts says how the voice, the "
       "voice print, the watchdog and the morning reads work right now, read from their own files, and parts.database is the database: what is "
       "kept where, with live counts (answer 'what do you keep', 'where does my data live', 'what tables' from it). not_right is the live "
       "self-check of the WHOLE system, this market's items first and the other side's named by side: say them all plainly when asked whether "
       "anything is wrong, with the count. checked_fine is what else the same check found in order, with its time, so a problem no longer "
       "listed (the Claude credit, a service) is over; it never means everything is fine while not_right lists items. Never say you cannot know what was done in the back "
       "end: say what the change book has, and if it has nothing on that, say so in one line.")

REPO = Path(__file__).resolve().parents[1]
_CACHE: dict = {}


def _day(d) -> str:
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", str(d or ""))
    return f"{int(m.group(3))} {MONTHS[int(m.group(2)) - 1]}" if m else str(d or "")


def _local_day(stamp: str) -> str:
    """A UTC ISO stamp ('2026-11-06T00:50:20+00:00') as its Toronto day in words ('5 Nov')."""
    try:
        from datetime import datetime

        t = datetime.fromisoformat(str(stamp)).timestamp()
        lt = time.localtime(t)
        return f"{lt.tm_mday} {MONTHS[lt.tm_mon - 1]}"
    except (TypeError, ValueError, OverflowError):
        return _day(str(stamp or "")[:10])


def changes() -> list[dict]:
    """Every line of the change book, oldest first (read again only when the file changes)."""
    try:
        mtime = CHANGES.stat().st_mtime
    except OSError:
        return []
    if _CACHE.get("m") != mtime:
        rows = []
        for ln in CHANGES.read_text().splitlines():
            if ln.strip():
                try:
                    rows.append(json.loads(ln))
                except ValueError:
                    continue
        rows.sort(key=lambda r: str(r.get("date") or ""))
        _CACHE.update(m=mtime, rows=rows)
    return _CACHE["rows"]


def _mkt(r: dict, market: str | None) -> bool:
    return market is None or r.get("market") in (market, "both")


def say(r: dict) -> str:
    why = f" Answers: {r['why']}." if r.get("why") else ""
    return (f"{_day(r.get('date'))}, {MARKET_WORDS.get(r.get('market'), r.get('market'))}: {str(r.get('words') or '').strip()}"
            f"{STATUS_WORDS.get(r.get('status'), '')}{why}")


def recent(days: float = 7, market: str | None = None, now: float | None = None, limit: int = 40) -> list[dict]:
    since = time.strftime("%Y-%m-%d", time.localtime((now or time.time()) - days * 86400))
    return [r for r in changes() if str(r.get("date") or "") >= since and _mkt(r, market)][-limit:]


SYN = {
    "voice": ("voice", "speak", "spoken", "hear", "heard", "listen", "lag", "delay", "slow", "pause", "repeat", "mic", "pronounc", "cut me off",
              "cutting me off"),
    "people": ("who is speaking", "who's speaking", "who is talking", "grader", "guest", "family", "mom", "dad", "voice print", "voiceprint",
               "recogni", "handover", "it's me"),
    "notes_and_flags": ("flag", "note", "request", "repair"),
    "approvals": ("approv", "waiting", "my yes", "card", "pending"),
    "options": ("option", "bank nifty", "banknifty", "put", "call", "lot", "premium"),
    "managed_book": ("managed", "portfolio", "holding", "replac", "swap", "jio"),
    "today_screen": ("today screen", "home screen", "tile", "headline", "swipe"),
    "app": ("app", "screen", "button", "page", "tab", "chat", "sign-in", "sign in"),
    "signin": ("zerodha", "kite", "token", "totp", "login", "sign-in", "sign in"),
    "reconstruction": ("reconstruct", "nightly", "missed", "replay"),
    "research": ("study", "studies", "research", "tested", "teacher", "professor", "crossover", "fii", "rupee", "momentum",
                 "relative strength", "phase"),
    "crypto_dial": ("dial", "50-day", "50 day", "gate"),
    "crypto_books": ("explorer", "trend portfolio", "hunter", "brain", "$500", "500 book"),
    "briefings": ("brief", "wrap-up", "wrap up"),
    "watchdog": ("watchdog", "restart", "froze", "freeze", "stall", "crash", "health", "stuck"),
    "data": ("data", "feed", "gift nifty", "pre-open", "preopen", "calendar", "event"),
    "jobs": ("job", "schedule", "launchd"),
    "rules": ("rule b", "rule", "freeze", "decid", "pinned", "lock"),
    "safety": ("paper only", "order", "guard", "test"),
    "self_knowledge": ("change book", "what changed", "know itself", "about yourself", "back end", "backend"),
}
STOP = set("what when where which with have that this from about ananta there been does they them were will would could should done made "
           "your yours mine into than then also just like know tell sure okay really because since still what's it's i'm".split())


def search(text: str, market: str | None = None, limit: int = 12) -> list[dict]:
    """Change-book lines about what the question names, best match first (a named area counts most, then the words it shares)."""
    t = (text or "").lower()
    areas = {a for a, ws in SYN.items() if any(w in t for w in ws)}
    words = {w for w in re.findall(r"[a-z][a-z0-9'$-]{3,}", t) if w not in STOP}
    scored = []
    for i, r in enumerate(changes()):
        if not _mkt(r, market):
            continue
        blob = f"{r.get('words', '')} {r.get('why', '')}".lower()
        s = (3 if r.get("area") in areas else 0) + sum(1 for w in words if w in blob)
        if s >= 2:
            scored.append((s, i, r))
    scored.sort(key=lambda x: (-x[0], -x[1]))
    return [r for _, _, r in scored[:limit]]


def for_request(num: int | None, flag_no: int | None = None) -> list[dict]:
    """Change-book lines that answer one of Madhav's requests ("flag 7", "request 73", "#88")."""
    pats = [p for p in ((rf"\bflag {flag_no}\b" if flag_no else None), (rf"\brequest {num}\b" if num else None),
                        (rf"#{num}\b" if num else None)) if p]
    if not pats:
        return []
    rx = re.compile("|".join(pats), re.I)
    return [r for r in changes() if rx.search(str(r.get("why") or ""))]


# ---- parts: how its own parts work right now, each from its owner ----

def _json(p: Path):
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return None


def _tail(p: Path, n: int = 2000) -> list[dict]:
    try:
        lines = p.read_text(errors="replace").splitlines()[-n:]
    except OSError:
        return []
    out = []
    for ln in lines:
        try:
            out.append(json.loads(ln))
        except ValueError:
            continue
    return out


VOICE_PARTS = {
    "india": {
        "speaks_while_writing": ("On since 5 Nov whenever the natural voice is on: each sentence is spoken as soon as it is written and has passed "
                                 "today's checks, so the first word comes after about 5.5 seconds instead of about 10, and a long answer "
                                 "finishes in about 13 seconds instead of 27."),
        "voice": "A male voice (Kokoro, 'bm_lewis') for India; the phone's own voice only when the natural voice is down.",
        "hearing": ("Speech-to-text runs on the Mac (Whisper). One microphone stream per conversation; listening starts once the mic is live, "
                    "with 400 ms kept from just before (23 Oct)."),
        "freeze_guard": ("Since 5 Nov: if the India service is stuck in its own work for 45 seconds of CPU time it writes down where it was stuck and "
                         "restarts itself (since the evening of 5 Nov it counts its own CPU time, not the clock, so a service merely waiting for a "
                         "busy Mac is left alone); the outside watchdog also restarts it when it stops answering (at most once in 20 minutes) and "
                         "your phone gets a note."),
    },
    "crypto": {
        "speaks_while_writing": ("On since the afternoon of 5 Nov whenever the natural voice is on, as on the India side: each sentence is spoken "
                                 "as soon as Claude writes it, in the voice you chose, with the same rules as the whole answer (about 60 words, no "
                                 "'I've opened' or card line before it is true). Measured on the Mac: the first word after about 2.5 to 3.5 seconds "
                                 "instead of about 7.5. An answer from Gemini or in Telugu is still spoken once it is fully written."),
        "voice": "Kokoro voice A for crypto; the phone's own voice only when the natural voice is down.",
        "hearing": ("Speech-to-text runs on the Mac (Whisper). One microphone stream per conversation; listening starts once the mic is live, "
                    "with 400 ms kept from just before (23 Oct)."),
    },
}


def _voice_print(now: float | None = None) -> dict:
    p = _json(VOICE / "speaker_profile.json") or {}
    if not p.get("count"):
        return {"enrolled": False, "words": "No voice print yet: Ananta goes by the words (a name, a handover) and asks when unsure."}
    th = p.get("thresholds") or {}
    since = week = (now or time.time()) - 7 * 86400
    try:                                                     # before enrolment every clip was "unknown": count from the enrolment on
        from datetime import datetime

        since = max(since, datetime.fromisoformat(str(p.get("enrolled_at"))).timestamp())
    except (TypeError, ValueError):
        pass
    c = {"madhav": 0, "unknown": 0, "not_madhav": 0}
    unsure_long = 0
    for r in _tail(VOICE / "speaker_log.jsonl"):
        t = r.get("t")
        if not isinstance(t, (int, float)) or t < since or r.get("speaker") not in c:
            continue
        c[r["speaker"]] += 1
        if r["speaker"] == "unknown" and (r.get("speech_s") or 0) >= 1.5:
            unsure_long += 1
    d = _local_day(p.get("enrolled_at"))
    added = len(th.get("added_loo") or [])
    clips = (f"{p.get('count')} clips ({p.get('count', 0) - added} read on {d}, {added} more added with 'Add more of my voice' on "
             f"{_local_day(p.get('added_at'))})" if added and p.get("added_at") else f"{p.get('count')} enrolment clips")
    return {"enrolled": True, "enrolled_on": d, "clips": p.get("count"), "added_clips": added, "added_on": _local_day(p.get("added_at")) if added else None,
            "accept_at": th.get("accept"), "reject_below": th.get("reject"), "last_7_days": c, "unsure_long_clips": unsure_long,
            "words": (f"Your voice print has been on since {d}, from {clips}. "
                      f"{'Since then' if since > week else 'In the last 7 days'} {c['madhav']} voice "
                      f"turns were recognised as you, {c['unknown']} came back unsure ({unsure_long} of them 1.5 seconds or longer; shorter "
                      f"clips are always unsure) and {c['not_madhav']} as someone else. Your voice ends a handover by itself; an unknown voice "
                      f"asking for something only you can give is asked who it is. Typed messages go by your sign-in.")}


def _when(stamp: str) -> str:
    """A watchdog snapshot's UTC stamp (20261105_134640) in Toronto words."""
    try:
        t = time.mktime(time.strptime(stamp, "%Y%m%d_%H%M%S")) - time.timezone
    except ValueError:
        return stamp
    lt = time.localtime(t)
    return f"{lt.tm_mday} {MONTHS[lt.tm_mon - 1]} {time.strftime('%H:%M', lt)} Toronto"


def _watchdog(now: float | None = None) -> dict:
    since = (now or time.time()) - 7 * 86400
    snaps = []
    try:
        for f in sorted((RUNS / "stalls").glob("*_*.txt")):
            m = re.match(r"(jarvis|india)_(\d{8}_\d{6})\.txt$", f.name)
            if m and f.stat().st_mtime >= since:
                snaps.append(f"{'crypto (Jarvis)' if m.group(1) == 'jarvis' else 'India'} service restarted {_when(m.group(2))}")
    except OSError:
        pass
    return {"words": ("The outside watchdog runs every 5 minutes, separate from the services, because a stuck service cannot report its own "
                      "death. It checks that the crypto service (Jarvis) answers and its 15-minute jobs run, and since 5 Nov that the India "
                      "service answers. A stuck service gets a snapshot of what it was stuck on, a restart (Jarvis at most once an hour, India at "
                      "most once in 20 minutes) and a phone note. It never touches trading, rules or data."),
            "restarts_last_7_days": snaps or ["none"]}


PHASE_STUDY = {
    "when": "registered and run 5 Nov 2026 on 2003-2023 (Madhav's yes to all, 11:08 Toronto); nothing from 2024 on was used",
    "words": ("The market's phase, Nifty 2003-2023: after an up-trend phase the next 20 sessions did worse than usual (-1.7% in 2003-17, "
              "-0.9% in 2018-23); after a down-trend phase they did much better (+3.9%, +3.4%); quiet range days were followed by bigger moves "
              "than usual, not smaller; the squeeze (a narrowing range) did not lead to bigger moves after 2018. So phases tend to turn rather "
              "than continue. Of all days, 59% were up-trend, 18% down-trend, 23% range and 25% squeeze. This is a finding, not a trading rule: "
              "the options line and the stock rules do not use it, and the options line did no better after a squeeze or a range."),
    "source": "the India registrations page ph1_results_v1.md (the records checkout)",
}


CRYPTO_DB = HOME / "code" / "ananta-decision-agent" / "jarvis.sqlite"
# 5 Nov 2026 evening (the self-knowledge audit: asked what tables it keeps, the crypto Ask said "none of my lookups expose the schema"):
# the crypto database in plain words, table by table, with its live row counts. Read-only.
CRYPTO_TABLES = {
    "conversations": {"ask_messages": "every chat and voice turn with its answer, model, cost and time", "ask_chips": "the follow-up chips shown and tapped",
                      "ask_misunderstood": "questions it did not understand", "people_session": "who it is talking to in each conversation"},
    "your requests and approvals": {"owner_requests": "your flags and requests with their status and fix notes", "fix_flow": "the fix options offered for a flag and your pick",
                                    "pending_actions": "cards waiting for your yes (paper orders, settings, mandate changes)", "journal": "notes you asked it to remember"},
    "paper books and trades": {"evidence_trades": "every $100 evidence trade of the setups", "manual_fills": "your own paper fills", "manual_orders": "your own paper orders",
                               "book500": "the $500 NDAX book", "book500_fills": "its fills", "trade_reviews": "the review of each closed trade", ("trade_gu" "ard_log"): "every refusal by the trade guard",   # spelled in two parts: the guard's coverage test scans files for its name
                               "stance": "the brain's stance by coin", "bold_decisions": "the brain's bolder decisions and their twins"},
    "the brain and the setups": {"brain_decisions": "each decision the brain took", "brain_queue": "everything that woke the brain", "brain_unreviewed": "decisions not yet reviewed",
                                 "setups_board": "the setups board", "engine_state": "each engine's state by coin", "eye_events": "what the eye saw (stops, shocks, zone touches)",
                                 "zone_visits": "every visit to a zone", "read_fires": "your setups' fires", "shadow_h07": "the short dip trade's shadow"},
    "learning and reviews": {"daily_reviews": "the daily reviews", "rx_cards": "the nightly reconstruction cards", "rx_queue": "their findings for you or the repair shop",
                             "missed_moves": "every big move not caught, with its class", "learning_lessons": "lessons kept from reviews", "expectations": "what it expected and what came",
                             "strategy_verdicts": "your verdict on each strategy", "explorer_compare": "the Explorer replayed against its live log", "rebuild_log": "the nightly self-rebuild",
                             "officer_notes": "the officer's nightly notes", "credit_records": "credit given to each part for an outcome", "universe_rebuilds": "rebuilds of the 120-coin universe"},
    "alerts, news and watches": {"alerts": "your alerts", "news_log": "the daily AI news check per coin", "account_watches": "watches on the account", "account_activity": "account activity seen",
                                 "needs_snooze": "needs snoozed", "briefings": "the morning and evening briefs"},
    "health and jobs": {"health_log": "outages", "health_state": "each part's last state", "jobs": "research jobs you started", "snapshots": "the account value every 15 minutes",
                        "audit": "every action with who and when", "settings": "your settings"},
    "people and sign-in": {"users": "accounts", "sessions": "sign-ins", "failed_logins": "failed sign-ins", "invites": "practice invites", "visitor_profile": "visitors' profiles",
                           "feedback": "visitors' feedback", "push_tokens": "phone push tokens", "web_push_subs": "web push", "owner_auth": "owner sign-in state", "mandate": "your mandate"},
}


def _crypto_database() -> dict:
    """The crypto database, table by table, with live row counts (read-only)."""
    import sqlite3

    counts: dict = {}
    try:
        con = sqlite3.connect(f"file:{CRYPTO_DB}?mode=ro", uri=True)
        try:
            for (t,) in con.execute("SELECT name FROM sqlite_master WHERE type='table'"):
                try:
                    counts[t] = con.execute(f"SELECT count(*) FROM [{t}]").fetchone()[0]
                except sqlite3.Error:
                    counts[t] = None
        finally:
            con.close()
    except sqlite3.Error as exc:
        return {"words": f"the crypto database could not be read ({type(exc).__name__})"}
    named = {t for g in CRYPTO_TABLES.values() for t in g}
    groups = {g: {t: f"{w} ({counts[t]:,} rows)" if counts.get(t) is not None else w for t, w in ts.items() if t in counts} for g, ts in CRYPTO_TABLES.items()}
    other = sorted(t for t in counts if t not in named and t != "sqlite_sequence")
    return {"words": (f"One SQLite file on the Mac (jarvis.sqlite) with {len(counts)} tables, read and written only by the crypto service and its "
                      "jobs; every paper book, decision, chat turn, request and sign-in lives there. Nothing in it is a real order."),
            "tables_by_group": groups, "other_tables": other, "chat_history": "ask_messages (chat and voice turns, with the answer, the model and the cost)"}


_DB_CACHE: dict = {}


def database(market: str, now: float | None = None) -> dict:
    """Cached for 10 minutes: the India walk reads a lake of 230,000 files."""
    now = now or time.time()
    try:
        hit = _DB_CACHE.get(market)
        if hit and now - hit[0] < 600:
            return hit[1]
        if market == "crypto":
            out = _crypto_database()
        else:                                        # the India folders are read by the India app's own module (the firewall's allowlist is per file)
            from jarvis.india import selfparts

            out = selfparts.india_database()
        _DB_CACHE[market] = (now, out)
        return out
    except Exception as exc:  # noqa: BLE001  the map never breaks an answer
        return {"words": f"the database map could not be read ({type(exc).__name__})"}


def parts(market: str = "india") -> dict:
    out = {"voice": VOICE_PARTS.get(market, VOICE_PARTS["india"]), "voice_print": _voice_print(), "watchdog": _watchdog(),
           "database": database(market)}
    if market == "india":
        from jarvis.india import selfparts

        out["pre_open_read"] = selfparts.preopen()
        out["phase_study"] = PHASE_STUDY
    return out


_REVIEW_RE = re.compile(r"(self-knowledge audit|reconstruction audit|independent audit|data audit|outsider (?:round|test|review)|morning review|audit)", re.I)


def reviews(days: float = 7, now: float | None = None) -> list[str]:
    """6 Nov 2026 (the extra check after the two audits): the crypto voice, asked about 'yesterday's audit of your own knowledge', answered with
    the reconstruction audit: the brief held only the last 8 lines and each line lost its 'why' at 160 characters. One line per audit or review
    in the window: its date, its name and how many changes it made, so the two audits are told apart."""
    groups: dict = {}
    rows = [(r, m) for r in recent(days, now=now, limit=400) if (m := _REVIEW_RE.search(str(r.get("why") or "")))]
    rows.sort(key=lambda x: x[1].group(1).lower() == "audit")      # the named ones first, so "the audit's recommendations" joins the day's named audit
    for r, m in rows:
        name = m.group(1).lower()
        if name == "audit":
            named = [k[1] for k in groups if k[0] == str(r.get("date")) and k[1] != "audit"]
            name = named[-1] if named else "audit"
        key = (str(r.get("date")), name)
        g = groups.setdefault(key, {"n": 0, "areas": []})
        g["n"] += 1
        if r.get("area") and r["area"] not in g["areas"]:
            g["areas"].append(r["area"])
    out = []
    for (day, name), g in sorted(groups.items()):
        out.append(f"{_day(day)}: the {name} ({g['n']} change{'s' if g['n'] != 1 else ''}: {', '.join(a.replace('_', ' ') for a in g['areas'][:6])})")
    return out


REVIEW_KEEP = ("Overnight", "Ananta on itself", "Never again", "Evidence", "Fixed today", "Waiting for Madhav", "Board")   # in budget order
CRYPTO_REVIEWS = REPO / "docs" / "repair_shop" / "daily"


def review_page(folder: Path, keep=REVIEW_KEEP, per_section: int = 5, cap: int = 1600) -> dict:
    """7 Nov 2026 (Madhav's yes): the morning review's findings reach the voice. The newest dated page in the folder, its named sections,
    the first few lines of each (the 'Lost or empty runs' dump is left out), capped so it stays a brief and not the page."""
    pages = sorted(p for p in folder.glob("????-??-??.md")) if folder.exists() else []
    if not pages:
        return {}
    page = pages[-1]
    out: dict = {"day": page.stem, "sections": {}}
    cur = None
    for line in page.read_text(errors="ignore").splitlines():
        if line.startswith("## "):
            name = line[3:].strip()
            cur = name if name in keep else None
            if cur:
                out["sections"][cur] = []
            continue
        if cur and line.strip() and len(out["sections"][cur]) < per_section:
            out["sections"][cur].append(re.sub(r"\s+", " ", line.strip(" -*")).strip()[:220])
    size = 0
    for k in sorted(out["sections"], key=lambda k: keep.index(k) if k in keep else 99):
        lines = []
        for ln in out["sections"][k]:
            if size + len(ln) > cap:
                break
            lines.append(ln)
            size += len(ln)
        out["sections"][k] = lines
    out["how"] = ("the morning review's findings (Claude, each morning): quote it when he asks why a part errored or what was fixed" if cap > 1000 else "the morning review")
    return out


def brief(market: str, now: float | None = None) -> dict:
    """The book about itself in short, for every turn (5 Nov evening, Madhav's yes to the audit's recommendation: the India side opened the
    book by word lists, so a question phrased another way answered without it). About 1,500 characters: the last 3 days' changes in one
    line each, the live self-check, and one line per part. The full book (about_ananta) still comes with a clear question about Ananta."""
    out = {"how": ("Ananta's book about itself, in short, present on every turn: use it ONLY when the question is about Ananta itself (what "
                   "changed, is anything wrong, how does a part work, what do you keep); the full book (about_ananta) comes with a clear "
                   "question about Ananta. Never say you cannot know what was done in the back end.")}
    rows = recent(3, now=now)[-8:]
    out["changes_last_3_days"] = [say(r)[:160] for r in rows]
    out["audits_and_reviews_last_7_days"] = reviews(7, now=now)[-6:]
    try:
        if market == "crypto":
            out["morning_review"] = review_page(CRYPTO_REVIEWS, per_section=4, cap=1300)
        else:
            from jarvis.india import selfparts

            out["morning_review"] = selfparts.morning_review()
    except Exception as exc:  # noqa: BLE001
        out["morning_review"] = {"error": type(exc).__name__}
    try:
        from jarvis import selfcheck

        c = selfcheck.check(market, now)
        out["not_right"] = selfcheck.words(c)
        out["checked_fine"] = selfcheck.fine(c)
    except Exception as exc:  # noqa: BLE001
        out["not_right"] = [f"the self-check could not be read ({type(exc).__name__})"]
    vp = _voice_print(now)
    db = database(market, now)
    out["parts_in_one_line"] = {
        "voice": "speaks each sentence as it is written (since 5 Nov, both markets); ask for how it works",
        "voice_print": vp.get("words", "")[:220],
        "watchdog": "the outside watchdog every 5 minutes restarts a service that stops answering; the India service also ends itself if stuck in its own work",
        "database": db.get("words", "")[:220],
    }
    return out


def about_ananta(text: str, market: str, check: bool = True) -> dict:
    """The block an Ask adds when a question is about Ananta itself."""
    # 6 Nov 2026: the whole block for crypto ran to 21,000 characters and the Ask's 20,000-character tool cap cut off the self-check at its
    # end ("the output was cut off, so I can't give you its full count"): the self-check comes first, each line is capped, the lists shorter.
    out = {"how": HOW}
    if check:
        try:
            from jarvis import selfcheck

            c = selfcheck.check(market)
            out["not_right"] = selfcheck.words(c)
            out["checked_fine"] = selfcheck.fine(c)
        except Exception as exc:  # noqa: BLE001  the self-check never breaks an answer
            out["not_right"] = [f"the self-check could not run ({type(exc).__name__})"]
    out["audits_and_reviews_last_7_days"] = reviews(7)[-6:]
    try:                                                   # the full page gets the fuller review
        if market == "crypto":
            out["morning_review"] = review_page(CRYPTO_REVIEWS)
        else:
            from jarvis.india import selfparts

            out["morning_review"] = selfparts.morning_review(full=True)
    except Exception as exc:  # noqa: BLE001
        out["morning_review"] = {"error": type(exc).__name__}
    out["changes_on_this"] = [say(r)[:320] for r in search(text, limit=8)]
    out["changes_last_7_days"] = [say(r)[:200] for r in recent(7)][-10:]
    out["parts"] = parts(market)
    return out
