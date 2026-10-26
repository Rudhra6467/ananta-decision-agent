"""Flag it, choose the fix, get told (jarvis/service/fixflow.py, scripts/repair_worker.py; Madhav, Oct 23).

What must hold: a flag files a repair-board request at once and offers fixes; code, not the AI, decides the lane, so a fix near trading is
never built by the worker; choosing moves the request on; the worker's own check refuses any file outside the safe paths or pinned by
the crypto lock; a deploy marks the request DONE so the phone says "Fixed"."""
import importlib.util
import sqlite3
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _j(tmp_path, now=2_000_000_000):
    from jarvis.service import core

    return types.SimpleNamespace(dir=tmp_path, db=core.SafeDB(sqlite3.connect(":memory:", check_same_thread=False)), now=lambda: now)


def _ai(reply: str, usage=(1000, 200)):
    def post(url, headers, body, timeout=40):
        assert body["model"].startswith("claude-") and "flagged a problem" in body["messages"][0]["content"]
        return {"content": [{"type": "text", "text": reply}], "usage": {"input_tokens": usage[0], "output_tokens": usage[1]}}
    return post


def _worker():
    spec = importlib.util.spec_from_file_location("repair_worker", ROOT / "scripts" / "repair_worker.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_a_flag_files_the_request_now_and_offers_fixes_with_lanes_decided_by_code(tmp_path, monkeypatch):
    from jarvis.service import fixflow, requests_log

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    j = _j(tmp_path)
    reply = ('{"diagnosis": "The card shows dollars on the India screen.", "options": ['
             '{"title": "Show rupees on the card", "what": "The book card formats the amount in rupees."},'
             '{"title": "Raise the stop on open positions", "what": "Move each stop closer."},'
             '{"title": "Needs your decision: change the book", "what": "Only a book change would fix it."}]}')
    r = fixflow.flag(j, "The book card shows $ instead of rupees", "india", "India · Home", "/(tabs)/today", post=_ai(reply))
    req = requests_log.get(j, r["num"])
    assert req["status"] == "OPEN" and req["text"].startswith("[Indian market · India · Home] ")      # on the board at once, market named
    lanes = [o["lane"] for o in r["options"]]
    assert lanes == ["SAFE", "DECISION", "DECISION"]          # "stop" is trading words; the AI's own "Needs your decision" also counts
    assert fixflow.get(j, r["num"])["state"] == "triaged" and fixflow.get(j, r["num"])["cost_usd"] > 0


def test_without_the_ai_the_plain_choices_still_work_and_a_trading_flag_is_never_safe(tmp_path, monkeypatch):
    from jarvis.service import fixflow

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    j = _j(tmp_path)
    r = fixflow.flag(j, "The exit rule sells too early", "crypto", "Home")
    assert [o["title"] for o in r["options"]] == ["Fix it as I described", "Investigate and tell me first"]
    assert {o["lane"] for o in r["options"]} == {"DECISION"}                                        # "exit rule" is near trading
    r2 = fixflow.flag(j, "The voice says 'em-dash' out loud", "crypto", "Ask")
    assert r2["options"][0]["lane"] == "SAFE"


def test_choosing_queues_a_safe_fix_and_plans_a_decision_one(tmp_path, monkeypatch):
    from jarvis.service import fixflow, requests_log

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    j = _j(tmp_path)
    safe = fixflow.flag(j, "The Market card text is cut off on the phone", "crypto", "Market")
    c = fixflow.choose(j, safe["num"], 0)
    assert c["state"] == "queued" and c["lane"] == "SAFE" and requests_log.get(j, safe["num"])["status"] == "PLANNED"
    with pytest.raises(ValueError):
        fixflow.choose(j, safe["num"], 1)                                                            # already queued
    dec = fixflow.flag(j, "Show the size of each trade bigger", "crypto", "Home")
    assert fixflow.choose(j, dec["num"], 0)["state"] == "plan"                                       # "size" -> plan only
    words = fixflow.flag(j, "The chart legend overlaps", "crypto", "Coin")
    assert fixflow.choose(j, words["num"], 0, words="and also change the stop")["state"] == "plan"   # his own words count too
    assert [f["num"] for f in fixflow.pending(j)] == [safe["num"], dec["num"], words["num"]]


def test_the_same_flag_twice_is_one_request(tmp_path, monkeypatch):
    from jarvis.service import fixflow, requests_log

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    j = _j(tmp_path)
    a = fixflow.flag(j, "Labels overlap on the Lab screen", "crypto", "Lab")
    b = fixflow.flag(j, "Labels overlap on the Lab screen", "crypto", "Lab")
    assert a["num"] == b["num"] and b.get("duplicate") and len(requests_log.list_(j)) == 1


def test_a_deploy_marks_the_request_fixed_for_the_phone_and_a_failure_goes_back_to_madhav(tmp_path, monkeypatch):
    from jarvis.service import fixflow, requests_log

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    j = _j(tmp_path)
    a = fixflow.flag(j, "Typo on the Today screen", "crypto", "Today")
    fixflow.choose(j, a["num"], 0)
    fixflow.report(j, a["num"], "working", "started")
    fixflow.report(j, a["num"], "deployed", "Fixed the typo.", commit="abcdef1234", cost=0.42)
    r = requests_log.get(j, a["num"])
    assert r["status"] == "DONE" and "abcdef1" in r["note"] and fixflow.get(j, a["num"])["cost_usd"] == pytest.approx(0.42)
    pushed = []
    assert any(x["num"] == a["num"] and x["status"] == "DONE" for x in requests_log.notify(j, push=lambda t, b: pushed.append(t)))
    assert pushed and pushed[-1] == f"Fixed: request {a['num']}"
    b = fixflow.flag(j, "Wrong colour on the badge", "india", "Markets")
    fixflow.choose(j, b["num"], 0)
    fixflow.report(j, b["num"], "failed", "tests failed")
    assert requests_log.get(j, b["num"])["status"] == "PLANNED" and fixflow.choose(j, b["num"], 1)["state"] in ("queued", "plan")


def test_the_worker_refuses_any_file_outside_the_safe_paths_or_pinned_by_the_lock():
    w = _worker()
    pinned = w.pinned_files()
    assert "src/research/book500.py" in pinned and "jarvis/service/exposure.py" in pinned and "docs/knowledge/acceptance_gate.json" in pinned
    assert w.allowed(["jarvis/app/app/market.tsx", "tests/test_app_theme.py"], pinned) == (True, [])
    for bad in ("jarvis/service/brain.py", "jarvis/service/app.py", "src/intelligence/ndax_costs.py", "jarvis/india/service.py",
                "jarvis/service/evidence_live.py", ".env", "jarvis/app/.env", "scripts/repair_worker.py", "docs/knowledge/crypto_lock.json",
                "jarvis/app/src/api.ts"):
        ok, refused = w.allowed(["jarvis/app/app/market.tsx", bad], pinned)
        assert not ok and refused == [bad], bad
    assert w.allowed([], pinned)[0] is False                                                        # nothing changed is not a fix
    for safe in w.SAFE_PATHS:                                                                        # no safe path is pinned
        assert not any(p.startswith(safe) or p == safe for p in pinned if not p.startswith("tests/")), safe


def test_a_research_note_has_no_menu_and_the_same_topic_is_added_not_refiled(tmp_path):
    """26 Oct: research requests were given app-fix menus and refiled (flags 36/37 rupee, 39/40 FII). A note is saved whole, with no options
    for the worker to build, and the same topic within 45 minutes goes into the first note."""
    from jarvis.service import fixflow, requests_log

    j = _j(tmp_path)
    a = fixflow.note(j, "FII flows and their influence on Nifty", "QUESTION\nDo sharp FII selling days lead Nifty?", market="india")
    row = fixflow.get(j, a["num"])
    assert row["state"] == "noted" and row["options"]["options"] == [] and "QUESTION" in row["options"]["note"]
    b = fixflow.note(j, "FII influence research on stock prices", "More: use the NSDL FPI history.", market="india")
    assert b["num"] == a["num"] and b["updated"] and "NSDL" in fixflow.get(j, a["num"])["options"]["note"]
    c = fixflow.note(j, "Rupee against dollar and Indian stocks", "QUESTION\nDoes a weak rupee hurt Nifty?", market="india")
    assert c["num"] != a["num"] and not c["updated"]
    assert fixflow.pending(j) == []                                  # nothing for the repair worker to build
    assert requests_log.get(j, a["num"])["status"] == "OPEN"
