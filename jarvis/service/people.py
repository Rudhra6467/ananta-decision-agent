"""Madhav's important people (Oct 10, 2026): who they are, how Ananta talks to each, and introduce mode.

The list itself is private and lives OUTSIDE every repository: ~/ananta_private/people.json (or PEOPLE_FILE). This module only
reads it. Nothing here creates accounts (Madhav: no guest accounts until he asks for one).

  load()                    the file (empty when missing)
  find(name)                one person by any of their names
  talking_to(j, thread)     who Ananta is talking with in this conversation right now (None = Madhav)
  introduce(j, thread, name) Madhav hands the conversation to someone ("Ananta, this is Sam")
  back(j, thread)           Madhav is back
  prompt_note(j, thread)    the note added to Ask's message: the person's profile and opener, or a short who's-who for Madhav
"""
from __future__ import annotations

import json
import os
import time
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

_CACHE: dict = {"m": None, "v": {}}


def path() -> Path:
    return Path(os.getenv("PEOPLE_FILE") or Path.home() / "ananta_private" / "people.json")


def load() -> dict:
    p = path()
    try:
        m = p.stat().st_mtime
    except OSError:
        return {}
    if _CACHE["m"] != m:
        try:
            _CACHE.update(m=m, v=json.loads(p.read_text()))
        except Exception:  # noqa: BLE001  a broken edit never breaks Ask
            return _CACHE["v"] or {}
    return _CACHE["v"]


def _norm(s: str) -> str:
    return " ".join((s or "").lower().replace(".", " ").split())


def find(name: str) -> dict | None:
    n = _norm(name)
    if not n:
        return None
    people = load().get("people") or []
    for p in people:                                   # exact name first ("Ravi Kumar" must not match Dad)
        if any(_norm(x) == n for x in p.get("names") or []) or _norm(p.get("id", "")) == n:
            return p
    for p in people:
        if any(n in _norm(x) or _norm(x) in n for x in p.get("names") or []):
            return p
    return None


def resolve(phrase: str) -> dict | None:
    """A person from free words: a name ("Chintu") or a relation ("my sister's son", "amma"). Longest match wins, so "my sister's son"
    is the nephew, not his mother; a first name alone means the person whose name it is exactly (plan Batch 2, Oct 11)."""
    t = " " + _norm(phrase).replace("’", "'") + " "
    best, size = None, 0
    for p in load().get("people") or []:
        for w in list(p.get("names") or []) + list(p.get("relations") or []):
            k = _norm(w).replace("’", "'")
            if k and f" {k} " in t and len(k) > size:
                best, size = p, len(k)
    return best


_WHO = r"(?P<who>[a-z' ]{2,40}?)"
_END = r"(?=[.,!?;]|\s+(?:please|now|here|ji|garu)\b|$)"
HANDOVER = [re.compile(x, re.I) for x in (
    r"\b(?:talk|speak|chat)\s+(?:to|with)\s+" + _WHO + _END,
    r"\bsay\s+(?:hi|hello|namaskaram)\s+to\s+" + _WHO + _END,
    r"\b(?:meet|greet|introduce yourself to)\s+" + _WHO + _END,
    r"\bthis is\s+" + _WHO + _END,
    r"\b" + _WHO + r"\s+(?:is|are)\s+(?:here|with me|on the line|talking)\b",
    r"\b" + _WHO + r"\s+wants?\s+to\s+(?:talk|speak|ask|say|chat)\b",
    r"\b" + _WHO + r"\s+tho\s+(?:matladu|maatladu|matladandi|maatladandi|matladu ra|matladava|maatladava)\b",
)]
RELAY = re.compile(r"\b" + _WHO + r"\s+(?:is asking|asks|asked|wants to know|is saying|says)\b", re.I)
BACK = re.compile(r"\b(?:i'?m back|i am back|it'?s me|it is me|madhav here|vamsi here|this is (?:madhav|vamsi)|back to me)\b", re.I)


def route(j, thread: str | None, text: str) -> dict | None:
    """What Madhav's message means for who is speaking, decided by code, not the AI (the Oct 10 log: the AI guessed wrong):
    {"kind": "back"} | {"kind": "handover", "person"} | {"kind": "relay", "person"} | None."""
    t = (text or "").replace("’", "'")
    now = talking_to(j, thread)
    if BACK.search(t):
        return {"kind": "back"} if now else None
    for rx in HANDOVER:
        for m in rx.finditer(t):
            p = resolve(m.group("who"))
            if p:
                return {"kind": "handover", "person": p, "same": bool(now and now["id"] == p["id"])}
    m = RELAY.search(t)
    if m:
        p = resolve(m.group("who"))
        if p:
            return {"kind": "relay", "person": p}
    return None


def set_speaker(j, thread: str, p: dict) -> None:
    _table(j)
    j.db.execute("INSERT OR REPLACE INTO people_session VALUES (?,?,?)", (thread, p["id"], int(j.now())))
    j.db.commit()


def opener(p: dict) -> str:
    part, _ = _part(p.get("tz"))
    return (p.get("opener") or "").replace("{part}", part)


def _table(j) -> None:
    j.db.execute("CREATE TABLE IF NOT EXISTS people_session (thread TEXT PRIMARY KEY, person TEXT, t INTEGER)")


def talking_to(j, thread: str | None) -> dict | None:
    if not thread:
        return None
    try:
        _table(j)
        r = j.db.execute("SELECT person, t FROM people_session WHERE thread=?", (thread,)).fetchone()
    except Exception:  # noqa: BLE001
        return None
    if not r or j.now() - r[1] > 3 * 3600:              # an introduction lasts the conversation, at most 3 hours
        return None
    return find(r[0])


def introduce(j, thread: str | None, name: str) -> dict:
    p = find(name) or resolve(name)
    if not p:
        known = ", ".join(x["names"][0] for x in load().get("people") or [])
        return {"error": f"I don't have {name} in sir's list of people yet" + (f" (I know: {known})" if known else "")
                         + ". Greet them kindly as a friend of Madhav, and Madhav can add them to the list."}
    if not thread:
        return {"error": "no conversation to hand over"}
    _table(j)
    j.db.execute("INSERT OR REPLACE INTO people_session VALUES (?,?,?)", (thread, p["id"], int(j.now())))
    j.db.commit()
    part, tz = _part(p.get("tz"))
    return {"now_talking_to": p["names"][0], "relation": p.get("relation"), "call_them": p.get("call"),
            "language": LANG.get(p.get("language"), "English"), "style": p.get("style"), "their_time": f"{part} ({tz})",
            "opener": (p.get("opener") or "").replace("{part}", part),
            "do_now": "Reply ONLY with the greeting to them now: their opener, in their language, warm and natural (light fixes are fine). "
                      "From the next message on you are talking with them directly."
                      + (" This is a child: keep it short, gentle and age-appropriate." if p.get("group") == "family_kid" else "")}


def back(j, thread: str | None) -> dict:
    if thread:
        _table(j)
        j.db.execute("DELETE FROM people_session WHERE thread=?", (thread,))
        j.db.commit()
    return {"now_talking_to": "Madhav (sir)"}


def _part(tz: str | None) -> tuple[str, str]:
    tz = tz or "America/Toronto"
    try:
        h = datetime.now(ZoneInfo(tz)).hour
    except Exception:  # noqa: BLE001
        tz, h = "America/Toronto", datetime.now(ZoneInfo("America/Toronto")).hour
    return ("morning" if 4 <= h < 12 else "afternoon" if 12 <= h < 17 else "evening"), tz     # after midnight is still evening


LANG = {"telugu": "Telugu in English letters, with English only for trading words (respect forms from the guide)",
        "telugu_mix": "a natural Telugu-English mix in English letters", "mix": "a playful Telugu-English mix in English letters",
        "english": "English (switch to Telugu in English letters if they write in Telugu)"}


def prompt_note(j, thread: str | None) -> str:
    d = load()
    if not d.get("people"):
        return ""
    p = talking_to(j, thread)
    if not p:
        who = "; ".join(f"{x['names'][0]} ({x.get('relation', '')})" for x in d["people"])
        return ("[PEOPLE: Madhav's important people: " + who + ". If Madhav introduces one of them or hands over ('this is Sam', "
                "'talk to my mom'), call introduce with their name and say hello to them in their style. If Madhav asks you to write to one of them, "
                "write it in their style and language. Never share one person's details with another.]")
    part, tz = _part(p.get("tz"))
    lines = [f"[TALKING TO: you are now talking directly with {p['names'][0]}, {p.get('relation')}, NOT with Madhav. Do not call them sir "
             f"unless their profile says so; call them: {p.get('call')}. It is {part} where they are ({tz}).",
             f"Language: {LANG.get(p.get('language'), 'English')}. Style: {p.get('style', '')}",
             "You already greeted them (their opener was: " + (p.get("opener") or "").replace("{part}", part)[:300] + "). Continue naturally "
             "and answer what they just said FIRST (if they ask how you are, say how you are), in their language and style (use the web "
             "when needed). Telugu must be simple, correct, spoken Telugu (e.g. 'Nenu baagunnanu andi, meeru ela unnaru?'); "
             "if unsure of a Telugu phrase, use a simpler one or the English word.",
             "Topics: " + "; ".join(p.get("talk_about") or []) + (". Avoid: " + "; ".join(p["avoid"]) if p.get("avoid") else ""),
             "Rules: " + " ".join(d.get("rules") or [])]
    if p.get("language") in ("telugu", "telugu_mix", "mix"):
        g = d.get("telugu_guide") or {}
        lines.append("Telugu guide: " + g.get("respect", "") + " " + g.get("mix", "") + " Words: "
                     + ", ".join(f"{k} = {v}" for k, v in (g.get("words") or {}).items()))
    if p.get("group") == "family_kid":
        lines.append("This is a child: short, gentle, playful, age-appropriate; no money, trading or investing; never ask for personal details.")
    lines.append("Madhav may still type here: a message asking you to talk to another of his people is Madhav handing over, so call "
                 "introduce with that person (never refuse it); a message that says what this person is asking is Madhav passing their "
                 "question on: answer it to them, in their language. If you are not sure what they are asking, ask them back in one short "
                 "question in their language. If Madhav comes back ('it's me', 'I'm back'), call back_to_madhav.]")
    return "\n".join(lines)


def voice_language(j, thread: str | None) -> str:
    """'te' when the person in this conversation is spoken to in Telugu, else 'en' (the voice picks the Telugu engine)."""
    p = talking_to(j, thread)
    return "te" if p and p.get("language") in ("telugu", "telugu_mix", "mix") else "en"
