"""Every figure Ananta says must come from its facts (3 Nov 2026, the outside trader's grade).

In the 3 Nov re-test Ananta said a Bank Nifty lot's premium was "about Rs 53,500"; it was Rs 24,699 (823.3 x 30). The number was the model's
own arithmetic. Fixing that one field did not fix the class, so every rupee amount and every number of 100 or more in an answer is looked
for in the facts the answer was given (and the question). A figure counts as found when a fact number is within 2% of it, or when it is
a round figure (to the nearest 10, 50, 100 or 1,000) of a fact number. Times (09:15), dates and years are not checked.

  check(answer, facts, question)  -> list of problem lines (empty when every figure is found)
  scrub(answer, figures)          -> the answer without the sentences that carry an unfound figure
"""
from __future__ import annotations

import json
import re

NUM = re.compile(r"(?<![\d:/.-])(?:(?:rs\.?|₹)\s*)?(\d{1,3}(?:,\d{2,3})+|\d+)(?:\.(\d+))?(?![\d:/-])", re.I)
YEAR = range(1990, 2036)


def _val(m: re.Match) -> float:
    whole = m.group(1).replace(",", "")
    return float(whole + ("." + m.group(2) if m.group(2) else ""))


def numbers_in(text: str) -> set[float]:
    return {_val(m) for m in NUM.finditer(text or "")}


def _wanted(answer: str) -> list[tuple[str, float]]:
    """(the figure as written, its value) for the figures to check: rupee amounts, and other numbers of 100 or more that are not years."""
    out = []
    for m in NUM.finditer(answer or ""):
        v = _val(m)
        rupee = bool(re.match(r"(?:rs\.?|₹)", m.group(0), re.I))
        tail = answer[m.end():m.end() + 12].lower()
        if not rupee and (v < 100 or (v in YEAR and "." not in m.group(0)) or re.match(r"\s*(?:%|percent|ist|am|pm|bp|basis)", tail)):
            continue
        if re.match(r"\s*(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)", tail):
            continue
        out.append((m.group(0).strip(), v))
    return out


def _found(v: float, pool: list[float]) -> bool:
    for p in pool:
        if p == 0:
            continue
        if abs(v - p) <= 0.02 * abs(p):
            return True
        for r in (10, 50, 100, 1000):
            if v % r == 0 and abs(v - p) < r and v >= r:
                return True
    return False


RUPEE_KEY = re.compile(r"inr|rs\b|rupee|value|pnl|p&l|price|premium|paid|cost|amount|cash|capital|crore|net|gain|loss|_cr\b|suggest|book", re.I)
RUPEE_TXT = re.compile(r"(?:rs\.?|₹)\s*-?\s*(\d{1,3}(?:,\d{2,3})+|\d+)(?:\.(\d+))?", re.I)


def rupee_pool(facts) -> set[float]:
    """Numbers that are rupees in the facts: values under a money-like key, and figures written after Rs or ₹ in any text."""
    out: set[float] = set()

    def walk(o, key=""):
        if isinstance(o, dict):
            for k, v in o.items():
                walk(v, str(k))
        elif isinstance(o, list):
            for v in o:
                walk(v, key)
        elif isinstance(o, (int, float)) and not isinstance(o, bool):
            if RUPEE_KEY.search(key):
                out.add(abs(float(o)))
        elif isinstance(o, str):
            for m in RUPEE_TXT.finditer(o):
                out.add(float(m.group(1).replace(",", "") + ("." + m.group(2) if m.group(2) else "")))
    walk(facts)
    return out


def check(answer: str, facts: dict, question: str = "") -> list[str]:
    allnums = sorted(numbers_in(json.dumps(facts, default=str, ensure_ascii=False)) | numbers_in(question))
    pool = [abs(x) for x in allnums if x]
    rpool = sorted(rupee_pool(facts) | {abs(x) for x in numbers_in(question)})
    bad = []
    for w, v in _wanted(answer):
        rupee = bool(re.match(r"(?:rs\.?|₹)", w, re.I))
        if not _found(v, rpool if rupee else pool):
            bad.append(w)
    return [f"the figure {w} is not in the facts (Ananta may not work numbers out itself; quote a fact or leave it out)" for w in dict.fromkeys(bad)]


def figures(problems: list[str]) -> list[str]:
    return [m.group(1) for p in problems for m in [re.match(r"the figure (.+?) is not in the facts", p)] if m]


def scrub(answer: str, figs: list[str]) -> str:
    sents = re.split(r"(?<=[.!?])\s+", answer or "")
    keep = [s for s in sents if not any(f in s for f in figs)]
    return " ".join(keep).strip() or answer
