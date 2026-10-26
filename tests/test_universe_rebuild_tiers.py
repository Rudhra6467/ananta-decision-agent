"""The Monday full rebuild judges each day on that week's tier, not today's (morning review, 26 Oct 2026: the registry re-tiers every
Monday and keeps no history, so all 15 'mismatches' of the Oct 26 rebuild were coins that had changed tier since their signal)."""
import sqlite3
import types

from jarvis.service import feed, registry, universe_watch as U, watch_engine

DAY = 86400
MON = 1792281600 - 6 * DAY  # 2026-10-12, a Monday (1792281600 = Sunday 2026-10-18 00:00 UTC)


def test_monday_of():
    assert U.monday_of(MON) == MON
    assert U.monday_of(MON + 3 * DAY + 5) == MON
    assert U.monday_of(MON + 6 * DAY) == MON          # Sunday belongs to the week that started on Monday
    assert U.monday_of(MON + 7 * DAY) == MON + 7 * DAY


def test_tier_at_follows_the_registry_rule_and_the_sunday_candle():
    rows = [(MON - (40 - k) * DAY, 25e6) for k in range(40)]                     # 40 days at $25M before MON: tier A
    rows += [(MON + k * DAY, 0.5e6) for k in range(7)]                           # the week of MON at $0.5M
    assert U.tier_at(rows, MON + 2 * DAY) == "A"                                 # judged on the 30 days before MON
    assert U.tier_at(rows, MON + 5 * DAY) == "A"                                 # Saturday candle: judged on Sunday, same week
    # Sunday's candle is judged just after it closes, on Monday, after the re-tier: the median of the 30 days before the next
    # Monday is still $25M (23 of 30 days), so A; a coin with under 30 days of history is C
    assert U.tier_at(rows, MON + 6 * DAY) == "A"
    low = [(MON - (40 - k) * DAY, 25e6) for k in range(10)] + [(MON - (30 - k) * DAY, 2e6) for k in range(30)]
    assert U.tier_at(low, MON + 1 * DAY) == "B"
    assert U.tier_at(low[-20:], MON + 1 * DAY) == "C"
    assert U.tier_at([], MON) == "C"


def _bars(n, t_end, mark_t=None):
    out = []
    for k in range(n):
        t = t_end - (n - 1 - k) * DAY
        c = 777.0 if t == mark_t else 100.0 + (k % 5)
        out.append((t, c, c * 1.01, c * 0.99, c, 10.0))
    return out


def _run(monkeypatch, ledger_watch):
    now = MON + 14 * DAY + 3600                                   # two weeks later
    signal_t = MON + 2 * DAY                                      # a Wednesday, when XYZ was tier A
    btc, xyz = _bars(300, now // DAY * DAY - DAY), _bars(300, now // DAY * DAY - DAY, mark_t=signal_t)
    qv = [(t, 25e6 if t < MON + 7 * DAY else 2e6) for t, *_ in xyz]  # A until the next Monday's window, B from the week after
    monkeypatch.setattr(U, "_daily", lambda j, c: btc if c == "BTC" else xyz)
    monkeypatch.setattr(feed, "daily_qv", lambda j, c: qv)
    monkeypatch.setattr(registry, "members", lambda j, tier=None, listed=True: ["XYZ"])
    monkeypatch.setattr(registry, "tier_of", lambda j, c: "B")    # today's tier: B
    specs = {U.wid(r, t): {"kind": "x", "id": U.wid(r, t)} for r in U.RULES_ALL for t in U.TIERS}
    monkeypatch.setattr(watch_engine, "DAILY", specs)
    monkeypatch.setattr(watch_engine, "_fires", lambda spec, S, B, i, r10: (S.c[i] == 777.0 and spec["id"].startswith("H07-"), None, None))
    db = sqlite3.connect(":memory:")
    db.execute("CREATE TABLE evidence_trades (id TEXT, watch TEXT, coin TEXT, source TEXT, signal_t INTEGER, entry_t INTEGER, exit_t INTEGER)")
    db.execute("INSERT INTO evidence_trades VALUES ('a', ?, 'XYZ', 'daily', ?, ?, ?)", (ledger_watch, signal_t, signal_t + DAY, signal_t + 5 * DAY))
    j = types.SimpleNamespace(db=db, now=lambda: now)
    return U.rebuild(j, 400)


def test_rebuild_judges_a_day_on_its_own_weeks_tier(monkeypatch):
    r = _run(monkeypatch, "H07-UA")                               # fired as tier A that week; tier B today
    assert r["match"] is True and r["only_in_ledger"] == [] and r["only_in_rebuild"] == []


def test_rebuild_still_fails_when_the_ledger_tier_is_wrong(monkeypatch):
    r = _run(monkeypatch, "H07-UB")                               # the ledger says B, but XYZ was A that week: a real mismatch
    assert r["match"] is False
    assert ["H07-UB", "XYZ", MON + 2 * DAY] in r["only_in_ledger"]
