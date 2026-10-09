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
    assert p["step"] == "capital" and p["input"]["options"][0] == 1000 and p["input"]["options"][-1] == 10000
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
    onboard.answer(g, "tour", "later")
    assert onboard.done(g)
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
