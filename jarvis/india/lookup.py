"""Look things up for the India Ask: any NSE stock or ETF, the sectors, gold, a mutual fund by name, and India's tax and market rules
(Madhav, 27 Oct 2026: "I asked a question about one mutual fund, which he didn't say, like he didn't have any data"; the outside review of 41
answers: "no price for TCS, Reliance, HDFC Bank ... the biggest gap").

Sources, all built by the records repo or fetched on demand:
  ~/ananta_data/india/manifests/quotebook.json        every liquid NSE stock and every ETF, sectors, broad indices, gold (india/quotebook.py, nightly)
  ~/ananta_data/india/manifests/quotebook_names.json  symbol -> company name, aliases
  ~/ananta_data/india/manifests/mf_schemes.json       every mutual fund scheme with its latest NAV (india/mfdata.py, nightly, from AMFI)
  https://api.mfapi.in/mf/<code>                      a scheme's full NAV history (free public mirror of AMFI), cached a day under mf_cache/
  ~/code/ananta-records/india/registrations/india_rules_facts.json   tax, SEBI and broker facts with as-of dates and sources

Use from ask.py:  f["lookup"] = lookup.facts_for(text)   (after facts(); only the blocks the question needs are filled)
"""
from __future__ import annotations

import datetime as dt
import json
import math
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, wait
from pathlib import Path

import requests

DATA = Path(os.getenv("ANANTA_INDIA_DATA", os.path.expanduser("~/ananta_data/india")))
MAN = DATA / "manifests"
RECORDS = Path(os.getenv("ANANTA_RECORDS", os.path.expanduser("~/code/ananta-records")))
RULES_FILE = RECORDS / "india" / "registrations" / "india_rules_facts.json"
CACHE = DATA / "mf_cache"
MFAPI = "https://api.mfapi.in/mf/{code}"
FUND_BUDGET_S = 6.0
_files: dict = {}

# capitals that are words or market terms, not tickers ("What is RSI?", "my SIP", "FII selling")
STOP_CAPS = {"I", "A", "OK", "NO", "YES", "RSI", "SIP", "SIPS", "ETF", "ETFS", "NSE", "BSE", "FII", "FIIS", "DII", "DIIS", "FPI", "VIX", "IPO", "IPOS", "GDP",
             "CPI", "RBI", "SEBI", "MF", "MFS", "NAV", "EPS", "PE", "PB", "ROE", "ROCE", "EBITDA", "USD", "INR", "US", "UK", "AI", "IT", "FMCG", "PSU", "PSUS",
             "LTCG", "STCG", "STT", "TDS", "GST", "FO", "MACD", "SMA", "EMA", "ATR", "OI", "PCR", "CE", "ATM", "OTM", "ITM", "FY", "YTD", "CAGR", "XIRR",
             "TER", "AMC", "KYC", "PAN", "UPI", "GTT", "OCO", "MIS", "CNC", "NRI", "HNI", "DMA", "EV", "NIFTY", "SENSEX", "BANKNIFTY", "MIDCAP", "SMALLCAP",
             "GIFT", "ELSS", "FOF", "SGB", "FD", "FDS", "PPF", "EPF", "NPS", "ULIP", "LIC", "TV", "CEO", "Q1", "Q2", "Q3", "Q4", "AUM", "NFO", "REIT", "INVIT",
             "OHLC", "VWAP", "ORB", "BTST", "STBT", "SL", "TP", "R", "DCF", "PEG", "ESG", "API", "ID", "PM", "AM", "IST", "EMI", "CRR", "SLR", "MPC", "WPI", "IIP"}
COMMON_WORDS = {"power", "capital", "finance", "financial", "energy", "steel", "bank", "industries", "india", "global", "infra", "motors", "auto",
                "chemicals", "pharma", "cement", "textiles", "ventures", "systems", "solutions", "services", "technologies", "holdings", "enterprises",
                "trust", "life", "general", "national", "united", "royal", "golden", "silver", "gold", "best", "star", "first", "prime", "future",
                "digital", "green", "smart", "titan", "sun", "sail", "page", "trent", "home", "one", "all", "bharat", "hindustan", "standard", "premier"}
SECTOR_Q = re.compile(r"\b(sectors?|sectoral|which (?:industr|theme)|strongest|weakest|leading|lagging|rotation|small ?caps?|mid ?caps?|broad market)\b", re.I)
GOLD_Q = re.compile(r"\b(gold|silver|sgb|bullion)\b", re.I)
FUND_Q = re.compile(r"\b(fund|funds|mutual|mf|sip|sips|scheme|nav|elss|fof|flexi ?cap|multi ?cap|index fund|direct plan|regular plan|amc)\b", re.I)
FUND_STOP = {"fund", "funds", "mutual", "mf", "plan", "direct", "regular", "growth", "option", "idcw", "dividend", "payout", "reinvestment", "the", "of",
             "a", "an", "my", "his", "her", "friend", "friends", "is", "it", "good", "bad", "to", "hold", "should", "i", "he", "she", "sip", "in", "for",
             "and", "or", "how", "has", "done", "what", "about", "this", "that", "know", "want", "status", "pl", "scheme", "limited", "ltd", "management",
             "company", "invest", "investing", "buy", "sell", "continue", "stop", "years", "year", "for", "with", "on", "do", "does", "doing", "me", "tell",
             "ananta", "sir", "uh", "um", "like", "can", "you", "check", "now", "right", "hash", "name", "given", "here", "think", "so", "not", "sure",
             "though", "be", "are", "was", "were", "worth", "keep", "running", "since", "started", "holding", "holds", "has", "have", "whether"}
BENCH = {"nifty50": ("UTI Nifty 50 Index Fund", 120716, "Nifty 50"), "nifty500": ("Motilal Oswal Nifty 500 Index Fund", 147625, "Nifty 500"),
         "midcap150": ("Motilal Oswal Nifty Midcap 150 Index Fund", None, "Nifty Midcap 150"),
         "smallcap250": ("Motilal Oswal Nifty Smallcap 250 Index Fund", None, "Nifty Smallcap 250"),
         "gold": ("Nippon India ETF Gold BeES", 140088, "gold (Nippon India Gold BeES ETF)")}


# ------------------------------------------------------------------------------------------------------------------------------ files
def _load(path: Path):
    try:
        m = path.stat().st_mtime
    except OSError:
        return None
    c = _files.get(str(path))
    if c and c[0] == m:
        return c[1]
    try:
        obj = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    _files[str(path)] = (m, obj)
    return obj


def _qb() -> dict:
    return _load(MAN / "quotebook.json") or {}


def _names() -> dict:
    return _load(MAN / "quotebook_names.json") or {}


def _dw(d) -> str:
    try:
        x = dt.date.fromisoformat(str(d)[:10])
        return f"{x:%a} {x.day} {x:%b}"
    except (TypeError, ValueError):
        return str(d)


def _pc(x, nd=1) -> str:
    return "n/a" if x is None else f"{x * 100:+.{nd}f}%"


def _rs(x) -> str:
    return "n/a" if x is None else f"Rs {x:,.2f}"


# ------------------------------------------------------------------------------------------------------------------------------ stocks
def _alias_index() -> list[tuple[str, str]]:
    key = "_alias_index"
    names = _names()
    c = _files.get(key)
    if c and c[0] == id(names):
        return c[1]
    quotes = _qb().get("quotes") or {}
    out = []
    for sym, e in names.items():
        for a in e.get("aliases") or []:
            if len(a) >= 2 and a not in ("vi",):
                out.append((a.lower(), sym))
        if sym in quotes:
            n = e.get("norm") or ""
            w = n.split()
            if len(w) >= 2 and len(n) >= 6:
                out.append((n, sym))
                if len(w) >= 3 and w[0] not in COMMON_WORDS and w[1] not in COMMON_WORDS:
                    out.append((" ".join(w[:2]), sym))
            elif len(w) == 1 and len(n) >= 5 and n not in COMMON_WORDS:
                out.append((n, sym))
    out.sort(key=lambda t: -len(t[0]))                       # longest phrase first: "tata motors" before "tata"
    _files[key] = (id(names), out)
    return out


def find_names(text: str, limit: int = 5) -> list[str]:
    """Stock and ETF symbols named in the text: tickers in capitals (not market words), the curated aliases ("tata motors", "hdfc bank",
    "gold bees"), and liquid companies' own names ("tata consultancy services", "infosys"). Ordered by where they appear."""
    if not text:
        return []
    names, quotes = _names(), (_qb().get("quotes") or {})
    hits: dict[str, int] = {}
    for m in re.finditer(r"(?<![A-Za-z0-9&-])([A-Z][A-Z0-9&-]{1,15})(?![A-Za-z0-9&-])", text):
        t = m.group(1)
        if t not in STOP_CAPS and (t in quotes or t in names):
            hits.setdefault(t, m.start())
    low = " " + re.sub(r"[^a-z0-9& ]", " ", text.lower().replace("’", "'").replace("'s", "")) + " "
    low = re.sub(r"\s+", " ", low)
    taken = []                                                # (start, end, phrase): a longer phrase owns its words
    for phrase, sym in _alias_index():
        if len(hits) >= limit * 2:
            break
        i = low.find(" " + phrase + " ")
        if i < 0:
            continue
        clash = [t for t in taken if t[0] <= i < t[1] or i <= t[0] < i + len(phrase) + 1]
        if not clash or all(t[2] == phrase for t in clash):  # the same words naming two companies ("tata motors": TMCV and TMPV) give both
            hits.setdefault(sym, i)
            taken.append((i, i + len(phrase) + 1, phrase))
    return [s for s, _ in sorted(hits.items(), key=lambda kv: kv[1])][:limit]


def _quote_words(q: dict) -> str:
    nm = q.get("name") or q.get("symbol")
    bits = [f"{q['symbol']} ({nm}) closed {_rs(q.get('close'))} on {_dw(q.get('as_of'))} ({_pc(q.get('chg_1d'))} on the day)"]
    ch = [f"{lab} {_pc(q.get(k))}" for lab, k in (("1 week", "chg_1w"), ("1 month", "chg_1m"), ("3 months", "chg_3m"), ("this year", "chg_ytd"), ("1 year", "chg_1y"))
          if q.get(k) is not None]
    if ch:
        bits.append("changes: " + ", ".join(ch))
    nf = _qb().get("nifty") or {}
    if q.get("chg_ytd") is not None and nf.get("chg_ytd") is not None:   # 27 Oct re-grade: "Reliance vs the Nifty this year" was left unanswered
        gap = q["chg_ytd"] - nf["chg_ytd"]
        bits.append(f"this year {'ahead of' if gap > 0 else 'behind'} the Nifty ({_pc(nf['chg_ytd'])} this year) by {abs(gap) * 100:.1f} points")
    if q.get("vs_nifty_1y") is not None:
        bits.append(f"{'ahead of' if q['vs_nifty_1y'] > 0 else 'behind'} the Nifty by {abs(q['vs_nifty_1y']) * 100:.1f} points over 1 year")
    if q.get("vs_high_52w") is not None:
        bits.append(f"{abs(q['vs_high_52w']) * 100:.0f}% below its 52-week high of {_rs(q.get('high_52w'))}")
    av = [f"{'above' if (q.get(f'vs_sma{n}') or 0) > 0 else 'below'} its {n}-day average ({_pc(q.get(f'vs_sma{n}'))})" for n in (50, 200) if q.get(f"vs_sma{n}") is not None]
    if av:
        bits.append(", ".join(av))
    if q.get("rsi14") is not None:
        bits.append(f"RSI {q['rsi14']:.0f}")
    if q.get("vol_60d") is not None:
        bits.append(f"swings about {q['vol_60d'] * 100:.0f}% a year")
    b = q.get("biggest_day_60d") or {}
    if b.get("move") is not None and abs(b["move"]) >= 0.08:
        bits.append(f"its biggest day in 60 sessions was {_pc(b['move'])} on {_dw(b.get('date'))}, which inflates that swing figure")
    s = "; ".join(bits) + "."
    if q.get("price_jump_unadjusted"):
        j = q.get("price_jump") or {}
        when = f" on {_dw(j['date'])} {j['date'][:4]} ({_pc(j.get('move'), 0)})" if j.get("date") else ""
        s += (f" Caution: the price history has a one-day move of more than 35%{when} that looks like a corporate action (demerger, split or "
              "bonus) not adjusted, so changes and averages over periods that include that day are unreliable.")
    return s


def quote_facts(symbols: list[str]) -> dict:
    """Compact dated facts per symbol from the quote book; a known but thinly traded or unknown symbol says so."""
    qb, names = _qb(), _names()
    quotes = qb.get("quotes") or {}
    out = {}
    for s in symbols:
        q = quotes.get(s)
        if q:
            keep = ("symbol", "name", "kind", "industry", "as_of", "close", "chg_1d", "chg_1m", "chg_3m", "chg_ytd", "chg_1y", "vs_nifty_1y",
                    "high_52w", "vs_high_52w", "vs_sma200", "rsi14", "vol_60d", "price_jump")   # the rest is in words: the prompt stays small
            out[s] = {**{k: q.get(k) for k in keep if q.get(k) is not None}, "words": _quote_words(q)}
        elif s in names:
            out[s] = {"symbol": s, "name": names[s].get("name"), "status": "thin",
                      "words": f"{s} ({names[s].get('name')}) is listed on NSE but trades too thinly to track here (under Rs 1 crore a day), or not in the last ten days."}
        else:
            out[s] = {"symbol": s, "status": "unknown", "words": f"No NSE stock or ETF called {s} in the quote book."}
    return out


# ------------------------------------------------------------------------------------------------------------------------------ sectors, gold
def sector_facts() -> dict:
    qb = _qb()
    sec, broad = qb.get("sectors") or [], qb.get("broad") or []
    if not sec:
        return {"status": "missing", "words": "The sector ranking is not built yet."}
    top, bot = sec[:3], sec[-3:]
    w = ("Sectors by their 3-month change as of " + _dw(sec[0].get("as_of")) + ": strongest " + ", ".join(f"{s['name']} {_pc(s['chg_3m'])}" for s in top)
         + "; weakest " + ", ".join(f"{s['name']} {_pc(s['chg_3m'])}" for s in bot) + f" (Nifty 50 {_pc((qb.get('nifty') or {}).get('chg_3m'))}).")
    sc = {b["index"]: b for b in broad}
    mid, small = sc.get("NIFTY MIDCAP 150"), sc.get("NIFTY SMLCAP 250")
    if mid and small:
        w += (f" Mid caps (Nifty Midcap 150) are {abs(mid['vs_high_52w']) * 100:.0f}% below their 52-week high and {_pc(mid['chg_1y'])} over 1 year; "
              f"small caps (Nifty Smallcap 250) are {abs(small['vs_high_52w']) * 100:.0f}% below their 52-week high and {_pc(small['chg_1y'])} over 1 year.")
    # the longer window: the total-return series since 2015 shows the fall from the real peak, not only from the 52-week high
    ath = []
    for key, label in (("midcap150", "mid caps"), ("smallcap250", "small caps")):
        s = _tri(key)
        if s:
            pk = max(s, key=lambda t: t[1])
            ath.append(f"{label} {abs(s[-1][1] / pk[1] - 1) * 100:.0f}% below their peak of {pk[0].day} {pk[0]:%b %Y}")
    if ath:
        w += " Measured with dividends since 2015: " + ", ".join(ath) + "."
    def brief(v):
        return {k: v.get(k) for k in ("name", "chg_1m", "chg_3m", "chg_1y", "vs_sma200", "vs_high_52w") if v.get(k) is not None}
    return {"status": "ok", "as_of": sec[0].get("as_of"), "sectors_by_3m": [brief(s) for s in sec], "broad": [brief(b) for b in broad], "words": w,
            "note": "say which window a fall is measured over: '52-week high' (price, about 15 months of data) or 'peak since 2015' (total-return index); "
                    "Ananta's test of 'the strongest sectors keep leading' did not hold, so a ranking describes, it does not pick"}


def gold_facts() -> dict:
    g = (_qb().get("gold") or {})
    if not g:
        return {"status": "missing", "words": "No gold price is built yet."}
    parts = []
    for metal in ("gold", "silver"):
        x = g.get(metal)
        if x:
            parts.append(f"{metal.title()} in rupees (via {x['symbol']}, {_dw(x['as_of'])}): 1 month {_pc(x.get('chg_1m'))}, 3 months {_pc(x.get('chg_3m'))}, "
                         f"this year {_pc(x.get('chg_ytd'))}, 1 year {_pc(x.get('chg_1y'))}, {abs((x.get('vs_high_52w') or 0)) * 100:.0f}% below its 52-week high")
    return {"status": "ok", **g, "words": "; ".join(parts) + ".", "note": (_qb().get("gold_note") or "")}


# ------------------------------------------------------------------------------------------------------------------------------ mutual funds
def _schemes() -> list[dict]:
    j = _load(MAN / "mf_schemes.json") or {}
    return j.get("rows") or []


# words that name a kind of fund, not a fund: a question about "a Nifty 50 index fund" is not about Axis's or Choice's
GENERIC_FUND = {"nifty", "50", "100", "150", "250", "500", "next", "index", "flexicap", "multicap", "midcap", "smallcap", "largecap", "large", "mid",
                "small", "cap", "gold", "silver", "etf", "etfs", "fof", "elss", "tax", "saver", "value", "focused", "contra", "equity", "debt", "liquid",
                "hybrid", "balanced", "advantage", "dynamic", "arbitrage", "overnight", "money", "market", "short", "long", "term", "duration", "income",
                "savings", "opportunities", "india", "bank", "banking", "of", "us", "global", "international", "active", "passive", "better", "than",
                "best", "top", "sensex", "bse", "nse", "total", "return", "plus", "growth", "pharma", "healthcare", "technology", "infrastructure",
                "consumption", "psu", "and", "one", "new", "sip", "lump", "sum", "lumpsum", "nav", "bees", "returns", "why", "which", "who", "when"}
# old names people still use, mapped to the renamed scheme
FUND_RENAMES = [(r"\bemerging blue ?chip\b", "large and midcap"), (r"(?<!us )\bblue ?chip\b", "large cap"), (r"\bhdfc top 100\b", "hdfc large cap")]


def _amc_tokens() -> set:
    c = _files.get("_amc_tokens")
    rows = _schemes()
    if c and c[0] == id(rows):
        return c[1]
    t = set()
    for amc in {r["amc"] for r in rows}:
        t |= {x for x in _toks(amc) if x not in GENERIC_FUND and x not in {"mutual", "fund", "the", "asset", "financial", "capital", "finserv", "life",
                                                                          "sun", "company", "wealth", "trust", "union", "choice"} and len(x) >= 3}
    _files["_amc_tokens"] = (id(rows), t)
    return t


def _toks(s: str) -> list[str]:
    s = s.lower().replace("&", " and ").replace("’", "'")
    s = re.sub(r"\bflexi\s*cap\b", "flexicap", s)
    s = re.sub(r"\bmulti\s*cap\b", "multicap", s)
    s = re.sub(r"\bmid\s*cap\b", "midcap", s)
    s = re.sub(r"\bsmall\s*cap\b", "smallcap", s)
    s = re.sub(r"\blarge\s*cap\b", "largecap", s)
    s = re.sub(r"\bnifty\s*bees\b", "niftybees", s)
    s = re.sub(r"\bgold\s*bees\b", "goldbees", s)
    return [t for t in re.findall(r"[a-z0-9]+", s)]


def find_funds(text: str, limit: int = 2) -> list[dict]:
    """Mutual fund schemes named in the text, matched on the scheme name and fund house (AMFI's list). When the plan is not said, the Direct
    plan with the Growth option is taken, and the answer says it assumed that."""
    if not text or not FUND_Q.search(text) and not re.search(r"\b(bees|ppfas|parikh)\b", text, re.I):
        return []
    rows = _schemes()
    if not rows:
        return []
    qtext = text.lower()
    for pat, rep in FUND_RENAMES:
        qtext = re.sub(pat, rep, qtext)
    q = [t for t in _toks(qtext) if t not in FUND_STOP and len(t) > 1]
    if not q or all(t in GENERIC_FUND for t in q):
        return []
    qs = set(q)
    groups: dict[tuple, list] = {}
    for r in rows:
        groups.setdefault((r["amc"], r["name"].strip().lower()), []).append(r)
    scored = []
    for (amc, nm), rs in groups.items():
        st = set(t for t in _toks(nm) if t not in FUND_STOP) | set(t for t in _toks(amc) if t not in {"mutual", "fund", "amc"})
        if not st:
            continue
        hit = qs & st
        if not hit or all(t in GENERIC_FUND for t in hit):   # at least one fund-house or distinctive name word
            continue
        name_t = set(t for t in _toks(nm) if t not in FUND_STOP)
        cover = len(hit & name_t) / max(1, len(name_t))
        score = cover + 0.15 * len(hit) - 0.02 * len(name_t - qs)
        if len(hit) >= 2 or (len(hit) == 1 and cover == 1.0 and len(name_t) <= 2 and len(next(iter(hit))) >= 5):
            scored.append((score, len(hit), nm, rs))
    if not scored:
        return []
    scored.sort(key=lambda t: (-t[0], -t[1]))
    want_reg = bool(re.search(r"\bregular\b", text, re.I))
    want_idcw = bool(re.search(r"\b(idcw|dividend)\b", text, re.I))
    out, seen = [], set()
    for score, nh, nm, rs in scored:
        if len(out) >= limit or (out and score < scored[0][0] - 0.2):
            break
        if nm in seen:
            continue
        seen.add(nm)
        plan = "Regular" if want_reg else "Direct"
        opt = "IDCW" if want_idcw else "Growth"
        pick = next((r for r in rs if r["plan"] == plan and r["option"] == opt), None) or next((r for r in rs if r["plan"] == plan), None) or rs[0]
        sib = next((r for r in rs if r["plan"] != pick["plan"] and r["option"] == pick["option"] and r["plan"]), None)
        out.append({"code": pick["code"], "name": pick["name"], "amc": pick["amc"], "category": pick["category"], "plan": pick["plan"], "option": pick["option"],
                    "nav": pick["nav"], "nav_date": pick["date"], "sibling_code": sib["code"] if sib else None, "sibling_plan": sib["plan"] if sib else None,
                    "assumed_plan": not (want_reg or re.search(r"\bdirect\b", text, re.I)), "assumed_option": not (want_idcw or re.search(r"\bgrowth\b", text, re.I)),
                    "match_score": round(score, 2)})
    return out


def _parse_hist(j: dict) -> list[tuple[dt.date, float]] | None:
    out = []
    for row in (j or {}).get("data") or []:
        try:
            out.append((dt.datetime.strptime(row["date"], "%d-%m-%Y").date(), float(row["nav"])))
        except (KeyError, ValueError, TypeError):
            continue
    out.sort()
    return _split_adjust(out) or None


def _split_adjust(navs):
    """ETFs split their units (SBI Gold ETF, Gold BeES): the NAV drops 90%+ overnight and returns read as a crash. A real fund never moves 5x in a
    day, so a jump like that is a split: scale everything before it by the jump."""
    if not navs:
        return navs
    out = list(navs)
    for i in range(len(out) - 1, 0, -1):
        a, b = out[i - 1][1], out[i][1]
        if a > 0 and b > 0 and (b / a < 0.2 or b / a > 5):
            k = b / a
            out[:i] = [(d, v * k) for d, v in out[:i]]
    return out


def _cached_nav(code: int, max_age_days: int | None = 0):
    """The cached history if it was fetched within max_age_days (None: any age), else None."""
    p = CACHE / f"{code}.json"
    try:
        c = json.loads(p.read_text())
        age = (dt.date.today() - dt.date.fromisoformat(c["fetched"])).days
    except (OSError, ValueError, KeyError, TypeError):
        return None
    if max_age_days is not None and age > max_age_days:
        return None
    return _parse_hist(c.get("body"))


def _fetch_nav(code: int) -> list[tuple[dt.date, float]] | None:
    """Fetch a scheme's full NAV history from mfapi.in and cache it for the day."""
    r = requests.get(MFAPI.format(code=code), timeout=FUND_BUDGET_S)
    r.raise_for_status()
    j = r.json()
    navs = _parse_hist(j)
    if navs:
        CACHE.mkdir(parents=True, exist_ok=True)
        tmp = CACHE / f".{code}.json.tmp"
        tmp.write_text(json.dumps({"fetched": dt.date.today().isoformat(), "body": j}))
        tmp.replace(CACHE / f"{code}.json")
    return navs


def _amfi_latest(code: int):
    by = _files.get("_amfi_by_code")
    rows = _schemes()
    if not by or by[0] != id(rows):
        by = (id(rows), {r["code"]: r for r in rows})
        _files["_amfi_by_code"] = by
    r = by[1].get(code)
    try:
        return (dt.date.fromisoformat(r["date"]), float(r["nav"])) if r else None
    except (TypeError, ValueError, KeyError):
        return None


def _with_amfi(code: int, navs):
    """mfapi lags AMFI by about a day: add AMFI's newer NAV when there is one."""
    a = _amfi_latest(code)
    if navs and a and a[0] > navs[-1][0] and a[1] > 0:
        return navs + [a]
    return navs


def _nav_on(navs, d: dt.date):
    """The NAV on d or the last one before it."""
    lo, hi = 0, len(navs) - 1
    if navs[0][0] > d:
        return None
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if navs[mid][0] <= d:
            lo = mid
        else:
            hi = mid - 1
    return navs[lo]


def _cagr(navs, years: float):
    end = navs[-1]
    start = _nav_on(navs, end[0] - dt.timedelta(days=round(365.25 * years)))
    if not start or (end[0] - start[0]).days < 365.25 * years - 10:
        return None
    return (end[1] / start[1]) ** (1 / years) - 1 if years >= 1 else end[1] / start[1] - 1


def _xirr(flows: list[tuple[dt.date, float]]):
    if not flows:
        return None
    t0 = flows[0][0]

    def npv(r):
        return sum(v / (1 + r) ** ((d - t0).days / 365.25) for d, v in flows)
    lo, hi = -0.99, 10.0
    f_lo, f_hi = npv(lo), npv(hi)
    if f_lo * f_hi > 0:
        return None
    for _ in range(100):
        mid = (lo + hi) / 2
        f = npv(mid)
        if abs(f) < 1e-7:
            break
        if f_lo * f < 0:
            hi, f_hi = mid, f
        else:
            lo, f_lo = mid, f
    return mid


def _sip_xirr(navs, years: int, amount: float = 1000.0):
    end = navs[-1][0]
    start = end - dt.timedelta(days=round(365.25 * years))
    if navs[0][0] > start + dt.timedelta(days=10):
        return None
    units, flows = 0.0, []
    for i in range(12 * years):
        y, m = divmod(start.month - 1 + i, 12)
        d = dt.date(start.year + y, m + 1, min(start.day, 28))
        nx = _first_on_or_after(navs, d)
        if not nx or nx[0] > end:
            break
        units += amount / nx[1]
        flows.append((nx[0], -amount))
    if not flows:
        return None
    flows.append((end, units * navs[-1][1]))
    return _xirr(flows)


def _first_on_or_after(navs, d):
    lo, hi = 0, len(navs)
    while lo < hi:
        mid = (lo + hi) // 2
        if navs[mid][0] < d:
            lo = mid + 1
        else:
            hi = mid
    return navs[lo] if lo < len(navs) else None


def _drawdown(navs):
    peak, worst, wdate, pdate, wpeak = navs[0][1], 0.0, None, navs[0][0], None
    for d, v in navs:
        if v > peak:
            peak, pdate = v, d
        dd = v / peak - 1
        if dd < worst:
            worst, wdate, wpeak = dd, d, pdate
    return worst, wpeak, wdate


def _vol(navs, years=3):
    start = navs[-1][0] - dt.timedelta(days=round(365.25 * years))
    xs = [v for d, v in navs if d >= start]
    if len(xs) < 120:
        return None
    rets = [xs[i] / xs[i - 1] - 1 for i in range(1, len(xs))]
    m = sum(rets) / len(rets)
    return math.sqrt(sum((r - m) ** 2 for r in rets) / (len(rets) - 1)) * math.sqrt(252)


def _metrics(navs) -> dict:
    dd, pk, tr = _drawdown(navs)
    return {"first_date": navs[0][0].isoformat(), "latest_date": navs[-1][0].isoformat(), "latest_nav": navs[-1][1],
            "ret_1y": _cagr(navs, 1), "cagr_3y": _cagr(navs, 3), "cagr_5y": _cagr(navs, 5),
            "cagr_since_launch": (navs[-1][1] / navs[0][1]) ** (365.25 / max(1, (navs[-1][0] - navs[0][0]).days)) - 1 if (navs[-1][0] - navs[0][0]).days > 365 else None,
            "worst_drawdown": dd, "worst_drawdown_from": pk.isoformat() if pk else None, "worst_drawdown_to": tr.isoformat() if tr else None,
            "vol_3y": _vol(navs), "sip_xirr_3y": _sip_xirr(navs, 3), "sip_xirr_5y": _sip_xirr(navs, 5)}


def _bench_key(fund: dict) -> str | None:
    c, n = (fund.get("category") or "").lower(), (fund.get("name") or "").lower()
    if "gold" in c or "gold" in n:
        return "gold"
    if any(k in c for k in ("debt", "liquid", "income", "money market", "gilt", "overnight", "arbitrage", "hybrid", "solution", "duration", "credit",
                            "banking and psu", "floater")):
        return None
    if "small cap" in c or "smallcap" in n:
        return "smallcap250"
    if "mid cap" in c and "large" not in c or "midcap" in n.replace(" ", ""):
        return "midcap150"
    if re.search(r"\bnifty ?500\b", n):
        return "nifty500"
    if "large cap" in c and "mid" not in c or re.search(r"\bnifty ?50\b(?!0)|\bnifty ?bees\b", n):
        return "nifty50"
    if "equity" in c or "index" in c or "elss" in c or "fof" in c or "etf" in c:
        return "nifty500"
    return None


def _bench_code(key: str) -> int | None:
    name, code, _ = BENCH[key]
    if code:
        return code
    for r in _schemes():
        if r["name"].lower() == name.lower() and r["plan"] == "Direct" and r["option"] == "Growth":
            return r["code"]
    return None


TRI_KEYS = {"nifty50": "NIFTY 50", "nifty500": "NIFTY 500", "midcap150": "NIFTY MIDCAP 150", "smallcap250": "NIFTY SMLCAP 250"}


def _tri(key: str, until: str | None = None) -> list[tuple[dt.date, float]] | None:
    """The total-return index (dividends included) for an equity benchmark, cut at the fund's own latest NAV date, so both are measured to the
    same day (27 Oct outside re-grade: a price index and mismatched end dates made an index fund look 1 point behind its ETF)."""
    j = _load(CACHE / "tri.json") or {}
    rows = (j.get("series") or {}).get(TRI_KEYS.get(key, ""))
    if not rows:
        return None
    out = [(dt.date.fromisoformat(d), float(v)) for d, v in rows if not until or d <= until]
    return out if len(out) > 300 else None


def _own_gold_etf(fund: dict) -> dict | None:
    """A gold fund of funds holds its own fund house's gold ETF: compare it with that ETF, not with another house's (SBI Gold Fund -> SBI Gold ETF)."""
    n = (fund.get("name") or "").lower()
    if "gold" not in n or "etf" in n or "fof" not in (fund.get("category") or "").lower() and "fund" not in n:
        return None
    amc = (fund.get("amc") or "").lower()
    best = None
    for r in _schemes():
        if r["amc"].lower() == amc and "gold" in r["name"].lower() and "etf" in (r["category"] + r["name"]).lower() and "fund" not in r["name"].lower():
            best = r
            break
    return best


_POOL = None


def _pool() -> ThreadPoolExecutor:
    global _POOL
    if _POOL is None:
        _POOL = ThreadPoolExecutor(max_workers=6, thread_name_prefix="mfapi")
    return _POOL


def _ret_words(head: str, m: dict) -> str:
    bits = []
    if m.get("ret_1y") is not None:
        bits.append(f"1 year {_pc(m['ret_1y'])}")
    for n in (3, 5):
        if m.get(f"cagr_{n}y") is not None:
            bits.append(f"{n} years {_pc(m[f'cagr_{n}y'])} a year")
    return f"{head}: " + ", ".join(bits) if bits else ""


def fund_facts(funds: list[dict]) -> dict:
    """For each fund from find_funds: returns, SIP returns, worst fall, swings, the index comparison and the Direct-Regular cost gap, from the
    NAV history (mfapi.in, cached a day). Never waits more than about FUND_BUDGET_S seconds; on failure the latest NAV from AMFI is still given."""
    jobs = {}
    for f in funds:
        jobs[("fund", f["code"])] = f["code"]
        if f.get("sibling_code"):
            jobs[("sib", f["code"])] = f["sibling_code"]
        bk = _bench_key(f)
        own = _own_gold_etf(f) if bk == "gold" else None
        if own:
            f["_own_etf"] = own
            jobs[("bench", f"own:{f['code']}")] = own["code"]
        elif bk and not (bk in TRI_KEYS and _tri(bk)) and _bench_code(bk):
            jobs[("bench", bk)] = _bench_code(bk)
    res, fut = {}, {}
    t0 = time.time()
    for k, code in jobs.items():                             # today's cache for the fund; up to a week old for comparisons
        c = _cached_nav(code, 0 if k[0] == "fund" else 7)
        if c:
            res[k] = c
        else:
            fut[_pool().submit(_fetch_nav, code)] = k
    if fut:
        done, _ = wait(list(fut), timeout=FUND_BUDGET_S)     # unfinished fetches keep running and warm the cache for next time
        for fu in done:
            try:
                res[fut[fu]] = fu.result()
            except Exception as e:  # noqa: BLE001
                res[fut[fu]] = e
    for k, code in jobs.items():
        if not res.get(k) or isinstance(res.get(k), Exception):
            res[k] = _cached_nav(code, None) or res.get(k)  # an older cache beats nothing
        if res.get(k) and not isinstance(res[k], Exception):
            res[k] = _with_amfi(code, res[k])
    out = {}
    for f in funds:
        navs = res.get(("fund", f["code"]))
        base = {k: f.get(k) for k in ("code", "name", "amc", "category", "plan", "option", "nav", "nav_date", "assumed_plan", "assumed_option")}
        is_etf = "etf" in (f.get("category") or "").lower() or re.search(r"\betf\b|\bbees\b", (f.get("name") or "").lower())
        label = f"{f['name']} (an ETF, bought on the exchange; ETFs have no Direct or Regular plan)" if is_etf else \
            f"{f['name']} ({f['plan']} plan, {f['option'] or 'option not stated'})"
        if not navs or isinstance(navs, Exception):
            out[str(f["code"])] = {**base, "status": "history_unavailable",
                                    "words": f"{label}: latest NAV {f['nav']} on {_dw(f['nav_date'])} (AMFI). Its return history could not be fetched right now, so returns are not available this time."}
            continue
        m = _metrics(navs)
        e = {**base, "status": "ok", **{k: (round(v, 4) if isinstance(v, float) else v) for k, v in m.items()}}
        bk = _bench_key(f)
        own = f.get("_own_etf")
        if own:
            bn, bname, bvia = res.get(("bench", f"own:{f['code']}")), f"its own fund house's gold ETF ({own['name']})", \
                "the ETF this fund of funds holds: after its extra layer of cost the fund should trail it slightly, never beat it for long"
            if bn and not isinstance(bn, Exception):
                bn = [x for x in bn if x[0] <= navs[-1][0]]          # the same end date as the fund
        elif bk in TRI_KEYS and _tri(bk, navs[-1][0].isoformat()):
            bn, bname, bvia = _tri(bk, navs[-1][0].isoformat()), f"{BENCH[bk][2]} total-return index", \
                "the index with dividends reinvested (TRI), to the fund's own latest NAV date: the fair yardstick for a fund"
        else:
            bn = res.get(("bench", bk)) if bk else None
            bname, bvia = (BENCH[bk][2], BENCH[bk][0] + " (an index fund or ETF, after its own small cost; to its own latest date)") if bk else (None, None)
        if bn and not isinstance(bn, Exception) and len(bn) > 260:
            bm = _metrics(bn)
            e["benchmark"] = {"name": bname, "via": bvia, "end_date": bn[-1][0].isoformat(),
                              **{k: (round(bm[k], 4) if isinstance(bm[k], float) else bm[k]) for k in ("ret_1y", "cagr_3y", "cagr_5y", "sip_xirr_3y", "sip_xirr_5y", "worst_drawdown")}}
            idx = "index" in (f.get("category") or "").lower() or "etf" in (f.get("category") or "").lower() or "index" in (f.get("name") or "").lower()
            if idx and bk in TRI_KEYS and m.get("ret_1y") is not None and bm.get("ret_1y") is not None:
                e["tracking_difference_1y"] = round(m["ret_1y"] - bm["ret_1y"], 4)
        sb = res.get(("sib", f["code"]))
        if sb and not isinstance(sb, Exception):
            s1, s3 = _cagr(sb, 1), _cagr(sb, 3)
            gap1 = (m["ret_1y"] - s1) if (m["ret_1y"] is not None and s1 is not None) else None
            gap3 = (m["cagr_3y"] - s3) if (m["cagr_3y"] is not None and s3 is not None) else None
            if f["plan"] == "Regular":
                gap1, gap3 = (-gap1 if gap1 is not None else None), (-gap3 if gap3 is not None else None)
            e["direct_minus_regular"] = {"ret_1y": round(gap1, 4) if gap1 is not None else None, "cagr_3y": round(gap3, 4) if gap3 is not None else None,
                                         "meaning": "how much more the Direct plan earned a year than the Regular plan of the same scheme: roughly the Regular plan's extra cost"}
        e["expense_ratio"] = "not available here (AMFI publishes it only on an interactive page); the Direct-Regular gap shows the extra cost of the Regular plan"
        cat = re.sub(r"^(Equity|Debt|Hybrid|Other) Scheme - ", "", f.get("category") or "")
        w = [f"{label}, {cat}: NAV {m['latest_nav']:.2f} on {_dw(m['latest_date'])}"]
        w.append(_ret_words("returns", m))
        if m.get("sip_xirr_3y") is not None:
            w.append(f"a monthly SIP over 3 years earned {_pc(m['sip_xirr_3y'])} a year" + (f" (over 5 years {_pc(m['sip_xirr_5y'])} a year)" if m.get("sip_xirr_5y") is not None else ""))
        if e.get("benchmark"):
            w.append(_ret_words(f"{e['benchmark']['name']} for comparison (to the same date)", e["benchmark"]))
        if e.get("tracking_difference_1y") is not None:
            w.append(f"over 1 year it was {abs(e['tracking_difference_1y']) * 100:.2f} points {'behind' if e['tracking_difference_1y'] < 0 else 'ahead of'} "
                     "the total-return index it tracks (its tracking difference: smaller is better)")
        if f.get("_own_etf"):
            w.append("a gold fund of funds holds its fund house's gold ETF and adds its own cost on top, so it should trail that ETF a little; "
                     "for tax, a gold fund of funds counts as long-term only after 24 months")
        w.append(f"worst fall {_pc(m['worst_drawdown'], 0)} ({m['worst_drawdown_from'][:7]} to {m['worst_drawdown_to'][:7]})" if m.get("worst_drawdown_to") else "")
        if m.get("vol_3y") is not None:
            w.append(f"swings about {m['vol_3y'] * 100:.0f}% a year")
        if e.get("direct_minus_regular", {}).get("ret_1y") is not None:
            w.append(f"the Direct plan earned about {e['direct_minus_regular']['ret_1y'] * 100:.1f} points a year more than the Regular plan")
        if f.get("assumed_plan") or f.get("assumed_option"):
            w.append("(plan not stated, so the Direct plan with the Growth option is shown)")
        e["words"] = "; ".join(x for x in w if x) + "."
        out[str(f["code"])] = e
    return {"funds": out, "seconds": round(time.time() - t0, 1),
            "source": "AMFI NAVs (via mfapi.in history); returns are NAV-based, before tax; 3- and 5-year figures are yearly (CAGR); SIP = Rs 1,000 a month",
            "how_to_say_it": ("judge a fund on its returns against the index comparison over 3-5 years, its worst fall, its swings, the plan (Direct is "
                              "cheaper) and how it fits the person's goal and horizon; past returns do not promise future ones; Ananta has not tested funds")}


# ------------------------------------------------------------------------------------------------------------------------------ rules
def rules_facts(text: str, limit: int = 4) -> list[dict]:
    j = _load(RULES_FILE) or {}
    low = (text or "").lower()
    hits = []
    for f in j.get("facts") or []:
        n = sum(1 for t in f.get("topics") or [] if re.search(rf"(?<![a-z0-9]){re.escape(t)}(?![a-z0-9])", low))
        if n:
            hits.append((n, f))
    hits.sort(key=lambda t: -t[0])
    return [{k: f[k] for k in ("id", "fact", "as_of", "source")} for _, f in hits[:limit]]


IPO_Q = re.compile(r"\b(ipos?|initial public offer\w*|new listings?|public issues?|grey market|gmp)\b", re.I)
INDEX_FUND_Q = re.compile(r"\bnifty ?50 index fund\b|\bindex fund\b.*\bnifty ?50\b(?!0)", re.I)


def ipo_facts() -> dict:
    """NSE's current and upcoming IPOs, from the nightly public API copy (records india/lookupdata.py)."""
    j = _load(CACHE / "ipo.json") or {}
    if not j:
        return {"status": "missing", "words": "The IPO calendar has not been fetched yet."}
    cur, up = j.get("current") or [], j.get("upcoming") or []
    def one(x):
        bits = [x.get("companyName") or x.get("symbol") or "?"]
        if x.get("issueStartDate") or x.get("issueEndDate"):
            bits.append(f"open {x.get('issueStartDate', '?')} to {x.get('issueEndDate', '?')}")
        if x.get("priceBand") or x.get("issuePrice"):
            bits.append(f"price band {x.get('priceBand') or x.get('issuePrice')}")
        try:
            bits.append(f"subscribed {float(x['noOfTime']):.2f} times so far")
        except (KeyError, TypeError, ValueError):
            pass
        return ", ".join(bits)
    w = ("NSE IPOs (fetched " + str(j.get("built_at", ""))[:10] + "): open now: " + ("; ".join(one(x) for x in cur[:6]) or "none")
         + ". Upcoming: " + ("; ".join(one(x) for x in up[:6]) or "none listed") + ".")
    return {"status": "ok", "current": cur[:8], "upcoming": up[:8], "words": w,
            "note": "dates, price bands and subscription only; a real view needs the offer document (valuation against listed peers, what the money is "
                    "for, promoters selling or fresh issue); grey-market premiums are unofficial and unreliable; Ananta has not tested IPOs"}


# ------------------------------------------------------------------------------------------------------------------------------ all of it
def facts_for(text: str) -> dict:
    """Only the blocks this question needs: named stocks/ETFs, sectors, gold, named mutual funds, rules. {} when nothing applies."""
    out = {}
    try:
        syms = find_names(text)
        if syms:
            out["stocks"] = quote_facts(syms)
            out["stocks_as_of"] = (_qb().get("as_of"))
            nf = _qb().get("nifty") or {}
            if nf.get("close") and nf.get("chg_ytd") is not None:
                out["nifty"] = {k: nf.get(k) for k in ("as_of", "close", "chg_1m", "chg_3m", "chg_ytd", "chg_1y")} | {
                    "words": f"Nifty 50 {nf.get('close'):,.2f} on {_dw(nf.get('as_of'))}: this year {_pc(nf.get('chg_ytd'))}, 1 year {_pc(nf.get('chg_1y'))}, 3 months {_pc(nf.get('chg_3m'))}."}
    except Exception as e:  # noqa: BLE001  a lookup must never break the answer
        out["stocks_error"] = f"{type(e).__name__}"
    try:
        if SECTOR_Q.search(text or ""):
            out["sectors"] = sector_facts()
    except Exception as e:  # noqa: BLE001
        out["sectors_error"] = f"{type(e).__name__}"
    try:
        if GOLD_Q.search(text or ""):
            out["gold"] = gold_facts()
    except Exception as e:  # noqa: BLE001
        out["gold_error"] = f"{type(e).__name__}"
    try:
        if IPO_Q.search(text or ""):
            out["ipo"] = ipo_facts()
    except Exception as e:  # noqa: BLE001
        out["ipo_error"] = f"{type(e).__name__}"
    try:
        funds = find_funds(text)
        if INDEX_FUND_Q.search(text or "") and not any(f["code"] == BENCH["nifty50"][1] for f in funds):
            # "a Nifty 50 index fund" names no scheme: show one large Direct index fund as the example, so an ETF can be compared on the same basis
            r = next((x for x in _schemes() if x["code"] == BENCH["nifty50"][1]), None)
            if r:
                funds = (funds + [{"code": r["code"], "name": r["name"], "amc": r["amc"], "category": r["category"], "plan": r["plan"],
                                   "option": r["option"], "nav": r["nav"], "nav_date": r["date"], "example": True}])[:3]
        if funds:
            out["mutual_funds"] = fund_facts(funds)
            # "SBI Gold Fund" names the fund house, not State Bank's shares: drop a stock hit that is only the fund house's name
            fw = set()
            for f in funds:
                fw |= set(_toks(f["amc"])) | set(_toks(f["name"]))
            names = _names()
            keep = {s: v for s, v in (out.get("stocks") or {}).items()
                    if not any(len(a.split()) == 1 and a in fw for a in (names.get(s, {}).get("aliases") or []))}
            if "stocks" in out:
                if keep:
                    out["stocks"] = keep
                else:
                    for k in ("stocks", "stocks_as_of"):
                        out.pop(k, None)
        elif FUND_Q.search(text or "") and set(_toks(text or "")) & _amc_tokens():
            out["mutual_funds"] = {"funds": {}, "words": "A fund house was named but no scheme in AMFI's list matched; ask for the exact scheme name."}
    except Exception as e:  # noqa: BLE001
        out["mutual_funds_error"] = f"{type(e).__name__}"
    try:
        r = rules_facts(text)
        if r:
            out["rules"] = r
    except Exception as e:  # noqa: BLE001
        out["rules_error"] = f"{type(e).__name__}"
    if out:
        out["how_to_say_it"] = ("Quote these as of their dates; they describe what the market or a fund did, not what it will do. Use 'words' lines "
                                "as written, in plain language. A rule fact is current as of its as_of date. If a name the person asked about is "
                                "missing here, say there is no data on it rather than guessing.")
    return out
