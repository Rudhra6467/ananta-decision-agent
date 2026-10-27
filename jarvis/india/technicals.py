"""The India technicals panel for Ask and voice (26 Oct 2026).

Madhav, 26 Oct: "clear gap is moving-average crossovers, like the 50-day crossing the 200-day ... RSI, MACD, support and resistance, and volume
signals. It may also have no live price data underneath, so it can't say whether a crossover has actually happened."

The numbers come from the read model's `technicals` section (records india/technicals.py: Ananta's own daily data, as of the last close, built
with the 22:30 paper job) and what was ever tested about each indicator from its `indicator_knowledge` section (the registry and the teacher
cards). Two entry points:
  facts_part(rm)        a compact dict for Ask's facts, so the model answers indicator questions from the panel, never from memory
  technicals_flow(text) an instant code answer for a short indicator question ("has the 50-day crossed the 200-day on Nifty?", "what is
                        Nifty's RSI?", "where is support for TATAPOWER?", "is volume high on JIOFIN?"), the same words every time
Every answer says the date of the close it uses and that nothing is intraday, and whether the indicator was ever tested. Description only:
nothing here is a buy or sell signal, and nothing trades on it.
"""
from __future__ import annotations

import datetime as dt
import re

from jarvis.india import views

INDEX_ALIASES = {"NIFTY BANK": r"\bbank ?nifty\b|\bnifty ?bank\b", "NIFTY 50": r"\bnifty(?: ?50)?\b"}
STOCK_ALIASES = {"TATAPOWER": r"\btata ?power\b", "JIOFIN": r"\bjio ?fin(?:ancial)?\b", "LICI": r"\blic\b", "TMPV": r"\btata motors\b",
                 "UNITDSPR": r"\bunited spirits\b", "TATACHEM": r"\btata chem(?:icals)?\b", "NATIONALUM": r"\bnalco\b|\bnational alumin(?:i)?um\b"}
# symbols that are also English words count only when written in capitals ("any idea what the RSI is" is not about Vodafone Idea)
WORD_SYMBOLS = {"IDEA", "SAIL", "GAIL", "BEL", "ITC", "TRENT", "PAGE", "CAN", "ONE", "ALL", "HOME", "STAR", "BASF", "IRB", "IEX"}
WHAT = {
    "cross": r"\bcross(?:ed|es|ing|over|overs)?\b|\bgolden\b|\bdeath cross|\b(?:20|50|200)[- ]?(?:day|dma|d)\b|\bmoving averages?\b|\bdma\b|\bsma\b",
    "rsi": r"\brsi\b|\boverbought\b|\boversold\b",
    "macd": r"\bmacd\b",
    "sr": r"\bsupport\b|\bresistance\b",
    "volume": r"\bvolumes?\b",
    "high52": r"\b52[- ]?week|\byearly high\b|\byear'?s high\b",
    "gap": r"\bgap[- ]?(?:up|down|fill|rule|trade|trading)s?\b|\b(?:opening|overnight) gaps?\b|\bgaps? (?:up|down)\b|\bgapp(?:ed|ing)\b",
    "stop": r"\btrailing[- ]stops?\b|\bfixed[- ]stops?\b|\bstop[- ]?loss(?:es)?\b|\btrail(?:ing)? (?:the )?stops?\b",
    "hedge": r"\bhedg(?:e|es|ed|ing)\b|\bprotective puts?\b|\bput protection\b",
    # 27 Oct (Madhav's yes): the five families being tested in records india/technicals.py, answered here only as "was it tested?"
    "candle": r"\bhammers?\b|\bengulfing\b|\bdojis?\b|\bcandlesticks?\b|\bcandle ?(?:stick )?patterns?\b",
    "valuation": r"\bp/?e(?: ratio)?s?\b|\bpe ratio\b|\bprice[- ]to[- ]earnings\b|\bp/?b(?: ratio)?\b|\bprice[- ]to[- ]book\b|\bvaluations?\b|\bdividend yield\b",
    "beta": r"\bbeta\b|\blow[- ]volatility\b|\blow[- ]vol\b",
    "spread": r"\b(?:option )?spreads?\b|\bbull call\b|\bbear put\b|\bdebit spread\b|\bcredit spread\b",
    "corp": r"\b(?:stock )?splits?\b|\bbonus(?: issues?)?\b|\bbuybacks?\b|\bdividends?\b",
    "all": r"\btechnicals?\b|\bindicators?\b|\bchart\b",
}
ORDER = ("cross", "rsi", "macd", "sr", "volume", "high52", "gap", "stop", "hedge", "candle", "valuation", "beta", "spread", "corp", "all")
NEWK = ("gap", "stop", "hedge", "candle", "valuation", "beta", "spread", "corp")      # 26 Oct (GP1, TS1, HG1): answered here only as "was it tested?"; a reading-style question about them goes to the model
FAMILY_OF = {"cross": "moving averages and crossovers", "rsi": "RSI and stochastic", "macd": "MACD", "sr": "support and resistance", "volume": "volume", "gap": "gaps", "stop": "stops and exits (trailing vs fixed)", "hedge": "hedging", "candle": "candlestick patterns", "valuation": "valuation (P/E, P/B)", "beta": "beta and volatility",
             "spread": "option spreads", "corp": "corporate actions"}
DEFINE_Q = re.compile(r"^\s*(?:(?:okay|so|and|ananta|sir)[\s,]*)*(?:what(?:'s| is| are| does)|explain|define|meaning of|tell me what)\s+"
                      r"(?:(?:an? )?(?:rsi|macd|support|resistance|volume|beta)|(?:an? |the )?(?:moving averages?|golden cross(?:es)?|death cross(?:es)?|"
                      r"crossovers?|candlesticks?|52[- ]week high))(?:\s+(?:is|are|and what does it (?:mean|signal)|means?|signals?|indicates?|tells? you))?\s*\??\s*$", re.I)
TESTED_Q = re.compile(r"\b(tested|test|evidence|proven|proof|work|works|working|edge|reliable|backtest(?:ed)?)\b", re.I)
NOT_FOR_US = re.compile(r"\b(stocks above|shares? of (the )?(liquid|stocks)|how many (stocks|shares)|breadth|research|study|studies|analy[sz]e|flag|log it|note it|should|let'?s|plan to|later|buy|sell|why|too late|enter|entry|"
                        r"earnings|results|worth|good time|what do you think|your read|hold|add|trim|exit)\b", re.I)
# 27 Oct: "TCS gapped up 4% after earnings. Is it too late to enter?" got NIFTY's support and resistance. A name Ananta has no panel for (an
# upper-case ticker or a well-known company word) means the question is not about the Nifty: the model answers (it says what it has).
TERMS = {"RSI", "MACD", "NSE", "BSE", "ETF", "ETFS", "ATR", "FII", "DII", "FPI", "VIX", "USD", "INR", "SMA", "DMA", "EMA", "SEBI", "RBI", "IPO", "OK",
         "PE", "PB", "EPS", "GDP", "US", "AI", "NAV", "SIP", "OTM", "ATM", "ITM", "IST", "CE", "PM", "AM", "I", "A", "F&O", "FO", "NIFTY", "BANKNIFTY", "SENSEX"}
COMPANY_WORDS = re.compile(r"\b(reliance|infosys|infy|wipro|hdfc|icici|kotak|axis bank|sbi|airtel|bharti|adani|bajaj|maruti|larsen|l&t|hul|hindustan unilever|"
                           r"asian paints|titan|sun pharma|cipla|ongc|ntpc|coal india|itc|tcs|zomato|paytm|nykaa)\b", re.I)


def _unknown_name(text: str, t: dict) -> bool:
    have = set((t.get("stocks") or {}).keys())
    for tok in re.findall(r"(?<![A-Za-z0-9])[A-Z][A-Z0-9&]{1,14}(?![A-Za-z0-9])", text):
        if tok not in TERMS and tok not in have:
            return True
    return bool(COMPANY_WORDS.search(text)) and not any(re.search(rf"(?<![a-z0-9]){re.escape(s.lower())}(?![a-z0-9])", text.lower()) for s in have)


def _dw(d) -> str:
    try:
        x = dt.date.fromisoformat(str(d)[:10])
        return f"{x:%a} {x.day} {x:%b}"
    except (TypeError, ValueError):
        return str(d)


def _num(x, nd=0) -> str:
    return "n/a" if x is None else f"{x:,.{nd}f}"


def _pc(x) -> str:
    return "n/a" if x is None else f"{x * 100:+.1f}%"


def _shares(x) -> str:
    if x is None:
        return "n/a"
    return f"{x / 1e7:.2f} crore shares" if x >= 1e7 else f"{x / 1e5:.1f} lakh shares" if x >= 1e5 else f"{x:,.0f} shares"


def _panel(rm: dict) -> dict:
    t = rm.get("technicals") or {}
    return t if t.get("status") == "ok" else {}


def facts_part(rm: dict) -> dict:
    """For Ask's facts: the index panels in full, the holdings' one-line summaries, the picks' key readings, and what was tested."""
    t = _panel(rm)
    if not t:
        return {"status": (rm.get("technicals") or {}).get("status", "missing"),
                "how_to_say_it": "the technicals panel is not built: say so; never read an indicator from memory"}
    keep = ("close", "as_of", "change_1d", "sma", "vs_sma", "cross_50_200", "cross_20_50", "rsi14", "rsi_zone", "macd", "high_52w", "low_52w", "vs_high_52w",
            "support", "resistance", "words")
    stocks = t.get("stocks") or {}
    hold = {s: {"words": p.get("words"), "rsi14": p.get("rsi14"), "cross_50_200": (p.get("cross_50_200") or {}).get("state"),
                "volume_ratio": (p.get("volume") or {}).get("ratio")} for s, p in stocks.items() if "holding" in str(p.get("role") or "")}
    picks = {s: {"rsi14": p.get("rsi14"), "cross_50_200": (p.get("cross_50_200") or {}).get("state"), "vs_sma50": (p.get("vs_sma") or {}).get("50"),
                 "volume_ratio": (p.get("volume") or {}).get("ratio")} for s, p in stocks.items() if str(p.get("role") or "") == "pick"}
    k = (rm.get("indicator_knowledge") or {}).get("families") or {}
    return {"as_of": t.get("as_of"), "basis": t.get("basis"),
            "indices": {n: {x: p.get(x) for x in keep} for n, p in (t.get("indices") or {}).items()},
            "holdings": hold, "picks": picks,
            "indicator_knowledge": {f: {"tested_study": v.get("headline"),
                                        "words": str(v.get("words") or "").replace(str(v.get("headline") or "\0"), "")[:420],
                                        "not_tested": v.get("not_tested")} for f, v in k.items()},
            "how_to_say_it": ("Indicator values are as of the last daily close (as_of), from Ananta's own daily data; nothing is intraday or live. A crossover "
                              "means the two averages crossed on a daily close (cross_50_200.last_cross, sessions_ago); when last_cross is empty, the averages "
                              "have not crossed since searched_from (the start of the window), so say exactly that. Say whether an indicator was ever tested "
                              "from indicator_knowledge (VALIDATED/CONDITIONAL = held; REJECTED = did not hold; OPPOSITE = the reverse showed up; "
                              "INCONCLUSIVE = too little data). Never present an untested indicator as a signal.")}


def _which(text: str, t: dict) -> list[tuple[str, dict]]:
    out = []
    low = text.lower()
    idx = t.get("indices") or {}
    rest = low
    if re.search(INDEX_ALIASES["NIFTY BANK"], low) and "NIFTY BANK" in idx:
        out.append(("NIFTY BANK", idx["NIFTY BANK"]))
        rest = re.sub(INDEX_ALIASES["NIFTY BANK"], " ", low)       # "bank nifty" alone is not also a question about Nifty 50
    if re.search(INDEX_ALIASES["NIFTY 50"], rest) and "NIFTY 50" in idx:
        out.insert(0, ("NIFTY 50", idx["NIFTY 50"]))
    squash = re.sub(r"[^a-z0-9]", "", low)
    for s, p in (t.get("stocks") or {}).items():
        if s in WORD_SYMBOLS:
            hit = bool(re.search(rf"(?<![A-Za-z0-9]){re.escape(s)}(?![A-Za-z0-9])", text))
        else:
            rx = STOCK_ALIASES.get(s)
            hit = bool(re.search(rf"(?<![a-z0-9]){re.escape(s.lower())}(?![a-z0-9])", low) or (rx and re.search(rx, low)) or (len(s) >= 6 and s.lower() in squash))
        if hit:
            out.append((s, p))
    return out


def _tested_line(rm: dict, fam: str | None, full: bool = False) -> str:
    """What the registry says about this indicator family: short in a reading's answer, in full when he asks whether it was tested."""
    f = ((rm.get("indicator_knowledge") or {}).get("families") or {}).get(fam) if fam else None
    if not f:
        return ""
    tested = f.get("tested") or []
    if full:
        bits = [str(x.get("words") or x.get("what") or "").rstrip(".") for x in tested[:3]]
    else:
        bits = [f"{x.get('what')} ({x['verdict'].lower() if isinstance(x.get('verdict'), str) else 'mixed'})" for x in tested[:2] if x.get("what")]
    bits = [b for b in bits if b and not b.startswith("study ")]
    head = str(f.get("headline") or "").strip()
    if head:     # a study of this very indicator (XO1 crossovers and MACD, FX1 rupee, FII1 flows; 26 Oct) says it first
        first = re.split(r"(?<=[A-Za-z)])\.\s", head, maxsplit=1)[0].rstrip(".") + "."
        line = (head + (" Other tests: " + "; ".join(bits) + "." if bits else "")) if full else first
    else:
        line = ("Tested: " + "; ".join(bits) + "." if bits else "This indicator was never tested as a signal.")
    if f.get("not_tested"):
        line += " Still open: " + str(f["not_tested"]).rstrip(".") + "."
    return line


def _say(kind: str, n: str, p: dict) -> str:
    if p.get("status") not in (None, "ok"):
        return p.get("words") or f"{n}: no reading."
    x, x2, m = p.get("cross_50_200") or {}, p.get("cross_20_50") or {}, p.get("macd") or {}
    sma, vs = p.get("sma") or {}, p.get("vs_sma") or {}
    if kind == "cross":
        if x.get("state") is None:
            first = f"{n} has too little history for a 200-day average."
        elif x.get("last_cross"):
            up = x.get("direction") == "up"
            first = (f"On {n} the 50-day average crossed {'above' if up else 'below'} the 200-day on {_dw(x['last_cross'])}, {x['sessions_ago']} sessions ago "
                     f"(a {'golden' if up else 'death'} cross), and it is still {x['state']} it.")
        else:
            below = x.get("state") == "below"
            first = (f"On {n} the 50-day average ({_num(sma.get('50'))}) is {x['state']} the 200-day ({_num(sma.get('200'))}) and has been since at least "
                     f"{_dw(x.get('searched_from'))}, as far back as my daily data allows a 200-day average; so any {'death' if below else 'golden'} cross "
                     f"came before that, and there has been no {'golden' if below else 'death'} cross since.")
        hist = [h for h in (x.get("history") or []) if h.get("date") != x.get("last_cross")]
        if hist:     # 26 Oct: the cross dates since 2015 (technicals_history)
            h = hist[-1]
            first += f" Before that, the {'golden' if h['direction'] == 'up' else 'death'} cross of {_dw(h['date'])} {h['date'][:4]}."
        second = (f" The 20-day crossed {'above' if x2.get('direction') == 'up' else 'below'} the 50-day on {_dw(x2['last_cross'])}." if x2.get("last_cross") else "")
        return first + second + f" The close is {_pc(vs.get('50'))} from the 50-day and {_pc(vs.get('200'))} from the 200-day."
    if kind == "rsi":
        return (f"{n}'s RSI(14) is {p['rsi14']:.0f}: {p.get('rsi_zone')} (over 70 is called overbought, under 30 oversold)." if p.get("rsi14") is not None
                else f"{n}: no RSI reading.")
    if kind == "macd":
        if m.get("line") is None:
            return f"{n}: no MACD reading."
        since = f" since {_dw(m['last_signal_cross'])}" if m.get("last_signal_cross") else ""
        return (f"{n}'s MACD (12, 26, 9) is {_num(m.get('line'), 1)} against its signal line {_num(m.get('signal'), 1)}: "
                f"{'above' if m.get('state') == 'above' else 'below'} it{since} (histogram {_num(m.get('hist'), 1)}).")
    if kind == "sr":
        s, r = p.get("support") or {}, p.get("resistance") or {}
        sp = (f"support near {_num(s['swing_low'])} (the swing low of {_dw(s.get('swing_low_date'))})" if s.get("swing_low")
              else f"no swing low under the close in the last 60 sessions, so the nearest round support is {_num(s.get('round'))}")
        rs = (f"resistance near {_num(r['swing_high'])} (the swing high of {_dw(r.get('swing_high_date'))})" if r.get("swing_high")
              else f"no swing high over the close in the last 60 sessions, so the nearest round resistance is {_num(r.get('round'))}")
        return f"{n} closed at {_num(p.get('close'), 2)}: {sp}; {rs}."
    if kind == "volume":
        v = p.get("volume") or {}
        if v.get("note"):
            return f"{n}: volume is {v['note']}."
        if not v.get("ratio"):
            return f"{n}: not enough volume history."
        how = "high" if v["ratio"] >= 1.5 else "low" if v["ratio"] <= 0.7 else "about normal"
        return f"{n}'s last volume was {v['ratio']:.1f} times its 20-day average ({_shares(v.get('last'))} against {_shares(v.get('avg20'))}): {how}."
    if kind == "high52":
        return f"{n} is {_pc(p.get('vs_high_52w'))} from its 52-week high of {_num(p.get('high_52w'))} and {_pc(p.get('vs_low_52w'))} from its low of {_num(p.get('low_52w'))}."
    return p.get("words") or ""


FOLLOW = {"cross": ["What is Nifty's RSI?", "Where is support for Nifty?"], "rsi": ["Has the 50-day crossed the 200-day on Nifty?", "What does MACD say for Nifty?"],
          "macd": ["What is Nifty's RSI?", "Where is resistance for Nifty?"], "sr": ["Has the 50-day crossed the 200-day on Nifty?", "What is Nifty's RSI?"],
          "volume": ["Where is support for it?", "What is its RSI?"], "high52": ["Has the 50-day crossed the 200-day on Nifty?", "What is Nifty's RSI?"],
          "all": ["Has the 50-day crossed the 200-day on Nifty?", "Is MACD tested?"]}


def technicals_flow(text: str) -> dict | None:
    """An instant answer for a short question about an indicator's reading (or whether it was tested). Long or multi-part questions, research
    requests, trade questions and flags go to the model, which has the same panel in its facts."""
    from jarvis.india.ask import _reply      # here, not at the top: ask.py imports this module

    if not text or len(text) > 200 or NOT_FOR_US.search(text):
        return None
    if DEFINE_Q.search(text):           # 27 Oct: "What is RSI?" wants the meaning, which the model gives briefly; a reading needs a name ("Nifty's RSI")
        return None
    kinds = [k for k in ORDER if re.search(WHAT[k], text, re.I)]
    if not TESTED_Q.search(text):
        kinds = [k for k in kinds if k not in NEWK]
    if not kinds:
        return None
    rm = views.readmodel()
    t = _panel(rm)
    if not t:
        return None
    names = _which(text, t)
    tested_q = bool(TESTED_Q.search(text))
    if _unknown_name(text, t) and not tested_q:
        return None                                   # a stock Ananta has no panel for: the model answers (27 Oct, the TCS question)
    asked = [k for k in kinds if k != "all"][:3] or ["all"]     # "RSI on Bank Nifty and where is its support?" answers both (26 Oct check)
    kind = asked[0]
    if TESTED_Q.search(text) and (not names or all(k in NEWK for k in asked)):          # "has RSI ever been tested?", "does the golden cross work?"
        line = " ".join(x for x in dict.fromkeys(_tested_line(rm, FAMILY_OF.get(k), full=True) for k in asked) if x)
        if not line:
            return None
        return _reply(f"Sir, here is what Ananta has tested about it. {line}", FOLLOW["all"], ["indicator_knowledge (the registry and the teacher cards)"])
    if any(k in NEWK for k in asked):
        return None                                   # gaps, stops, hedges and the 27 Oct families are answered here only as "was it tested?"
    if not names:
        if kind == "all":
            return None                               # "what indicators do you use?" is not a question about one chart: the model answers
        names = [("NIFTY 50", (t.get("indices") or {}).get("NIFTY 50") or {})]
    if not names[0][1]:
        return None
    as_of = names[0][1].get("as_of") or t.get("as_of")
    body = " ".join(_say(k, n, p) for n, p in names[:3] for k in asked)
    tl = " ".join(x for x in dict.fromkeys(_tested_line(rm, FAMILY_OF.get(k)) for k in asked) if x)
    a = (f"Sir, as of the {_dw(as_of)} close (Ananta's own daily data, nothing intraday): {body}"
         + (f" {tl}" if tl else "")
         + (" A reading describes the chart; it is not a buy or sell signal." if any(k in ("cross", "rsi", "macd", "all") for k in asked) else ""))
    return _reply(a, FOLLOW.get(kind, FOLLOW["all"]), [f"technicals panel (manifests/technicals.json), as of {as_of}"],
                  {"show": ["markets"] if names[0][0].startswith("NIFTY") else []})
