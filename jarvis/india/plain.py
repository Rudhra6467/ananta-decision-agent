"""Plain words on every India screen (Madhav, 23 Oct 2026: "rewrite the content from an outside perspective of making it easy for me"; the same
rule as crypto's jarvis/service/plain.py). Every sentence the India service sends to the app passes through scrub(): internal codes and research
names become the words a person uses, web addresses and file paths never reach a screen, and the few sentences that only an engineer would write
are rewritten whole. Identifiers (no spaces: ids, keys, routes, symbols) are kept as they are. tests/test_india_plain.py fails if a code gets through.

The names, in one place, so the screens, Ask and the voice say the same thing:
  SP1 -> the index playbook        SZ2 -> the sizing study          G01 -> the exit book            G02 -> the gate
  CTL -> random control            BRK / PULL / REV -> breakout / pullback / reversal
  HINDSIGHT / RANDOM / MARKET -> the best possible / chance / the market average
  the liquid 250 -> the 250 most-traded stocks     the read model -> the daily summary     Rs 50,000 notional -> about Rs 50,000
  20-day average -> one-month average    50-day -> ten-week    200-day -> long-term average    RSI -> momentum    VIX -> the fear gauge
  ADMITTED / SHADOW -> proved / on trial  class a / b / c -> a rule fired but it was not taken / no rule was set for it / could not be traded
"""
from __future__ import annotations

import re

IDENT_RE = re.compile(r"^\S+$")                     # no spaces: an id, a key, a route, a symbol; the app looks these up
URL_RE = re.compile(r"\s*\(?(?:https?://|/Users/|~/)[^\s)]+\)?")

SENTENCES: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\s*:?\s*open\s+on the Mac\b", re.I), ""),
    (re.compile(r"\bboth its 50- and 200-day averages\b"), "its ten-week and long-term averages"),
    (re.compile(r"\b50- and 200-day averages\b"), "ten-week and long-term averages"),
    (re.compile(r"\b(below|above) both (?:its )?averages\b"), lambda m: f"{m.group(1)} its ten-week and long-term averages"),
    (re.compile(r"\b200-day averages\b"), "long-term averages"),
    (re.compile(r"\bthe SP1 (?:index )?playbook\b"), "the index playbook"),
    (re.compile(r"\bSP1 index playbook\b"), "the index playbook"),
    (re.compile(r"\b(?:the )?SP1 (?:index )?line\b"), "the options line"),
    (re.compile(r"\bthe G02 gate\b"), "the gate"),
    (re.compile(r"\bon (\d{2})-(\d{2})\b"), lambda m: f"on {int(m.group(2))} {['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][int(m.group(1)) - 1]}" if 1 <= int(m.group(1)) <= 12 else m.group(0)),
    (re.compile(r"no Kite sign-in by 09:10 IST: the Kite token expired at 6 am IST(?::\s*open\b.*?on the Mac)?", re.I), "the morning sign-in to Zerodha was missing"),
    (re.compile(r"the Kite token expired at 6 am IST(?::\s*open\b.*?on the Mac)?", re.I), "the morning sign-in to Zerodha had lapsed"),
    (re.compile(r"session lost: ", re.I), ""),
    (re.compile(r"\bno Kite sign-in\b", re.I), "no morning sign-in to Zerodha"),
    (re.compile(r"\btoken dead\b", re.I), "the Zerodha sign-in had lapsed"),
    (re.compile(r"\bthe Kite token\b", re.I), "the Zerodha sign-in"),
    (re.compile(r"\bKite\b"), "Zerodha"),
    (re.compile(r"\bthe (?:index line|SP1 line|index-line)\b", re.I), "the options line"),
    (re.compile(r"\bRs 50,000 notional\b", re.I), "about ₹50,000"),
    (re.compile(r"\bevery registered exit tracked\b", re.I), "the exit rule decides when it sells"),
    (re.compile(r"\bthe liquid 250\b", re.I), "the 250 most-traded stocks"),
    (re.compile(r"\bliquid 250\b", re.I), "250 most-traded stocks"),
    (re.compile(r"\bthe read model\b", re.I), "the daily summary"),
    (re.compile(r"\bread model\b", re.I), "daily summary"),
    (re.compile(r"\bpaper twin\b", re.I), "paper copy of your account"),
    (re.compile(r"\bbelow both market\b", re.I), "downtrend"),
    (re.compile(r"\babove both market\b", re.I), "uptrend"),
    (re.compile(r"\bbelow_both\b"), "a downtrend"),
    (re.compile(r"\babove_both\b"), "an uptrend"),
    (re.compile(r"\bclass \(?a\)?\b"), "a rule fired but it was not taken"),
    (re.compile(r"\bclass \(?b\)?\b"), "no rule was set for it"),
    (re.compile(r"\bclass \(?c\)?\b"), "it could not be traded"),
    (re.compile(r"\bliq[_ ]rank\b", re.I), "trading rank"),
    (re.compile(r"\bREF_POLICY\b|\bhold_20d\b"), "the 20-day hold"),
    (re.compile(r"\b20-day (?:average|avg)\b"), "one-month average"),
    (re.compile(r"\b20-day\b"), "one-month"),
    (re.compile(r"\b50-day (?:average|avg)\b"), "ten-week average"),
    (re.compile(r"\b50-day\b"), "ten-week"),
    (re.compile(r"\b200-day (?:average|avg)\b"), "long-term average"),
    (re.compile(r"\b200-day\b"), "long-term average"),
    (re.compile(r"\bRSI(?:14)?\b"), "momentum"),
    (re.compile(r"\bINDIA VIX\b|\bVIX\b"), "the fear gauge"),
    (re.compile(r"\bH1 trips\b"), "one-session trades"),
    (re.compile(r"\bH(1|5|20)\b"), lambda m: {"1": "one-session", "5": "five-session", "20": "20-session"}[m.group(1)]),
    (re.compile(r"\bHINDSIGHT\b"), "the best possible"),
    (re.compile(r"\bRANDOM\b"), "chance"),
    (re.compile(r"\bMARKET\b"), "the market average"),
    (re.compile(r"\bINFORMED\b"), "the informed trader"),
    (re.compile(r"\bSP1\b"), "the index playbook"),
    (re.compile(r"\bSP3\b"), "the positional playbook"),
    (re.compile(r"\bSZ2\b"), "the sizing study"),
    (re.compile(r"\bG01\b"), "the exit book"),
    (re.compile(r"\bG02\b"), "the gate"),
    (re.compile(r"\bK02\b"), "the daily-call study"),
    (re.compile(r"\bR01\b"), "the calibration check"),
    (re.compile(r"\bO-0[34](?:/O-0[34])?\b"), "expiry-day"),
    (re.compile(r"\bCTL\b"), "random control"),
    (re.compile(r"\bBRK\b"), "breakout"),
    (re.compile(r"\bPULL\b"), "pullback"),
    (re.compile(r"\bREV\b"), "reversal"),
    (re.compile(r"\bADMITTED\b"), "proved"),
    (re.compile(r"\bSHADOW\b"), "on trial"),
    (re.compile(r"\bLIVE_ELIGIBLE\b"), "ready for real money"),
    (re.compile(r"\bREGISTERED\b"), "registered"),
    (re.compile(r"\bTESTED\b"), "tested"),
    (re.compile(r"\bNOTED\b"), "noted"),
    (re.compile(r"\bDRAFT\b"), "draft"),
    (re.compile(r"\bD8\b"), "the no-copying rule"),
    (re.compile(r"\bthe evidence staircase\b", re.I), "the proving steps"),
    (re.compile(r"\bstaircase\b", re.I), "proving steps"),
    (re.compile(r"\bthe repair board\b", re.I), "the repair shop"),
    (re.compile(r"\bmissed[- ]movers\b", re.I), "missed moves"),
    (re.compile(r"\bthe reference[- ]traders league\b", re.I), "the comparison with other traders"),
    (re.compile(r"\breference traders\b", re.I), "other traders"),
    (re.compile(r"\bthe league\b", re.I), "the comparison with other traders"),
    (re.compile(r"\bshadow sessions\b", re.I), "trial sessions"),
    (re.compile(r"\bdecision days\b", re.I), "trading days"),
    (re.compile(r"\bmanifests?/\S+", re.I), "its file"),
    (re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b"), lambda m: f"{int(m.group(3))} {['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][int(m.group(2)) - 1]}"),
    (re.compile(r"\bIST\b"), "Indian time"),
    (re.compile(r"  +"), " "),
]

CODE_RE = re.compile(r"\b(SP1|SP3|SZ2|G01|G02|K02|R01|CTL|BRK|PULL|REV|REF_POLICY|hold_20d|liq_rank|HINDSIGHT|RANDOM|INFORMED|ADMITTED|SHADOW|LIVE_ELIGIBLE|O-0[34])\b|https?://|/Users/|\bread model\b|\bnotional\b|\bKite\b")


def text(s: str) -> str:
    """One display string, rewritten."""
    out = URL_RE.sub("", s)
    for pat, rep in SENTENCES:
        out = pat.sub(rep, out)
    out = re.sub(r"\b(the|a|an) \1\b", r"\1", out, flags=re.I)                       # "the the index playbook"
    out = re.sub(r"\b([A-Za-z]{3,}) \1\b", r"\1", out)                                # "playbook playbook", "gate gate"
    out = out.replace(" ,", ",").replace(" .", ".").replace(":.", ".").replace("..", ".").strip()
    return out


def scrub(o, key: str = ""):
    """Every display string in an API answer, rewritten; identifiers (no spaces) and the fields the app uses as keys are kept."""
    if isinstance(o, dict):
        return {k: scrub(v, k) for k, v in o.items()}
    if isinstance(o, list):
        return [scrub(v, key) for v in o]
    if isinstance(o, str) and key not in ("id", "key", "route", "link", "sid", "source", "url", "urls", "page", "sha256", "decision_sha") and not IDENT_RE.match(o):
        return text(o)
    return o


def leaks(o) -> list[str]:
    """Strings that still carry a code or an address after scrub (for the test and the nightly check)."""
    out: list[str] = []
    if isinstance(o, dict):
        for k, v in o.items():
            if k in ("id", "key", "route", "link", "sid", "source", "url", "urls", "page", "sha256", "decision_sha"):
                continue
            out += leaks(v)
    elif isinstance(o, list):
        for v in o:
            out += leaks(v)
    elif isinstance(o, str) and not IDENT_RE.match(o) and CODE_RE.search(o):
        out.append(o[:120])
    return out
