"""Build plan Phase 5 (2026-10-09): the first conversation. Step by step, saved as it goes (resume where you stopped), a typed
path for every step, words that change with experience, capital $1,000-$10,000, and it ends with a real watch running."""
import tempfile
from pathlib import Path

from jarvis.service import account, core, onboard, watches


def _g(clock):
    d = Path(tempfile.mkdtemp())
    g = core.Jarvis(d, owner_email="owner@x.com", password_hash=core.hash_password("correct horse 1"), secret="s" * 40,
                    now=lambda: clock["t"], db_file="jarvis_guest_kim_x_com.sqlite")
    g.prices = lambda: {"BTC": 100.0, "SOL": 50.0}
    return g


def test_first_conversation_end_to_end(monkeypatch):
    monkeypatch.setattr(onboard, "_setup_choice", lambda j: {"best": None, "kinds": watches.kinds()})
    px = {"BTC": 100.0}
    monkeypatch.setattr(onboard, "_live", lambda c: px.get(c))
    clock = {"t": 1_800_000_000}
    g = _g(clock)
    p = onboard.prompt(g)
    assert p["step"] == "permission" and p["input"]["options"][1][1] == "I'll type"      # a typed path from the first line
    onboard.answer(g, "permission", "type", tz="America/Toronto")
    onboard.answer(g, "can_do", "ok")
    p = onboard.prompt(g)
    assert p["step"] == "name" and "designed by Madhav" in p["say"] and p["input"]["type"] == "name"
    onboard.answer(g, "name", "Kim")
    p = onboard.prompt(g)
    assert p["say"].startswith("Nice to meet you, Kim.")
    onboard.answer(g, "experience", "never")
    onboard.answer(g, "crypto", "new")
    p = onboard.prompt(g)
    assert p["step"] == "risk" and p.get("note")                                        # beginners get the plain extra sentence
    onboard.answer(g, "risk", "balanced")
    onboard.answer(g, "coins", ["BTC", "SOL"])
    p = onboard.prompt(g)
    assert p["step"] == "capital" and p["input"]["options"][0] == 500 and p["input"]["options"][1] == 1000 and p["input"]["options"][-1] == 10000
    assert "keep the jargon out" in p["say"]
    onboard.answer(g, "capital", 6000)
    assert "the $6,000 you picked" in onboard.prompt(g)["log"][-1]["text"]
    # resume: a fresh look at the account continues at the same step
    assert onboard.step(g) == "interest"
    onboard.answer(g, "interest", "BTC")
    p = onboard.prompt(g)
    assert p["step"] == "setup" and "Nothing worth taking right now" in p["say"]
    onboard.answer(g, "setup", "any")
    onboard.answer(g, "mode", "ask")
    ws = watches.list_(g)
    assert len(ws) == 1 and ws[0]["coins"] == ["BTC"] and ws[0]["mode"] == "ask" and ws[0]["kind"] == watches.DEFAULT_KIND
    p = onboard.prompt(g)
    assert p["step"] == "acts" and "I'll ask before buying" in p["say"]
    onboard.answer(g, "acts", "seen")
    # the DEMO trade (Oct 11): ask mode shows a request to approve, then the exit; never in the book
    p = onboard.prompt(g)
    assert p["step"] == "demo" and "DEMO" in p["say"] and p["input"]["options"][0][0] == "approve" and p["demo"]["usd"] == 60.0
    onboard.answer(g, "demo", "approve")
    d = onboard.demo(g)
    assert d["status"] == "OPEN" and d["coin"] == "BTC" and d["qty"] == 0.6 and d["stop"] == 97.0 and d["mode"] == "ask"
    assert onboard.prompt(g)["step"] == "demo_exit"
    px["BTC"] = 101.0
    onboard.answer(g, "demo_exit", "exit")
    d = onboard.demo(g)
    assert d["status"] == "CLOSED" and d["pnl"] == round(0.6 * 101 * 0.998 - 60 * 1.002, 2)
    assert not account._has_fills(g.db)                                                 # not in the practice book
    p = onboard.prompt(g)
    assert p["step"] == "explore" and p["input"]["options"][-1][0] == "tour"
    r = onboard.answer(g, "explore", onboard.EXPLORE[0])
    assert r["explore"] == onboard.EXPLORE[0] and r["follow_ups"][-2:] == onboard.NEXT_CHIPS
    assert onboard.done(g)
    clock["t"] += 25 * 3600                                                               # gone after 24 hours at most
    assert onboard.demo(g) is None
    assert account.profile(g.db)["capital"] == 6000 and account.me(g)["onboard"] == "done"
    who = [x["who"] for x in onboard.prompt(g)["log"]]
    assert who[:2] == ["ananta", "you"]                                                  # question, then answer, all the way


def test_experienced_wording_and_bad_answers(monkeypatch):
    clock = {"t": 1_800_000_000}
    g = _g(clock)
    for s, v in (("permission", "voice"), ("can_do", "ok"), ("name", "Raj"), ("experience", "over_3y"), ("crypto", "trade"), ("risk", "bold"),
                 ("coins", ["BTC"])):
        onboard.answer(g, s, v)
    assert "keep it short" in onboard.prompt(g)["say"]
    try:
        onboard.answer(g, "capital", 12345)
    except ValueError:
        pass
    else:
        raise AssertionError("a bad capital was accepted")
    assert onboard.step(g) == "capital"                                                  # nothing moved
    onboard.start_over(g)
    assert onboard.step(g) == "permission"


def test_typing_ends_the_first_conversation_and_the_chips_after_it(monkeypatch):
    monkeypatch.setattr(onboard, "_live", lambda c: 100.0)
    clock = {"t": 1_800_000_000}
    g = _g(clock)
    onboard.answer(g, "permission", "type")
    r = onboard.answer(g, "can_do", onboard.TYPED)                                       # typed a question at any step
    assert r["ask"] and onboard.done(g)
    r = onboard.set_capital(g, 500)
    assert account.profile(g.db)["capital"] == 500 and r["follow_ups"] == ["Ask me first for every setup", "Fully automatic"]
    r = onboard.set_mode(g, "ask")                                                        # never saw the ask demo: it runs again
    assert r["demo_again"] and onboard.step(g) == "demo"
    onboard.answer(g, "demo", "approve")
    onboard.answer(g, "demo_exit", "exit")
    assert onboard.set_mode(g, "ask").get("demo_again") is None                          # seen once is enough
    assert "Fully automatic" in onboard.set_mode(g, "auto")["say"]
    onboard.clear_demo(g)                                                                 # the sign-out
    assert onboard.demo(g) is None


def test_old_last_step_moves_into_the_demo(monkeypatch):
    monkeypatch.setattr(onboard, "_live", lambda c: 100.0)
    g = _g({"t": 1_800_000_000})
    onboard._put(g.db, "onboard_step", "tour")
    assert onboard.step(g) == "demo"
    onboard.answer(g, "tour", "skip")                                                      # an old app's "Later" lands on the demo step
    assert onboard.step(g) == "explore"
