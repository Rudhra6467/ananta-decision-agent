"""One list of every strategy with its status and verdict (docs/knowledge/strategy_status.json; Madhav, Oct 13).

  load()                the file
  of_watch(watch)       the strategy entry a watch id belongs to ("ZONE_TOUCH-UB" -> ZONE_TOUCH)
  of_book(home_book)    the entry a home-page book belongs to ("15-minute Explorer" -> EXPLORER)
  trades(watch)         False for a RETIRED / PARKED watch: it takes no new paper trades (open ones finish on their own plan)
  counts(watch|book)    True when it belongs in the headline (ACTIVE or UNDER_REVIEW); evidence and retired books are shown apart
  losing_trades(j)      every closed losing trade classified: won't take again / will try again / rules modified, with the reason
"""
from __future__ import annotations

import collections
import json
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
    e = of_watch(watch)
    return not e or e[1].get("status") not in ("RETIRED", "PARKED")


def counts_watch(watch: str) -> bool:
    e = of_watch(watch)
    return not e or e[1].get("status") in COUNTS


def counts_book(home_book: str) -> bool:
    e = of_book(home_book)
    return not e or e[1].get("status") in COUNTS


def losing_trades(j) -> dict:
    """Madhav, Oct 13: of all the lost trades, which ones won't Ananta take again, which will it try again, and which say the rules
    had to change? Every closed losing paper trade, by strategy, with the verdict and the reason; the Explorer's from its own book."""
    from jarvis.service import views, watch_engine as W

    per: dict = collections.defaultdict(lambda: {"closed": 0, "lost": 0, "net_usd": 0.0, "lost_usd": 0.0, "trades": []})
    rows = j.db.execute(f"SELECT {', '.join(W.COLS)} FROM evidence_trades WHERE status='CLOSED'").fetchall()
    for r in rows:
        t = dict(zip(W.COLS, r))
        e = of_watch(t["watch"])
        sid = e[0] if e else t["watch"]
        p = per[sid]
        p["closed"] += 1
        p["net_usd"] += t["net_usd"] or 0
        if (t["net_usd"] or 0) < 0:
            p["lost"] += 1
            p["lost_usd"] += t["net_usd"] or 0
            if len(p["trades"]) < 60:
                p["trades"].append({"id": t["id"], "coin": t["coin"], "watch": t["watch"], "day": t.get("exit_day"), "net_usd": round(t["net_usd"] or 0, 2),
                                    "why": t.get("exit_why")})
    try:
        for x in views.trades_list(j)["closed"]:
            p = per["EXPLORER"]
            p["closed"] += 1
            p["net_usd"] += x.get("net_usd") or 0
            if (x.get("net_usd") or 0) < 0:
                p["lost"] += 1
                p["lost_usd"] += x.get("net_usd") or 0
                if len(p["trades"]) < 60:
                    p["trades"].append({"id": x["id"], "coin": x["coin"], "watch": "EXPLORER", "setup": x.get("setup_name"), "day": x.get("time"),
                                        "net_usd": round(x.get("net_usd") or 0, 2), "why": x.get("exit")})
    except Exception:  # noqa: BLE001
        pass
    strats = _strats()
    out, totals = [], collections.defaultdict(lambda: {"strategies": 0, "lost_trades": 0, "lost_usd": 0.0})
    for sid, p in per.items():
        s = strats.get(sid) or {}
        verdict = s.get("verdict") or ("will_try_again" if sid.startswith("RANDOM") or sid == "JARVIS_RANDOM" else "will_try_again")
        if s.get("status") == "EVIDENCE":
            verdict_words = "evidence only (a yardstick, not a strategy)"
        else:
            verdict_words = VERDICT_WORDS.get(verdict, verdict)
        row = {"strategy": sid, "name": s.get("name") or sid, "status": s.get("status") or "UNLISTED", "verdict": verdict, "verdict_words": verdict_words,
               "why": s.get("why") or "not on the strategy list yet", "closed": p["closed"], "lost": p["lost"], "net_usd": round(p["net_usd"], 2),
               "lost_usd": round(p["lost_usd"], 2), "trades": p["trades"]}
        out.append(row)
        if s.get("status") != "EVIDENCE" and p["lost"]:
            k = totals[verdict]
            k["strategies"] += 1
            k["lost_trades"] += p["lost"]
            k["lost_usd"] += p["lost_usd"]
    out.sort(key=lambda r: r["lost_usd"])
    return {"as_of": time.strftime("%Y-%m-%d %H:%M", time.gmtime(j.now())), "by_strategy": out,
            "totals": {VERDICT_WORDS.get(k, k): {**v, "lost_usd": round(v["lost_usd"], 2)} for k, v in totals.items()},
            "meaning": "A losing trade is judged by its strategy's verdict, never one by one: a strategy is retired by evidence over hundreds of "
                       "trades on history plus its paper record, not by a bad week. Retired strategies keep their records (they are the proof) "
                       "but take no new trades and leave the headline."}
