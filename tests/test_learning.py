"""The learning loop (plan Batch 4b): situation cards, the weekly review, credit, the brain rebuild, worked examples, peers."""
import json
import time

from tests.test_universe_live import J

DAY = 86400


def _bars(n=120, start=None):
    t0 = (start or int(time.time()) - n * DAY)
    t0 -= t0 % DAY
    return [(t0 + k * DAY, 100 + k, 101 + k, 99 + k, 100 + k, 1.0) for k in range(n)]


def _setup(tmp_path, monkeypatch):
    from jarvis.service import brain, feed, watch_engine as W

    monkeypatch.setattr(feed, "daily", lambda j, c: _bars())
    j = J(tmp_path)
    brain._table(j)
    W._table(j)
    now = int(time.time())
    row = {c: None for c in W.COLS}
    row.update(id="T1", watch="JARVIS", coin="ETH", source="brain", signal_t=now - 3 * DAY, signal_day=time.strftime("%Y-%m-%d", time.gmtime(now - 3 * DAY)),
               entry_t=now - 3 * DAY, entry=150.0, stop=140.0, exit_t=now - DAY, exit=210.0, status="CLOSED", net_usd=-4.0, exit_why="stop (live price)",
               detail="{}")
    W._insert(j, row)
    twin = dict(row, id="R1", watch="JARVIS_RANDOM", coin="SOL", net_usd=1.0)
    W._insert(j, twin)
    for i, (act, k, tid, rid, a5) in enumerate([("TAKE", ["ZONES", "REGIME"], "T1", "R1", None), ("PASS", ["ZONES"], None, None, 7.5),
                                                  ("PASS", ["REGIME"], None, None, -2.0)]):
        j.db.execute("INSERT INTO brain_decisions (id, t, coin, action, price, plan, thesis, knowledge, trade_id, random_id, after_5d_pct) "
                     "VALUES (?,?,?,?,?,?,?,?,?,?,?)", (f"D{i}", now - 3 * DAY + i, "ETH", act, 150.0, "{}", "test", json.dumps(k), tid, rid, a5))
    j.db.commit()
    return j


def test_card_four_views(tmp_path, monkeypatch):
    from jarvis.service import learning as L

    j = _setup(tmp_path, monkeypatch)
    d = L._decisions(j, 0)
    c = L.card(j, d[0])
    assert set(c) >= {"what_we_did", "what_if", "what_else", "what_others_did", "lesson"}
    assert c["what_we_did"]["net_usd"] == -4.0
    assert c["what_others_did"]["random_twin"]["coin"] == "SOL"
    assert c["lesson"] == "random beat the pick"
    assert L.card(j, d[1])["lesson"].startswith("missed winner")


def test_weekly_review_every_situation_ends(tmp_path, monkeypatch):
    from jarvis.service import learning as L

    j = _setup(tmp_path, monkeypatch)
    r = L.weekly_review(j, write=False)
    assert r["decisions"] == 3 and r["takes"] == 1
    assert r["situations"] and all(c["ends_in"].startswith(("ticket", "no change, because")) for c in r["situations"])
    assert r["tickets"] == []                                      # one case is not a pattern
    md = L._markdown(r)
    assert "What we did" in md and "What others did" in md


def test_credit_per_knowledge(tmp_path, monkeypatch):
    from jarvis.service import learning as L

    c = L.credit(_setup(tmp_path, monkeypatch))
    assert c["ZONES"]["buys"] == 1 and c["ZONES"]["passes"] == 1
    assert c["ZONES"]["avg_buy_usd"] == -4.0
    assert c["ZONES"]["avg_move_after_pass_pct"] == 7.5
    assert c["REGIME"]["avg_move_after_pass_pct"] == -2.0


def test_rebuild_flags_impossible_exit(tmp_path, monkeypatch):
    from jarvis.service import learning as L

    j = _setup(tmp_path, monkeypatch)
    r = L.rebuild_brain(j)
    assert r["checked"] == 2 and r["mismatches"] == 2              # exit 210 lies outside the exit day's candle
    assert j.db.execute("SELECT COUNT(*) FROM rebuild_log WHERE source='brain'").fetchone()[0] == 1


def test_worked_examples_are_his_cases():
    from jarvis.service import learning as L

    ex = L.worked_examples(2)
    assert ex and all(e["his_reasons"] for e in ex)
