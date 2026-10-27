"""Ask's market context (Madhav, 26 Oct 2026: "rupee-dollar, FII flows, global cues aren't in its facts, so it can't read why a gap opened or why the rupee's
moving"): the records' `market_context` section (rupee same day from the Kite USDINR future, dollar index, Brent, US yields and indices, the two fear gauges,
FII/DII cash) in Ask's facts, and an instant answer for a short plain question about one of them.

Every reading is said with its as-of date; the FRED series lag by days and are never called live. The section explains, it never predicts: the studies of
26 Oct (XO1, FX1, FII1, DII1, TWT-H43) found no edge in any of it, and the tested line is said whenever he asks what to do about a reading. "Why did the
Nifty gap down?" goes to the model, which has the same section in its facts and says what it can and cannot tie to the move.
"""
from __future__ import annotations

import re

from jarvis.india import views

WHAT = {
    "rupee": r"\brupee\b|\busd ?/? ?inr\b|\bdollar[- ]rupee\b|\brupee[- ]dollar\b|\binr\b",
    "us": r"\bs ?&? ?p ?500\b|\bnasdaq\b|\bwall street\b|\bus (?:market|markets|close|stocks|indices)\b|\bhow did (?:the )?(?:us|america)\b|\boverseas\b|\bglobal (?:cues|markets)\b",
    "crude": r"\bcrude\b|\bbrent\b|\boil price",
    "yield": r"\b(?:us )?10[- ]?year\b|\bus yields?\b|\btreasur(?:y|ies)\b|\bbond yields?\b",
    "dollar": r"\bdollar index\b|\bdxy\b|\bstrong dollar\b|\bweak dollar\b",
    "vix": r"\bvix\b|\bfear gauge\b",
    "flows": r"\bfii\b|\bdii\b|\bfpi\b|\bforeign (?:institutions?|investors?|flows?)\b|\bdomestic (?:institutions?|flows?)\b|\binstitutions?\b",
    "gift": r"\bgift nifty\b|\bsgx nifty\b|\bpre-?open (?:signal|indicator)\b",
}
ORDER = ("rupee", "gift", "crude", "yield", "dollar", "us", "vix", "flows")
# questions the flow leaves to the model, which has the facts and answers in context
NOT_FOR_US = re.compile(r"\b(research|study|studies|analy[sz]e|flag|log it|note it|should (?:we|i)|\bif\b|let'?s|plan to|later|buy|sell|why|because|reason|cause|gap(?:ped|s)?|explain|affect|impact|influence|predict|forecast|will |what if|tested|test)\b", re.I)
READING_Q = re.compile(r"\b(what|how|where|show|tell|is|are|did|does)\b", re.I)


def _dw(d) -> str:
    import datetime as dt
    try:
        x = dt.date.fromisoformat(str(d)[:10])
        return f"{x:%a} {x.day} {x:%b}"
    except (TypeError, ValueError):
        return str(d)


def facts_part(rm: dict) -> dict:
    mc = rm.get("market_context") or {}
    if mc.get("status") != "ok":
        return {"status": mc.get("status", "missing"), "how_to_say_it": "the market-context feed is not built: say so; never state a rupee, crude, yield or US-market reading from memory"}
    def r(x):   # one reading, trimmed
        return {k: x.get(k) for k in ("label", "status", "as_of", "lag_days", "value", "unit", "change_1", "change_5", "change_kind", "source", "contract")} if x else None
    return {"as_of": "each reading carries its own as_of and lag_days", "words": mc.get("words"), "explains": mc.get("explains"), "tested": mc.get("tested"),
            "rupee_same_day": r(mc.get("rupee_same_day")), "macro": {k: r(v) for k, v in (mc.get("macro") or {}).items()},
            "india_vix": r(mc.get("india_vix")), "flows": mc.get("flows"), "gift_nifty": mc.get("gift_nifty"),
            "opening_gaps": mc.get("opening_gaps"),     # 26 Oct: each index's open against the previous close, with the GP1 tested line
            "valuation": mc.get("valuation"),           # 27 Oct: Nifty 50 / 500 / Bank P/E, P/B, yield and their percentiles in 2024-free history
            "how_to_say_it": mc.get("how_to_say_it")}


def _chg(x: dict) -> str:
    if x.get("change_kind") == "points":
        return f"{x['change_1']:+.2f} points on the day, {x['change_5']:+.2f} over five readings"
    c5 = f", {x['change_5'] * 100:+.1f}% over five readings" if x.get("change_5") is not None else ""
    return f"{x['change_1'] * 100:+.1f}% on the day{c5}"


def _line(x: dict, fmt: str = ",.2f") -> str:
    if not x or x.get("status") != "ok":
        return f"{(x or {}).get('label', 'that reading')} is not available right now."
    lag = f", {x['lag_days']} days behind today" if (x.get("lag_days") or 0) > 1 and "FRED" in str(x.get("source")) else ""
    return f"{x['label']} {x['value']:{fmt}}{(' ' + x['unit']) if x.get('unit') and x['unit'] != '%' else ('%' if x.get('unit') == '%' else '')} on {_dw(x['as_of'])} ({_chg(x)}{lag})."


def market_context_flow(text: str) -> dict | None:
    """An instant answer for a short, plain question about the rupee, the US close, crude, yields, the dollar, the fear gauges, FII/DII or GIFT Nifty."""
    from jarvis.india.ask import _reply      # here, not at the top: ask.py imports this module

    if not text or len(text) > 160 or NOT_FOR_US.search(text) or not READING_Q.search(text):
        return None
    kinds = [k for k in ORDER if re.search(WHAT[k], text, re.I)]
    if not kinds:
        return None
    rm = views.readmodel()
    mc = rm.get("market_context") or {}
    if mc.get("status") != "ok":
        return None
    macro, parts = mc.get("macro") or {}, []
    for k in kinds[:3]:
        if k == "rupee":
            rs = mc.get("rupee_same_day") or {}
            if rs.get("status") == "ok":
                w = "weaker" if rs["change_1"] > 0 else "stronger"
                parts.append(f"The rupee, same day: USD/INR {rs['value']:.2f} on {_dw(rs['as_of'])} ({_chg(rs)}; the rupee is {w}; this is the Kite {rs.get('contract', 'USDINR')} future's last candle of the session, "
                             f"so read the move, not the exact level). " + _line(macro.get("DEXINUS", {})).replace("USD/INR, FRED", "The longer series (FRED USD/INR)"))
            else:
                parts.append(_line(macro.get("DEXINUS", {})))
        elif k == "us":
            parts.append(_line(macro.get("SP500", {}), ",.0f") + " " + _line(macro.get("NASDAQCOM", {}), ",.0f"))
        elif k == "crude":
            parts.append(_line(macro.get("DCOILBRENTEU", {})))
        elif k == "yield":
            parts.append(_line(macro.get("DGS10", {})))
        elif k == "dollar":
            parts.append(_line(macro.get("DTWEXBGS", {})))
        elif k == "vix":
            iv = mc.get("india_vix") or {}
            parts.append((f"India VIX {iv['value']:.2f} on {_dw(iv['as_of'])} ({_chg(iv)}). " if iv.get("status") == "ok" else "") + _line(macro.get("VIXCLS", {})))
        elif k == "flows":
            f = mc.get("flows") or {}
            if f.get("status") == "ok":
                rows = f["rows"]
                bits = [f"{n} {v['net_cr']:+,.0f} crore" for n, v in (("FII", rows.get("FII")), ("DII", rows.get("DII"))) if v]
                parts.append(f"Institutions on {_dw(f['as_of'])} (cash, net, NSE provisional): " + ", ".join(bits) + ".")
            else:
                parts.append("The institutions' flows are not available right now.")
        elif k == "gift":
            parts.append("GIFT Nifty (the pre-open signal) has no free source, so Ananta does not have it.")
    ans = "Sir, " + " ".join(p for p in parts if p) + " " + (mc.get("tested") or "")
    return _reply(ans, ["What is the rupee doing?", "How did the US close?", "What did FII and DII do?"], ["market_context (manifests/market_context.json), each reading with its as-of date"],
                  {})
