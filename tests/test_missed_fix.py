"""The missed-moves study, Oct 20 fixes.

1. Each tier's review guards on its own tier: universe_watch.missed() (UNIV, dfb84fe) writes its rows for the day first, and the old
   guard ("any row for that day") skipped the live 10 and the 30-coin tier on 9 of 11 nights from Oct 9 (silent-failure audit, issue 2).
2. Each CAUGHT row records the books that were in the move, whether each may trade, and its P&L (Madhav, Oct 20); reporting only.
3. No summary shows a catch P&L total or average before 2026-12-15 (pre-registered review #38): counts only until then.
"""
import hashlib
import json
import sqlite3
import time
import types
from datetime import datetime, timezone
from pathlib import Path

import pytest

from tests.test_reads import DAY, _bars

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _no_live_prices():
    from jarvis.service import eye

    eye.STATE.update(prices={})


def _t(day: str) -> int:
    return int(datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())


def _j(tmp_path, now):
    return types.SimpleNamespace(dir=tmp_path, db=sqlite3.connect(":memory:"), now=lambda: now["t"], prices=lambda: {})


def _store(tmp_path, rows):
    con = sqlite3.connect(tmp_path / "explorer_bars.sqlite")
    con.execute("CREATE TABLE IF NOT EXISTS bars (coin TEXT, tf TEXT, t INTEGER, o REAL, h REAL, l REAL, c REAL, v REAL, PRIMARY KEY (coin, tf, t))")
    con.executemany("INSERT OR REPLACE INTO bars VALUES (?,?,?,?,?,?,?,?)", rows)
    con.commit()
    con.close()


def _sol_move(tmp_path):
    """300 daily candles, then a day on which SOL rises 8% on 15-minute candles (the test_jarvis_brain set-up)."""
    up = [100 * (1.001 ** k) for k in range(300)]
    D = _bars(up, wick=0.01)
    day_t = D[-1][0] + DAY
    q = []
    for k in range(96):
        base = up[-1] * (1.08 if k > 60 else 1 + 0.002 * max(0, k - 40) if k > 40 else 1.0)
        q.append((day_t + 900 * k, base, base * 1.001, base * 0.999, base, 10.0))
    _store(tmp_path, [(c, "1d", *b) for c in ("BTC", "SOL") for b in D] + [("SOL", "15m", *b) for b in q])
    return day_t


def _univ_row(missed, day: str, coin: str = "AVA", label: str = "CAUGHT", saw=None, low_t: int = 0) -> dict:
    return {"id": f"{day}:UNIV:{coin}", "day": day, "coin": coin, "low_t": low_t, "high_t": low_t + DAY, "low": 1.0, "high": 1.2, "move_pct": 20.0,
            "move_atr": 2.0, "label": label, "saw": json.dumps(saw or {"traded": [], "saw": []}), "kind": "breakout", "pattern": "breakout|no zone|ALLOWED",
            "why": "tier B", "tier": "UNIV", "miss_class": None if label == "CAUGHT" else "DETECTION"}


# ---------------------------------------------------------------------------
# 1. the skipped reviews
# ---------------------------------------------------------------------------
def test_a_univ_row_written_first_no_longer_skips_the_live_and_tier_reviews(tmp_path):
    from jarvis.service import missed

    day_t = _sol_move(tmp_path)
    j = _j(tmp_path, {"t": day_t + DAY + 3600})
    missed._table(j)
    day = missed._day_str(day_t)
    missed._insert(j, _univ_row(missed, day, low_t=day_t))                 # universe_watch.missed() ran first, as it does every night
    j.db.commit()
    # the old guard: "any row for that day" -> done before (this is the skip)
    assert j.db.execute("SELECT 1 FROM missed_moves WHERE day=? LIMIT 1", (day,)).fetchone()
    r = missed.run(j)
    assert not r.get("done_before") and r["ran"] == ["LIVE10", "T30"]
    live = j.db.execute("SELECT coin, label FROM missed_moves WHERE day=? AND tier='LIVE10'", (day,)).fetchall()
    assert live == [("SOL", "MISSED")]
    assert j.db.execute("SELECT 1 FROM engine_state WHERE k=?", (f"missed:{day}",)).fetchone()
    assert j.db.execute("SELECT 1 FROM engine_state WHERE k=?", (f"missed_t30:{day}",)).fetchone()
    assert missed.run(j)["done_before"]                                    # still once a day


def test_each_tier_guards_on_its_own_tier(tmp_path, monkeypatch):
    from jarvis.service import missed

    calls = []
    monkeypatch.setattr(missed, "moves", lambda j, day_t: calls.append("LIVE10") or [])
    monkeypatch.setattr(missed, "run_t30", lambda j, day_t: calls.append("T30") or [])
    day_t = _t("2026-10-14")
    j = _j(tmp_path, {"t": day_t + DAY + 3600})
    missed._table(j)
    j.db.execute("INSERT INTO engine_state (k, v) VALUES ('missed:2026-10-14', '0')")   # the live review ran, the tier's did not
    assert missed.run(j)["ran"] == ["T30"] and calls == ["T30"]
    calls.clear()
    j2 = _j(tmp_path, {"t": day_t + DAY + 3600})
    missed._table(j2)
    missed._insert(j2, {**_univ_row(missed, "2026-10-14"), "id": "2026-10-14:T30:WLD", "tier": "T30"})   # a 30-coin row only
    assert missed.run(j2)["ran"] == ["LIVE10"] and calls == ["LIVE10"]
    calls.clear()
    assert missed.run(j2)["done_before"] and calls == []


def test_backfill_reruns_only_the_skipped_days_with_force(tmp_path, monkeypatch):
    from jarvis.service import missed

    seen = []
    real_run = missed.run
    monkeypatch.setattr(missed, "moves", lambda j, day_t: [])
    monkeypatch.setattr(missed, "run_t30", lambda j, day_t: [])
    monkeypatch.setattr(missed, "run", lambda j, day_t=None, log_request=None, force=False: seen.append((missed._day_str(day_t), force))
                        or real_run(j, day_t, log_request, force))
    j = _j(tmp_path, {"t": _t("2026-10-20") + 3600})
    missed._table(j)
    for d in ("2026-10-12", "2026-10-18"):                                 # the two nights the review did run
        j.db.execute("INSERT INTO engine_state (k, v) VALUES (?, '3')", (f"missed:{d}",))
    for d in ("2026-10-13", "2026-10-19"):                                 # UNIV rows do not count as the live review
        missed._insert(j, _univ_row(missed, d))
    want = ["2026-10-09", "2026-10-10", "2026-10-11", "2026-10-13", "2026-10-14", "2026-10-15", "2026-10-16", "2026-10-17", "2026-10-19"]
    assert missed.skipped_days(j) == want
    out = missed.backfill(j, log_request=lambda t: {"num": None})
    assert [d for d, _ in seen] == want and all(f for _, f in seen)
    assert set(out) - {"_scored"} == set(want)
    assert missed.skipped_days(j) == []                                     # once
    assert j.db.execute("SELECT COUNT(*) FROM missed_moves WHERE tier='UNIV'").fetchone()[0] == 2   # the universe's rows untouched


# ---------------------------------------------------------------------------
# the migration (the Oct 14 incident was a positional INSERT after a column change)
# ---------------------------------------------------------------------------
OLD16 = ("CREATE TABLE missed_moves (id TEXT PRIMARY KEY, day TEXT, coin TEXT, low_t INTEGER, high_t INTEGER, low REAL, high REAL, move_pct REAL, "
         "move_atr REAL, label TEXT, saw TEXT, kind TEXT, at_zone TEXT, regime TEXT, pattern TEXT, why TEXT)")


@pytest.mark.parametrize("shape", ["16 columns (before tiers)", "18 columns (live until Oct 20)"])
def test_migration_adds_the_catch_columns_in_place_and_keeps_old_rows(tmp_path, shape):
    from jarvis.service import missed

    j = _j(tmp_path, {"t": _t("2026-10-21")})
    j.db.execute(OLD16)
    if shape.startswith("18"):
        j.db.execute("ALTER TABLE missed_moves ADD COLUMN tier TEXT DEFAULT 'LIVE10'")
        j.db.execute("ALTER TABLE missed_moves ADD COLUMN miss_class TEXT")
    j.db.execute("INSERT INTO missed_moves (id, day, coin, label, why) VALUES ('old', '2026-10-05', 'SOL', 'MISSED', 'kept')")
    missed._table(j)
    missed._table(j)                                                       # twice: the guard holds, nothing added again
    cols = [r[1] for r in j.db.execute("PRAGMA table_info(missed_moves)")]
    assert tuple(cols) == missed.COLS                                       # named order = the table's order, migrated or fresh
    fresh = _j(tmp_path, {"t": 0})
    missed._table(fresh)
    assert [r[1] for r in fresh.db.execute("PRAGMA table_info(missed_moves)")] == cols
    assert j.db.execute("SELECT coin, label, why, coalesce(tier, 'LIVE10'), caught_books FROM missed_moves WHERE id='old'").fetchone() == (
        "SOL", "MISSED", "kept", "LIVE10", None)
    missed._insert(j, {**_univ_row(missed, "2026-10-19"), "caught_allowed": 1, "caught_pnl_usd": 1.5})
    assert j.db.execute("SELECT caught_allowed, caught_pnl_usd, tier FROM missed_moves WHERE id='2026-10-19:UNIV:AVA'").fetchone() == (1, 1.5, "UNIV")
    src = (ROOT / "jarvis" / "service" / "missed.py").read_text()
    assert "INTO missed_moves VALUES" not in src and "INTO engine_state VALUES" not in src   # named columns everywhere


# ---------------------------------------------------------------------------
# 2. the catch's books and P&L
# ---------------------------------------------------------------------------
def _books(tmp_path, j):
    from jarvis.service import watch_engine

    watch_engine._table(j)
    t0 = _t("2026-10-14")
    rows = [("z1", "ZONE_TOUCH-UC", "AVA", t0 - 5 * DAY, None, None, 1.0, "OPEN"),          # monitor-only (won't take again), open
            ("h1", "H07-UB", "AVA", t0 - DAY, t0 + 2 * DAY, 7.77, 1.0, "CLOSED"),           # allowed, realised
            ("b1", "JARVIS_BOLD", "AVA", t0, None, None, 1.0, "OPEN"),                      # monitor-only (never wakes the brain)
            ("r1", "RANDOM_20D", "AVA", t0, None, None, 1.0, "OPEN"),                       # a random twin: never "in it"
            ("j1", "JARVIS", "PHA", t0, None, None, 2.0, "OPEN")]                           # allowed (the brain's book), marked
    for tid, w, c, et, xt, net, entry, st in rows:
        j.db.execute("INSERT INTO evidence_trades (id, watch, coin, entry_t, exit_t, net_usd, entry, status) VALUES (?,?,?,?,?,?,?,?)",
                     (tid, w, c, et, xt, net, entry, st))
    con = sqlite3.connect(tmp_path / "universe_bars.sqlite")
    con.execute("CREATE TABLE px (coin TEXT PRIMARY KEY, price REAL, t INTEGER)")
    con.executemany("INSERT INTO px (coin, price, t) VALUES (?,?,?)", [("AVA", 1.5, t0), ("PHA", 2.2, t0)])
    con.commit()
    con.close()
    return t0


def _snapshot(j):
    return sorted(j.db.execute("SELECT * FROM evidence_trades").fetchall()), hashlib.sha256((ROOT / "docs/knowledge/strategy_status.json").read_bytes()).hexdigest()


def test_each_catch_records_its_books_whether_they_may_trade_and_their_pnl(tmp_path):
    from jarvis.service import missed, watch_engine

    j = _j(tmp_path, {"t": _t("2026-10-20")})
    missed._table(j)
    t0 = _books(tmp_path, j)
    before = _snapshot(j)
    for d in ("2026-10-14", "2026-10-15"):                                 # the same AVA trades span two days: one trade, two rows
        missed._insert(j, _univ_row(missed, d, "AVA", low_t=_t(d), saw={"traded": ["ZONE_TOUCH-UC", "H07-UB", "JARVIS_BOLD"], "saw": []}))
    missed._insert(j, _univ_row(missed, "2026-10-14", "PHA", low_t=t0, saw={"traded": ["JARVIS"], "saw": []}))
    missed._insert(j, _univ_row(missed, "2026-10-14", "OP", low_t=t0, label="MISSED"))
    assert missed.score_catches(j)["scored"] == 3
    got = {r[0]: r[1:] for r in j.db.execute("SELECT id, caught_allowed, caught_pnl_usd, caught_books FROM missed_moves")}
    ava = json.loads(got["2026-10-14:UNIV:AVA"][2])
    by = {h["book"]: h for h in ava}
    assert set(by) == {"ZONE_TOUCH-UC", "H07-UB", "JARVIS_BOLD"}            # the random twin is never a catch
    assert by["ZONE_TOUCH-UC"]["allowed"] is False and by["ZONE_TOUCH-UC"]["monitor_why"] == "won't take again"
    assert by["JARVIS_BOLD"]["allowed"] is False and "never wake" in by["JARVIS_BOLD"]["monitor_why"]
    assert by["H07-UB"]["allowed"] is True and by["H07-UB"]["pnl"] == "realised" and by["H07-UB"]["pnl_usd"] == 7.77
    assert by["ZONE_TOUCH-UC"]["pnl"] == "marked" and by["ZONE_TOUCH-UC"]["pnl_usd"] == watch_engine.net("AVA", 1.0, 1.5, "ZONE_TOUCH-UC")
    assert got["2026-10-14:UNIV:AVA"][:2] == (1, 7.77)                     # the row's P&L is the allowed books' only
    pha = got["2026-10-14:UNIV:PHA"]
    assert pha[0] == 1 and pha[1] == watch_engine.net("PHA", 2.0, 2.2, "JARVIS")
    assert got["2026-10-14:UNIV:OP"] == (None, None, None)                 # not caught: nothing recorded
    assert missed.book_allowed("EXPLORER") == (False, "won't take again") and missed.book_allowed("HOURLY")[0] is False
    assert missed.book_allowed("RANDOM") == (False, "a random baseline") and missed.book_allowed(None)[0] is False
    assert missed.book_allowed("BOOK500") == (True, None) and missed.book_allowed("H07") == (True, None)
    assert _snapshot(j) == before                                           # reporting only: no book, trade or register changed
    j.db.execute("DELETE FROM evidence_trades WHERE id='z1'")               # scoring again only touches the open ones; idempotent
    missed.score_catches(j)
    assert {h["book"] for h in json.loads(j.db.execute("SELECT caught_books FROM missed_moves WHERE id='2026-10-14:UNIV:AVA'").fetchone()[0])} == {
        "H07-UB", "JARVIS_BOLD"}


def test_only_monitor_only_watches_in_a_move_is_not_a_trade_ok_catch(tmp_path):
    from jarvis.service import missed

    j = _j(tmp_path, {"t": _t("2026-10-20")})
    missed._table(j)
    _books(tmp_path, j)
    j.db.execute("DELETE FROM evidence_trades WHERE id IN ('h1')")
    missed._insert(j, _univ_row(missed, "2026-10-17", "AVA", low_t=_t("2026-10-17"), saw={"traded": ["ZONE_TOUCH-UC"], "saw": []}))
    missed.score_catches(j)
    assert j.db.execute("SELECT caught_allowed, caught_pnl_usd FROM missed_moves").fetchone() == (0, None)
    c = missed.recent(j, 7)["universe"]["counts"]
    assert (c["CAUGHT"], c["CAUGHT_TRADE_OK"], c["CAUGHT_MONITOR_ONLY"]) == (1, 0, 1)


# ---------------------------------------------------------------------------
# 3. review #38's date guard
# ---------------------------------------------------------------------------
def _scored(tmp_path, now):
    from jarvis.service import missed

    j = _j(tmp_path, now)
    missed._table(j)
    _books(tmp_path, j)
    for d in ("2026-12-01", "2026-12-02"):
        missed._insert(j, _univ_row(missed, d, "AVA", low_t=_t("2026-10-14"), saw={"traded": ["H07-UB", "ZONE_TOUCH-UC"], "saw": []}))
    missed.score_catches(j, since="2026-12-01")
    assert j.db.execute("SELECT caught_pnl_usd FROM missed_moves WHERE day='2026-12-01'").fetchone()[0] == 7.77   # recorded per row
    return j


def test_no_catch_pnl_is_shown_before_review_38s_look(tmp_path):
    from jarvis.service import missed

    assert missed.PNL_SHOWN_FROM == "2026-12-15" and missed.REVIEW38_FROM == "2026-10-21"
    now = {"t": _t("2026-12-14") + DAY - 1}                                 # the last second of Dec 14 UTC
    j = _scored(tmp_path, now)
    out = missed.recent(j, 30)
    text = json.dumps(out)
    assert "pnl" not in text.lower() and "7.77" not in text and "avg_usd" not in text
    assert out["universe"]["counts"]["CAUGHT_TRADE_OK"] == 2 and out["catches"]["all_tiers"]["CAUGHT_TRADE_OK"] == 2
    assert "not shown before 2026-12-15" in out["catches"]["money"]
    now["t"] = _t("2026-12-15")                                             # the day of the one look
    out = missed.recent(j, 30)
    m = out["catches"]["money"]["allowed_to_trade"]
    assert m["trades"] == 1 and m["pnl_usd"] == 7.77                        # the same trade in two moves counts once
    assert out["universe"]["moves"][0]["catch_pnl_usd"] == 7.77


def test_no_other_module_reads_the_catch_pnl_columns():
    """Pages, Ask, the reviews and the morning review read catches through missed.recent() only, so the date guard cannot be bypassed."""
    bad = []
    for g in ("jarvis/**/*.py", "src/**/*.py"):
        for p in ROOT.glob(g):
            if p.name == "missed.py" and p.parent.name == "service":
                continue
            t = p.read_text(errors="ignore")
            if any(w in t for w in ("caught_pnl_usd", "caught_books", "_catch_money")):
                bad.append(str(p.relative_to(ROOT)))
    assert not bad, bad
