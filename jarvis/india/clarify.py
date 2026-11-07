"""Clarifying questions (7 Nov 2026, Madhav: "like ChatGPT ... only for some important questions and when it needs more information").

Ananta asks one question with choices, in code, before any flow or the model, and only where a wrong guess would cost something:
  * "approve it" / "skip it" when more than one draft waits (one draft: no question, it is that one);
  * "how is the book doing?" with no book named, because four things are called a book here;
  * "flag it" when nothing came before it in the conversation (nothing to point back to).
Never for a fact question. One round at most: his next message is matched to a choice (a tap sends the choice's words; by voice "the second
one", "2", or the words of the choice) and becomes the full question, which is then answered as if he had asked it that way. A message that
matches no choice drops the question and is answered on its own; a question older than ten minutes is forgotten.

The app already shows "Did you mean" choices as tappable chips and the voice speaks them ("1. ... 2. ..."), so nothing new is learned.
Every question and what came of it goes to reports/ask_clarify.jsonl, read by the Ask's facts ("how often do you ask me which one I mean?"),
which is the feature's route on the fact map; the nightly harness asks the feature question (neveragain.FEATURE_QS)."""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

PENDING_SECONDS = 10 * 60
LOG_NAME = "ask_clarify.jsonl"

_FILL = r"(?:(?:yes|yeah|yep|ok(?:ay)?|sure|please|alright|ananta|hey ananta|so|then)[\s,.!]*)*"
APPROVE_BARE = re.compile(rf"^\s*{_FILL}(approve|register|accept|skip|reject|drop)\s+(?:it|that|this|this one|that one|the draft|the one|them)"
                          rf"(?:\s+(?:please|now|then|for me))?[\s.!]*$", re.I)
BOOK_BARE = re.compile(r"^\s*(?:(?:hey |hi |ok )?ananta,?\s*)?(?:how is|how's|how are|how did|how was|what about|and|so|is)\s+(?:the |our |my )?(?:paper )?books?\b"
                       r"(?:\s+(?:doing|going|performing|today|now|so far|these days|this week|holding up))*\s*\??\s*$", re.I)
PICK = re.compile(r"^\s*(?:(?:the|number|option|choice|go with|pick|take|use|i mean|i meant|it's|its)\s+)*(\d|one|two|three|four|first|second|third|fourth|last)"
                  r"(?:\s+(?:one|please|then|is good|works))*[\s.!]*$", re.I)
NUMS = {"1": 1, "one": 1, "first": 1, "2": 2, "two": 2, "second": 2, "3": 3, "three": 3, "third": 3, "4": 4, "four": 4, "fourth": 4}
QUESTION = re.compile(r"\?|^\s*(?:what|how|why|when|where|which|who|is|are|do|does|did|can|could|should|will|would)\b", re.I)
_STOP = {"the", "a", "an", "of", "on", "in", "my", "our", "its", "it", "is", "to", "and", "or", "one", "book", "paper", "doing", "going", "draft"}

BOOKS = [("the practice book (the research trades)", "How is the research book doing?"),
         ("the managed book", "How is the managed book doing?"),
         ("the index options line", "How is the index options line doing?"),
         ("my account on paper", "How is my account doing on paper?")]


# ------------------------------------------------------------------------------------------------------------------------ the pending question
def _ask():
    from jarvis.india import ask
    return ask


def _store() -> Path:
    return Path(_ask().ASK_DIR) / "clarify.json"


def _all() -> dict:
    try:
        return json.loads(_store().read_text())
    except (OSError, ValueError):
        return {}


def pending(thread: str) -> dict | None:
    c = _all().get(thread)
    if not c:
        return None
    if time.time() - float(c.get("at") or 0) > PENDING_SECONDS:
        set_pending(thread, None)
        return None
    return c


def set_pending(thread: str, c: dict | None) -> None:
    d = _all()
    if c is None:
        d.pop(thread, None)
    else:
        d[thread] = c
    p = _store()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(d))


def _log(row: dict) -> None:
    a = _ask()
    if a.DRY_RUN:
        return
    try:
        p = a.DATA / "reports" / LOG_NAME
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a") as fh:
            fh.write(json.dumps({"t": int(time.time()), **row}) + "\n")
    except OSError:
        pass


# ---------------------------------------------------------------------------------------------------------------------- what Ananta asks
def _reply(answer: str, options: list[str], trigger: str) -> dict:
    return _ask()._reply(answer, [], [f"a clarifying question ({trigger}): the choice becomes the question"],
                         {"kind": "clarify", "options": options[:4], "clarify": trigger})


def maybe(text: str, thread: str, context: dict | None = None) -> dict | None:
    """None, {"ask": reply} (a question with choices; the reply is sent as it is), or {"resolved": text} (only one thing it could mean)."""
    a = _ask()
    m = APPROVE_BARE.match(text or "")
    if m:
        verb = "skip" if m.group(1).lower() in ("skip", "reject", "drop") else "approve"
        from jarvis.india import views
        drafts = views.drafts()["drafts"]
        if not drafts:
            return None                                   # the drafts flow / the model says nothing waits
        if len(drafts) == 1:
            return {"resolved": f"{verb} draft {drafts[0]['n']}"}
        opts = [f"draft {x['n']}: {str(x.get('words') or x.get('type') or '')[:60].rstrip('.,;')}" for x in drafts[:3]]
        choices = [{"label": o, "q": f"{verb} draft {x['n']}"} for o, x in zip(opts, drafts)] + [{"label": "all of them", "q": f"{verb} all drafts"}]
        opts.append("all of them")
        c = {"trigger": "approve", "q": text, "at": time.time(), "options": choices}
        set_pending(thread, c)
        _log({"thread": thread, "event": "asked", "trigger": "approve", "n": len(drafts)})
        return {"ask": _reply(f"Which draft, sir? {len(drafts)} are waiting.", opts, "approve")}
    if BOOK_BARE.match(text or ""):
        c = {"trigger": "book", "q": text, "at": time.time(), "options": [{"label": lab, "q": q} for lab, q in BOOKS]}
        set_pending(thread, c)
        _log({"thread": thread, "event": "asked", "trigger": "book", "n": len(BOOKS)})
        return {"ask": _reply("Which book do you mean, sir?", [lab for lab, _ in BOOKS], "book")}
    ctx = context or {}
    if a._refers_back(text or "") and not a.STATUS.search(text or "") and not ctx.get("about"):
        if not any(x.get("role") == "user" for x in a.thread_messages(thread)):
            c = {"trigger": "flag", "q": text, "at": time.time(), "options": []}
            set_pending(thread, c)
            _log({"thread": thread, "event": "asked", "trigger": "flag", "n": 0})
            return {"ask": _reply("What should I flag, sir? A few words is enough.", [], "flag")}
    return None


def a_refers_back(t: str) -> bool:
    return bool(_ask()._refers_back(t))


def resolve(text: str, thread: str) -> str | None:
    """His answer to the pending question, as the full question it stands for; None when nothing is pending or the message is not an answer."""
    c = pending(thread)
    if not c:
        return None
    set_pending(thread, None)                              # one round: whatever comes next closes the question
    t = (text or "").strip()
    opts = c.get("options") or []
    if c.get("trigger") == "flag":
        if QUESTION.search(t) or len(t.split()) > 40 or a_refers_back(t):
            _log({"thread": thread, "event": "dropped", "trigger": "flag"})
            return None
        _log({"thread": thread, "event": "answered", "trigger": "flag"})
        return f"flag this: {t}"
    n = None
    m = PICK.match(t)
    if m:
        w = m.group(1).lower()
        n = len(opts) if w == "last" else NUMS.get(w)
    if n is None:
        low = t.lower().strip(" .!?")
        exact = [i for i, o in enumerate(opts, 1) if low == str(o.get("label", "")).lower().strip(" .!?")]
        if len(exact) == 1:
            n = exact[0]
    if n is None and len(t.split()) <= 12:
        said = {w for w in re.findall(r"[a-z']+", t.lower()) if w not in _STOP and len(w) > 2}
        hits = []
        for i, o in enumerate(opts, 1):
            tw = {w for w in re.findall(r"[a-z']+", str(o.get("label", "")).lower()) if w not in _STOP and len(w) > 2}
            if tw and said & tw:                        # one telling word is enough when it names only one choice
                hits.append(i)
        if len(hits) == 1:
            n = hits[0]
    if n is None or not (1 <= n <= len(opts)):
        _log({"thread": thread, "event": "dropped", "trigger": c.get("trigger")})
        return None
    _log({"thread": thread, "event": "answered", "trigger": c.get("trigger"), "pick": n})
    return str(opts[n - 1]["q"])


# ---------------------------------------------------------------------------------------------------------------------------- the facts
def summary(days: int = 7) -> dict:
    """What the Ask's facts say about this: how often Ananta asked which one he meant, and how often the answer picked a choice."""
    a = _ask()
    rows = []
    try:
        since = time.time() - days * 86400
        for line in (a.DATA / "reports" / LOG_NAME).read_text().splitlines():
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if float(r.get("t") or 0) >= since:
                rows.append(r)
    except OSError:
        pass
    asked = [r for r in rows if r.get("event") == "asked"]
    answered = [r for r in rows if r.get("event") == "answered"]
    dropped = [r for r in rows if r.get("event") == "dropped"]
    by = {}
    for r in asked:
        by[r.get("trigger")] = by.get(r.get("trigger"), 0) + 1
    words = (f"In the last {days} days Ananta asked which one Madhav meant {len(asked)} time{'s' if len(asked) != 1 else ''}"
             + (" (" + ", ".join(f"{v} about {k}" for k, v in sorted(by.items())) + ")" if by else "")
             + f"; {len(answered)} picked a choice, {len(dropped)} moved on."
             if asked else f"In the last {days} days Ananta did not need to ask which one Madhav meant.")
    return {"rule": "one question with 2-4 choices, in code, only when a wrong guess would cost something: which draft to approve or skip, "
                    "which book he means, what to flag when nothing came before; never for a fact question; one round, then the choice is the question",
            "asked": len(asked), "answered": len(answered), "dropped": len(dropped), "by_trigger": by, "words": words}
