"""Say = show (request #73, Oct 20): does the screen show what the voice says?

- record(): the app reports what its screen really did after an answer (POST /v3/voice/ui_result) -> table voice_ui
- summary(): what the gate (appmap.say_show) did to the screen moves of the last N days, and moves that failed in the app
  (for the morning review to print; not wired in yet)
- check(): the Oct 20 checker over logged voice turns: matched / MISMATCH / names no book, as logged and with the gate
  re-applied (scripts/say_vs_show.py runs it over a turns.jsonl)
"""
from __future__ import annotations

import json
import re

from jarvis.service import appmap


def _table(db) -> None:
    db.execute("CREATE TABLE IF NOT EXISTS voice_ui (answer_id TEXT, t INTEGER, ui_json TEXT, results_json TEXT, say_show TEXT)")
    db.execute("CREATE INDEX IF NOT EXISTS voice_ui_t ON voice_ui(t)")


def record(db, answer_id: str, results: list, spots: list, now: int) -> bool:
    """One row per answer the app moved the screen for: what Ananta planned (the reply's ui and the gate's note, from
    ask_messages) next to what the app did (each move: target, ok, where it landed; the spots it was to light)."""
    aid = str(answer_id or "")
    if not re.fullmatch(r"[A-Za-z0-9_\-]{1,40}", aid):
        raise ValueError("answer_id is missing or not an answer id")
    res = [{"target": str(r.get("target") or "")[:80], "ok": bool(r.get("ok")), "landed": str(r.get("landed") or "")[:80]}
           for r in (results or [])[:10] if isinstance(r, dict)]
    sp = [str(s)[:80] for s in (spots or [])[:8] if isinstance(s, str)]
    _table(db)
    ui, note = None, None
    try:
        row = db.execute("SELECT reply FROM ask_messages WHERE id=? AND role='assistant'", (aid,)).fetchone()
        rep = json.loads(row[0] or "{}") if row else {}
        ui, note = rep.get("ui"), rep.get("say_show")
    except Exception:  # noqa: BLE001  a report is kept even when its answer is not found
        pass
    db.execute("INSERT INTO voice_ui (answer_id, t, ui_json, results_json, say_show) VALUES (?,?,?,?,?)",
               (aid, int(now), None if ui is None else json.dumps(ui), json.dumps({"results": res, "spots": sp}), note))
    db.commit()
    return True


def summary(db, now: int, days: int = 7) -> dict:
    """Kept / retargeted / dropped screen moves (the gate's notes on the answers) and app reports with a move that failed."""
    since = int(now) - days * 86400
    counts = {"kept": 0, "retargeted": 0, "dropped": 0}
    answers = 0
    try:
        rows = db.execute("SELECT reply FROM ask_messages WHERE role='assistant' AND t >= ? AND reply LIKE '%\"say_show\"%'", (since,)).fetchall()
    except Exception:  # noqa: BLE001  no conversations yet
        rows = []
    for (rep,) in rows:
        try:
            note = json.loads(rep or "{}").get("say_show") or ""
        except ValueError:
            continue
        answers += 1
        for part in note.split(";"):
            word = part.strip().split(" ")[0]
            if word in counts:
                counts[word] += 1
    _table(db)
    reported = failed = 0
    for (rj,) in db.execute("SELECT results_json FROM voice_ui WHERE t >= ?", (since,)):
        reported += 1
        try:
            failed += any(not r.get("ok") for r in json.loads(rj or "{}").get("results") or [])
        except (ValueError, AttributeError):
            pass
    line = (f"Say = show, last {days} days: {answers} answers had a screen move checked: {counts['kept']} kept, {counts['retargeted']} "
            f"moved to the book the voice named, {counts['dropped']} dropped. The app reported back on {reported} answers, {failed} with a screen that did not open.")
    return {"days": days, "answers": answers, **counts, "reported": reported, "failed": failed, "line": line}


# ---------------------------------------------------------------------------
# The checker (Oct 20, ~/ananta_runs/voice_review/say_vs_show.py): for each voice turn that moved the screen, does the place it
# opened match what the voice talked about? Its table is kept exactly as it was (not the gate's BOOKS), so before and after are
# measured the same way and the gate is not graded by its own table.
# ---------------------------------------------------------------------------
CHECK_BOOK = [
    ("home", r"\$?\s?500\b|five hundred|ndax|the account\b|account's|real book"),
    ("portfolio", r"trend portfolio|\bT3\b|autopilot"),
    ("portfolio:explorer", r"\bexplorer\b"),
    ("jarvis", r"my own book|jarvis'?s book|my book|ananta'?s book|random twins?"),
    ("portfolio:mine", r"your (own )?paper book|your orders|my trades"),
    ("evidence", r"evidence|repair shop|gate\b|checks pass"),
    ("markets", r"market gate|trend dial|the dial|markets? (?:is|are) open|buying allowed"),
    ("missed", r"missed|caught"),
]


def measure(said: str, ui: list[dict]) -> str | None:
    """-> 'matched' / 'mismatch' / 'unclear' (the words name no book), or None when nothing opens a place."""
    named = {s for s, rx in CHECK_BOOK if re.search(rx, said or "", re.I)}
    targets = [u.get("target") for u in ui or [] if u.get("do") in ("go_to", "open")]
    if not targets:
        return None
    t = targets[-1] or ""
    base = t.split(":")[0] if t.split(":")[0] in ("coin", "trade") else t
    if base in ("coin", "trade") or base in named:
        return "matched"
    return "mismatch" if named else "unclear"


def regate(x: dict) -> tuple[list[dict], list[dict], str]:
    """One logged turn with the gate applied as the service now does. Instant navigation ("open Ethereum", mode nav) and
    tours never pass the gate. The spoken words are rebuilt from the answer when the log has none."""
    if x.get("rmode") in ("nav", "people") or str(x.get("mode") or "").endswith((":nav", ":people")) or x.get("tour"):
        return list(x.get("ui") or []), list(x.get("points") or []), ""
    from jarvis.service.ask import speak_text

    spoken = x.get("speak") or speak_text({"answer": x.get("answer") or "", "kind": x.get("kind") or "answer"})
    return appmap.say_show(None, spoken, x.get("ui") or [], x.get("points") or [], x.get("heard") or "")


def check(turns: list[dict]) -> dict:
    """Before (as logged) and after (gate re-applied) over the voice turns that moved the screen."""
    moved = [x for x in turns if x.get("ui") and not (x.get("heard") or "").startswith("Good. It")]     # "Good. It..." = test runs
    out = {"moved": len(moved), "before": {"matched": 0, "mismatch": 0, "unclear": 0},
           "after": {"matched": 0, "mismatch": 0, "unclear": 0, "dropped": 0}, "rows": []}
    for x in moved:
        said = x.get("speak") or x.get("answer") or ""
        before = measure(said, x["ui"])
        if before is None:
            continue
        ui2, _, note = regate(x)
        after = measure(said, ui2) or "dropped"
        out["before"][before] += 1
        out["after"][after] += 1
        out["rows"].append({"t": x.get("t"), "heard": x.get("heard") or "", "said": said, "before": before, "after": after, "note": note,
                            "opened": [u.get("target") for u in x["ui"] if u.get("do") in ("go_to", "open")],
                            "opens_now": [u.get("target") for u in ui2 if u.get("do") in ("go_to", "open")]})
    return out
