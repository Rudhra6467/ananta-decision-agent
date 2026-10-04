"""One scoreboard for every watch (Madhav, 2026-10-03: "if every watch trades, only then we can measure its performance").

Every watch in the registry (docs/knowledge/watches.json) that trades has an evidence book; this module reads them all
(read-only) into one table with the same columns:

  closed / open trades, wins and win rate, net and average per $100 trade after costs, independent market events,
  the worst run (largest fall of the running total), results by market regime (Bitcoin above / below its 50-day),
  and the average against the random baseline with the same horizon.

Books read: the Explorer (real trades plus the signals a slot or cap blocked, the would-be trades, so each setup's every
signal counts; random entries as the 15-minute baseline), Hunter's book (SD6: real trades plus shadows kept when the book was
full; costs at Kraken's 0.80% a side), and the daily / live evidence book (watch_engine: your setups, the short dip trade,
zone touches, the daily random baselines, and Jarvis's own decisions with their random twins). The trend portfolio is a portfolio, not single trades: it is shown with its
return against buy-and-hold.

Small numbers are small: a watch is only "ahead of random" with at least 10 independent events.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

MIN_EVENTS = 10
BLOCKED = ("REJECTED_SLOT", "CAP", "REJECTED_DUP")            # a trade type fitted; only a limit stopped it
DAY = 86400


def registry(j) -> dict:
    from jarvis.service.core import docs_dir

    try:
        return json.loads((docs_dir(j.dir) / "knowledge" / "watches.json").read_text())
    except Exception:  # noqa: BLE001
        return {"sections": [], "watches": []}


def _btc(j):
    from jarvis.service.reads_watch import _daily
    from src.research import reads as R

    D = _daily(j, "BTC")
    return R.Series(D) if D else None


def _regime(B, t) -> str | None:
    if B is None or not t:
        return None
    from jarvis.service.watch_engine import regime_at

    return regime_at(B, int(t))


# ---------------------------------------------------------------------------
# books -> rows {watch, coin, status OPEN/CLOSED, entry_t, exit_t, net, regime, kind}
# ---------------------------------------------------------------------------
def _explorer(j, B) -> list[dict]:
    from jarvis.service import views

    ex = j._explorer()
    if not ex:
        return []
    entry = {}
    for tid, js in ex.store.book.execute("SELECT id, json FROM trades"):
        try:
            entry[tid] = (json.loads(js) or {}).get("entry_t")
        except ValueError:
            pass
    rows = []
    for o in views._outcomes(ex):
        sh = o.get("shadow")
        if sh == "RANDOM":
            w = "RANDOM_15M"
        elif sh in (None,) + BLOCKED:
            w = o.get("setup")
        else:
            continue                                         # NO_TYPE / MISSED_CHASE: the rulebook itself would not trade them
        et = entry.get(o["id"])
        rows.append({"watch": w, "coin": o.get("coin"), "status": "CLOSED", "entry_t": et, "exit_t": o.get("exit_t"), "net": o["net"],
                     "regime": _regime(B, et or o.get("exit_t")), "real": sh is None})
    for e in ex.st["engines"].values():                      # open trades and blocked signals still running
        for t in e.trades:
            if t.actual.done or not (t.shadow is None or t.shadow in BLOCKED or t.shadow == "RANDOM"):
                continue
            rows.append({"watch": "RANDOM_15M" if t.shadow == "RANDOM" else t.setup, "coin": t.coin, "status": "OPEN", "entry_t": t.entry_t,
                         "exit_t": None, "net": None, "regime": _regime(B, t.entry_t), "real": t.shadow is None})
    return rows


def _sd6(j, B) -> list[dict]:
    p = Path(j.dir) / "paper_book.sqlite"
    if not p.exists():
        return []
    con = sqlite3.connect(f"file:{p}?mode=ro", uri=True, timeout=10)
    rows = []
    try:
        for status, js in con.execute("SELECT status, payload_json FROM positions"):
            d = json.loads(js)
            core = (d.get("core") or "").upper()
            if core not in ("HUNTER", "SQUEEZE"):
                continue
            et = (d.get("entry_bar_close_ms") or 0) / 1000 or None
            closed = status in ("CLOSED", "SHADOW_CLOSED")
            xt = (d.get("exit_bar_open_ms") or 0) / 1000 + 3600 if closed and d.get("exit_bar_open_ms") else None
            rows.append({"watch": core, "coin": d.get("asset"), "status": "CLOSED" if closed else "OPEN", "entry_t": et, "exit_t": xt,
                         "net": d.get("realized_pnl_usd") if closed else None, "regime": _regime(B, et), "real": not status.startswith("SHADOW")})
    finally:
        con.close()
    return rows


def _engine(j) -> list[dict]:
    from jarvis.service import watch_engine

    return [{"watch": t["watch"], "coin": t["coin"], "status": "OPEN" if t["status"] in ("OPEN", "WAITING") else "CLOSED",
             "entry_t": t["entry_t"] or t["signal_t"], "exit_t": t["exit_t"], "net": t["net_usd"], "regime": t["regime"], "real": True}
            for t in watch_engine.trades(j, None, 5000)]


# ---------------------------------------------------------------------------
# stats
# ---------------------------------------------------------------------------
def _events(rows: list[dict], daily: bool) -> int:
    """Independent market moves: daily watches = entries within 3 days (any coin) are one event (the repair shop's rule);
    15-minute / hourly watches = exits within an hour are one move."""
    key = "entry_t" if daily else "exit_t"
    gap = 3 * DAY if daily else 3600
    ts = sorted(int(r.get(key) or 0) for r in rows)
    n, last = 0, None
    for t in ts:
        if last is None or t - last > gap:
            n += 1
        last = t
    return n


def stats(rows: list[dict], daily: bool) -> dict:
    closed = [r for r in rows if r["status"] == "CLOSED" and r.get("net") is not None]
    n = len(closed)
    tot = sum(r["net"] for r in closed)
    run = peak = worst = 0.0
    for r in sorted(closed, key=lambda r: r.get("exit_t") or 0):
        run += r["net"]
        peak = max(peak, run)
        worst = min(worst, run - peak)
    by = {}
    for reg in ("ALLOWED", "RISK_OFF"):
        sub = [r["net"] for r in closed if r.get("regime") == reg]
        by[reg] = {"closed": len(sub), "avg_usd": round(sum(sub) / len(sub), 2) if sub else None}
    return {"closed": n, "open": sum(1 for r in rows if r["status"] == "OPEN"), "wins": sum(1 for r in closed if r["net"] > 0),
            "win_rate": round(sum(1 for r in closed if r["net"] > 0) / n, 2) if n else None, "net_usd": round(tot, 2),
            "avg_usd": round(tot / n, 2) if n else None, "events": _events(closed, daily) if n else 0, "worst_run_usd": round(worst, 2),
            "by_regime": by, "real_closed": sum(1 for r in closed if r.get("real"))}


BASELINE = {"15m": "RANDOM_15M", "1h": "RANDOM_15M"}


def _baseline_for(w: dict) -> str | None:
    if w["section"] == "BASELINES":
        return None
    if w.get("baseline"):
        return w["baseline"]
    if w["timeframe"] in BASELINE:
        return BASELINE[w["timeframe"]]
    ex = (w.get("exit") or "").lower()
    if "10 days" in ex:
        return "RANDOM_10D"
    if "20 days" in ex:
        return "RANDOM_20D"
    if "30 days" in ex:
        return "RANDOM_30D"
    return None


def board(j) -> dict:
    reg = registry(j)
    B = None
    try:
        B = _btc(j)
    except Exception:  # noqa: BLE001
        pass
    rows: list[dict] = []
    errors = {}
    for name, fn in (("explorer", lambda: _explorer(j, B)), ("sd6", lambda: _sd6(j, B)), ("engine", lambda: _engine(j))):
        try:
            rows += fn()
        except Exception as exc:  # noqa: BLE001  one book failing must not hide the others
            errors[name] = str(exc)[:160]
    by_watch: dict[str, list] = {}
    for r in rows:
        by_watch.setdefault(r["watch"], []).append(r)
    order = {s["id"]: k for k, s in enumerate(reg.get("sections", []))}
    out, base_avg = [], {}
    trading = [w for w in reg.get("watches", []) if w.get("size_usd")]
    for w in trading:
        s = stats(by_watch.get(w["id"], []), daily=w["timeframe"] in ("1d", "live"))
        if w["section"] == "BASELINES":
            base_avg[w["id"]] = s["avg_usd"]
        out.append({"id": w["id"], "name": w["name"], "section": w["section"], "timeframe": w["timeframe"], "book": w["book"],
                    "status": w["status"], "since": w.get("since"), "costs": w.get("costs"), **s})
    for r in out:
        w = next(x for x in trading if x["id"] == r["id"])
        b = _baseline_for(w)
        r["baseline"] = b
        r["vs_random_usd"] = round(r["avg_usd"] - base_avg[b], 2) if b and r["avg_usd"] is not None and base_avg.get(b) is not None else None
        r["verdict"] = ("the bar to beat" if r["section"] == "BASELINES" else "too early" if r["events"] < MIN_EVENTS else
                        "ahead of random" if (r["vs_random_usd"] or 0) > 0 else "not ahead of random")
    out.sort(key=lambda r: (order.get(r["section"], 9), r["id"]))
    t3 = None
    try:
        from jarvis.service import views

        tr = next((x.get("tracking") or {} for x in views.evidence_forwarded(j)["in_use"] if x["id"] == "T3"), {})
        t3 = {"return_pct": tr.get("main_return_pct"), "buy_hold_pct": tr.get("buy_hold_return_pct"), "automatic_copy_pct": tr.get("shadow_return_pct"),
              "days": tr.get("days")}
    except Exception:  # noqa: BLE001
        pass
    ahead = [r["name"] for r in out if r["verdict"] == "ahead of random"]
    return {"watches": out, "trend_portfolio": t3, "errors": errors,
            "headline": (f"Ahead of random with enough events: {', '.join(ahead)}." if ahead else
                         f"No watch has {MIN_EVENTS} independent events yet, so none can be called ahead of random; the books keep filling."),
            "how_to_read": "Each row is one watch's evidence book: every signal it gave is a $100 paper trade (blocked signals included), "
                           "after costs. Compare the average with its random baseline (same holding time); count events, not trades: "
                           "our coins move together, so trades closing in the same move are one piece of evidence. Hunter's book pays "
                           "Kraken's 0.80% a side; the rest pay NDAX's 0.20% plus the spread."}
