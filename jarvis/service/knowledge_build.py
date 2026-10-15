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


def ledger(j) -> dict:
    """Fix 10 of the reconstruction audit (Oct 15): the repair ledger cannot drift quietly. Read-only; it writes nothing. It checks the
    ledger against the files that are the record: every file a row names exists, ids are unique, a finished review is not still in the
    queue, every review document on disk has a ledger row, and the `updated` date is not older than the newest dated row. (The 65-versus-105
    accounts and the 'never traded' lines the audit found were prose that no check could catch; what a check can catch is below.)"""
    import re

    docs = docs_dir(j.dir)
    out: dict = {"problems": [], "checked": 0}
    try:
        led = json.loads((docs / "repair_shop" / "ledger.json").read_text())
    except Exception as exc:  # noqa: BLE001
        return {"problems": [f"ledger.json cannot be read: {str(exc)[:120]}"], "checked": 0}

    def add(msg: str) -> None:
        out["problems"].append(msg)

    rows = {k: led.get(k) or [] for k in ("reviews", "queue", "tickets", "in_use", "studies")}
    for k in ("reviews", "queue", "tickets"):
        ids = [r.get("id") for r in rows[k]]
        out["checked"] += len(ids)
        dup = sorted({i for i in ids if ids.count(i) > 1})
        if dup:
            add(f"{k}: id used twice: {', '.join(map(str, dup))}")
    root = docs.parent
    for k in ("reviews", "queue", "studies", "in_use"):
        for r in rows[k]:
            for f in r.get("files") or []:
                out["checked"] += 1
                if not (root / f).exists():
                    add(f"{k} {r.get('id')}: the file {f} does not exist")
    done = {r.get("id") for r in rows["reviews"] if r.get("status") == "DONE"}
    for q in rows["queue"]:
        if q.get("id") in done:
            add(f"queue {q.get('id')} is also a DONE review: it should have left the queue")
    have = {str(r.get("id")) for r in rows["reviews"]}
    nums = set()
    for sub in ("research", "repair_shop"):
        for p in (docs / sub).glob("REVIEW_*.md"):
            m = re.match(r"REVIEW_(\d+)(?:_RESULTS)?\.md$", p.name)
            if m:
                nums.add(int(m.group(1)))
    for n in sorted(nums):
        out["checked"] += 1
        if f"R{n}" not in have:
            add(f"review {n} has a document on disk but no row in the ledger")
    dates = [str(r.get("date")) for k in ("reviews", "tickets", "changes") for r in (rows.get(k) or led.get(k) or []) if r.get("date")]
    if dates and str(led.get("updated") or "") < max(dates):
        add(f"updated is {led.get('updated')}, older than the newest row ({max(dates)})")
    out["ok"] = not out["problems"]
    return out


def ledger_nightly(j) -> dict:
    """The nightly run of ledger(): a problem it has not reported before becomes one repair-board request (by ananta-auto), once for each
    distinct set of problems, so a standing problem is not repeated every night and a check nobody reads is not the only trace."""
    import hashlib

    r = ledger(j)
    if r["problems"]:
        key = "kb:ledger_flag:" + hashlib.sha1("\n".join(sorted(r["problems"])).encode()).hexdigest()[:12]
        j.db.execute("CREATE TABLE IF NOT EXISTS engine_state (k TEXT PRIMARY KEY, v TEXT)")
        if not j.db.execute("SELECT 1 FROM engine_state WHERE k=?", (key,)).fetchone():
            from jarvis.service import requests_log

            requests_log.add(j, "data", "The repair ledger disagrees with its own files (the nightly check): " + "; ".join(r["problems"][:6])
                             + (f"; and {len(r['problems']) - 6} more" if len(r["problems"]) > 6 else "") + ".", about="ledger check", by="ananta-auto")
            j.db.execute("INSERT OR REPLACE INTO engine_state VALUES (?, ?)", (key, str(int(j.now()))))
            j.db.commit()
            r["flagged"] = True
    return r


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
