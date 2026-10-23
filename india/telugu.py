"""Telugu for father mode: a glossary of market words with plain meanings, and the spoken states (blueprint 22 Oct, section 5), each built
from the V0 read model and nothing else. Respectful register throughout (మీరు, -ండి); every number spoken is also shown as digits.
  python -m india.telugu brief        the morning brief in Telugu from readmodel/latest.json
  python -m india.telugu glossary     writes registrations/telugu_glossary.md and prints it
States here: morning brief, found a trade, confirm (read-back), guardrail hit, don't know. Holding (daily position review) comes with V1,
when the order path exists on paper. Nothing here decides anything; it says what the read model holds, in Telugu.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REG = Path(__file__).parent / "registrations"
PEOPLE = Path(os.path.expanduser("~/ananta_private/india_people.json"))   # {"father": {"address": "..."}}: names stay on the Mac, never in git


def address() -> str:
    """How the father is addressed: from the private people file on the Mac; the respectful generic word when it is absent."""
    try:
        return str(json.loads(PEOPLE.read_text())["father"]["address"]).strip() or "నాన్నగారు"
    except (OSError, ValueError, KeyError, TypeError):
        return "నాన్నగారు"

# term: (Telugu, plain meaning in Telugu, plain meaning in English)
GLOSSARY = {
    "nifty": ("నిఫ్టీ", "NSEలోని 50 పెద్ద కంపెనీల సూచిక", "index of the 50 largest NSE companies"),
    "bank nifty": ("బ్యాంక్ నిఫ్టీ", "పెద్ద బ్యాంకుల సూచిక", "index of the large banks"),
    "sensex": ("సెన్సెక్స్", "BSEలోని 30 పెద్ద కంపెనీల సూచిక", "index of 30 large BSE companies"),
    "index": ("సూచిక", "చాలా స్టాక్‌ల కలయికను ఒక సంఖ్యగా చూపేది", "many stocks shown as one number"),
    "stock": ("షేరు / స్టాక్", "ఒక కంపెనీలో చిన్న వాటా", "a small share of a company"),
    "uptrend": ("పెరుగుదల దిశ", "ధర కొన్ని వారాలుగా పైకి వెళ్తోంది", "price has been rising for weeks"),
    "downtrend": ("తగ్గుదల దిశ", "ధర కొన్ని వారాలుగా కిందకు వెళ్తోంది", "price has been falling for weeks"),
    "moving average": ("కదిలే సగటు", "గత N రోజుల సగటు ధర; ధర దానికి పైన ఉంటే బలం, కింద ఉంటే బలహీనత", "average price of the last N days; above it is strength, below is weakness"),
    "breakout": ("బ్రేక్అవుట్", "ధర ఇటీవలి గరిష్ఠాన్ని దాటి పైకి వెళ్లడం", "price moves above its recent high"),
    "pullback": ("పుల్‌బ్యాక్", "పెరుగుతున్న స్టాక్ కొంచెం వెనక్కి రావడం", "a rising stock dips for a while"),
    "reversal": ("రివర్సల్", "చాలా పడిన స్టాక్ మళ్లీ తిరగడం", "a stock that fell a lot turns back up"),
    "support": ("ఆధారం", "ధర పడకుండా ఆగే స్థాయి", "a level where price tends to stop falling"),
    "resistance": ("అడ్డంకి", "ధర పైకి వెళ్లకుండా ఆగే స్థాయి", "a level where price tends to stop rising"),
    "volume": ("వాల్యూమ్", "ఒక రోజులో కొన్న/అమ్మిన షేర్ల సంఖ్య", "shares traded in a day"),
    "liquidity": ("లిక్విడిటీ", "సులభంగా కొనడం, అమ్మడం కుదిరే స్టాక్", "how easily a stock can be bought and sold"),
    "entry": ("ప్రవేశం", "ట్రేడ్ మొదలుపెట్టే ధర", "the price a trade starts at"),
    "exit": ("నిష్క్రమణ", "ట్రేడ్ ముగించే ధర", "the price a trade ends at"),
    "stop loss": ("స్టాప్ లాస్", "నష్టం ఇంతకు మించకూడదని ముందే పెట్టుకునే ధర", "the price at which a losing trade is closed to cap the loss"),
    "target": ("లక్ష్యం", "లాభం తీసుకునే ధర", "the price at which profit is taken"),
    "position": ("పొజిషన్", "ప్రస్తుతం నడుస్తున్న ట్రేడ్", "a trade that is currently open"),
    "book profit": ("లాభం బుక్ చేయడం", "అమ్మి లాభాన్ని ఖాతాలోకి తీసుకోవడం", "selling to take the profit"),
    "paper trading": ("పేపర్ ట్రేడింగ్", "నిజమైన డబ్బు లేకుండా అభ్యాసం; నియమాలు నిజమైనవే", "practice with no real money, the rules are real"),
    "realised": ("వచ్చిన లాభనష్టం", "అమ్మేసిన ట్రేడ్‌ల లాభనష్టం", "profit or loss on trades already closed"),
    "unrealised": ("ఇంకా అమ్మని లాభనష్టం", "నడుస్తున్న ట్రేడ్‌లపై ఇప్పటి లాభనష్టం", "profit or loss on trades still open"),
    "bullish": ("బుల్లిష్", "మార్కెట్ పెరుగుతుందనే అంచనా", "expecting the market to rise"),
    "bearish": ("బేరిష్", "మార్కెట్ తగ్గుతుందనే అంచనా", "expecting the market to fall"),
    "option": ("ఆప్షన్", "ఒక ధరకు కొనే లేదా అమ్మే హక్కు; హక్కు ధరను ప్రీమియం అంటారు", "the right to buy or sell at a set price; its cost is the premium"),
    "call option": ("కాల్ ఆప్షన్", "పెరుగుతుందనుకుంటే కొనే హక్కు", "a right that gains if the market rises"),
    "put option": ("పుట్ ఆప్షన్", "తగ్గుతుందనుకుంటే కొనే హక్కు", "a right that gains if the market falls"),
    "premium": ("ప్రీమియం", "ఆప్షన్ కొనడానికి చెల్లించే ధర; గరిష్ఠ నష్టం ఇదే", "the price paid for an option; the most that can be lost when buying one"),
    "lot": ("లాట్", "ఒకేసారి కొనాల్సిన కనీస సంఖ్య", "the minimum bundle traded at once"),
    "expiry": ("ఎక్స్పైరీ", "ఆప్షన్ లేదా ఫ్యూచర్ ముగిసే రోజు", "the day an option or future ends"),
    "future": ("ఫ్యూచర్", "భవిష్యత్ తేదీకి ఒప్పందం; లాభనష్టం రెండూ పెద్దవి కావచ్చు", "a contract for a future date; gains and losses can both be large"),
    "margin": ("మార్జిన్", "ట్రేడ్ కోసం బ్రోకర్ దగ్గర ఉంచాల్సిన డిపాజిట్", "the deposit the broker holds for a trade"),
    "drawdown": ("డ్రాడౌన్", "ఖాతా తన గరిష్ఠ విలువ నుంచి ఎంత శాతం పడిందో", "how far the account has fallen from its peak"),
    "risk": ("రిస్క్", "ఒక ట్రేడ్‌లో పోగొట్టుకోవడానికి సిద్ధంగా ఉన్న డబ్బు", "the money one is prepared to lose on a trade"),
    "capital": ("మూలధనం", "ట్రేడింగ్ కోసం కేటాయించిన మొత్తం డబ్బు", "the total money set aside for trading"),
    "fii": ("విదేశీ సంస్థలు (FII)", "విదేశీ పెద్ద పెట్టుబడిదారులు; వారి కొనుగోళ్లు/అమ్మకాలు మార్కెట్‌ను కదిలిస్తాయి", "foreign institutional investors; their flows move the market"),
    "dii": ("దేశీయ సంస్థలు (DII)", "మ్యూచువల్ ఫండ్‌లు, బీమా సంస్థలు వంటి దేశీయ పెద్ద పెట్టుబడిదారులు", "domestic institutions such as mutual funds and insurers"),
    "vix": ("భయ సూచిక (VIX)", "మార్కెట్ రాబోయే నెలలో ఎంత ఊగుతుందో చెప్పే సంఖ్య", "how much the market is expected to swing in the coming month"),
    "breadth": ("వెడల్పు", "ఎన్ని స్టాక్‌లు పెరుగుతున్నాయో, ఎన్ని తగ్గుతున్నాయో", "how many stocks are rising versus falling"),
    "gap": ("గ్యాప్", "నిన్నటి ముగింపుకు దూరంగా ఈరోజు తెరవడం", "opening far from yesterday's close"),
    "session": ("సెషన్", "ఒక ట్రేడింగ్ రోజు (ఉదయం 9:15 నుంచి 3:30 వరకు)", "one trading day, 9:15 to 15:30"),
    "intraday": ("ఇంట్రాడే", "అదే రోజు కొని అదే రోజు అమ్మడం", "buy and sell within the same day"),
    "delivery": ("డెలివరీ", "షేర్లను ఖాతాలోకి తీసుకుని రోజులు/నెలలు ఉంచడం", "taking shares into the account to hold for days or months"),
    "results": ("ఫలితాలు", "కంపెనీ త్రైమాసిక లాభనష్టాల ప్రకటన", "a company's quarterly profit announcement"),
    "dividend": ("డివిడెండ్", "కంపెనీ లాభంలో వాటాదారులకు ఇచ్చే భాగం", "the part of profit a company pays to shareholders"),
    "ipo": ("IPO", "కంపెనీ మొదటిసారి షేర్లు అమ్మడం", "a company selling its shares to the public for the first time"),
    "percentile": ("పర్సంటైల్", "100 మందిలో ర్యాంకు; 57 అంటే 57 మంది కంటే మెరుగు", "rank out of 100; 57 means better than 57 of 100"),
    "hindsight": ("వెనక్కి చూసి తెలిసేది", "రోజు ముగిశాక తెలిసే అత్యుత్తమ ట్రేడ్; ముందే ఎవరికీ తెలియదు", "the best trade known only after the day ends; nobody knows it in advance"),
    "random": ("యాదృచ్ఛికం", "పాచిక వేసి ఎంచుకున్నట్టు; దీన్ని మించకపోతే నైపుణ్యం లేదు", "picked by chance; a yardstick skill must beat"),
    "evidence": ("సాక్ష్యం", "నమోదు చేసిన ఫలితాలు; మాటలు కాదు", "recorded results, not words"),
    "guardrail": ("రక్షణ నియమం", "నష్టం ఒక హద్దు దాటితే ఆపేసే నియమం", "a rule that stops trading when a loss limit is hit"),
    "pause": ("విరామం", "కొత్త ట్రేడ్‌లు లేకుండా ఆగడం", "no new trades until resumed"),
    "consent": ("అనుమతి", "ఖాతాలో ట్రేడ్ చేయడానికి ఇచ్చిన రాతపూర్వక అంగీకారం", "written agreement to trade the account"),
}
CAMPAIGN_TE = {"BRK": "బ్రేక్అవుట్ (ధర కొత్త గరిష్ఠాన్ని దాటింది)", "PULL": "పుల్‌బ్యాక్ (పెరుగుతున్న స్టాక్ కొంచెం వెనక్కి వచ్చింది)",
               "REV": "రివర్సల్ (ఎక్కువగా పడిన స్టాక్ మళ్లీ తిరుగుతోంది)", "CTL": "యాదృచ్ఛిక నియంత్రణ (పోల్చడానికి మాత్రమే, ఇది సిఫార్సు కాదు)"}
CALL_TE = {"BULLISH": "పెరుగుతుంది (బుల్లిష్)", "BEARISH": "తగ్గుతుంది (బేరిష్)", "NEUTRAL": "స్పష్టత లేదు"}
TREND_TE = {"above_both": "నిఫ్టీ తన 50-రోజుల, 200-రోజుల సగటులకు పైన ఉంది — మార్కెట్ పెరుగుదల దిశలో ఉంది",
            "below_both": "నిఫ్టీ తన 50-రోజుల, 200-రోజుల సగటులకు కింద ఉంది — మార్కెట్ తగ్గుదల దిశలో ఉంది",
            "mixed": "నిఫ్టీ తన 50-రోజుల, 200-రోజుల సగటుల మధ్య ఉంది — స్పష్టమైన దిశ లేదు", "unknown": "నిఫ్టీ దిశ ఈరోజు చదవలేకపోయాం"}


def _rs(x: float | None) -> str:
    return "—" if x is None else f"₹{x:+,.0f}" if x < 0 or x > 0 else "₹0"


# ---------------------------------------------------------------------------------------------------------------- the states

def brief_te(rm: dict) -> list[str]:
    """State 1, morning brief: what the market did, what today's plan is, what Ananta is watching. Read only. Three to five sentences."""
    out = [f"నమస్కారం {address()}."]
    m, c, sb, d, s = rm.get("market", {}), rm.get("call", {}), rm.get("stock_book", {}), rm.get("decisions_today", {}), rm.get("sp1", {})
    if m.get("status") == "ok":
        out.append(f"{m['data_through']} నాటికి నిఫ్టీ {m['nifty_close']:,.0f} వద్ద ముగిసింది. {TREND_TE.get(m.get('trend_state'), TREND_TE['unknown'])}.")
    else:
        out.append("ఈరోజు మార్కెట్ సమాచారం అందలేదు.")
    if d.get("status") == "ok":
        picks = [x for x in d.get("chosen", []) if x.get("campaign") != "CTL"]
        if picks:
            names = ", ".join(f"{x['symbol']} ({CAMPAIGN_TE.get(x['campaign'], x['campaign']).split(' ')[0]})" for x in picks[:6])
            more = f" ఇంకా {len(picks) - 6}" if len(picks) > 6 else ""
            out.append(f"రేపటి ప్రణాళిక: అనంత {len(picks)} స్టాక్‌లను పేపర్ ట్రేడ్‌గా తీసుకుంటోంది — {names}{more}. ఇవి ఇప్పుడు నిజమైన డబ్బుతో కాదు, అభ్యాసం కోసం మాత్రమే.")
        else:
            out.append("రేపటి ప్రణాళిక: కొత్త స్టాక్‌లు ఏవీ లేవు; ఉన్నవాటిని గమనిస్తాం.")
    if sb.get("status") == "ok":
        tot = sum((v.get("realised_inr") or 0) for v in sb.get("by_campaign", {}).values())
        out.append(f"పేపర్ ఖాతాలో ఇప్పుడు {sb['open_positions']} స్టాక్‌లు ఉన్నాయి; అమ్మేసిన ట్రేడ్‌లపై ఇప్పటివరకు లాభనష్టం {_rs(tot)}.")
    if c.get("status") == "ok" and c.get("call"):
        out.append(f"అనంత గమనిస్తున్నది: రేపటి రోజుకు అంచనా — మార్కెట్ {CALL_TE.get(c['call'], c['call'])}; ఇప్పటివరకు {c['scored']} అంచనాల్లో {c['hits']} సరైనవి.")
    if s.get("status") == "lost":
        out.append("నిన్న ఇండెక్స్ (నిఫ్టీ ఆప్షన్) లైన్ నడవలేదు — లాగిన్ సమస్య. ఆ రోజు ఏ ట్రేడూ జరగలేదు.")
    out.append("ఏదైనా అడగాలంటే చెప్పండి.")
    return out


def trade_te(pick: dict, size_inr: float = 50000, risk_inr: float = 1000, stop: str | None = None) -> str:
    """State 2, found a trade: instrument, direction, why, the stop, the size and the worst case in rupees. Read only; waits for the answer."""
    camp = pick.get("campaign", "")
    why = pick.get("why", "")
    stop_t = f"స్టాప్ లాస్ {stop}" if stop else "స్టాప్ లాస్ నియమం ప్రకారం (ప్రవేశం దగ్గర చూపిస్తాను)"
    return (f"ఒక ట్రేడ్ దొరికింది: {pick.get('symbol')} — కొనడం. రకం: {CAMPAIGN_TE.get(camp, camp)}. కారణం: {why}. "
            f"పరిమాణం సుమారు ₹{size_inr:,.0f}; {stop_t}; నియమం ప్రకారం ఒక ట్రేడ్‌లో గరిష్ఠ నష్టం సుమారు ₹{risk_inr:,.0f} (గ్యాప్ వస్తే కొంచెం ఎక్కువ కావచ్చు). "
            f"మీరు సరే అంటేనే ముందుకు వెళ్తాను — ఇప్పుడు కాగితంపై మాత్రమే.")


def confirm_te(symbol: str, qty: int, size_inr: float, live: bool = False) -> str:
    """State 3, read-back before anything is booked. Live needs a second explicit yes; paper books on one."""
    tail = "ఇది నిజమైన డబ్బు — మళ్లీ ఒకసారి 'అవును' అంటేనే పెడతాను." if live else "ఇది పేపర్ ట్రేడ్ — 'అవును' అంటే నమోదు చేస్తాను, 'లేదు' అంటే ఆగుతాను."
    return f"మళ్లీ చెబుతున్నాను: {symbol}, {qty} షేర్లు, సుమారు ₹{size_inr:,.0f}. కొనమంటారా? {tail}"


def guardrail_te(daily_pct: float, pause_pct: float) -> str:
    """State 5, guardrail hit: the 5%-day and 22%-pause rules in plain words, and that Ananta will not trade until the rule lifts."""
    return (f"రక్షణ నియమం: ఒక రోజులో ఖాతాలో {daily_pct:g}% నష్టం వస్తే ఆ రోజు ఇక ట్రేడింగ్ ఆపేస్తాను. ఖాతా తన గరిష్ఠ విలువ నుంచి {pause_pct:g}% తగ్గితే, "
            f"మాధవ్ గారు తిరిగి అనుమతించే వరకు కొత్త ట్రేడ్‌లు ఉండవు. ఇది నష్టం పెద్దది కాకుండా కాపాడే నియమం; నేను దీన్ని దాటి వెళ్లను.")


def dont_know_te(known: str = "") -> str:
    """State 6: say so, and offer what is known."""
    return "క్షమించండి, దీని గురించి నా దగ్గర సమాచారం లేదు." + (f" నాకు తెలిసింది ఇది: {known}" if known else "")


def glossary_md() -> str:
    L = ["# Telugu glossary for father mode (generated by `python -m india.telugu glossary`)", "",
         "Every market word Ananta may say in father mode, with its Telugu and a plain meaning in both languages. Ananta says the word and the meaning together (\"simplify the explanation, not the intelligence\").", "",
         "| term | Telugu | plain meaning (Telugu) | plain meaning (English) |", "|---|---|---|---|"]
    L += [f"| {k} | {v[0]} | {v[1]} | {v[2]} |" for k, v in GLOSSARY.items()]
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    from india import paths

    cmd = sys.argv[1] if len(sys.argv) > 1 else "brief"
    if cmd == "brief":
        p = paths.data_dir() / "readmodel" / "latest.json"
        rm = json.loads(p.read_text()) if p.exists() else {}
        for s in brief_te(rm):
            print(s)
    elif cmd == "glossary":
        md = glossary_md()
        (REG / "telugu_glossary.md").write_text(md)
        print(md)
    else:
        print("usage: python -m india.telugu [brief|glossary]")
        sys.exit(64)
