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


def test_close_counterfactuals_scores_and_labels(tmp_path, monkeypatch):
    import sqlite3

    from jarvis.service import learning as L

    j = _setup(tmp_path, monkeypatch)
    now = int(time.time())
    t0 = now - 2 * DAY
    t0 -= t0 % 3600
    bars = sqlite3.connect(tmp_path / "explorer_bars.sqlite")
    bars.execute("CREATE TABLE bars (coin TEXT, tf TEXT, t INTEGER, o REAL, h REAL, l REAL, c REAL, v REAL)")
    for k in range(8):                                             # BTC falls 1% an hour: a refusal was CORRECT
        px = 100 * (1 - 0.01 * k)
        bars.execute("INSERT INTO bars VALUES ('BTC','1h',?,?,?,?,?,1)", (t0 + k * 3600, px, px * 1.001, px * 0.985, px * 0.99))
    bars.commit()
    bars.close()
    import datetime as dt
    case = {"id": "counterfactual.v1", "status": "OPEN", "issued": "NO_TRADE", "asset": "BTC-USD-SPOT", "horizon_hours": 4.0,
            "issued_at": dt.datetime.fromtimestamp(t0, dt.timezone.utc).isoformat()}
    con = sqlite3.connect(tmp_path / "agent_decisions.sqlite")
    con.execute("CREATE TABLE decisions (id TEXT PRIMARY KEY, payload_json TEXT)")
    con.execute("INSERT INTO decisions VALUES ('d1', ?)", (json.dumps({"counterfactual": case}, indent=1),))
    con.commit()
    con.close()
    r = L.close_counterfactuals(j)
    assert r["closed"] == 1 and r["labels"] == {"CORRECT_REFUSE": 1}
    con = sqlite3.connect(tmp_path / "agent_decisions.sqlite")
    cf = json.loads(con.execute("SELECT payload_json FROM decisions").fetchone()[0])["counterfactual"]
    assert cf["status"] == "CLOSED" and cf["fwd_return_pct"] < -2 and cf["mae_pct"] < cf["fwd_return_pct"] <= cf["mfe_pct"]
    assert L.close_counterfactuals(j)["closed"] == 0               # nothing left open


def test_worked_examples_are_his_cases():
    from jarvis.service import learning as L

    ex = L.worked_examples(2)
    assert ex and all(e["his_reasons"] for e in ex)


def test_the_weekly_due_lines_list_every_scheduled_study_and_the_due_list(tmp_path, monkeypatch):
    import calendar
    from pathlib import Path

    from jarvis.service import core, strategy_status
    from jarvis.service import learning as L

    (tmp_path / "docs" / "knowledge").mkdir(parents=True)
    (tmp_path / "docs" / "repair_shop").mkdir(parents=True)
    studies = [{"id": "R2", "title": "Other traders", "schedule": {"every": "quarter", "next_due": "2027-01-01"}},
               {"id": "X9", "title": "A second study", "schedule": {"every": "month", "next_due": "2026-10-01"}}, {"id": "NOSCHED", "title": "never"}]
    (tmp_path / "docs" / "repair_shop" / "ledger.json").write_text(json.dumps({"studies": studies}))
    items = [{"id": "A-OVERDUE", "what": "check the first Sunday review", "how": "open docs/repair_shop/weekly", "due": "2026-10-10"},
             {"id": "OD-X", "what": "a decision for Madhav", "how": "he chooses a or b", "due": "2026-10-31", "owner": "Madhav", "owner_decision": True},
             {"id": "E-1", "what": "Q1 answer", "how": "the ledger counts", "cadence": "evidence", "goal": "10 events"},
             {"id": "PW-1", "what": "a re-test", "how": "write the pre-registration first", "after_window": True}]
    (tmp_path / "docs" / "knowledge" / "due_list.json").write_text(json.dumps({"version": 1, "items": items}))
    monkeypatch.setattr(L, "ROOT", tmp_path)
    monkeypatch.setattr(core, "docs_dir", lambda base: Path(base) / "docs")
    monkeypatch.setattr(strategy_status, "load", lambda *a, **k: {"evidence_window": {"start": "2026-10-15", "days": 60}})
    j = J(tmp_path, now=calendar.timegm(time.strptime("2026-10-20", "%Y-%m-%d")) + 3600)
    lines = L._due(j)
    text = "\n".join(lines)
    assert "Study R2 (Other traders), every quarter: next due 2027-01-01" in text and "DUE NOW" in text.split("Study X9")[1].split("\n")[0]
    assert "NOSCHED" not in text and "R2" in lines[0] and "DUE NOW" not in lines[0]
    assert any(x.startswith("OVERDUE A-OVERDUE (was due 2026-10-10)") for x in lines)
    assert "decisions waiting for Madhav: OD-X" in lines and "waiting for evidence: E-1" in lines
    assert "after the window (2026-12-14): 1 items" in text and "THE WINDOW IS OVER" not in text
    assert L._due(None) == [x for x in lines if x.startswith("Study ")]                 # without a service handle only the ledger is read
    assert "Study X9" in L._markdown({"from": "a", "to": "b", "decisions": 0, "takes": 0, "lessons": {}, "situations": [], "tickets": [], "credit": {},
                                       "changes": [], "peers": {}}, j)
