"""How to answer this particular question (Madhav, 27 Oct 2026 night: "frame some questions ... be an outsider and analyze those answers
according to the market ... and then do that, use those inputs and perform the fixes").

The outside review of 41 fresh questions (grade B-) found the Ask applying a trader's horizon to long-term money (the 50/200-day averages and
"downtrend, so wait" in answers about SIPs, gold for five years, loans and beginners), stapling its paper-book record (0 of 35 closed, -7.8%) onto
real-money and safety answers, forcing a "decision" where none was asked, and missing everyday Indian practice. This module decides in code, per
question, what the model is told for this turn (FACTS.answer_guide): the horizon, whether a decision was asked, whether the book may be quoted,
and the short India checklist lines for the topics in the question. Rule numbers come from the records' india_rules_facts.json (FACTS.lookup.rules);
the few lines here are practice points that file does not carry.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
from pathlib import Path

DATA = Path(os.getenv("ANANTA_INDIA_DATA", os.path.expanduser("~/ananta_data/india")))

LONG = re.compile(r"\b(sips?|mutual funds?|index funds?|funds?|flexi ?cap|large ?cap|mid ?cap fund|small ?cap fund|elss|ppf|nps|long[- ]term|"
                  r"(?:for|over|next|in) (?:the next )?(?:\d+|five|ten|three|fifteen|twenty) years|\d+[- ]years?|years? from now|retire\w*|pension|"
                  r"my (?:kid|child|son|daughter)|children'?s education|wealth|asset allocation|new to investing|start investing|beginner|fresher|"
                  r"first[- ]time investor|per month|a month|monthly|lakh(?:s)? (?:in|lying)|savings account|nifty bees|etf)\b", re.I)
PF = re.compile(r"\b(emergency fund|insurance|personal loan|loan|borrow\w*|emi|income tax|capital gains|tax\w*|fd|fds|fixed deposit|savings account|"
                r"salary|debt|credit card|ppf|nps|retire\w*)\b", re.I)
TRADE = re.compile(r"\b(intraday|scalp\w*|today'?s trade|this week|next week|tomorrow|entry|enter|stop[- ]?loss|trailing|target price|breakouts?|"
                   r"breakdown|swing|short[- ]term|options?|futures?|f&o|fno|expiry|lots?|gap(?:ped|s)? (?:up|down)|rsi|macd|moving averages?|"
                   r"crossover|golden cross|death cross|chart|support|resistance|position size|risk per trade|bracket order)\b", re.I)
DECIDE = re.compile(r"\b(should (?:i|we|he|she|my)|shall i|what should|what would you do|do i (?:buy|sell|hold|add|keep|switch)|is (?:it|this|now) (?:a )?"
                    r"(?:good|right|bad) (?:time|idea|moment)|good (?:buy|fund|stock|investment)|worth (?:buying|it|holding|applying)|buy,? (?:or )?sell|"
                    r"sell,? (?:or )?hold|hold,? (?:or )?(?:sell|add)|hold or|keep or|continue (?:it|the|his|her|my)|should .* continue|switch|stop (?:my|the|it|his)|"
                    r"too late|buy now|your read|what do you think|your view|what'?s your take|square that|average down|is .* a (?:good|buying) (?:opportunity|time))\b",
                    re.I)
BOOK = re.compile(r"\b(practice (?:book|trades?)|research book|paper (?:book|trades?|trading)|the book|our book|your (?:picks|trades|book)|"
                  r"win rate|expectancy|how (?:is|are) (?:you|ananta|the practice|the paper) (?:doing|performing)|strategy record|sharpe)\b", re.I)
LOAN = re.compile(r"\b(personal loan|borrow\w*|take (?:a )?loan|loan to (?:buy|invest)|margin (?:money|funding|trading)|leverage)\b", re.I)
TIP = re.compile(r"\b(telegram|whatsapp|tip|tips|sure[- ]?shot|guaranteed|10x|multibagger|penny stock|pump|insider|group says|will (?:surely|definitely|double))\b", re.I)
BEGINNER = re.compile(r"\b(new to investing|start investing|beginner|fresher|first[- ]time|where should i start|just started|i'?m \d{2}\b|savings account)\b", re.I)
PCR = re.compile(r"\b(put[- ]call ratio|pcr)\b", re.I)
RUPEE = re.compile(r"\b(rupee|usd ?/? ?inr|dollar)\b", re.I)
MINE = re.compile(r"\b(my (?:holdings?|stocks|portfolio|account|shares)|for me|matter for|mean for|affect (?:me|my))\b", re.I)
BROAD = re.compile(r"\b(small ?caps?|mid ?caps?|a sector|sectors?|gold|silver|it stocks|pharma stocks|bank stocks|psu)\b", re.I)

# What a weaker rupee usually does to each of his holdings' businesses: general knowledge about the business, not an Ananta test.
RUPEE_SENSITIVITY = {
    "TMPV": "Tata Motors passenger vehicles owns Jaguar Land Rover, which earns mostly in pounds, dollars and euros: a weaker rupee usually helps its rupee earnings",
    "TMCV": "Tata Motors commercial vehicles sells mostly in India and imports some parts: little direct gain, a slightly higher cost",
    "TATAPOWER": "Tata Power imports coal and has dollar costs: a weaker rupee usually raises its costs",
    "JIOFIN": "Jio Financial is a domestic finance business: little direct effect",
    "LICI": "LIC is a domestic insurer: little direct effect (its bond and share portfolio moves with Indian markets)",
    "IRFC": "IRFC lends to Indian Railways; it has some foreign-currency borrowing, but the railway contract passes costs through: little direct effect",
    "IEX": "Indian Energy Exchange is a domestic power exchange: little direct effect",
    "KARURVYSYA": "Karur Vysya Bank is a domestic bank: little direct effect",
    "MARICO": "Marico sells mostly in India but has an overseas business and some imported or crude-linked inputs: mixed, small effect",
    "UNITDSPR": "United Spirits imports Scotch and other inputs: a weaker rupee usually raises its costs",
    "NATIONALUM": "NALCO sells aluminium and alumina at dollar-linked prices and exports: a weaker rupee usually helps",
    "IDEA": "Vodafone Idea buys network equipment priced in dollars: a weaker rupee usually raises its costs",
    "NETWORK18": "Network18 is a domestic media business: little direct effect",
    "TATACHEM": "Tata Chemicals has operations in the US and UK and exports soda ash: a weaker rupee usually helps a little",
}

EXTRA_LINES = {
    "beginner": "Before investing: term life cover if anyone depends on his income and health insurance come first, then the emergency fund (6 months "
                "of expenses), then high-interest debt, then a low-cost index fund SIP.",
    "pcr": "In India a high put-call ratio on open interest is usually read as put writers supporting the market (often bullish), and extremes are "
           "read as contrarian; do not give only the US 'more puts means fear' reading.",
    "options_sleeve": "The options share in his account plan is Ananta's paper allocation rule, not a normal part of a long-term investor's money.",
    "broad": "For broad exposure (small caps, mid caps, a sector, gold) suggest a diversified fund or ETF bought in small staggered amounts, never a "
             "single stock; check a 'it fell X%' claim against FACTS.lookup (sector and index drawdowns).",
}


def horizon(text: str) -> str | None:
    """'personal_finance' | 'long_term' | 'trade' | None (not stated)."""
    t = text or ""
    trade = bool(TRADE.search(t))
    if PF.search(t) and not trade:
        return "personal_finance"
    if LONG.search(t) and not trade:
        return "long_term"
    if trade:
        return "trade"
    return None


def decision_asked(text: str) -> bool:
    """'How big an emergency fund should I have?' asks for a size, not a decision."""
    if re.match(r"\s*(?:hey ananta,?\s*)?how (?:big|much|many|long|often|large|soon)\b", text or "", re.I):
        return False
    return bool(DECIDE.search(text or ""))


def book_question(text: str) -> bool:
    return bool(BOOK.search(text or ""))


def topics(text: str) -> list[str]:
    t = text or ""
    out = []
    for name, rx in (("loan", LOAN), ("tip", TIP), ("beginner", BEGINNER), ("pcr", PCR), ("broad", BROAD)):
        if rx.search(t):
            out.append(name)
    if RUPEE.search(t) and MINE.search(t):
        out.append("rupee_holdings")
    return out


def rupee_lines(holdings: list[str]) -> dict:
    return {s: RUPEE_SENSITIVITY[s] for s in holdings if s in RUPEE_SENSITIVITY}


def guide(text: str, f: dict | None = None) -> dict:
    """FACTS.answer_guide for this turn: the horizon, whether a decision was asked, whether the book may be quoted, and topic lines."""
    f = f or {}
    h = horizon(text)
    tp = topics(text)
    lines = []
    if h in ("long_term", "personal_finance"):
        lines.append("HORIZON: long-term money / personal finance. Do not use the 50/200-day averages, 'downtrend so wait', the October low or the "
                     "practice book. Answer from the goal and time horizon, asset allocation, valuation against the long-run average, costs and tax.")
    elif h == "trade":
        lines.append("HORIZON: a trade (days to weeks): the read-and-decide shape with Ananta's tested filters applies.")
    if not book_question(text):
        lines.append("Do not quote the practice book's results (closed trades, win rate, per-trade average) in this answer.")
    if not decision_asked(text):
        lines.append("No decision was asked: explain and inform; no 'decision' line.")
    else:
        lk = f.get("lookup") or {}
        if not (lk.get("stocks") or lk.get("mutual_funds") or lk.get("sectors") or lk.get("gold")):
            # 27 Oct re-ask: "What do you think of Tesla shares?" got the no-data shape and then "Decision: wait"
            lines.append("NO-DATA CHECK: if the company or fund he names is not in FACTS.lookup or his holdings, use the NO-DATA SHAPE and write no "
                         "'decision' line, not even 'wait'.")
    if "loan" in tp:
        lines.append("SAFETY: borrowing to buy shares is a plain no, whatever the market does; give no condition under which it becomes fine.")
    if "tip" in tp:
        lines.append("SAFETY: say no; tell him to check the adviser's SEBI registration (SEBI Check) and pay only to @valid UPI handles, and to "
                     "report the group to SEBI; no Ananta test or practice-book numbers here.")
    for k in ("beginner", "pcr", "broad"):
        if k in tp:
            lines.append(EXTRA_LINES[k])
    if h in ("long_term", "personal_finance") and re.search(r"\b(option|f&o|fno|20% in options|options share)\b", text or "", re.I):
        lines.append(EXTRA_LINES["options_sleeve"])
    out = {"horizon": h or "not stated", "decision_asked": decision_asked(text), "book_question": book_question(text), "lines": lines}
    if "rupee_holdings" in tp:
        hold = [x.get("symbol") for x in ((f.get("account_allocation") or {}).get("holdings_ranked") or []) if x.get("symbol")]
        out["rupee_sensitivity"] = {"note": "general knowledge about each business, not an Ananta test; say it that way",
                                    "holdings": rupee_lines(hold or list(RUPEE_SENSITIVITY))}
    return out


# ------------------------------------------------------------------------------------------------------------------------------ sessions
def _holidays() -> set[dt.date]:
    for name in ("nse_holidays.json", "nse_holidays_2026.json"):
        p = DATA / "manifests" / name
        try:
            d = json.loads(p.read_text())
            return {dt.datetime.strptime(x["tradingDate"], "%d-%b-%Y").date() for x in d.get("CM", [])}
        except (OSError, ValueError, KeyError, TypeError):
            continue
    return set()


def next_session_after(day: str | dt.date | None) -> dt.date | None:
    """The NSE trading day after `day` (weekends and NSE holidays skipped, from the records' holiday master)."""
    if not day:
        return None
    d = day if isinstance(day, dt.date) else dt.date.fromisoformat(str(day)[:10])
    hol = _holidays()
    d += dt.timedelta(days=1)
    while d.weekday() >= 5 or d in hol:
        d += dt.timedelta(days=1)
    return d


def day_words(d) -> str:
    try:
        x = d if isinstance(d, dt.date) else dt.date.fromisoformat(str(d)[:10])
        return f"{x:%a} {x.day} {x:%b}"
    except (TypeError, ValueError):
        return str(d)
