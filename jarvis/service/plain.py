"""Plain words on every screen (plan 2.3). One dictionary of display names, built from docs/knowledge/glossary.json ("names") and
the watch catalogue (docs/knowledge/watches.json). Internal codes (E4, H07, T3, P02, V02, TK13...) stay inside the system: the API
keeps pure identifiers as they are (the app looks them up with /v3/names), and every sentence or label it sends is rewritten so
no code reaches a screen. tests/test_plain_words.py fails if one does.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

KNOW = Path(__file__).resolve().parents[2] / "docs" / "knowledge"
CODE = r"(?:H07-T30|T3-B|ZONE_TOUCH|JARVIS_RANDOM|T3_TREND(?:_T30)?|REGIME_V02|E\d{1,2}|H\d{2}|T\d{1,2}|P\d{2}|V\d{2}|TK\d+|R\d{2})"
CODE_RE = re.compile(rf"\b{CODE}\b")
# a code in brackets after its own name: "Dip trade (H07)", "(T3-B on 10 coins)" keeps the words, drops the code
PAREN_RE = re.compile(rf"\s*\(\s*{CODE}(?:\s*[,;·]\s*{CODE})*\s*\)")
RANGE_RE = re.compile(rf"\b({CODE})\s*[-–]\s*({CODE})\b")
IDENT_RE = re.compile(r"^[A-Za-z0-9_:\-./#]+$")      # a pure identifier ("E1", "BCH-1791504000-E6-86", "explorer:E6"): left for the app


@lru_cache(maxsize=1)
def names() -> dict[str, str]:
    out: dict[str, str] = {}
    try:
        w = json.loads((KNOW / "watches.json").read_text())
        def walk(o):
            if isinstance(o, dict):
                if isinstance(o.get("id"), str) and isinstance(o.get("name"), str):
                    out[o["id"]] = o["name"]
                for v in o.values():
                    walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)
        walk(w.get("watches") or [])
    except (OSError, ValueError):
        pass
    try:
        out.update(json.loads((KNOW / "glossary.json").read_text()).get("names") or {})
    except (OSError, ValueError):
        pass
    return out


def short(code: str) -> str:
    """The name to use inside a sentence: 'Deep dip (15-minute RSI under 30)' -> 'deep dip'."""
    n = name(code)
    if n == code:
        return code
    n = re.sub(r"\s*\([^)]*\)", "", n).strip()
    if n.split(" ")[0] in ("Bitcoin", "Explorer", "Ananta's", "Jarvis's") or n[:2] == n[:2].upper():
        return n
    return n[:1].lower() + n[1:]


def name(code: str) -> str:
    c = str(code)
    if c in names():
        return names()[c]
    m = re.fullmatch(r"TK(\d+)", c)
    if m:
        return f"Repair ticket {m.group(1)}"
    m = re.fullmatch(r"R(\d{2})", c)
    if m:
        return f"Review {int(m.group(1))}"
    m = re.fullmatch(r"([EHVPT])(\d{1,2})", c)                    # a code with no name yet: say what kind of thing it is
    if m:
        kind = {"E": "Setup", "H": "Idea", "V": "Checked rule", "P": "Risk rule", "T": "Tier"}[m.group(1)]
        return f"{kind} {int(m.group(2))}"
    m = re.fullmatch(r"explorer:(\w+)", c)
    if m:
        return f"Explorer: {short(m.group(1))}"
    return c


JARVIS_RE = re.compile(r"\bJarvis\b")


def _range(m: re.Match) -> str:
    before = m.string[:m.start()].rstrip().lower()
    if before.endswith(("setups", "setup", "trades")):          # "Dip setups E6-E8 are watched" -> "Dip setups are watched"
        return ""
    return f"{short(m.group(1))} to {short(m.group(2))}"


def text(s: str) -> str:
    """Rewrite one sentence or label so it carries names, not codes (and Ananta's name, not the old one)."""
    if not s:
        return s
    s = JARVIS_RE.sub("Ananta", s)
    if not CODE_RE.search(s):
        return s
    lead = bool(CODE_RE.match(s))
    s = PAREN_RE.sub("", s)
    s = RANGE_RE.sub(_range, s)
    s = CODE_RE.sub(lambda m: short(m.group(0)), s)
    s = re.sub(r"\s{2,}", " ", s).replace(" ,", ",").strip()
    return s[:1].upper() + s[1:] if lead else s


def scrub(o, key: str = ""):
    """Every display string in an API answer, rewritten; identifiers (no spaces) are kept for the app to look up."""
    if isinstance(o, dict):
        return {k: scrub(v, k) for k, v in o.items()}
    if isinstance(o, list):
        return [scrub(v, key) for v in o]
    if isinstance(o, str) and not IDENT_RE.match(o):
        return text(o)
    return o
