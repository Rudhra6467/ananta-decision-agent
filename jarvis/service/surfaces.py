"""The new look's four surfaces for crypto (Madhav, 1 Nov 2026: "why no new look for crypto ananta?").

The same shapes the India service returns from jarvis/india/surfaces.py (today, money, proof, people), filled from the crypto
service's own sources: the $500 NDAX book, the dial, the officer's note, the setups scan, the weekly exam, the strategy register and
the reconstruction. Read-only: nothing here places, changes or decides anything. Rule B holds until 14 Dec 2026 (no new crypto
studies, no rule changes), so the screens say what is parked and when it returns, and never suggest a rule change.
The app reads these at /v3/surface/{today,money,proof,people}; India answers the same addresses (views.ROUTES aliases).
"""
from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from zoneinfo import ZoneInfo

TOR = ZoneInfo("America/Toronto")
UTC = dt.timezone.utc
WINDOW_START = dt.date(2026, 10, 15)          # strategy_status evidence_window (Rule A/B, Madhav 14 Oct)
WINDOW_DAYS = 60
RULE_B_END = dt.date(2026, 12, 14)
REPO = Path(__file__).resolve().parents[2]


def _dw(d) -> str:
    try:
        x = d if isinstance(d, dt.date) else dt.date.fromisoformat(str(d)[:10])
        return x.strftime("%a %-d %b")
    except Exception:  # noqa: BLE001
        return str(d or "")


def _cad(v, nd: int = 2) -> str:
    if not isinstance(v, (int, float)):
        return "—"
    return ("−C$" if v < 0 else "C$") + f"{abs(v):,.{nd}f}"


def _pct(p, nd: int = 1) -> str:
    if not isinstance(p, (int, float)):
        return "—"
    return f"{'+' if p > 0 else '−' if p < 0 else ''}{abs(p):.{nd}f}%"


CODE_WORDS = {"H07": "short dip", "BRK": "breakout", "PULL": "pullback", "RBD": "rebound", "ZONE_TOUCH": "zone touch", "BOLD": "bold book",
              "JARVIS": "brain's book", "READS": "your setups", "M2a-G": "your setup M2", "M2a": "your setup M2"}


def _plain(s: str | None) -> str:
    """No codes on the screen (design principle 4): rule codes become their names, capitals become words."""
    s = str(s or "")
    s = re.sub(r"\b([A-Z0-9]{2,10}) (H07|BRK|PULL|RBD)\b", lambda m: f"{m.group(1)} ({CODE_WORDS[m.group(2)]})", s)
    s = re.sub(r"\((H07|BRK|PULL|RBD)\)", lambda m: f"({CODE_WORDS[m.group(1)]})", s)
    s = re.sub(r"\bThe (H07|BRK|RBD|ZONE_TOUCH) (losses|book|trades)\b", lambda m: f"The {CODE_WORDS[m.group(1)]} {m.group(2)}", s)
    s = re.sub(r"\b(H07|BRK|RBD|ZONE_TOUCH|M2a-G|M2a)\b", lambda m: CODE_WORDS[m.group(1)], s)
    s = s.replace("is still CLOSED", "is still closed").replace("is CLOSED", "is closed").replace("is OPEN", "is open").replace("BTC closed", "Bitcoin closed")
    return s


def _isodates(s: str) -> str:
    return re.sub(r"\b(20\d\d-\d\d-\d\d)\b", lambda m: _dw(m.group(1)), str(s or ""))


def _r1(x):
    return round(x, 1) if isinstance(x, (int, float)) else None


def _why(s) -> str:
    s = _plain(s).removeprefix("invalidation: ")
    return "the dial closed" if s == "dial closed" else s


def _safe(f, *a, default=None):
    try:
        return f(*a)
    except Exception:  # noqa: BLE001
        return default


def _window(today: dt.date | None = None) -> dict:
    today = today or dt.datetime.now(TOR).date()
    day = max(0, min(WINDOW_DAYS, (today - WINDOW_START).days + 1))
    return {"day": day, "of": WINDOW_DAYS, "ends": RULE_B_END.isoformat(),
            "words": f"Day {day} of {WINDOW_DAYS} · ends {_dw(RULE_B_END)}"}


def _next_close_words(now: dt.datetime) -> str:
    """Crypto's daily close is 00:00 UTC; say it in Toronto time."""
    nxt = (now.astimezone(UTC) + dt.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return nxt.astimezone(TOR).strftime("%-I:%M %p Toronto").replace(":00 ", " ").lower().replace("toronto", "Toronto")


def _book(j) -> dict:
    from jarvis.service import ndax_book
    return _safe(ndax_book.status, j, default={}) or {}


def _dial(j) -> dict:
    from jarvis.service import exposure
    return _safe(exposure.state, j, default={}) or {}


def _positions(b: dict) -> list[dict]:
    rows = []
    value = b.get("value_cad") or 0
    for coin, p in (b.get("positions") or {}).items():
        qty, last, paid = p.get("qty") or 0, p.get("last"), p.get("paid")
        v = qty * last if isinstance(last, (int, float)) else None
        pnl = (100 * (v / paid - 1)) if v and paid else None
        rows.append({"symbol": coin, "value": v, "value_words": _cad(v), "weight_pct": round(100 * v / value, 1) if v and value else None,
                     "weight_of": "of book", "pnl_pct": round(pnl, 1) if pnl is not None else None, "paid": paid, "since": p.get("day"),
                     "rule": p.get("rule"), "stop": p.get("stop_on_ndax"), "sleeve": (p.get("sleeve") or "").lower(),
                     "grade": None, "action": "hold", "chip": f"{CODE_WORDS.get(p.get('rule'), 'held')} · stop {_cad(p.get('stop_on_ndax'), 0 if (p.get('stop_on_ndax') or 0) >= 100 else 2)}"})
    rows.sort(key=lambda r: -(r["value"] or 0))
    return rows


def _brake(b: dict, now: dt.datetime) -> str | None:
    br = b.get("brakes") or {}
    until = br.get("block_until")
    if br.get("paused"):
        return "the book is paused"
    if isinstance(until, (int, float)) and until > now.timestamp():
        u = dt.datetime.fromtimestamp(until, TOR)
        when = u.strftime("%-I %p").lower() + (" today" if u.date() == now.date() else " tomorrow" if u.date() == now.date() + dt.timedelta(days=1) else u.strftime(", %a %-d %b"))
        return "a loss brake blocks new buys until " + when
    return None


def _officer_note(j) -> dict | None:
    from jarvis.service import officer
    notes = _safe(officer.latest, j, 1, default=[]) or []
    if not notes:
        return None
    n = notes[0]
    text = re.sub(r"^(Good (morning|evening|afternoon),\s*)?[Ss]ir,\s*", "", str(n.get("note") or "")).strip()  # the screen never says sir
    return {"day": n.get("day"), "text": text[:1].upper() + text[1:] if text else ""}


def _plan_parts(line: str) -> dict:
    """discipline.plan_line's one long line, cut at its own labels."""
    parts: dict[str, str] = {}
    keys = ["Account", "Bold", "Officer", "Setups", "Strongest", "Held back", "Touched", "View"]
    pat = re.compile(r"(?:^|(?<=\.)\s)(" + "|".join(re.escape(k) for k in keys) + r")\b:?\s*")
    hits = list(pat.finditer(line or ""))
    if hits:
        parts["dial"] = line[:hits[0].start()].strip()
    for i, m in enumerate(hits):
        end = hits[i + 1].start() if i + 1 < len(hits) else len(line)
        parts[m.group(1)] = (m.group(0).strip() + " " + line[m.end():end].strip()).strip() if m.group(1) in ("Strongest", "Held back", "Touched") else line[m.end():end].strip()
    return parts


def _decision(dial: dict, b: dict, pos: list[dict], brake: str | None) -> str:
    held = " and ".join(p["symbol"] for p in pos)
    if (dial.get("dial") or 0) <= 0:
        s = "The dial is closed, so no new buys: cash is the position."
    else:
        s = "The dial is open: the core may buy Bitcoin and Ether in steps, and the edges may trade."
    if held:
        s += f" {held} {'stays' if len(pos) == 1 else 'stay'} held with {'its stop' if len(pos) == 1 else 'their stops'} on NDAX."
    return s


def today(j) -> dict:
    from jarvis.service import discipline, health, waiting
    now = dt.datetime.now(TOR)
    b, dial = _book(j), _dial(j)
    pos = _positions(b)
    brake = _brake(b, now)
    plan = _safe(discipline.plan_line, j, default={}) or {}
    parts = _plan_parts(plan.get("line") or "")
    h = _safe(health.status, j, default={}) or {}
    w = _safe(waiting.collect, j, default={}) or {}
    why = dial.get("why") or []
    btc = None
    m = re.search(r"closed (\S+) at ([\d,\.]+)", why[0]) if why else None
    if m:
        btc = m.group(2)
    cards = []
    note = _officer_note(j)
    if note and note["text"]:
        cards.append({"kind": "note", "label": f"Ananta's note · {_dw(note['day'])}", "text": _plain(note["text"]), "accent": True})
    if parts.get("View"):
        cards.append({"kind": "market", "label": "The market", "text": _plain(parts["View"])})
    setups = " ".join(x for x in (parts.get("Setups"), parts.get("Held back"), parts.get("Touched")) if x)
    if setups:
        cards.append({"kind": "setups", "label": "Setups", "text": _plain(setups), "foot": "Held back means seen and noted; the brain looks at them only when the dial reopens."})
    fails = [c.get("words") for c in (plan.get("checks") or []) if c.get("state") == "FAIL" and c.get("words")]
    if fails:
        cards.append({"kind": "checks", "label": "Checks that fail", "text": "; ".join(fails).capitalize() + ".",
                      "foot": "Parked to the 14 Dec review (Rule B: no crypto rule changes before then)."})
    closed_today = [c for c in (b.get("closed") or []) if c.get("out") == now.date().isoformat()]
    evening = {"label": f"What the $500 book did on {_dw(now.date())}",
               "text": "; ".join(f"sold {c['coin']} ({c.get('why')}), {_cad(c.get('pnl_cad'))}" for c in closed_today)} if closed_today else None
    win = _window(now.date())
    return {"ready": True, "market": "crypto", "now_words": now.strftime("%A %-d %b, %-I:%M %p Toronto").replace("AM", "am").replace("PM", "pm"),
            "when": f"next decision at the daily close, {_next_close_words(now)}",
            "decision": _decision(dial, b, pos, brake),
            "decision_source": f"From the daily close {_dw(dial.get('as_of_day'))} · " + ", ".join(why[1:3]) + (f" · {brake}" if brake else "") + " · nothing is placed, paper only",
            "numbers": [{"label": "Bitcoin · " + _dw(dial.get("as_of_day")), "value": btc or "—", "focus": "dial",
                         "sub": "dial " + ("open" if (dial.get("dial") or 0) > 0 else "closed")},
                        {"label": "Your account", "value": _cad(b.get("value_cad"), 0), "focus": "holdings",
                         "sub": f"{_pct(b.get('return_pct'))} since {_dw(b.get('started'))} · {len(pos)} coin{'s' if len(pos) != 1 else ''}"}],
            "waiting": {"count": w.get("count") or 0, "words": w.get("line")},
            "running": {"ok": bool(h.get("all_ok")), "words": "Everything is running" if h.get("all_ok") else f"{len(h.get('down') or [])} part{'s' if len(h.get('down') or []) != 1 else ''} down",
                        "checked": "every 2 min"},
            "cards": cards, "evening": evening, "clock": f"Evidence window: {win['words']}. Until then no new crypto studies and no rule changes (Rule B).",
            "suggested": ["Why is the dial closed?", f"How are {' and '.join(p['symbol'] for p in pos)} doing?", "What happens on 14 Dec?"] if pos else ["Why is the dial closed?", "What would reopen the dial?", "What happens on 14 Dec?"],
            "next_view": None, "paper": True}


def money(j) -> dict:
    from jarvis.service import exposure
    now = dt.datetime.now(TOR)
    b, dial = _book(j), _dial(j)
    pos = _positions(b)
    coins = sum(p["value"] or 0 for p in pos)
    bk = {x.get("book"): x for x in ((_safe(exposure.books, j, default={}) or {}).get("books") or [])}
    win = _window(now.date())
    books = [{"id": "managed", "label": "The $500 book", "ret_pct": _r1(b.get("return_pct"))},
             {"id": "index", "label": "Bitcoin, just held", "ret_pct": _r1((bk.get("HOLD") or {}).get("return_pct"))},
             {"id": "twin", "label": "The dial's hurdle", "ret_pct": _r1((bk.get("GATE50") or {}).get("return_pct"))}]
    cp = b.get("core_plan") or {}
    closed_dial = (dial.get("dial") or 0) <= 0
    brake = _brake(b, now)
    brief = (("The dial is closed: the core holds no Bitcoin or Ether and cash is the position until Bitcoin closes back above its 50- and 200-day averages."
              if closed_dial else f"The dial is open: the core aims for {cp.get('words') or 'its targets'}, bought in steps.")
             + (f" {brake[0].upper() + brake[1:]}." if brake else "")
             + " The edge trades held keep their stops on NDAX.")
    closed = [{"coin": c.get("coin"), "in": _dw(c.get("in")), "out": _dw(c.get("out")), "pnl_words": _cad(c.get("pnl_cad")), "pnl": c.get("pnl_cad"),
               "pct": c.get("pct"), "why": _why(c.get("why"))} for c in (b.get("closed") or [])][::-1]
    g = b.get("graduation") or {}
    return {"ready": True, "paper": True, "market": "crypto", "ccy": "CAD",
            "value_cad": b.get("value_cad"), "value_words": _cad(b.get("value_cad")),
            "sub_words": f"NDAX bid · {_dw(now.date())} · {_cad(coins)} in coins · {_cad(b.get('cash_cad'))} cash · {_pct(b.get('return_pct'))} since {_dw(b.get('started'))}",
            "books_title": "The book and its yardsticks",
            "books": books, "clock": {"words": win["words"], "sessions": win["day"], "of": WINDOW_DAYS},
            "books_note": "Bitcoin-held and the hurdle are paper books on Bitcoin's daily candles since 10 Oct; the $500 book began 11 Oct. Nothing is read into the gap before 14 Dec.",
            "books_ask": "Explain the book and its yardsticks in detail: what the $500 book holds and why, what 'Bitcoin, just held' and the dial's hurdle are, what the numbers mean today, what the 60-day evidence window is for, and what would tell us the book is working.",
            "plan": {"title": "At the next daily close", "tag": "dial closed" if closed_dial else "dial open", "brief": brief,
                     "asks": [{"label": "What would reopen it", "q": "What exactly would reopen the dial, and how close is Bitcoin to it?"},
                              {"label": "Ask about it", "q": "What will the $500 book do at the next daily close, and why?"}]},
            "managed": None,
            "holdings_title": "Your coins", "holdings_head": ["Coin · value · on cost", "Rule · stop on NDAX"],
            "holdings": pos, "holdings_note": "Paper, at real NDAX prices. Each edge trade risks 0.5% of the book; the stop sits on NDAX.",
            "holdings_empty": "No coins held: the whole book is cash.",
            "dial_block": {"state": "closed" if closed_dial else "open", "words": _plain(str(dial.get("dial_words") or "").replace("CLOSED", "Closed").replace("OPEN", "Open")), "why": [_isodates(x) for x in dial.get("why") or []], "as_of": _dw(dial.get("as_of_day")),
                           "brake": brake, "rule": "Buying is allowed only while Bitcoin closes above both its 50-day and 200-day averages.",
                           "closed": closed, "graduation": {"passed": g.get("passed"), "of": g.get("of"), "verdict": "not ready" if g.get("verdict") == "NOT READY" else (g.get("verdict") or "").lower()}},
            "options_book": None}


FINDING_WORDS = {"MISS_PATTERN": ("repeated miss", "repeated misses"), "WAIT_ARRIVED": ("wait that came true (woke the brain)", "waits that came true (each woke the brain)"),   # 6 Nov: older cards only; new cards count wakes apart
                 "GAVE_BACK": ("gain given back", "gains given back"), "BLEED": ("book losing steadily", "books losing steadily"),
                 "SELECTION": ("selection slip", "selection slips")}


def _exam() -> dict | None:
    p = REPO / "docs" / "repair_shop" / "exam" / "latest.json"
    try:
        e = json.loads(p.read_text())
    except Exception:  # noqa: BLE001
        return None
    ok = all(e.get(k) for k in ("knows_pass", "unknowns_pass", "why_pass", "consistency_pass"))
    return {"grade": "Pass" if ok else "Fail", "day": e.get("day"),
            "words": f"{e.get('known')}/{e.get('known_of')} facts · {e.get('unknown')}/{e.get('unknown_of')} unknowns · {e.get('why')}/{e.get('why_of')} whys · {_dw(e.get('day'))}"}


def proof(j) -> dict:
    from jarvis.service import missed, reconstruct, strategy_status
    now = dt.datetime.now(TOR)
    reg = _safe(strategy_status.load, default={}) or {}
    st = reg.get("strategies") or {}
    st = st if isinstance(st, dict) else {x.get("id"): x for x in st}
    count: dict[str, int] = {}
    for v in st.values():
        count[v.get("status") or "?"] = count.get(v.get("status") or "?", 0) + 1
    b = _book(j)
    g = b.get("graduation") or {}
    win = _window(now.date())
    clocks = [{"name": "The evidence window (Rule A and B)", "done": win["day"], "need": WINDOW_DAYS, "finish_words": _dw(RULE_B_END), "complete": win["day"] >= WINDOW_DAYS},
              {"name": "Round trips in the $500 book", "done": g.get("closed_trades") or 0, "need": 50, "finish_words": "", "complete": (g.get("closed_trades") or 0) >= 50},
              {"name": "Graduation gates passed", "done": g.get("passed") or 0, "need": g.get("of") or 10, "finish_words": "", "complete": g.get("verdict") == "READY"}]
    m = _safe(missed.recent, j, 7, default={}) or {}
    c, cl = m.get("counts") or {}, m.get("classes") or {}
    missed_words = (f"In 7 days, of the big moves: {c.get('CAUGHT', 0)} caught, {c.get('SEEN', 0)} seen, {c.get('MISSED', 0)} missed. "
                    f"{cl.get('INTENTIONAL', 0)} were held back on purpose by the closed dial.") if c else None
    r = _safe(reconstruct.latest, j, default={}) or {}
    kinds: dict[str, int] = {}
    for f in r.get("findings") or []:
        kinds[f.get("kind")] = kinds.get(f.get("kind"), 0) + 1
    found = ", ".join(f"{n} {FINDING_WORDS.get(k, (k.lower(), k.lower()))[0 if n == 1 else 1]}" for k, n in kinds.items())
    last_night = (f"{_dw(r.get('day'))}: {(r.get('market') or {}).get('dial_words') or ''}. Found {found or 'nothing new'}. "
                  "Each is noted on the card; nothing changes a rule before the 14 Dec review.") if r else None
    return {"ready": True, "paper": True, "market": "crypto",
            "studies": {"label": "Strategies ›", "big": len(st), "run": len(st),
                        "sub": f"{count.get('ACTIVE', 0)} active · {count.get('PARKED', 0)} parked · {count.get('EVIDENCE', 0)} measured only",
                        "ask": "Explain the strategies on record: which are active, which are parked and why, which are only measured, what the one measured edge is, and what Rule B means until 14 Dec."},
            "exam": {**(_exam() or {"grade": None, "words": None}), "label": "Weekly exam ›",
                     "ask": "Explain the weekly exam: what it asks, how it is graded, what it found this week, and what is still open."},
            "clocks": clocks, "clocks_ask": "Explain every crypto clock in detail: the 60-day evidence window, the round trips the $500 book needs, the graduation gates, where each stands and what would count as a pass.",
            "missed": {"words": missed_words, "day": "last 7 days"} if missed_words else None,
            "last_night": {"words": last_night} if last_night else None,
            "links": [{"label": "The repair board", "route": "/flags"}, {"label": "What we missed", "route": "/missed"}, {"label": "The evidence, live", "route": "/reconstruction"}]}


def people(j, is_owner: bool = True) -> dict:
    rows = [{"id": "madhav", "name": "Madhav", "relation": "owner", "can": "decides everything", "voice": None}]
    if is_owner:
        pp = _safe(j.people, default={}) or {}
        vs = pp.get("visitors") or []
        for v in [x for x in vs if not x.get("expired")]:
            rows.append({"id": "v" + str(len(rows)), "name": v.get("name") or "Guest", "relation": "invited",
                         "can": "can ask; can't approve or change anything", "voice": None})
        gone = sum(1 for x in vs if x.get("expired"))
        if gone:
            rows.append({"id": "past", "name": "Past guests", "relation": f"{gone} invite{'s' if gone != 1 else ''} expired", "can": "no access now", "voice": None})
    return {"ready": True, "people": rows, "rule": "Only Madhav decides; everyone else can ask. A guest is greeted by name and never 'sir'.",
            "invite": "An invited person gets their own paper book and Ananta's tour in its own voice; they never see your account."}
