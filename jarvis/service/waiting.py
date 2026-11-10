"""What is waiting for Madhav's yes, in one place (Madhav, 28 Oct 2026: "it asks for my approval in evidence layer, but never notifies me when
I am using the app ... I had to be told and reminded by the voice agent (when I am talking to it) and notifications when there is something
waiting for me").

collect(j)  every item waiting for him: India research drafts (the reconstruction's DECISION lane), flags waiting for his pick or his yes, and the
            crypto "Needs you" cards (jarvis/service/needs.py). Read-only.
remind(j)   called by the 15-minute loop: a phone note (and web push) when something NEW starts waiting, and one evening reminder (19:00-21:00
            Toronto) while anything has waited over a day. Never more than one note per new item.

The app shows the same list as a bar on every screen (src/waiting.tsx) and the India Ask says it once per conversation (jarvis/india/ask.py).
Nothing here approves anything: a yes is still his tap or his words ("approve all drafts", "approve draft 2", "fix 1").
"""
from __future__ import annotations

import hashlib
import json
import re
import os
import time
from pathlib import Path

STATE = Path(os.path.expanduser(os.getenv("WAITING_STATE", "~/ananta_runs/waiting_state.json")))
FLAG_DAYS = 7                    # a flag still waiting for a pick after a week is old news; it stays in My flags


def _flags(j, now: float) -> list[dict]:
    from jarvis.service import fixflow, requests_log

    out = []
    for f in fixflow.pending(j, states=("triaged", "needs_decision")):
        if not f or now - float(f.get("t") or 0) > FLAG_DAYS * 86400:
            continue
        r = requests_log.get(j, f["num"]) or {}
        if r.get("status") in ("DONE", "WONT", "PLANNED"):   # 6 Nov: flags 58 and 59 were done or planned on 3-4 Nov, yet "pick a fix" still waited
            continue
        if r.get("waits"):                                    # 10 Nov: an item with a kind is said by its kind (_asks for YOU), never as "pick a fix" too
            continue
        no = requests_log.flag_no(f["num"])
        what = (r.get("text") or "").strip().split("\n")[0]
        if len(what) > 160:                                   # 2 Nov: never cut mid-word ("against a 70% t")
            what = what[:160].rsplit(" ", 1)[0].rstrip(",;:") + "…"
        # 2 Nov 2026 (India voice: "I don't have the wording of the three fixes in front of me"): each flag carries its fixes' wording and the
        # morning review's note, so Ananta can say what each fix does and what the review found, and stop pushing a flag the review settled
        fixes = [str(o.get("title") or "") for o in ((f.get("options") or {}).get("options") or []) if o.get("title")][:3]
        note = str(r.get("note") or "")
        review = None
        if note.startswith("Review"):
            body = note.split(":", 1)[-1].strip()
            m = re.search(r"Proposal[^:]{0,60}:\s*(.+)", body, re.S)
            prop = re.split(r"(?<=[.;])\s+", m.group(1).strip())[0] if m else None
            review = {"words": body[:600], "proposal": prop,
                      "settled": bool(re.search(r"\b(no change|the rules working|the rule held|card misleads|parked|after it|in the window)\b", body, re.I))}
        mkt = f.get("market") or ("crypto" if what.startswith("[Crypto") else "india" if "Indian market" in what else "")
        base = {"id": f"flag:{f['num']}", "market": mkt, "count": 1, "t": f.get("t"), "line": what, "route": "flags", "fixes": fixes, "review": review}
        if f["state"] == "triaged":
            out.append({**base, "kind": "flag_pick", "title": f"Flag {no}: pick a fix", "say": "fix 1, fix 2 or fix 3"})
        else:
            out.append({**base, "kind": "flag_decision", "title": f"Flag {no}: a plan needs your yes", "say": "open My flags"})
    return out


def _drafts() -> list[dict]:
    try:
        from jarvis.india import views

        d = views.drafts()["drafts"]
    except Exception:  # noqa: BLE001  India data missing never breaks the list
        return []
    if not d:
        return []
    days = sorted({x.get("day") or "" for x in d})
    return [{"id": "india:drafts", "market": "india", "kind": "drafts", "count": len(d), "since": days[0] if days else "",
             "title": f"{len(d)} research draft{'s' if len(d) != 1 else ''} wait for your yes or skip",
             "line": "Yes registers a study (written down first, tested on 2000-2023 only); nothing trades from it.",
             "route": "evidence", "say": "approve all drafts, approve draft 2, or skip draft 3",
             "keys": [x["key"] for x in d]}]


def _needs(j) -> list[dict]:
    try:
        from jarvis.service import needs

        return [{"id": f"needs:{x['id']}", "market": "crypto", "kind": "needs", "count": 1, "title": x.get("title") or "A decision",
                 "line": x.get("line") or "", "route": "home", "say": "open Home"} for x in needs.list_(j)]
    except Exception:  # noqa: BLE001
        return []


def _asks(j) -> list[dict]:
    """10 Nov 2026 (the open list): board items whose kind is YOU: a yes or a step only Madhav can give. They wait until answered."""
    from jarvis.service import openlist, requests_log

    out = []
    for r in reversed(requests_log.list_(j, include_done=False)):
        if r.get("waits") != "YOU":
            continue
        out.append({"id": f"ask:{r['num']}", "market": openlist.market_of(r), "kind": "ask", "count": 1, "t": r.get("t"),
                    "title": r["label"].capitalize(), "line": r.get("line") or openlist.plain(r["text"], 190), "route": "flags", "say": f"yes or no to {r['label']}",
                    "review": {"words": str(r.get("note") or "")[:600], "proposal": openlist.advice_of(r.get("note")), "settled": False}})
    return out


def _owner_decisions(j) -> list[dict]:
    """The due list's decisions that are his and fall due within a week or are overdue (docs/knowledge/due_list.json)."""
    try:
        from jarvis.service import due_list, openlist

        return [{"id": f"due:{r['id']}", "market": "crypto", "kind": "ask", "count": 1, "title": r["id"], "line": openlist.plain(r["what"], 190),
                 "route": "flags", "say": "tell Ananta your decision", "review": None}
                for r in due_list.rows(j) if r.get("owner_decision") and r["state"] in ("overdue", "soon")]
    except Exception:  # noqa: BLE001
        return []


def collect(j, now: float | None = None) -> dict:
    now = now or time.time()
    items = _drafts() + _flags(j, now) + _needs(j) + _asks(j) + _owner_decisions(j)
    n = sum(int(x.get("count") or 1) for x in items)
    key = hashlib.sha1(json.dumps(sorted((x["id"], x.get("count")) for x in items)).encode()).hexdigest()[:12] if items else ""
    return {"items": items, "count": n, "key": key, "line": line(items)}


def line(items: list[dict]) -> str:
    """One short spoken sentence: 'Sir, 12 research drafts and flag 49 are waiting for your yes.' Questions put to him from the open list
    are counted together ('3 questions for you'), so the bar stays one line."""
    if not items:
        return ""
    parts = []
    for x in items:
        if x["kind"] == "drafts":
            parts.append(f"{x['count']} research draft{'s' if x['count'] != 1 else ''}")
        elif x["kind"].startswith("flag"):
            parts.append(x["title"].split(":")[0].lower())
        elif x["kind"] != "ask":
            parts.append("a crypto decision")
    asks = [x for x in items if x["kind"] == "ask"]
    if len(asks) == 1:
        t = asks[0]["title"]
        parts.append(t.lower() if t.lower().startswith(("flag", "request")) else t)
    elif asks:
        parts.append(f"{len(asks)} questions for you")
    shown = parts[:3]
    if len(parts) > 3:
        shown.append(f"{len(parts) - 3} more")
    words = shown[0] if len(shown) == 1 else ", ".join(shown[:-1]) + " and " + shown[-1]
    m = re.match(r"(\d+)\s", shown[0])
    verb = "is" if len(shown) == 1 and (not m or int(m.group(1)) == 1) else "are"
    return f"{words[:1].upper()}{words[1:]} {verb} waiting for your yes."


def _load() -> dict:
    try:
        return json.loads(STATE.read_text())
    except (OSError, ValueError):
        return {}


def _toronto_hour(now: float) -> int:
    try:
        from zoneinfo import ZoneInfo
        import datetime as dt

        return dt.datetime.fromtimestamp(now, ZoneInfo("America/Toronto")).hour
    except Exception:  # noqa: BLE001
        return time.localtime(now).tm_hour


def remind(j, push=None, web=None, now: float | None = None) -> dict:
    """A note when something new waits; one evening reminder while anything has waited a day. Returns what it sent."""
    now = now or time.time()
    w = collect(j, now)
    st = _load()
    seen = st.get("seen") or {}                 # id -> count already told
    new = [x for x in w["items"] if int(x.get("count") or 1) > int(seen.get(x["id"], 0))]
    out = {"count": w["count"], "new": [x["id"] for x in new], "sent": None}
    title, body = None, None
    if new:
        title = "Waiting for your yes" if len(new) > 1 else new[0]["title"]
        body = (w["line"] + " " + ("Say it to Ananta, or open the app." if any(x["kind"] == "drafts" for x in new) else "Open the app to choose.")).strip()
    elif [x for x in w["items"] if x["kind"] != "ask"] and now - float(st.get("evening_t", 0)) > 20 * 3600 and 19 <= _toronto_hour(now) < 21 \
            and now - float(st.get("first_t", now)) > 86400:
        # 10 Nov 2026: the evening reminder is for drafts, flags and crypto decisions, as before. A question on the open list (the kind
        # "ask": an Apple sign-in, a yes with no hurry) shows in the bar and is said when he asks; it is not repeated every evening.
        title, body = "Still waiting for your yes", line([x for x in w["items"] if x["kind"] != "ask"])
        st["evening_t"] = now
    if title:
        for f in (push, web):
            if f:
                try:
                    f(title, body)
                except Exception:  # noqa: BLE001  a note that fails never stops the loop
                    pass
        out["sent"] = title
    st["seen"] = {x["id"]: int(x.get("count") or 1) for x in w["items"]}
    if w["items"] and not st.get("first_t"):
        st["first_t"] = now
    if not w["items"]:
        st.pop("first_t", None)
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(st))
    return out
