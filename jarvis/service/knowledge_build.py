"""One truth registry (Madhav, Oct 14): strategy_status.json decides; this nightly build step makes the other
knowledge surfaces agree with it and reports any drift it cannot repair on its own.

  align(j)   repair watches.json statuses and status_cards.json permissions from strategy_status.json; stamp "updated"
  window(j)  the 60-day evidence-window block (day N of 60, loop health) for the officer's note and the daily review

Paper bookkeeping only: it rewrites the two knowledge files, returns exactly what it changed, and lists the
conflicts it would not decide by itself (a named card that does not exist, say) instead of guessing.
"""
from __future__ import annotations

import calendar
import json
import time
from pathlib import Path

from jarvis.service.core import docs_dir

# a strategy's status -> the watch-registry word for its watches
WATCH_WORD = {"ACTIVE": "ACTIVE", "UNDER_REVIEW": "UNDER_REVIEW", "EVIDENCE": "EVIDENCE_ONLY",
              "RETIRED": "EVIDENCE_ONLY", "PARKED": "PARKED"}
# a retired or parked strategy's cards may describe the idea, never justify a buy
DEMOTE = ("RETIRED", "PARKED")


def _knowledge(j) -> Path:
    return docs_dir(j.dir) / "knowledge"


def align(j) -> dict:
    """Make watches.json and status_cards.json agree with strategy_status.json; say what changed."""
    from jarvis.service import strategy_status

    strats = strategy_status.load().get("strategies") or {}
    today = time.strftime("%Y-%m-%d", time.gmtime(j.now()))
    out: dict = {"fixed": [], "conflicts": [], "checked": 0}

    p = _knowledge(j) / "watches.json"
    try:  # every watch that belongs to a strategy carries that strategy's word
        doc = json.loads(p.read_text())
        changed = False
        for w in doc.get("watches") or []:
            e = strategy_status.of_watch(w.get("id"))
            if not e:
                continue
            out["checked"] += 1
            want = WATCH_WORD.get(e[1].get("status") or "")
            if want and w.get("status") != want:
                out["fixed"].append(f"watches.json {w.get('id')}: {w.get('status')} -> {want} ({e[0]} is {e[1].get('status')})")
                w["status"] = want
                changed = True
        if changed or doc.get("updated") != today:
            doc["updated"] = today
            p.write_text(json.dumps(doc, indent=1, ensure_ascii=False))
    except Exception as exc:  # noqa: BLE001
        out["watches_error"] = str(exc)[:160]

    p = _knowledge(j) / "status_cards.json"
    try:  # a card of a retired/parked strategy may not stay a reason to trade
        doc = json.loads(p.read_text())
        cards = {c.get("id"): c for c in doc.get("cards") or []}
        changed = False
        for sid, s in strats.items():
            for cid in s.get("cards") or []:
                c = cards.get(cid)
                if not c:
                    out["conflicts"].append(f"strategy {sid} names card {cid}, which does not exist in status_cards.json")
                    continue
                out["checked"] += 1
                if s.get("status") in DEMOTE and c.get("permission") == "PAPER":
                    out["fixed"].append(f"status_cards.json {cid}: permission PAPER -> CONTEXT ({sid} is {s.get('status')})")
                    c["permission"] = "CONTEXT"
                    c["reason"] = (c.get("reason") or "") + f" [{sid} {str(s.get('status')).lower()} {today}: no longer a reason to buy]"
                    changed = True
        if changed or doc.get("updated") != today:
            doc["updated"] = today
            p.write_text(json.dumps(doc, indent=1, ensure_ascii=False))
    except Exception as exc:  # noqa: BLE001
        out["cards_error"] = str(exc)[:160]
    return out


def window(j) -> dict | None:
    """Day N of the 60-day evidence window, with the learning loop's health; None until a window is declared."""
    from jarvis.service import strategy_status

    w = strategy_status.load().get("evidence_window") or {}
    if not w.get("start"):
        return None
    d0 = calendar.timegm(time.strptime(w["start"], "%Y-%m-%d"))
    dayn = int((int(j.now()) - d0) // 86400) + 1
    loop: dict = {}
    try:
        r = j.db.execute("SELECT t, match FROM rebuild_log WHERE source='brain' ORDER BY t DESC LIMIT 1").fetchone()
        loop["brain_rebuild"] = (f"{round((int(j.now()) - r[0]) / 3600)}h ago, " + ("clean" if r[1] else "MISMATCH")) if r else "never"
        d = j.db.execute("SELECT day FROM daily_reviews ORDER BY day DESC LIMIT 1").fetchone()
        loop["daily_review"] = d[0] if d else "never"
    except Exception as exc:  # noqa: BLE001
        loop["error"] = str(exc)[:120]
    try:
        weekly = sorted((docs_dir(j.dir) / "repair_shop" / "weekly").glob("*.md"))
        loop["weekly_review"] = weekly[-1].stem if weekly else "none yet (first Sunday ahead)"
    except Exception:  # noqa: BLE001
        pass
    return {"day": max(0, dayn), "of": int(w.get("days") or 60), "started": w["start"],
            "rule": w.get("rule") or "", "loop": loop}
