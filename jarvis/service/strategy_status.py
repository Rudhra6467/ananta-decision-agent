"""One list of every strategy with its status and verdict (docs/knowledge/strategy_status.json; Madhav, Oct 13).

  load()                the file
  of_watch(watch)       the strategy entry a watch id belongs to ("ZONE_TOUCH-UB" -> ZONE_TOUCH)
  of_book(home_book)    the entry a home-page book belongs to ("15-minute Explorer" -> EXPLORER)
  trades(watch)         False for a RETIRED / PARKED watch: it takes no new paper trades (EVIDENCE books keep recording)
  wakes(watch)          False when the strategy's signals must never wake the brain (a failed idea is recorded, not decided on)
  counts(watch|book)    True when it belongs in the headline (ACTIVE or UNDER_REVIEW); evidence and retired books are shown apart
  record_verdicts(j)    stamp every strategy's status and verdict, with the time, when it differs from the last one recorded
  losing_trades(j)      every closed losing trade classified: won't take again / will try again / rules modified, with the reason; the verdict is
                        the one in force when the trade was ENTERED (strategy_verdicts), not today's, so the history stays honest as verdicts change
  render_why(text, p)   fills {closed} {won} {lost} {net} {lost_usd} in a strategy's reason with its live record (never frozen in the file)
"""
from __future__ import annotations

import collections
import json
import re
import time
from pathlib import Path

VERDICT_WORDS = {"wont_take_again": "won't take again", "will_try_again": "will try again", "modify_rules": "rules modified, trying again"}
COUNTS = ("ACTIVE", "UNDER_REVIEW")
_CACHE: dict = {"m": None, "v": {}}


def _path() -> Path:
    from jarvis.service.core import docs_dir

    return docs_dir(".") / "knowledge" / "strategy_status.json"


def load() -> dict:
    p = _path()
    try:
        m = p.stat().st_mtime
    except OSError:
        return {}
    if _CACHE["m"] != m:
        _CACHE.update(m=m, v=json.loads(p.read_text()))
    return _CACHE["v"]


def _strats() -> dict:
    return (load().get("strategies") or {})


def of_watch(watch: str | None) -> tuple[str, dict] | None:
    w = str(watch or "")
    best = None
    for sid, s in _strats().items():
        for prefix in s.get("watches") or []:
            if w == prefix or w.startswith(prefix + "-"):
                if best is None or len(prefix) > len(best[2]):
                    best = (sid, s, prefix)
    return (best[0], best[1]) if best else None


def of_book(home_book: str | None) -> tuple[str, dict] | None:
    for sid, s in _strats().items():
        if s.get("home_book") == home_book:
            return sid, s
    return None


def trades(watch: str) -> bool:
    """May this watch open new paper trades? EVIDENCE books do (they measure in the background); RETIRED and PARKED do not."""
    e = of_watch(watch)
    return not e or e[1].get("status") not in ("RETIRED", "PARKED")


def wakes(watch: str) -> bool:
    """May this watch's signals wake the brain? A failed idea is recorded, never decided on (wakes_brain: false)."""
    e = of_watch(watch)
    if not e:
        return True
    return e[1].get("status") not in ("RETIRED", "PARKED") and e[1].get("wakes_brain", True)


def account() -> str:
    return str(load().get("account") or "BOOK500")


def pushed_rule() -> str:
    return str(load().get("pushed") or "")


def counts_watch(watch: str) -> bool:
    e = of_watch(watch)
    return not e or e[1].get("status") in COUNTS


def counts_book(home_book: str) -> bool:
    e = of_book(home_book)
    return not e or e[1].get("status") in COUNTS


# ---------------------------------------------------------------------------
# the verdict in force at each time (Oct 15, research audit: LOSSES judged a trade by TODAY's verdict, so history changed with it)
# ---------------------------------------------------------------------------
def _verdict_table(j) -> None:
    j.db.execute("CREATE TABLE IF NOT EXISTS strategy_verdicts (sid TEXT NOT NULL, t INTEGER NOT NULL, status TEXT, verdict TEXT, source TEXT, "
                 "PRIMARY KEY (sid, t))")


def record_verdicts(j, source: str = "register") -> int:
    """Stamp each strategy's (status, verdict) with the time when it differs from the last one recorded. Run with the service's 15-minute
    jobs, so a verdict Madhav changes is on record within minutes and every later trade is judged by it, every earlier one by the old.
    scripts/backfill_strategy_verdicts.py fills the history from the file's git log once. Returns how many rows were added."""
    _verdict_table(j)
    now, n = int(j.now()), 0
    for sid, s in _strats().items():
        cur = (s.get("status"), s.get("verdict"))
        last = j.db.execute("SELECT status, verdict FROM strategy_verdicts WHERE sid=? ORDER BY t DESC LIMIT 1", (sid,)).fetchone()
        if last is None or tuple(last) != cur:
            j.db.execute("INSERT OR REPLACE INTO strategy_verdicts (sid, t, status, verdict, source) VALUES (?,?,?,?,?)", (sid, now, cur[0], cur[1], source))
            n += 1
    if n:
        j.db.commit()
    return n


def _timeline(j) -> dict:
    """sid -> [(t, status, verdict)] oldest first; empty when nothing was recorded yet."""
    out: dict = collections.defaultdict(list)
    try:
        for sid, t, st, v in j.db.execute("SELECT sid, t, status, verdict FROM strategy_verdicts ORDER BY sid, t").fetchall():
            out[sid].append((int(t), st, v))
    except Exception:  # noqa: BLE001  no table yet
        pass
    return out


def verdict_in_force(timeline: dict, sid: str, t: float | None, today: str | None) -> tuple[str | None, bool]:
    """(verdict, recorded): the verdict recorded for `sid` at time t. Before its first record, the first recorded verdict (the register
    did not exist yet); with nothing recorded, or no entry time, today's verdict (recorded False)."""
    rows = timeline.get(sid) or []
    if not rows or t is None:
        return today, False
    best = None
    for rt, _st, v in rows:
        if rt > t:
            break
        best = v
    if best is not None:
        return best, True
    return rows[0][2], False


# ---------------------------------------------------------------------------
# live numbers: one place counts the closed paper trades of every strategy
# ---------------------------------------------------------------------------
def _explorer_closed(j) -> list[dict]:
    """The Explorer's WHOLE closed book, newest first (the screen's list shows only the last 30; counting from it undercounted the Explorer:
    30 closed when the book held 232). The entry time is the trade's FILLED event."""
    try:
        from jarvis.service import views

        ex = j._explorer()
        book = ex.store.book if ex else None
        if book is None:
            return []
        fills = {i: t for i, t in book.execute("SELECT id, t FROM events WHERE kind='FILLED'")}
        out = []
        for (js,) in book.execute("SELECT json FROM events WHERE kind='CLOSED' ORDER BY seq DESC"):
            e = json.loads(js)
            out.append({"id": e["id"], "coin": e["coin"], "setup": views.SETUP.get(e.get("setup"), e.get("setup")), "net_usd": e.get("net_usd") or 0.0,
                        "why": views.exit_text(e.get("bell")), "day": views._local(e["t"]), "entry_t": fills.get(e["id"]), "closed_t": e.get("t")})
        return out
    except Exception:  # noqa: BLE001  no Explorer here (a test, a worker): nothing to count
        return []


def per_strategy(j) -> dict:
    """sid -> {closed, won, lost, net_usd, lost_usd, trades (the 60 newest losses), by_verdict (the losses by the verdict in force at
    entry)}. The evidence book's closed trades, and the Explorer's whole closed book under EXPLORER."""
    from jarvis.service import watch_engine as W

    timeline = _timeline(j)
    strats = _strats()
    per: dict = collections.defaultdict(lambda: {"closed": 0, "won": 0, "lost": 0, "net_usd": 0.0, "lost_usd": 0.0, "trades": [],
                                                  "by_verdict": collections.defaultdict(lambda: {"lost": 0, "lost_usd": 0.0}), "unrecorded": 0})

    def add(sid: str, net: float, entry_t, trade: dict) -> None:
        p = per[sid]
        p["closed"] += 1
        p["net_usd"] += net
        if net > 0:
            p["won"] += 1
        if net < 0:
            p["lost"] += 1
            p["lost_usd"] += net
            v, recorded = verdict_in_force(timeline, sid, entry_t, (strats.get(sid) or {}).get("verdict") or "will_try_again")
            p["by_verdict"][v or "will_try_again"]["lost"] += 1
            p["by_verdict"][v or "will_try_again"]["lost_usd"] += net
            if not recorded:
                p["unrecorded"] += 1
            if len(p["trades"]) < 60:
                p["trades"].append({**trade, "net_usd": round(net, 2), "verdict_at_entry": v})

    rows = j.db.execute(f"SELECT {', '.join(W.COLS)} FROM evidence_trades WHERE status='CLOSED' ORDER BY exit_t DESC").fetchall()
    for r in rows:
        t = dict(zip(W.COLS, r))
        e = of_watch(t["watch"])
        add(e[0] if e else t["watch"], t["net_usd"] or 0.0, t.get("entry_t"),
            {"id": t["id"], "coin": t["coin"], "watch": t["watch"], "day": t.get("exit_day"), "why": t.get("exit_why")})
    for x in _explorer_closed(j):
        add("EXPLORER", x["net_usd"], x["entry_t"] or x["closed_t"],
            {"id": x["id"], "coin": x["coin"], "watch": "EXPLORER", "setup": x["setup"], "day": x["day"], "why": x["why"]})
    return per


_TOKEN = re.compile(r"\{(closed|won|lost|net|lost_usd)\}")


def _money(x: float) -> str:
    return f"{'-' if x < 0 else '+'}${abs(x):,.2f}"


def render_why(text: str, p: dict | None) -> str:
    """A strategy's reason with its live paper record filled in. The file holds {closed} {won} {lost} {net} {lost_usd}, never the numbers
    (Oct 15, research audit: numbers frozen in the file went stale within a day). A strategy with no closed trade yet reads as zeros."""
    if "{" not in text:
        return text
    p = p or {}
    vals = {"closed": str(p.get("closed", 0)), "won": str(p.get("won", 0)), "lost": str(p.get("lost", 0)),
            "net": _money(round(p.get("net_usd", 0.0), 2)), "lost_usd": _money(round(p.get("lost_usd", 0.0), 2))}
    return _TOKEN.sub(lambda m: vals[m.group(1)], text)


def strategies_live(rows: list[dict]) -> dict:
    """The strategy list as the app shows it: each reason already filled in by losing_trades (so the numbers are the ones on the page)."""
    why = {r["strategy"]: r["why"] for r in rows}
    return {sid: {**s, "why": why.get(sid) or render_why(str(s.get("why") or ""), None)} for sid, s in _strats().items()}


def losing_trades(j) -> dict:
    """Madhav, Oct 13: of all the lost trades, which ones won't Ananta take again, which will it try again, and which say the rules
    had to change? Every closed losing paper trade, by strategy, with the verdict and the reason; the Explorer's from its whole book.
    Each loss carries the verdict in force when it was entered (Oct 15, research audit), so changing a verdict never rewrites history."""
    per = per_strategy(j)
    strats = _strats()
    out, totals = [], collections.defaultdict(lambda: {"strategies": set(), "lost_trades": 0, "lost_usd": 0.0})
    for sid, p in per.items():
        s = strats.get(sid) or {}
        verdict = s.get("verdict") or "will_try_again"
        yardstick = sid == "RANDOM"
        if yardstick:
            verdict_words = "evidence only (a yardstick, not a strategy)"
        else:
            verdict_words = VERDICT_WORDS.get(verdict, verdict) + (" (measuring in the background)" if s.get("status") == "EVIDENCE" else "")
        at_entry = {VERDICT_WORDS.get(v, v): {"lost": d["lost"], "lost_usd": round(d["lost_usd"], 2)} for v, d in p["by_verdict"].items()}
        row = {"strategy": sid, "name": s.get("name") or sid, "status": s.get("status") or "UNLISTED", "verdict": verdict, "verdict_words": verdict_words,
               "why": render_why(str(s.get("why") or "not on the strategy list yet"), p), "closed": p["closed"], "won": p["won"], "lost": p["lost"],
               "net_usd": round(p["net_usd"], 2), "lost_usd": round(p["lost_usd"], 2), "lost_by_verdict_at_entry": at_entry,
               "verdict_changed_since": any(v != verdict for v in p["by_verdict"]), "lost_before_register": p["unrecorded"], "trades": p["trades"]}
        out.append(row)
        if not yardstick:
            for v, d in p["by_verdict"].items():
                k = totals[v]
                k["strategies"].add(sid)
                k["lost_trades"] += d["lost"]
                k["lost_usd"] += d["lost_usd"]
    out.sort(key=lambda r: r["lost_usd"])
    return {"as_of": time.strftime("%Y-%m-%d %H:%M", time.gmtime(j.now())), "by_strategy": out,
            "totals": {VERDICT_WORDS.get(k, k): {"strategies": len(v["strategies"]), "lost_trades": v["lost_trades"], "lost_usd": round(v["lost_usd"], 2)}
                       for k, v in totals.items()},
            "meaning": "A losing trade is judged by its strategy's verdict, never one by one: a strategy is judged by evidence over hundreds of "
                       "trades on history plus its paper record, not by a bad week. 'Won't take again' means THE ACCOUNT (the $500 book) will "
                       "not trade it and it will not be pushed; a book with status EVIDENCE still records paper trades in the background as a "
                       "yardstick (watching, scanning, recording), it is just never counted as holdings. Each loss is classed by the verdict "
                       "in force when the trade was entered (strategy_verdicts); trades older than the register use its first recorded verdict."}
