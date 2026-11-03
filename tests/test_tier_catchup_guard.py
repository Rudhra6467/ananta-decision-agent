"""#105/#138 (Madhav's yes, 3 Nov 2026): a coin that comes back into a tier with an old cursor catches up its last 10 days; it must not
write signals for days it was not in that tier (MITO's 18 Oct candle was written under tier C as well as tier B)."""
import sqlite3
import types

from jarvis.service import feed, trade_guard, universe_watch as U, watch_engine

DAY = 86400
MON = 1792281600 - 6 * DAY  # 2026-10-12, a Monday


def _bars(n, t_end, mark_t):
    out = []
    for k in range(n):
        t = t_end - (n - 1 - k) * DAY
        c = 777.0 if t == mark_t else 100.0 + (k % 5)
        out.append((t, c, c * 1.01, c * 0.99, c, 10.0))
    return out


def _run(monkeypatch, guard: bool):
    t_end = MON + 9 * DAY                                         # the Wednesday of the next week, closed
    signal_t = MON + 3 * DAY                                      # the Thursday before: XYZ was tier B that week
    btc, xyz = _bars(300, t_end, None), _bars(300, t_end, signal_t)
    qv = [(t, 2e6 if t < MON else 0.5e5) for t, *_ in xyz]        # B on the 30 days before MON, then C from the next Monday's window
    monkeypatch.setattr(feed, "daily_qv", lambda j, c: qv)
    monkeypatch.setattr(watch_engine, "DAILY", {"H07-UC": {"kind": "x", "id": "H07-UC", "tier": "C"}})
    monkeypatch.setattr(watch_engine, "_fires", lambda spec, S, B, i, r10: (S.c[i] == 777.0, None, "marked"))
    monkeypatch.setattr(trade_guard, "blocked", lambda j, w, c: None)
    db = sqlite3.connect(":memory:")
    j = types.SimpleNamespace(db=db, now=lambda: t_end + 2 * DAY)
    watch_engine._table(j)
    db.execute("CREATE TABLE IF NOT EXISTS engine_state (k TEXT PRIMARY KEY, v TEXT)")
    db.execute("INSERT OR REPLACE INTO engine_state VALUES (?, ?)", ("last_t:H07-UC:XYZ", str(MON - 20 * DAY)))   # an old cursor
    r = watch_engine.run(j, watches=["H07-UC"], coins=["XYZ"], daily_fn=lambda jj, c: btc if c == "BTC" else xyz, live_trades=False,
                         day_ok=U._in_tier_on(j, "C") if guard else None)
    return r, db.execute("SELECT watch, coin, signal_t FROM evidence_trades").fetchall(), signal_t


def test_without_the_guard_the_catch_up_writes_a_day_outside_the_tier(monkeypatch):
    r, rows, signal_t = _run(monkeypatch, guard=False)
    assert ("H07-UC", "XYZ", signal_t) in rows                    # the old behaviour: the bug #105 found


def test_the_guard_skips_days_when_the_coin_was_in_another_tier(monkeypatch):
    r, rows, _ = _run(monkeypatch, guard=True)
    assert rows == [] and r["opened"] == []


def test_btc_always_counts_as_tier_a():
    ok = U._in_tier_on(types.SimpleNamespace(db=None), "A")
    assert ok("BTC", MON) is True
