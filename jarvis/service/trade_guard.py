"""The trade guard (acceptance gate ops_no_trade_unhealthy, Oct 15): one check before ANY new paper position opens, in every book.

  blocked(j, book, coin, price_t, max_age_s, daily_t) -> None when the position may open, else the reason in plain words.
  In this order:
    1. the kill switch, read where the Explorer reads it (Hands /api/risk/status, manual_kill). A read that fails BLOCKS.
    2. the price's age, when its time is given: at most 5 minutes for a live quote (the eye, the universe feed), 20 minutes for
       the Explorer's last 5-minute close (its time is the bar's close: open + 5 minutes). health.py's thresholds.
    3. the daily candle's age, when its open time is given: yesterday's or today's candle only (at most 2 days 3 hours old,
       health.py's daily threshold).
  Exits, stops, targets and sells never ask: a protective exit always works, whatever the guard says.

Every block is written once per book, coin, reason and UTC day in trade_guard_log (t, day, book, coin, why) of the caller's
database, so the Evidence page and the gate can count them. recent() reads Jarvis's log and the trend book's own one (the
Explorer process writes the T3 books' blocks into portfolio_book.sqlite).
"""
from __future__ import annotations

import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

LIVE_PRICE_S = 5 * 60                 # a live quote: the eye's Kraken look, the universe feed's ticker
BAR_PRICE_S = 20 * 60                 # the Explorer's last 5-minute close: it refreshes about a minute after each quarter hour, so
                                      # just before a refresh its close is ~16 minutes old; 15 refused a minute in every 15 (Oct 15)
DAILY_S = 2 * 86400 + 3 * 3600        # yesterday's or today's daily candle (the health watchdog's daily threshold)
FAIL_MEMORY_S = 60                    # a failed kill-switch read is remembered this long (every entry meanwhile is blocked)

KILL_ON = "the kill switch is on"
KILL_UNREAD = "the kill switch could not be read"
NO_DAILY = "there is no daily candle"
DAILY_OLD = "the daily candle is older than yesterday's"
ZONES_OLD = "the zones and the market rule are more than 2 days old"

_FAIL: dict[str, Any] = {}
_DEFAULT: dict[str, Any] = {}


class Prices(dict):
    """Prices that remember when each one was seen: .t maps coin -> unix time, so the guard can check the age."""

    def __init__(self, px: dict | None = None, t: dict | None = None):
        super().__init__(px or {})
        self.t = dict(t or {})


def times(px: Any) -> dict | None:
    """The coin -> time map of prices that carry one (Prices), else None (age unknown: the caller decides)."""
    t = getattr(px, "t", None)
    return t if isinstance(t, dict) else None


class Ctx:
    """For a caller that is not a Jarvis (the Explorer process and its command line): the clock, Hands, and the database the
    blocks are written to. The caller commits (the log row joins the caller's own transaction)."""
    guard_commit = False

    def __init__(self, db, now: Callable[[], float], hands):
        self.db, self.now, self.hands = db, now, hands


def reset() -> None:
    """Forget a remembered failed read and the default Hands (tests)."""
    _FAIL.clear()
    _DEFAULT.clear()


def _now(j) -> float:
    return float(j.now()) if callable(getattr(j, "now", None)) else time.time()


def _hands(j):
    h = getattr(j, "hands", None)
    if h is not None:
        return h
    if "h" not in _DEFAULT:                    # a caller without Hands of its own (the manual book): the same API, same login
        from src.intelligence.explorer_live import Hands

        _DEFAULT["h"] = Hands()
    return _DEFAULT["h"]


def kill_switch_on(j) -> bool:
    """The kill switch, read as the Explorer reads it. Raises when it cannot be read. A failed read is remembered for a minute,
    so a burst of entries (a night's daily signals) does not wait on a silent Hands again and again: all of them are blocked."""
    h = _hands(j)
    if _FAIL.get("h") is h and time.time() - _FAIL.get("t", 0.0) < FAIL_MEMORY_S:
        raise RuntimeError(_FAIL.get("err") or "kill switch read failed")
    try:
        return bool(h.kill_switch_on())
    except Exception as exc:
        _FAIL.update(h=h, t=time.time(), err=str(exc)[:160] or type(exc).__name__)
        raise


def blocked(j, book: str, coin: str | None = None, price_t: float | None = None, max_age_s: float | None = None,
            daily_t: float | None = None) -> str | None:
    """None when a new paper position may open now; otherwise the reason (also written to trade_guard_log)."""
    now = _now(j)
    try:
        why = KILL_ON if kill_switch_on(j) else None
    except Exception:  # noqa: BLE001  fail closed: an unread kill switch is an unhealthy input
        why = KILL_UNREAD
    if why is None and price_t is not None:
        lim = float(max_age_s or LIVE_PRICE_S)
        if now - float(price_t) > lim:
            why = f"the price is more than {int(lim // 60)} minutes old"
    if why is None and daily_t is not None:
        if not daily_t:
            why = NO_DAILY
        elif now - float(daily_t) > DAILY_S:
            why = DAILY_OLD
    if why:
        refuse(j, book, coin, why)
    return why


def _day(t: float) -> str:
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d")


def _table(db) -> None:
    db.execute("CREATE TABLE IF NOT EXISTS trade_guard_log (t INTEGER, day TEXT, book TEXT, coin TEXT, why TEXT, "
               "UNIQUE (day, book, coin, why))")


def refuse(j, book: str, coin: str | None, why: str) -> str:
    """Write a block (once per book, coin, reason and UTC day) and return its reason. For checks a caller makes itself."""
    try:
        t = _now(j)
        _table(j.db)
        j.db.execute("INSERT OR IGNORE INTO trade_guard_log (t, day, book, coin, why) VALUES (?,?,?,?,?)",
                     (int(t), _day(t), book, coin or "", why))
        if getattr(j, "guard_commit", True):
            j.db.commit()
    except Exception:  # noqa: BLE001  the log never stops the guard
        pass
    return why


# Every path that opens a paper position: its name, the file that runs it, where that file runs from ("service" = this service's own
# checkout; "explorer" = the Explorer's checkout, the data folder, which only changes when main is merged and the Explorer is
# restarted) and the mark in the file that shows the check is there. coverage() reads those files, so the gate fails the day a
# module stops asking. tests/test_trade_guard.py fails when a module that opens positions is missing from this list.
PATHS = [
    ("JARVIS and its random twin (the brain)", "jarvis/service/brain.py", "service", "trade_guard"),
    ("JARVIS_BOLD and its random twin", "jarvis/service/bold.py", "service", "trade_guard"),
    ("zone touches in the 10 books (the eye)", "jarvis/service/eye.py", "service", "trade_guard"),
    ("universe zone touches and daily signals", "jarvis/service/universe_watch.py", "service", "trade_guard"),
    ("the automatic watches", "jarvis/service/watch_engine.py", "service", "trade_guard"),
    ("manual orders and the account's own watches", "jarvis/service/manual.py", "service", "trade_guard"),
    ("the $500 book", "jarvis/service/ndax_book.py", "service", "trade_guard"),
    ("the 30-coin trend books", "jarvis/service/tier30.py", "service", "trade_guard"),
    ("approving a trend-book suggestion in the app", "jarvis/service/core.py", "service", "trade_guard"),
    ("the trend books T3 (they run inside the Explorer)", "src/intelligence/explorer_live.py", "explorer", "trade_guard"),
    ("the Explorer's own setups (a switch that cannot be read pauses new entries)", "src/intelligence/explorer_live.py", "explorer",
     "KILL_SWITCH_UNREAD"),
]


def coverage(j) -> dict:
    """Which position-opening paths still call the guard, read from the code that runs: the service's own checkout, and the Explorer's
    (j.dir). {"paths": n, "ok": [names], "missing": [{"path", "file", "why"}]}."""
    root = Path(__file__).resolve().parents[2]
    ok, missing = [], []
    for name, rel, where, mark in PATHS:
        base = root if where == "service" else Path(getattr(j, "dir", root))
        try:
            text = (base / rel).read_text(errors="replace")
        except OSError:
            missing.append({"path": name, "file": rel, "why": "the file is not there"})
            continue
        if mark in text:
            ok.append(name)
        else:
            missing.append({"path": name, "file": rel, "why": "the running code does not ask the guard yet"
                            + (" (the Explorer's folder changes when main is merged and the Explorer restarts)" if where == "explorer" else "")})
    return {"paths": len(PATHS), "ok": ok, "missing": missing}


def recent(j, days: float = 7) -> list[dict]:
    """The blocks of the last N days, newest first: Jarvis's own books, and the T3 books' decisions inside the Explorer."""
    since = int(_now(j) - days * 86400)
    rows: list[tuple] = []
    try:
        _table(j.db)
        rows += [tuple(r) for r in j.db.execute("SELECT t, day, book, coin, why FROM trade_guard_log WHERE t >= ?", (since,)).fetchall()]
    except Exception:  # noqa: BLE001
        pass
    p = Path(getattr(j, "dir", ".")) / "portfolio_book.sqlite"
    if p.exists():
        try:
            con = sqlite3.connect(f"file:{p}?mode=ro", uri=True, timeout=10)
            try:
                rows += [tuple(r) for r in con.execute("SELECT t, day, book, coin, why FROM trade_guard_log WHERE t >= ?", (since,))]
            finally:
                con.close()
        except sqlite3.Error:
            pass
    return [dict(zip(("t", "day", "book", "coin", "why"), r)) for r in sorted(set(rows), reverse=True)]
