"""Being ready for the open: four questions answered in code, the same every time (9 Nov 2026; Madhav: "yes, lets complete" to the outsider
readiness review, and at 18:25 Toronto: "how to make sure the agent adjusts itself according to the given situation without sticking to old
decisions when new challenges are being faced").

  how will it open?                          the 09:09 pre-open read, or before it GIFT Nifty against its own level at the last close
  what will the options line do at the open?  its own written plan for each way the market can open, its inputs, and any that were stale
  did any of my stocks file anything?         one line for each holding that filed since the last close, the movers, the results ahead
  has anything changed since the view?        the second look (jarvis/india/recheck.py): 09:09 against the 08:30 view, 10:20 against the pre-open

Each fact has one owner (preopen.py, the records repo's giftnifty.py, sp1plan.py and desk.py, recheck.py); this module only chooses which to
say. Read-only. answer() returns (words, follow-ups, evidence) or None when the message is not one of the four.
"""
from __future__ import annotations

import datetime as dt
import json
import re

OPEN_Q = re.compile(r"\b(how (?:will|would|might|is|does) (?:it|the market|nifty|india|the indian market|bank nifty) (?:going to |likely to |look to )?open|"
                    r"(?:what|how) (?:does|is|did) the (?:open|opening|pre-?open)(?: read)? (?:look|looking|show|showing|say|saying)|"
                    r"indicated open|pre-?open read|(?:is it|will it be|are we looking at) a gap (?:up|down))\b", re.I)
PLAN_Q = re.compile(r"\b(what (?:will|would|does|is) the options line (?:do|doing|going to do|plan(?:ning)?)(?: to do)?(?: (?:at|for) the open| today| tomorrow| this morning)?|"
                    r"options line'?s plan|(?:the )?plan for the open|what happens at (?:the )?(?:open|9:?15))\b", re.I)
NEWS_Q = re.compile(r"\b(?:(?:any|did|has|have|what)\b[^.?!]{0,40}\b(?:my (?:stocks|holdings|companies|shares)|holdings)\b[^.?!]{0,40}\b(?:fil(?:e|ed|ing|ings)|news|announc\w+|results)|"
                    r"(?:news|filings|announcements) (?:on|for|from|about|in) my (?:stocks|holdings|companies|shares)|holdings'? news)\b", re.I)
CHANGED_Q = re.compile(r"\b((?:has |did |is there )?(?:anything|something|what(?:'s| has| is)?) chang(?:e|ed|es|ing) since (?:the|your|you wrote the|this) (?:morning )?(?:view|note|plan)|"
                       r"is (?:the|your) (?:morning )?(?:view|plan) still (?:valid|good|right|true|current|standing)|second look|"
                       r"does (?:the|your) (?:morning )?view still (?:stand|hold))\b", re.I)
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))


def _at(label: str) -> str:
    try:
        from jarvis.india import schedule
        return schedule.at(label)
    except Exception:  # noqa: BLE001
        return {"com.ananta.india.preopen": "09:09 IST", "com.ananta.india.morningview": "08:30 IST", "com.ananta.india.openingview": "10:20 IST",
                "com.ananta.india.sp1paper": "07:30 IST"}.get(label, "")


def _preopen_file(day: str | None) -> dict:
    try:
        from jarvis.india import preopen
        return json.loads((preopen.OUT / f"{day}.json").read_text())
    except Exception:  # noqa: BLE001
        return {}


def how_it_opens(live: dict) -> str:
    clk = live.get("clock") or {}
    po, g, plan = live.get("preopen") or {}, live.get("gift") or {}, live.get("options_plan") or {}
    if po.get("words"):
        return "Sir, " + po["words"][0].lower() + po["words"][1:]
    if clk.get("state") == "open":
        return "Sir, the market is open, so its own prices are the read: " + str((live.get("index_now") or {}).get("words") or "the index prices could not be read just now.")
    if g.get("words"):
        row = ((plan.get("row") or {}).get("NIFTY") or {}).get("words")
        tail = (f" Options line: {row}" if row else "") + (f" The pre-open's matched prices come at {_at('com.ananta.india.preopen')} and go to your phone."
                                                           if clk.get("state") in ("before_open", "pre_open") else f" That is for {clk.get('next_session_words') or 'the next session'}.")
        return "Sir, " + g["words"] + tail
    why = f" ({g['error']})" if g.get("error") else ""
    return (f"Sir, I cannot see the open yet: GIFT Nifty could not be read just now{why}. The first Indian prices of the day are the pre-open's matched prices at "
            f"{_at('com.ananta.india.preopen')}, which go to your phone.")


def _last_session_line(live: dict) -> str:
    """What the options line did in the latest session, in one short sentence built from its ledger rows (not the long block written for the model)."""
    clk, ot = live.get("clock") or {}, live.get("options_today") or {}
    day = clk.get("latest_session_words") or "the last session"
    if not ot.get("decisions"):
        return f"On {day} it has no decision in its ledger."
    name = {"NIFTY": "Nifty", "BANKNIFTY": "Bank Nifty"}
    took = []
    for x in ot.get("taken") or []:
        res = (x.get("result") or {}).get("net_inr")
        took.append(f"{name.get(x.get('index'), x.get('index'))} {x.get('direction')} at {x.get('at')} IST"
                    + (f", closed about {'+' if res >= 0 else '−'}₹{abs(res):,} on paper" if isinstance(res, (int, float)) else
                       (", with no result on the record yet" if x.get("unscored") else ", still open on paper")))
    return (f"On {day} it took " + "; ".join(took) + "." if took else f"On {day} it passed at every decision point.")


def options_plan(live: dict) -> str:
    clk = live.get("clock") or {}
    plan = live.get("options_plan") or {}
    if plan.get("words"):
        rows = " ".join(r["words"] for r in (plan.get("row") or {}).values())
        return "Sir, " + plan["words"][0].lower() + plan["words"][1:] + (f" For the open as it is indicated now: {rows}" if rows else "")
    today_is_live = clk.get("state") in ("open", "closed") and clk.get("latest_session") == clk.get("today_india")
    if today_is_live and (live.get("options_today") or {}).get("decisions"):
        return "Sir, the options line's decision points for today have passed. " + _last_session_line(live)
    nxt = "today" if clk.get("state") in ("before_open", "pre_open") else clk.get("next_session_words")
    return (f"Sir, the options line writes its plan for the open at {_at('com.ananta.india.sp1paper')} on the session's own morning, from the inputs it has by then, so the plan for "
            f"{nxt or 'the next session'} is not written yet. When it is, I will say what it does if the market opens down, flat or up, and any input that was missing. "
            + _last_session_line(live))


def holdings_news() -> str:
    try:
        from jarvis.india import desk
        d = desk.load()
    except Exception:  # noqa: BLE001
        d = {}
    h = d.get("holdings_news") or {}
    if not h.get("lines"):
        return "Sir, the list of what your stocks have filed is not built yet; it is rebuilt after each close, at night and before the morning view."
    try:
        at = dt.datetime.fromisoformat(str(d.get("built_at"))).astimezone(IST)
        read = f" (filings read up to {at:%H:%M} IST on {at:%a} {at.day} {at:%b})"
    except (TypeError, ValueError):
        read = ""
    return "Sir, on your holdings" + read + ": " + " ".join(h["lines"]) + " I read what was filed and when, not the figures inside a results filing."


def what_changed(live: dict) -> str:
    clk = live.get("clock") or {}
    pre = _preopen_file(clk.get("today_india") if clk.get("state") in ("before_open", "pre_open", "open") else clk.get("latest_session"))
    rc, ol = pre.get("recheck") or {}, pre.get("opening_look") or {}
    if rc.get("words") or ol.get("words"):
        head = "Yes, sir. " if (rc.get("changed") or ol.get("changed")) else "Nothing that overturns it, sir. "
        s = head + (f"At the 09:09 second look: {rc['words']} " if rc.get("words") else "") + (f"After the first hour: {ol['words']}" if ol.get("words") else "")
        return s.strip() + " What adjusts by itself is what I read and say; the options line and the books keep their written rules, and a change to a rule waits for your yes."
    if clk.get("state") in ("before_open", "pre_open"):
        return (f"Sir, nothing has been checked against this morning's view yet. The second look comes at {_at('com.ananta.india.preopen')}, when the pre-open's matched prices are in: "
                f"I set them beside what the view was written with and send you what changed. The next one is after the first hour, at {_at('com.ananta.india.openingview')}.")
    nxt = clk.get("next_session_words") or "the next session"
    return (f"Sir, there is no second look on file for {clk.get('latest_session_words') or 'the last session'}. For {nxt}: the view is written at {_at('com.ananta.india.morningview')} "
            f"on its own morning, checked against the pre-open at {_at('com.ananta.india.preopen')} and again after the first hour at {_at('com.ananta.india.openingview')}; "
            "each time I say what changed since the view, and what the options line's own plan says for the open it gets.")


def answer(text: str, live) -> tuple[str, list[str], list[str]] | None:
    """live: today's block, or a function that returns it (called only when the question needs today's prices; the holdings' filings do not)."""
    t = text or ""
    if len(t) > 140:
        return None

    def now() -> dict:
        return (live() if callable(live) else live) or {}
    if CHANGED_Q.search(t):
        return what_changed(now()), ["How will it open?", "What will the options line do at the open?"], ["the second look (paper/preopen, jarvis/india/recheck.py)"]
    if NEWS_Q.search(t):
        return holdings_news(), ["How are my holdings doing?", "What results are coming up?"], ["company announcements (NSE) through the desk (manifests/desk.json holdings_news)"]
    if PLAN_Q.search(t):
        return options_plan(now()), ["How will it open?", "What did the options line do last session?"], ["the options line's plan (paper/sp1/plans) and its ledger"]
    if OPEN_Q.search(t):
        return how_it_opens(now()), ["What will the options line do at the open?", "Has anything changed since the view?"], ["the pre-open read (paper/preopen) or GIFT Nifty through Zerodha"]
    return None
