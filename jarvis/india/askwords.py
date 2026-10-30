"""Plain words on every India Ask answer, written or spoken (Madhav, 27 Oct: "making it simpler and easier to understand ... converting the
database language to human language before showing and telling me").

Every answer (code-built or the model's) passes words() in ask.finish(): study and teacher-card codes become what they test ("TWT-H22" ->
the stocks teacher's "-7% stop" test, "XO1" -> Ananta's crossover test), verdict labels become what they mean (REJECTED -> did not hold),
exit and timing codes become times and words (D2 -> 09:45, ATRSTOP -> a stop at the usual daily swing), R units and basis points become
plain amounts, and field names become words. The codes stay in the answer's "evidence" list (shown on tap), never in what is read or heard.
The screens have their own pass (jarvis/india/plain.py); this one is for Ask.
"""
from __future__ import annotations

import re
import time

STUDIES = {
    "XO1": "Ananta's moving-average crossover test", "SR1": "Ananta's support-and-resistance test", "TS1": "Ananta's trailing-stop test",
    "GP1": "Ananta's opening-gap test", "HG1": "Ananta's hedging test", "FII1": "Ananta's foreign-flows test", "DII1": "Ananta's domestic-flows test",
    "FX1": "Ananta's rupee test", "CP1": "Ananta's candlestick test", "VL1": "Ananta's valuation test", "BT1": "Ananta's low-beta test",
    "OS1": "Ananta's option-spread test", "CA1": "Ananta's corporate-actions test", "F06": "the put-protection test", "E02": "the exit test",
    "E04": "the exit test", "C06": "the futures-positioning test", "P01": "the entry test", "H12F": "a follow-up test of a teacher's idea",
    "H18F": "a follow-up test of a teacher's idea", "SP1": "the options line", "SP3": "the positional playbook", "SZ2": "the sizing study",
    # 29 Oct audit (map class F): studies the voice's facts carry that had no plain name
    "F01": "the sell-a-straddle test", "F02": "the expiry-eve strangle test", "F03": "the option-chain shape test", "F04": "the futures open-interest test",
    "GK1": "the time-decay test", "I01": "the first-hour test", "I05": "the expiry-afternoon test", "IB1": "the opening-range breakout test",
    "MS1": "the intraday-patterns test", "V03": "the IPO test",
    "G01": "the exit book", "RX1": "Ananta's test of the 12 reconstruction drafts", "G02": "the gate", "K02": "the daily-call study", "R01": "the calibration check", "PW-HF-CHRONOS": "the Chronos forecast study",
}
VERDICTS = {"VALIDATED": "held up", "CONDITIONAL": "held up, weaker in one period", "REJECTED": "did not hold",
            "OPPOSITE": "the opposite showed up", "INCONCLUSIVE": "not enough data to judge"}
VERBS = {"VALIDATED": "held up", "CONDITIONAL": "held up, but weaker in one period", "REJECTED": "did not hold",
         "OPPOSITE": "came out the opposite way", "INCONCLUSIVE": "had too little data to judge"}
POINTS = {"D0": "09:15", "D1": "09:30", "D2": "09:45", "D3": "10:15"}
EXITS = {"ATRSTOP": "a stop at the usual daily swing", "T1515": "the 15:15 exit", "NEXTOPEN": "the next morning's open", "EOD": "the close",
         # 28 Oct outside round 3: "exit ORSTOP" reached an answer
         "ORSTOP": "a stop at the other side of the first 15 minutes' range", "T1130": "the 11:30 exit", "TRAIL": "a trailing stop"}
FIELDS = {"wrong_if": "the 'wrong if' line", "suggest_inr": "the suggested amount", "paper_moves_today": "today's paper moves",
          "moves_applied": "the moves applied", "data_through": "data up to", "by_campaign": "by family", "win_rate": "win rate",
          "stale_inputs": "stale inputs", "account_allocation": "your account plan", "indicator_knowledge": "Ananta's test results",
          "market_context": "the market background", "book_stats": "the book's numbers", "beta_vol": "beta and volatility",
          "reconstruction_detail": "last night's review", "decisions_for_next_session": "the plan for the next session"}
TEACHER = {"TWT": "the YouTube stocks teacher's", "OPT": "the YouTube options teacher's", "M": "a YouTube teacher's"}
# 27 Oct outside review: in-house words that reached his answers, said the way a person would (each replacement is idempotent)
JARGON = [
    (re.compile(r"\b(?:the )?liquid[- ]250(?: stocks| names| universe)?\b", re.I), "the 250 most traded stocks"),
    (re.compile(r"\bresearch book\b"), "practice book"),
    (re.compile(r"\b(?:[Tt]he |[Mm]y )?(?:FACTS\.)?lookup\b(?! (?:table|page))"), "Ananta's data"),
    (re.compile(r"\bfull suggestion\b"), "suggested change"),
    (re.compile(r"\bstudy fill(s?)\b"), r"ideal price\1"),
    (re.compile(r"\brealistic fill(s?)\b"), r"realistic price\1"),
    (re.compile(r"\bscored (sessions?|trades?|calls?)\b"), r"\1 with a result"),
    (re.compile(r"\b(?:the |a )?5% daily loss stop\b"), "the rule that stops trading for the day after a 5% loss"),
    (re.compile(r"\b(?:the |a )?22% pause\b"), "the rule that pauses trading after a 22% fall"),
    # 27 Oct second review: no 'flexi-cap index fund' exists; the broad-market index fund is a Nifty 500 index fund
    (re.compile(r"\bflexi[- ]?cap index funds?\b", re.I), "Nifty 500 index fund"),
    # the model's decision stamp (answer_guide: no labels), only at the start of a sentence
    (re.compile(r"(^|[.!?]\s+)(?:Decision|My read)\s*:\s*([a-z])"), lambda m: m.group(1) + m.group(2).upper()),
]


def _plural(s: str) -> str:
    """'1 call(s)' -> '1 call', '3 trade(s)' -> '3 trades', a bare 'trade(s)' -> 'trades' (records lines write '(s)')."""
    s = re.sub(r"\b(\d[\d,]*) ((?:[A-Za-z-]+ ){0,2})([A-Za-z]+)\(s\)", lambda m: f"{m.group(1)} {m.group(2)}{m.group(3)}" + ("" if m.group(1) == "1" else "s"), s)
    return re.sub(r"\b([A-Za-z]+)\(s\)", r"\1s", s)

_CARD = r"(?:TWT|OPT|M)-H\d+[A-Z]?"
_STUDY = "|".join(sorted((re.escape(k) for k in STUDIES), key=len, reverse=True))
_CODE = rf"(?:{_CARD}|(?:{_STUDY})(?:-ANY)?)"
CODE_RE = re.compile(rf"(?<![\w-]){_CODE}(?![\w-])")
SNAKE_RE = re.compile(r"(?<![\w/.:@])[a-z]+(?:_[a-z0-9]+)+(?![\w/(])")
LEFT_RE = re.compile(rf"(?<![\w-])(?:{_CARD}|{_STUDY}|ATRSTOP|T1515|NEXTOPEN|VALIDATED|CONDITIONAL|REJECTED|OPPOSITE|INCONCLUSIVE)(?![\w-])"
                     r"|(?<![\w/.:@])[a-z]+_[a-z0-9_]+")

_TITLES: dict = {"t": 0, "v": {}}


def titles() -> dict:
    """Teacher-card titles by id (from the tested cards the app shows), refreshed every 10 minutes; {} when not available."""
    if time.time() - _TITLES["t"] < 600:
        return _TITLES["v"]
    out = {}
    try:
        from jarvis.india import views
        for c in (views.teachers() or {}).get("cards") or []:
            if c.get("id") and c.get("title"):
                out[str(c["id"])] = str(c["title"]).strip().rstrip(".")
    except Exception:  # noqa: BLE001  the generic name is used
        pass
    _TITLES.update(t=time.time(), v=out)
    return out


def name(code: str, known: dict | None = None) -> str:
    code = code.replace("-ANY", "")
    if code in STUDIES:
        return STUDIES[code]
    m = re.match(r"(TWT|OPT|M)-H\d+", code)
    if m:
        t = (known if known is not None else titles()).get(code)
        return f"{TEACHER[m.group(1)]} “{t[0].lower() + t[1:] if t and not t[:2].isupper() else t}” test" if t else f"{TEACHER[m.group(1)]} test"
    return code


def _paren(m: re.Match, known: dict) -> str:
    """'(study XO1, 2000-2023)' -> '(2000-2023)'; '(TWT-H22)' -> ''; '(TWT-H15, TWT-H22)' -> ''."""
    inner = m.group(1)
    rest = re.sub(rf"\b(?:studies|study|card|cards|test|tests|teacher card)?\s*{_CODE}\s*(?:and|,|;|/)?\s*", "", inner).strip(" ,;/")
    return f" ({rest})" if rest and rest != inner else ("" if not rest else m.group(0))


def words(s: str, known: dict | None = None) -> str:
    """One answer in plain words (idempotent)."""
    if not s:
        return s
    known = titles() if known is None else known
    out = re.sub(rf"\s*\(([^()]*?{_CODE}[^()]*?)\)", lambda m: _paren(m, known), s)
    out = re.sub(rf"\b(?:the )?(?:teacher'?s? card|teacher card|teacher|study|card|test)\s+({_CODE})\b", lambda m: name(m.group(1), known), out)
    out = re.sub(rf"\bthe\s+({_CODE})\s+(?:test|study|card)\b", lambda m: name(m.group(1), known), out)
    out = CODE_RE.sub(lambda m: name(m.group(0), known), out)
    out = re.sub(r"\b(?:decision point|point|at)\s+(D[0-3])\b", lambda m: ("the " + POINTS[m.group(1)] + " decision") if m.group(0).lower().startswith(("decision", "point"))
                 else "at " + POINTS[m.group(1)], out)
    for k, v in EXITS.items():
        out = re.sub(rf"(?<![\w-]){k}(?![\w-])", v, out)
    out = re.sub(r"\(\s*'?(ATR|ATRSTOP)'?\s*,\s*(-?1)\s*\)", "a stop at the usual daily swing", out)
    vb = "|".join(VERDICTS)
    out = re.sub(rf"\b(?:the )?verdict (?:is|was|:)\s*(?:that )?['‘\"]?({vb})\b['’\"]?", lambda m: "it " + VERBS[m.group(1)], out, flags=re.I)
    out = re.sub(rf"\b(?:was|were|is|are|came out|came back|marked)\s+({vb})\b", lambda m: VERBS[m.group(1)], out)
    for k, v in VERDICTS.items():
        out = re.sub(rf"(?<![\w-]){k}(?![\w-])", v, out)
        out = re.sub(rf"\({k.lower()}\)", f"({v})", out)                              # the code-built lines write "(validated)"
    out = re.sub(r"\bRSI\s?\(14\)", "RSI", out)
    out = re.sub(r"([+-−]?\d+(?:\.\d+)?)\s?R\b(?!\w)", lambda m: f"{m.group(1)} times the risk taken", out)
    out = re.sub(r"([+-−]?\d+(?:\.\d+)?)\s?(?:bps?|basis points)\b", lambda m: f"{float(m.group(1).replace('−', '-')) / 100:+.2f}%", out)
    for k, v in FIELDS.items():
        out = re.sub(rf"`?(?<![\w/.]){k}(?![\w/])`?", v, out)
    out = SNAKE_RE.sub(lambda m: m.group(0).replace("_", " "), out)
    out = re.sub(r"\b(Ananta's [a-z-]+(?: [a-z-]+)? test) (?:test|study)\b", r"\1", out)
    out = re.sub(r"\b(?:on|by|in) (?:Ananta's|the) (Ananta's [^,.;]+ test)", r"in \1", out)
    out = re.sub(r"\b([Tt]he|[Aa]) (Ananta's)\b", r"\2", out)
    out = _plural(out)                                  # before the jargon: '2 scored session(s)' -> '2 scored sessions' -> '2 sessions with a result'
    for rx, v in JARGON:
        out = rx.sub(v, out)
    out = re.sub(r"\b(?:the|The) the\b", lambda m: m.group(0).split()[0], out)
    out = re.sub(r"\(\s*\)", "", out)
    out = re.sub(r"\s+([,.;:])", r"\1", out)
    out = re.sub(r"  +", " ", out).strip()
    out = re.sub(r"((?:^|[.!?]\s+))(it) (came out|did not|held|had)\b", lambda m: m.group(1) + ("It" if m.group(1).strip() or not m.group(1) else m.group(2)) + " " + m.group(3), out)
    return out


def leaks(s: str) -> list[str]:
    """Codes or field names still in an answer (the exam's plain-words check and the tests use it)."""
    return sorted({m.group(0) for m in LEFT_RE.finditer(s or "")})
