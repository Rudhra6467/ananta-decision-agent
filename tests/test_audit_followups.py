"""Research-audit follow-ups (Oct 15): the setup retirement rule's detection leg, the rebuild's "explained" breakdown by reason, and the
10-coin side-by-side check logged every night with a repair-board request under 60%."""
import json
import sqlite3
import time
import types

DAY = 86400


def _j(tmp_path, now=2_000_000_000):
    from jarvis.service import core

    return types.SimpleNamespace(dir=tmp_path, db=core.SafeDB(sqlite3.connect(":memory:", check_same_thread=False)), now=lambda: now)


def _trade(W, j, i, watch, net, entry_t, coin="SOL", status="CLOSED", hold=5):
    row = {c: None for c in W.COLS}
    row.update(id=f"a{i}", watch=watch, coin=coin, source="daily", signal_t=entry_t, signal_day="2026-10-10", entry_t=entry_t, entry=100.0,
               exit_t=None if status != "CLOSED" else entry_t + hold * DAY, exit_day="2026-10-15", exit=100 + net, status=status, net_usd=net,
               exit_why="rsi", detail="{}")
    W._insert(j, row)


# ---------------------------------------------------------------------------
# BOOK500-BRAKES: the retirement rule's detection leg
# ---------------------------------------------------------------------------
def test_a_setup_whose_last_20_closed_trades_average_below_zero_is_flagged_once_and_nothing_is_switched_off(tmp_path, monkeypatch):
    from jarvis.service import ev, exposure, requests_log, watch_engine as W

    j = _j(tmp_path)
    W._table(j)
    base = 1_790_000_000 - 1_790_000_000 % DAY
    dial = {time.strftime("%Y-%m-%d", time.gmtime(base + i * DAY)): 0 for i in range(60)}                  # days 0-59: the dial is closed
    dial.update({time.strftime("%Y-%m-%d", time.gmtime(base + i * DAY)): 1 for i in range(60, 70)})       # days 60-69: open
    monkeypatch.setattr(exposure, "dial_by_day", lambda jj: dial)
    for i in range(19):
        _trade(W, j, i, "H07-UA", -1.0, base + i * DAY)
    for i in range(5):                                  # winners entered on open-dial days belong to another cell and must not rescue this one
        _trade(W, j, 100 + i, "H07-UA", 10.0, base + (60 + i) * DAY)
    pushed = []

    def cell(rows, state="CLOSED"):
        return next(r for r in rows if r["rule"] == "H07" and r["state"] == state)

    h = cell(ev.retirement_watch(j, lambda t, b: pushed.append(t)))
    assert h["closed"] == 19 and h["of"] == 20 and h["retire"] is False and not requests_log.list_(j) and not pushed       # before 20 nothing is decided
    _trade(W, j, 19, "H07-UA", -1.0, base + 19 * DAY)
    rows = ev.retirement_watch(j, lambda t, b: pushed.append(t))
    h = cell(rows)
    assert h["closed"] == 20 and h["window_avg_pct"] == -1.0 and h["retire"] is True and h["flagged"] is True
    reqs = requests_log.list_(j)
    assert len(reqs) == 1 and reqs[0]["by"] == "ananta-auto" and "Nothing was switched off" in reqs[0]["text"] and len(pushed) == 1
    again = cell(ev.retirement_watch(j, lambda t, b: pushed.append(t)))
    assert again["retire"] is True and "flagged" not in again and len(requests_log.list_(j)) == 1 and len(pushed) == 1     # once per setup


def test_a_setup_averaging_above_zero_over_its_last_20_trades_is_not_flagged(tmp_path, monkeypatch):
    from jarvis.service import ev, exposure, requests_log, watch_engine as W

    j = _j(tmp_path)
    W._table(j)
    base = 1_790_000_000 - 1_790_000_000 % DAY
    monkeypatch.setattr(exposure, "dial_by_day", lambda jj: {time.strftime("%Y-%m-%d", time.gmtime(base + i * DAY)): 0 for i in range(60)})
    for i in range(30):                                   # 10 old losers, then 20 winners: the window is the LAST 20
        _trade(W, j, i, "H07-UA", -5.0 if i < 10 else 2.0, base + i * DAY)
    h = next(r for r in ev.retirement_watch(j) if r["rule"] == "H07" and r["state"] == "CLOSED")
    assert h["closed"] == 20 and h["window_avg_pct"] == 2.0 and h["retire"] is False and not requests_log.list_(j)


# ---------------------------------------------------------------------------
# U-REBUILD: why each rebuilt signal that is not in the ledger is "explained"
# ---------------------------------------------------------------------------
def test_each_unlogged_rebuilt_signal_is_explained_by_one_named_reason_or_not_at_all(tmp_path, monkeypatch):
    from jarvis.service import registry, trade_guard, universe_watch as U, watch_engine as W

    j = _j(tmp_path)
    W._table(j)
    trade_guard._table(j.db)
    monkeypatch.setattr(registry, "tier_of", lambda jj, c: "A")
    t = 1_790_000_000 - 1_790_000_000 % DAY
    started = t - 30 * DAY
    assert U.explain_unlogged(j, "H07-UA", "SOL", t, started) is None                                 # nothing explains it: a mismatch
    _trade(W, j, 1, "H07-UA", 0.0, t - 2 * DAY, status="OPEN")                                         # a trade already open on that rule and coin
    assert U.explain_unlogged(j, "H07-UA", "SOL", t, started) == "busy"
    read = next(w for w, spec in W.DAILY.items() if spec.get("kind") == "read" and w.endswith("-UA"))
    _trade(W, j, 2, read, 0.0, t - 1 * DAY, hold=0)                                                    # closed a day earlier, same episode
    assert U.explain_unlogged(j, read, "SOL", t, started) == "same_episode"
    j.now = lambda: t + 3600
    trade_guard.refuse(j, "H07-UB", "ETH", "the kill switch is on")
    assert U.explain_unlogged(j, "H07-UB", "ETH", t, started) == "held_back_by_trade_guard"
    assert U.explain_unlogged(j, "H07-UA", "ADA", started - DAY, started) == "before_books_started"
    monkeypatch.setattr(registry, "tier_of", lambda jj, c: "B")
    assert U.explain_unlogged(j, "H07-UA", "ADA", t, started) == "tier_changed"
    assert set(U.EXPLAINED_BY) == {"busy", "same_episode", "held_back_by_trade_guard", "parked", "before_books_started", "tier_changed"}


def test_a_rule_madhav_parked_explains_its_unlogged_signals_only_after_the_park_day(tmp_path, monkeypatch):
    """30 Oct 2026: H07 was parked on 28 Oct; run_rules skips a parked rule without asking the guard, so its signals of the 28 Oct
    candle on were never logged and the rebuild called them a mismatch (ops_reconstructable FAIL). They are now 'parked'; a candle
    judged before the park day (the 27 Oct candle, judged 28 Oct 00:05 UTC) is not explained by it."""
    import calendar

    from jarvis.service import registry, strategy_status, trade_guard, universe_watch as U, watch_engine as W

    j = _j(tmp_path)
    W._table(j)
    trade_guard._table(j.db)
    monkeypatch.setattr(registry, "tier_of", lambda jj, c: "A")
    park = calendar.timegm(time.strptime("2026-10-28", "%Y-%m-%d"))
    started = park - 30 * DAY
    strats = {"strategies": {"H07": {"status": "PARKED", "watches": ["H07", "H07-UA", "H07-UB"], "status_before_park": "ACTIVE",
                                     "parked": {"date": "2026-10-28"}}}}
    monkeypatch.setattr(strategy_status, "load", lambda: strats)
    assert U.explain_unlogged(j, "H07-UA", "LINK", park, started) == "parked"            # the 28 Oct candle, judged 29 Oct
    assert U.explain_unlogged(j, "H07-UC", "EDU", park + DAY, started) == "parked"       # tier C by prefix, the 29 Oct candle
    assert U.explain_unlogged(j, "H07-UA", "LINK", park - DAY, started) is None          # judged 28 Oct 00:05 UTC, before the park
    del strats["strategies"]["H07"]["parked"]
    assert U.explain_unlogged(j, "H07-UA", "LINK", park, started) is None                # a park without a date explains nothing
    strats["strategies"]["H07"].update(status="ACTIVE", parked={"date": "2026-10-28"})
    assert U.explain_unlogged(j, "H07-UA", "LINK", park, started) is None                # unparked: a missing signal is a mismatch again


# ---------------------------------------------------------------------------
# U-15M: the side-by-side check is logged every night and falls to the repair board under 60%
# ---------------------------------------------------------------------------
def _explorer_with(live, j):
    j._explorer = lambda: types.SimpleNamespace(store=types.SimpleNamespace(book=live))


def _events_table():
    con = sqlite3.connect(":memory:", check_same_thread=False)
    con.execute("CREATE TABLE events (seq INTEGER PRIMARY KEY AUTOINCREMENT, t INTEGER, kind TEXT, coin TEXT, id TEXT, json TEXT)")
    return con


def _order(con, t, i, setup="E1"):
    con.execute("INSERT INTO events (t, kind, coin, id, json) VALUES (?,?,?,?,?)",
                (t, "ORDER", "BTC", f"o{i}", json.dumps({"kind": "ORDER", "t": t, "coin": "BTC", "setup": setup})))


def test_the_side_by_side_check_is_logged_nightly_and_under_60_percent_it_reaches_the_repair_board_once_a_week(tmp_path):
    from jarvis.service import requests_log, universe_explorer as UE, universe_watch as U

    now = 1_790_000_000
    j = _j(tmp_path, now)
    j.db.execute("CREATE TABLE IF NOT EXISTS engine_state (k TEXT PRIMARY KEY, v TEXT)")
    live = _events_table()
    _explorer_with(live, j)
    mine = UE._con(j)
    for i in range(1, 13):                        # this engine: 12 orders in the last 12 hours
        _order(mine, now - 3600 * i, i)
    for i in range(1, 7):                         # the live Explorer sees the first 6 of them ...
        _order(live, now - 3600 * i, i)
    for i in range(13, 25):                       # ... plus 12 more this engine did not
        _order(live, now - 3600 * i, i)
    mine.commit()
    out = UE.compare_nightly(j)
    assert out["72h"]["same_like_for_like"] == 6 and out["72h"]["events_like_for_like"] == 24 and out["72h"]["agreement_like_for_like_pct"] == 25.0
    assert out["alert"] is True and out["24h"]["events_like_for_like"] == 24
    logged = j.db.execute("SELECT hours, like_n, like_pct FROM explorer_compare ORDER BY hours").fetchall()
    assert logged == [(24.0, 24, 25.0), (72.0, 24, 25.0)]
    fwd = U.forward(j, None, compare=out)
    assert any(f["key"].startswith("compare:") for f in fwd) and any("side-by-side" in r["text"] for r in requests_log.list_(j))
    assert not [f for f in U.forward(j, None, compare=out) if f["key"].startswith("compare:")]            # the same week: once


def test_a_quiet_stretch_or_a_good_agreement_raises_no_alert(tmp_path):
    from jarvis.service import requests_log, universe_explorer as UE, universe_watch as U

    now = 1_790_000_000
    j = _j(tmp_path, now)
    j.db.execute("CREATE TABLE IF NOT EXISTS engine_state (k TEXT PRIMARY KEY, v TEXT)")
    live = _events_table()
    _explorer_with(live, j)
    mine = UE._con(j)
    for i in range(1, 5):                         # 4 events each side and none agree: under 20 events between them, so no alert however low
        _order(mine, now - 3600 * i, i)
        _order(live, now - 3600 * i - 7 * 3600, i + 100)
    mine.commit()
    out = UE.compare_nightly(j)
    assert out["72h"]["events_like_for_like"] == 8 and out["72h"]["agreement_like_for_like_pct"] == 0.0 and out["alert"] is False
    assert not [f for f in U.forward(j, None, compare=out) if f["key"].startswith("compare:")] and not requests_log.list_(j)
    # 20+ events and 75% agreement: no alert
    (tmp_path / "second").mkdir()
    j2 = _j(tmp_path / "second", now)
    live2 = _events_table()
    _explorer_with(live2, j2)
    mine2 = UE._con(j2)
    for i in range(1, 25):
        _order(mine2, now - 3600 * i, i)
        if i <= 18:
            _order(live2, now - 3600 * i, i)
    mine2.commit()
    out2 = UE.compare_nightly(j2)
    assert out2["72h"]["events_like_for_like"] == 24 and out2["72h"]["agreement_like_for_like_pct"] == 75.0 and out2["alert"] is False
