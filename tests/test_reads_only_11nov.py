"""11 Nov 2026, the keen audit's register (R-182; Madhav, 10 Nov 21:22: "Why can't we fix them based on historical data and performance
of Ananta instead of waiting?"): reading the crypto plan writes nothing. discipline.plan_line saved the night's plan on every call, so each
page view and question re-saved it; on 5 of the 18 nights since the plan began, the saved plan (engine_state plan:<day>) no longer matched
the plan the officer's note was written from. A page view could also use up a wait_for arrival before the note reported it. Now only the
officer's note saves the plan, with the wait_for marks it reported."""
import json

from jarvis.service import discipline, exposure, feed, ndax_book, officer
from tests.test_universe_live import J

NOW = 1794355560.0                     # 11 Nov 2026, 00:06 UTC: minutes after the daily close
BRAIN = ("CREATE TABLE IF NOT EXISTS brain_decisions (id TEXT PRIMARY KEY, t INTEGER, coin TEXT, triggers TEXT, action TEXT, confidence REAL, "
         "size_pct REAL, price REAL, plan TEXT, thesis TEXT, knowledge TEXT, model TEXT, cost_usd REAL, trade_id TEXT, random_id TEXT, "
         "after_1d_pct REAL, after_5d_pct REAL, note TEXT)")


def _j(tmp_path, monkeypatch):
    j = J(tmp_path, now=NOW)
    ndax_book._table(j)
    j.db.execute(BRAIN)
    plan = {"wait_for": {"price_above": 3000, "words": "a close over 3,000"}}
    j.db.execute("INSERT INTO brain_decisions (id, t, coin, action, plan, thesis) VALUES (?,?,?,?,?,?)",
                 ("d1", int(NOW) - 20 * 3600, "ETH", "PASS", json.dumps(plan), "wait for strength"))
    j.db.commit()
    monkeypatch.setattr(feed, "daily", lambda j, coin, *a, **k: [])
    monkeypatch.setattr(feed, "last_closes", lambda j: {"ETH": 3100.0})
    monkeypatch.setattr(ndax_book, "status", lambda j: {"value_cad": 439.49, "cash_cad": 439.49, "return_pct": -12.1, "positions": {}, "closed": [],
                                                         "brakes": {}, "last_step": "2026-11-11 00:05", "started": "2026-10-11"})
    monkeypatch.setattr(exposure, "state", lambda j: {"dial_words": "CLOSED: no new buys", "why": [], "as_of_day": "2026-11-10"})
    return j


def _rows(j, like: str) -> list:
    try:
        return j.db.execute("SELECT k, v FROM engine_state WHERE k LIKE ? ORDER BY k", (like,)).fetchall()
    except Exception:  # noqa: BLE001
        return []


def test_reading_the_plan_writes_nothing(tmp_path, monkeypatch):
    j = _j(tmp_path, monkeypatch)
    first = discipline.plan_line(j)
    assert [a["decision"] for a in first["arrived"]] == ["d1"] and first["arrived"][0]["hit"] == ["closed at 3,100, above 3,000"]
    assert _rows(j, "plan:%") == [] and _rows(j, "wait:%") == [], "a page view or a question saves nothing"
    assert [a["decision"] for a in discipline.plan_line(j)["arrived"]] == ["d1"], "a second read still sees the arrival: reading no longer uses it up"
    assert discipline.latest_plan(j) is None


def test_the_note_saves_the_plan_it_was_written_from(tmp_path, monkeypatch):
    j = _j(tmp_path, monkeypatch)
    discipline.plan_line(j)                                                     # a page view before the note: it changes nothing
    users = []

    def call(rules, user):
        users.append(user)
        return "The account sat in cash. Ethereum closed over the level a pass waited for.", {}

    out = officer.write(j, {}, call=call)
    assert out["ok"] and out["facts"]["plan_saved"] is True
    assert '"_plan"' not in users[0] and "_plan" not in out["facts"], "the whole plan is saved beside the note, not sent in the facts"
    saved = discipline.latest_plan(j)
    note_facts = json.loads(j.db.execute("SELECT facts FROM officer_notes WHERE day='2026-11-11'").fetchone()[0])
    assert saved["day"] == "2026-11-11" and saved["line"] == note_facts["plan_line"] and saved["saved_t"] == int(NOW)
    assert [a["decision"] for a in note_facts["wait_for_arrived"]] == ["d1"]
    assert json.loads(_rows(j, "wait:%")[0][1]) == {"t": int(NOW), "hit": ["closed at 3,100, above 3,000"]}
    assert discipline.plan_line(j)["arrived"] == [], "once the note reported it, the arrival is not reported again"
    # a page view after the note leaves the saved plan alone, and a second run of the note is "already" and saves nothing
    j._now = NOW + 7200
    monkeypatch.setattr(feed, "last_closes", lambda j: {"ETH": 2900.0})
    discipline.plan_line(j)
    assert officer.write(j, {}, call=call).get("already") is True
    assert discipline.latest_plan(j) == saved and len(users) == 1


def test_nothing_else_saves_the_plan():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    src = (root / "jarvis" / "service" / "discipline.py").read_text()
    body = src.split("def plan_line(", 1)[1].split("\ndef save_plan(", 1)[0]
    assert "INSERT" not in body and "commit(" not in body, "plan_line only reads"
    wait = src.split("def wait_for_arrived(", 1)[1].split("\ndef ", 1)[0]
    assert "INSERT" not in wait and "commit(" not in wait, "wait_for_arrived only reads"
    files = [*(root / "jarvis").glob("*.py"), *(root / "jarvis" / "service").glob("*.py"), *(root / "jarvis" / "india").glob("*.py"),
             *(root / "src").rglob("*.py"), *(root / "scripts").glob("*.py")]
    callers = sorted(p.name for p in files if "save_plan(" in p.read_text() and p.name != "discipline.py")
    assert callers == ["officer.py"], callers
