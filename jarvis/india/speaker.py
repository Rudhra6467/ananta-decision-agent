"""Who is speaking in an India Ask conversation (Madhav, 27 Oct: "I will ask Ananta here to talk to a grader, like I use to ask it to talk to
my mom and my dad ... But Ananta should understand when it's me. Even sometimes when I say Ananta it's me, it won't recognise me well").

Decided in code, per conversation, before any model call (the crypto Ask's rule since Oct 10-11; jarvis/service/people.py):
  route(thread, text)  -> {"kind": "handover", "person"} | {"kind": "back", "rest"} | {"kind": "owner_only"} | {"kind": "ask_who"} | None
  current(thread)      -> the guest Ananta is talking with now, or None (= Madhav); a handover lasts the conversation, at most 3 hours
  greeting(person)     -> what Ananta says to them first
  prompt_note(person)  -> the block added to the model's message while a guest is talking
  label(thread)        -> {"name", "role"} for the app (who Ananta thinks it is talking with)

People: Madhav's private people note (~/ananta_private/people.json, read through jarvis.service.people; never in git) for family and friends,
and observers by role: "the grader" / tester / examiner, whom Madhav brings in to grade Ananta. An observer may hear everything Madhav could
(the books, the account, the tests); nobody but Madhav can approve, say yes to a fix, file a flag or change anything.
(The voice-print helper is jarvis/india/voiceid.py.)
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

from jarvis.service import people

ASK_DIR = Path(os.getenv("ANANTA_INDIA_DATA", os.path.expanduser("~/ananta_data/india"))) / "ask"
TTL = 3 * 3600
OWNER = people.OWNER_HEARD + r"(?!'s|’s)"           # his names as speech-to-text writes them (Madhav, Vamsi ...), not "Madhav's account"
_FILL = r"(?:(?:uh+|um+|er+|ah+|hmm+|so|okay|ok|hey|hi|hello|yeah|yes|right|well|and|ananta|anantha|anant|jarvis|sir)[\s,.!-]*)*"
# His return, with speech fillers and stutters ("uh, Ananta, it's, it's me"): checked on the message with fillers and repeats squeezed out
BACK = re.compile(
    r"\b(?:it'?s (?:me|really me|" + OWNER + r")|it is (?:me|" + OWNER + r")|(?:this is|i am|i'?m) (?:me|" + OWNER + r")\b(?! ?'?s)|" + OWNER + r" (?:here|again|back|speaking)"
    r"|i'?m back|i am back|back to me|(?:talk|switch|come) (?:back )?to me|i'?ll take (?:it|over) from here|i will take (?:it|over) from here"
    r"|(?:the )?(?:grader|tester|examiner|evaluator)(?:'?s| is| has)? (?:done|finished|gone|over)|(?:she|he|they)'?(?:s| is| are|re) (?:gone|done)|(?:she|he) left"
    r"|nenu " + OWNER + r"|it'?s you(?:r)? (?:boss|owner)|madhav calling)\b", re.I)
IDENT = re.compile(r"\b(?:it'?s (?:me|really me|" + OWNER + r")|it is (?:me|" + OWNER + r")|(?:this is|i am|i'?m) " + OWNER + r"|"
                   + OWNER + r" (?:here|again|back|speaking))\b", re.I)
# What only Madhav does: approvals, fix picks, flags, changes to the books or the account
OWNER_ONLY = re.compile(
    r"\b(?:yes to (?:all|everything|your|the|that|these|those)|i (?:say )?yes|go ahead|approved?|approval|i approve|confirm(?:ed)?|"
    r"(?:pick|choose|use|go with) (?:fix|option) ?\d|fix (?:\d|one|two|three)\b|flag (?:this|it|that)|note (?:this|it) for research|"
    r"(?:file|log|raise) (?:a |the )?(?:flag|bug|issue)|deploy|kill switch|go autonomous|switch (?:to )?(?:autonomous|advisory)|"
    r"(?:move|sell|buy|trim|exit|add to) (?:my|the) (?:holdings?|account|capital|money)|change (?:the|my) (?:rules?|allocation|plan))\b", re.I)
OWNER_TOPIC = re.compile(r"\b(?:my account|my portfolio|my holdings|my flags?|my requests?|my money|my capital)\b", re.I)
OBSERVER = re.compile(r"\b(?:the |our |my |an? )?(?P<role>grader|greater|grater|grade her|tester|examiner|evaluator|judge|reviewer|auditor|interviewer|assessor)\b", re.I)
# 27 Oct voice session: Whisper writes "grader" as "greater" / "grater" / "grade her"; inside a handover or an introduction they mean the grader
ROLE_ALIAS = {"greater": "grader", "grater": "grader", "grade her": "grader"}
# The grader introducing itself ("No, you're talking to the greater ... I'm the greater and Ananta's the one"; "grader here: ...")
SELF_INTRO = re.compile(
    r"\b(?:i'?m|i am|this is|it'?s|it is|you'?re (?:talking|speaking) (?:to|with)|you are (?:talking|speaking) (?:to|with))\s+(?:the |your |an? )?"
    r"(?P<role>grader|greater|grater|grade her|tester|examiner|evaluator)\b(?!\s+(?:than|chance|risk|return|number|part|good))"
    r"|^\W*(?:(?:hi|hello|hey|okay|ok|so)[\s,.!]+)*(?:the )?(?P<role2>grader|greater|grater|tester|examiner) (?:here|speaking)\b", re.I)
AFFIRM = re.compile(r"^\W*(?:yes|yeah|yep|yup|correct|right|that'?s right|that is right|i am|yes,? i am|yes,? (?:it'?s|this is) (?:the )?(?:grader|greater))"
                    r"(?:,? (?:the )?(?:grader|greater))?[\s.!]*$", re.I)
MOM_DAD = re.compile(r"\bmy (?P<rel>mom|mum|mother|amma|mummy|dad|father|nanna|daddy)\b", re.I)
_WHO = r"(?P<who>[A-Za-z' ]{2,40}?)"
_END = r"(?=[.,!?;:]|\s+(?:please|now|here|for a (?:bit|while|moment)|ji|garu)\b|$)"
# (pattern, strong): a strong pattern ("talk to X") may introduce someone not in the people note; a weak one ("this is X", "X is here")
# only a known person or an observer, so "This is a bad answer" or "TATAPOWER is here" never becomes a guest
HANDOVER = [(re.compile(x, re.I), strong) for x, strong in (
    (r"\b(?:talk|speak|chat)\s+(?:to|with)\s+" + _WHO + _END, True),
    (r"\bsay\s+(?:hi|hello|namaskaram)\s+to\s+" + _WHO + _END, True),
    (r"\b(?:meet|greet|introduce yourself to)\s+" + _WHO + _END, True),
    (r"\b(?:i'?m |i am )?(?:handing|passing|giving|putting) (?:you |this |it |the (?:mic|phone|conversation) )?(?:over )?(?:to|on to)\s+" + _WHO + _END, True),
    (r"^\s*" + _FILL + r"this is\s+" + _WHO + _END, False),
    (r"\b" + _WHO + r"\s+(?:is|are)\s+(?:here|with me|on the line|joining|going to (?:ask|talk|grade))\b", False),
    (r"\b" + _WHO + r"\s+wants?\s+to\s+(?:talk|speak|ask|chat|grade)\b", False),
)]
NOT_A_PERSON = re.compile(r"^(?:me|you|him|her|them|it|this|that|us|who|what|which|there|here|nobody|no one|everything|nothing|something|someone|somebody|"
                          r"anyone|everyone|people|my people|market|the market|nifty|bank nifty|sensex|ananta|jarvis|india|indian market|crypto|flags?|app|"
                          r"chart|screen|support|resistance|stocks?|options?|price|book|books|account|portfolio|news|data|ai|model|chatgpt|claude)$", re.I)
MARKET_WORDS = re.compile(r"\b(?:market|mood|trend|price|prices|stocks?|shares?|nifty|sensex|index|chart|data|numbers?|book|books|rules?|plan|news|"
                          r"rupee|dollar|gold|oil|crude|options?|futures?|volume|support|resistance|average|averages)\b", re.I)


def _path() -> Path:
    try:                                   # the Ask's own folder (tests move it), else the default
        from jarvis.india import ask
        return Path(ask.ASK_DIR) / "speakers.json"
    except Exception:  # noqa: BLE001
        return ASK_DIR / "speakers.json"


def _load() -> dict:
    try:
        return json.loads(_path().read_text())
    except (OSError, ValueError):
        return {}


def _save(d: dict) -> None:
    _path().parent.mkdir(parents=True, exist_ok=True)
    now = time.time()
    _path().write_text(json.dumps({k: v for k, v in d.items() if now - float(v.get("t", 0)) < TTL}, indent=1))


def current(thread: str | None) -> dict | None:
    if not thread:
        return None
    s = _load().get(thread)
    if not s or time.time() - float(s.get("t", 0)) > TTL:
        return None
    return s


def set_guest(thread: str, person: dict) -> None:
    d = _load()
    d[thread] = {**person, "t": time.time(), "log": (d.get(thread, {}).get("log") or [])[-10:] + [[int(time.time()), "in", person.get("name")]]}
    _save(d)


def clear(thread: str) -> None:
    d = _load()
    d.pop(thread, None)
    _save(d)


def label(thread: str | None) -> dict:
    s = current(thread)
    return {"name": s.get("name"), "role": s.get("role"), "since": int(s.get("t", 0))} if s else {"name": "Madhav", "role": "owner"}


def _squeeze(text: str) -> str:
    """Speech fillers and stutters out ("uh, Ananta, it's, it's me" -> "it's me")."""
    t = (text or "").replace("’", "'").replace("‘", "'")
    t = re.sub(r"\b(\w+(?:'\w+)?)(?:[\s,.-]+\1\b)+", r"\1", t, flags=re.I)          # "it's, it's" -> "it's"
    t = re.sub(r"\b(?:uh+|um+|er+|ah+|hmm+)\b[\s,.-]*", "", t, flags=re.I)
    return re.sub(r"\s+", " ", t).strip()


def person_for(who: str, unknown_ok: bool = True) -> dict | None:
    """A guest from the words after 'talk to': an observer role, a family member from the people note, or (strong patterns only) a named guest."""
    raw = (who or "").strip(" .,!?'\"")
    w = re.sub(r"^(?:the|our|my|a|an)\s+", "", raw, flags=re.I).strip()
    if not w or NOT_A_PERSON.match(w) or NOT_A_PERSON.match(raw) or people.is_owner_name(w):
        return None
    m = OBSERVER.search(who)
    if m:
        return observer(m.group("role"))
    try:
        p = people.resolve(who) or people.find(w)
    except Exception:  # noqa: BLE001
        p = None
    if p:
        return {"id": p.get("id"), "name": (p.get("names") or [w])[0], "role": "family" if str(p.get("group", "")).startswith("family") else "guest",
                "call": p.get("call") or (p.get("names") or [w])[0], "person": p}
    named = any(x[:1].isupper() for x in raw.split() if x.lower() not in ("the", "our", "my", "a", "an"))
    if (unknown_ok and not MARKET_WORDS.search(w) and (named or len(w.split()) == 1) and len(w.split()) <= 3 and w[:1].isalpha()
            and not re.search(r"\d", w)):
        nm = " ".join(x[:1].upper() + x[1:] for x in w.split())
        return {"id": re.sub(r"[^a-z0-9]+", "_", w.lower()), "name": nm, "role": "guest", "call": nm}
    return None


def route(thread: str | None, text: str) -> dict | None:
    t = _squeeze(text)
    now = current(thread)
    b = BACK.search(t)
    if b:
        rest = (t[:b.start()] + " " + t[b.end():]).strip(" ,.!-")
        if not now:
            # no guest: only a bare "Ananta, it's me" is about who is speaking (a short "yes, sir"); "talk to me about RSI" is a question
            return {"kind": "back", "rest": "", "was": None} if IDENT.search(t) and not _rest(rest) else None
        return {"kind": "back", "rest": _rest(rest), "was": now}
    si = SELF_INTRO.search(t)
    if si:                                   # 27 Oct: the grader introduces itself (ask.py ignores it when the voice print says Madhav)
        p = observer(si.group("role") or si.group("role2"))
        if now and now.get("id") == p["id"]:
            return None
        rest = _rest((t[:si.start()] + " " + t[si.end():]).strip(" ,.!-:"))
        rest = re.sub(r"^(?:no|yes|okay|understood|and)\b[\s,.!]*", "", rest, flags=re.I) if rest else rest
        rest = re.sub(r"\b(?:and )?ananta'?s the one\b[\s,.!]*", "", rest, flags=re.I).strip(" ,.!-") if rest else rest
        return {"kind": "handover", "person": p, "self_intro": True, "rest": rest if "?" in (rest or "") else ""}
    for rx, strong in HANDOVER:
        for m in rx.finditer(t):
            p = person_for(m.group("who"), unknown_ok=strong)
            if p:
                if now and now.get("id") == p["id"]:
                    return None
                return {"kind": "handover", "person": p}
    m = MOM_DAD.search(t)
    if m and re.search(r"\b(?:is|are) (?:here|with me|on the line)\b|\bsay (?:hi|hello)\b", t, re.I):
        p = person_for("my " + m.group("rel"))
        if p:
            return {"kind": "handover", "person": p}
    if now and OWNER_ONLY.search(t):
        return {"kind": "owner_only", "was": now}
    if now and OWNER_TOPIC.search(t) and now.get("role") != "observer":
        return {"kind": "ask_who", "was": now}
    return None


def observer(role: str) -> dict:
    """An observer guest from its role word ('greater' is Whisper's 'grader')."""
    r = re.sub(r"\s+", " ", (role or "grader").lower().strip())
    r = ROLE_ALIAS.get(r, r)
    return {"id": r, "name": "the " + r, "role": "observer", "call": r}


# ---- a voice the voice print says is clearly not Madhav, with no handover (27 Oct): no "sir", and once "Am I speaking with the grader?"
def _vkey(thread: str) -> str:
    return f"{thread}#voice"


def stranger_tick(thread: str) -> dict:
    d = _load()
    st = d.get(_vkey(thread)) or {"n": 0, "asked": False}
    st = {"n": int(st.get("n", 0)) + 1, "asked": bool(st.get("asked")), "t": time.time()}
    d[_vkey(thread)] = st
    _save(d)
    return st


def stranger_mark_asked(thread: str) -> None:
    d = _load()
    st = d.get(_vkey(thread)) or {"n": 0}
    d[_vkey(thread)] = {**st, "asked": True, "t": time.time()}
    _save(d)


def stranger_reset(thread: str) -> None:
    d = _load()
    if d.pop(_vkey(thread), None) is not None:
        _save(d)


def _rest(s: str) -> str:
    """What is left of his message once 'Ananta, it's me again' is taken out: a question to answer, or ''."""
    s = re.sub(r"^\s*" + _FILL, "", s or "", flags=re.I).strip(" ,.!-")
    s = re.sub(r"^(?:again|now|back|here)\b[\s,.!-]*", "", s, flags=re.I).strip(" ,.!-")
    return s if len(re.findall(r"[A-Za-z]{2,}", s)) >= 3 else ""


def greeting(p: dict) -> str:
    if p.get("role") == "observer":
        return (f"Hello, {p['call']}. I'm Ananta, Madhav's paper-trading assistant for the Indian market. Ask me anything about the market, "
                "the practice books or my tests; anything that needs a yes stays with Madhav.")
    if p.get("person"):
        try:
            o = people.opener(p["person"])
            if o:
                return o
        except Exception:  # noqa: BLE001
            pass
    return f"Hello {p['call']}! I'm Ananta, the trading assistant Madhav built for the Indian market. Lovely to meet you. What would you like to know?"


def prompt_note(p: dict) -> str:
    """Added to the model's message while a guest is talking (the crypto Ask's TALKING TO block, for India)."""
    base = (f"[TALKING TO: you are now talking with {p['name']}, NOT with Madhav. Do not call them sir; call them {p.get('call')}. "
            "Approvals, yes to fixes, flags and any change belong to Madhav only: if they ask for one, say it needs Madhav's yes. "
            "If Madhav comes back ('it's me', 'Madhav here') that is handled in code before you.")
    if p.get("role") == "observer":
        return base + (" They are an observer Madhav brought in to grade you: answer exactly as you would answer Madhav (the books, his account, "
                       "the tests, in plain words and just as briefly), only without calling them sir.]")
    pp = p.get("person") or {}
    lines = [base, f"Who they are: {pp.get('relation') or 'a guest of Madhav'}.",
             f"Language: {people.LANG.get(pp.get('language'), 'English')}. Style: {pp.get('style') or 'warm, simple and respectful'}.",
             "Keep it simple and kind; no jargon; do not share Madhav's account details unless Madhav has said so; never give them a trading instruction."]
    if pp.get("group") == "family_kid":
        lines.append("This is a child: short, gentle, playful; no money or trading.")
    return " ".join(lines) + "]"


def address(answer: str, p: dict | None) -> str:
    """A code-built answer says 'Sir, ...': to a guest it uses their name instead."""
    if not p or not answer:
        return answer
    call = p.get("call") or ""
    a = re.sub(r"^(?:Yes|No|Okay|Sure|Good morning|Sorry|Thank you),?\s+sir\b", lambda m: m.group(0)[: -len(" sir")] + (f" {call}" if call else ""), answer)
    a = re.sub(r"^Sir,\s*", (call[:1].upper() + call[1:] + ", ") if call else "", a)
    a = re.sub(r",\s*sir([.!?,])", r"\1", a)
    a = re.sub(r"\bsir,\s*", "", a)
    return a[:1].upper() + a[1:] if a else a
