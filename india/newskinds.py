"""The kinds of company news, by keyword (NC1, Madhav, 25 Nov 2026: "what are the most effective news for the Indian market ... use some keywords
to analyze ... what are the main influencing keywords, sometimes for market gainers or market losers").

One fixed dictionary, written before any outcome was looked at (registrations/nc1_v1.json freezes it by its sha256). It reads an NSE announcement's
category and the first 400 characters of its subject text, lower-cased, and returns the news kinds it matches (an announcement can match several).
Used by the NC1 study on history (india/nc1.py) and by the live "movers and their news" line (india/movernews.py), so both read the news the same way.

  from india import newskinds
  newskinds.kinds("Financial Result Updates", "XYZ Ltd has informed the Exchange regarding Financial Results for the quarter ended ...")  -> ['results']
  newskinds.routine(category, text)  -> True for notices that are not company news (lost share certificates, trading window, newspaper copies ...)

No trading rule reads this module. Nothing here places an order.
"""
from __future__ import annotations

import re

# Notices that are not company news: never a kind, and a stock-day with only these counts as a day without news.
ROUTINE_CATEGORIES = {
    "loss of share certificates", "loss of share certificate", "trading window", "copy of newspaper publication", "newspaper advertisements",
    "certificate under sebi (depositories and participants) regulations, 2018", "book closure", "record date", "agm/book closure",
    "shareholders meeting", "annual general meeting updates", "duplicate share certificate", "issue of duplicate share certificates",
    "compliances-certificate under reg. 74 (5) of sebi (dp) regulations, 2018", "price movement", "clarification - financial results",
}
# An exchange query about a price move follows the move; it is never treated as the news behind it.
ROUTINE_TEXT = re.compile(r"(loss of share certificate|duplicate share certificate|closure of trading window|trading window|newspaper publication|"
                          r"newspaper advertisement|clarification sought|sought clarification|price movement|movement in price|regulation 74\(5\))")

_FDA = r"(usfda|us fda|u\.s\. fda|food and drug administration|\bfda\b)"
KINDS: dict[str, dict] = {
    "results": {"what": "quarterly or annual financial results",
                "cat": r"financial result", "text": r"(financial results?\b|audited results|unaudited results)"},
    "order_win": {"what": "a new order, contract or award won",
                  "text": r"(\border(s)?\b|letter of award|\bloa\b|letter of intent|\bloi\b|\bcontract(s)?\b|work order|purchase order)",
                  "and": r"(receiv|bag|\bwin\b|\bwon\b|secur|awarded|award of|bagged)",
                  "not": r"(court|tribunal|nclt|sebi|order dated|order passed|interim order|\bitat\b|demand order|assessment order|tax order)"},
    "usfda_adverse": {"what": "a US drug regulator warning, import alert or inspection observations",
                      "text": _FDA, "and": r"(warning letter|import alert|form 483|\b483\b|observation|\boai\b|official action indicated)"},
    "usfda_approval": {"what": "a US drug regulator approval",
                       "text": _FDA, "and": r"(approv|\banda\b|clearance)", "not": r"(warning letter|import alert|form 483|\b483\b|observation)"},
    "rating_down": {"what": "a credit rating cut or a negative outlook",
                    "text": r"(rating|outlook)", "and": r"(downgrad|negative|watch with developing|revised downward|lowered)"},
    "rating_up": {"what": "a credit rating raised or a positive outlook",
                  "text": r"(rating|outlook)", "and": r"(upgrad|positive|revised upward|raised)", "not": r"(downgrad|negative)"},
    "fund_raising": {"what": "raising equity: a QIP, a rights issue or a preferential issue",
                     "text": r"(\bqip\b|qualified institution|rights issue|preferential (issue|allotment)|raising of funds|fund raising|fund-raising|warrants)"},
    "merger_acquisition": {"what": "an acquisition, merger, demerger, stake sale or joint venture",
                           "text": r"(acqui|merger|amalgamat|scheme of arrangement|demerg|stake sale|divest|joint venture|open offer|takeover)",
                           "not_cat": r"(disclosure under sebi takeover regulations|sast)"},
    "holding_change": {"what": "a disclosure of shares bought or sold by promoters or insiders",
                       "cat": r"(disclosure under sebi takeover regulations|\(sast\)|insider trading)"},
    "management_exit": {"what": "a resignation or exit of a chief executive, finance chief, managing or whole-time director, or chairman",
                        "text": r"(resign|cessation|steps down|stepped down)",
                        "and": r"(\bceo\b|\bcfo\b|managing director|\bmd\b|chief executive|chief financial|chairman|whole[- ]time director)"},
    "pledge_default": {"what": "pledged shares, an invoked pledge, a missed payment or insolvency",
                       "text": r"(pledge|invocation|encumbr|\bdefault\b|delay in (payment|servicing)|insolvency|\bnclt\b|\bcirp\b|\bibc\b)"},
    "regulatory_legal": {"what": "a penalty, search, show-cause notice, regulator order or court matter",
                         "text": r"(penalt|show cause|show-cause|search (and|&) seizure|income tax (search|survey|department)|raid|sebi order|"
                                 r"enforcement directorate|\bcbi\b|\bcourt\b|tribunal|arbitra|litigation|\bgst\b (demand|notice)|demand notice)"},
    "buyback": {"what": "a share buyback", "text": r"buy[- ]?back"},
    "dividend_bonus_split": {"what": "a dividend, bonus issue or share split", "cat": r"(dividend|bonus|split)",
                             "text": r"(dividend|bonus|stock split|sub-?division)"},
    "operations_up": {"what": "a new plant, capacity, launch or start of commercial production",
                      "text": r"(commission|commercial production|capacity|new plant|expansion|launch)"},
    "disruption": {"what": "a fire, accident, shutdown, strike, lockout, flood or cyber attack",
                   "text": r"(\bfire\b|explosion|accident|shutdown|shut down|\bstrike\b|lockout|lock-out|\bflood|cyber|ransomware|suspension of operations)"},
    "analyst_meet": {"what": "a scheduled analyst or investor meeting or presentation (routine: the control kind)",
                     "cat": r"(analysts/institutional investor meet|investor presentation|con\. call)"},
}
_C = {k: {f: re.compile(v[f]) for f in ("cat", "text", "and", "not", "not_cat") if f in v} for k, v in KINDS.items()}


def routine(category: str | None, text: str | None) -> bool:
    c = (category or "").strip().lower()
    return c in ROUTINE_CATEGORIES or bool(ROUTINE_TEXT.search((text or "")[:400].lower()))


def kinds(category: str | None, text: str | None) -> list[str]:
    """The news kinds an announcement matches (empty for routine notices and for news of no listed kind)."""
    c, t = (category or "").strip().lower(), (text or "")[:400].lower()
    if routine(c, t):
        return []
    out = []
    for k, r in _C.items():
        hit = bool(("cat" in r and r["cat"].search(c)) or ("text" in r and r["text"].search(t)))
        if hit and "and" in r and not r["and"].search(t):
            hit = False
        if hit and "not" in r and r["not"].search(t):
            hit = False
        if hit and "not_cat" in r and r["not_cat"].search(c):
            hit = False
        if hit:
            out.append(k)
    return out


def words(kind: str) -> str:
    return KINDS[kind]["what"]
