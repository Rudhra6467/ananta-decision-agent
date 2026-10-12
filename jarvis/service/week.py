"""The last 7 days, every book (request #34, Oct 11: Madhav asked for last week's wins and losses and Ananta could only give totals
since late September). Trades CLOSED in the window, per book: wins, losses, net and average per $100 after costs, best and worst,
and how many separate market events they came from, with the random entries beside them as the bar to beat. Reporting only."""
from __future__ import annotations

from typing import Any

DAY = 86400
# evidence_trades watches by book (a tier suffix such as -UA, -UB, -UC, -T30 belongs to the same book)
BOOKS = (("JARVIS", "Jarvis's own trades"), ("JARVIS_RANDOM", "Jarvis's random twins (its bar to beat)"),
         ("ZONE_TOUCH", "Zone touch watch"), ("H07", "Dip trade (H07)"), ("M2a", "Watch M2a"), ("M3a", "Watch M3a"),
         ("RANDOM_", "Random entries, daily watches (the bar to beat)"))


def _family(watch: str) -> str | None:
    for key, _ in BOOKS:
        if watch == key or watch.startswith(key + "-") or (key.endswith("_") and watch.startswith(key)):
            return key
    return None


def _line(key: str, label: str, rows: list[tuple[str, float, float]]) -> dict[str, Any]:
    """rows: (coin, exit_t, net per $100)."""
    from jarvis.service.scoreboard import independent_events

    n = len(rows)
    net = sum(r[2] for r in rows)
    best = max(rows, key=lambda r: r[2]) if rows else None
    worst = min(rows, key=lambda r: r[2]) if rows else None
    return {"key": key, "label": label, "closed": n, "wins": sum(1 for r in rows if r[2] > 0), "losses": sum(1 for r in rows if r[2] <= 0),
            "net_usd": round(net, 2), "avg_usd": round(net / n, 2) if n else None,
            "best": {"coin": best[0], "usd": round(best[2], 2)} if best else None,
            "worst": {"coin": worst[0], "usd": round(worst[2], 2)} if worst else None,
            "events": independent_events([r[1] for r in rows], daily=False) if rows else 0}


def week(j, days: int = 7) -> dict[str, Any]:
    now = j.now()
    since = now - days * DAY
    books: list[dict] = []
    errors: dict[str, str] = {}
    try:
        from jarvis.service import views

        rows = [r for r in views._outcomes(j._explorer()) if (r.get("exit_t") or 0) >= since]
        books.append(_line("explorer", "Explorer: real paper trades", [(r["coin"], r["exit_t"], r["net"]) for r in rows if not r["shadow"]]))
        books.append(_line("explorer_random", "Explorer: random entries (the bar to beat)",
                           [(r["coin"], r["exit_t"], r["net"]) for r in rows if r["shadow"] == "RANDOM"]))
    except Exception as exc:  # noqa: BLE001
        errors["explorer"] = str(exc)[:160]
    try:
        fam: dict[str, list] = {}
        for watch, coin, exit_t, net in j.db.execute("SELECT watch, coin, exit_t, net_usd FROM evidence_trades WHERE status='CLOSED' "
                                                     "AND exit_t >= ? AND net_usd IS NOT NULL", (since,)):
            k = _family(watch)
            if k:
                fam.setdefault(k, []).append((coin, exit_t, net))
        for key, label in BOOKS:
            if key in fam:
                books.append(_line(key, label, fam[key]))
    except Exception as exc:  # noqa: BLE001
        errors["evidence"] = str(exc)[:160]
    own = None
    try:
        from jarvis.service.manual import Manual

        Mn = Manual(j.db, j.now)
        f = [x for x in Mn.fills(500) if (x["t"] or 0) >= since]
        st = Mn.state(j.prices())
        own = {"label": "Your own paper book", "buys": sum(1 for x in f if x["side"] == "BUY"), "sells": sum(1 for x in f if x["side"] == "SELL"),
               "equity": st.get("equity"), "return_pct_since_start": st.get("return_pct"), "realized_since_start": st.get("realized")}
    except Exception as exc:  # noqa: BLE001
        errors["own"] = str(exc)[:160]
    real = [b for b in books if b["key"] in ("explorer", "JARVIS", "ZONE_TOUCH", "H07", "M2a", "M3a") and b["closed"]]
    tot = sum(b["closed"] for b in real)
    out = {"days": days, "since_t": int(since), "books": books, "own_book": own,
           "totals": {"closed": tot, "wins": sum(b["wins"] for b in real), "losses": sum(b["losses"] for b in real),
                      "net_usd": round(sum(b["net_usd"] for b in real), 2)},
           "read": "Trades closed in the last 7 days, each a $100 paper trade after costs. Random entries are the bar to beat; "
                   "trades closing on the same day are one market event, not separate evidence."}
    if errors:
        out["errors"] = errors
    return out
