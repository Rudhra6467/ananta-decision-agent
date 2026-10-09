"""Jarvis abilities added 2026-10-03 (Madhav: more abilities, report back on requests, a voice that sounds like a person):
requests that report back, price history from stored candles, web lookup (fake HTTP), notes, new confirmation cards and what
they do, hearing checks (echo / filler / cut-off sentences), and the written -> spoken text."""
import json

import pytest

from jarvis.service import ask, requests_log, speech
from tests.test_ask_ananta import _jarvis


@pytest.fixture(autouse=True)
def _no_local(monkeypatch):
    monkeypatch.setenv("ANANTA_VOICE_LOCAL", "0")
    monkeypatch.setenv("ASK_LOCAL", "0")


def test_requests_report_back_once():
    j, ex = _jarvis()
    a = requests_log.add(j, "data", "Track the highest price of a trade while it is open.", "XRP")
    assert a["num"] == 1 and "number 1" in a["say"] and "tell you when it's fixed" in a["say"]
    assert requests_log.add(j, "data", "Track the highest price of a trade while it is open.")["duplicate"]   # same words: no copy
    b = requests_log.add(j, "bug", "The voice said Vamsi instead of Madhav.")
    assert b["num"] == 2
    assert requests_log.news(j) == [] and requests_log.notify(j, push=lambda t, x: 1 / 0) == []     # nothing changed yet
    requests_log.set_status(j, "#1", "DONE", "each trade page shows its highest and lowest price")
    pushed = []
    assert requests_log.notify(j, push=lambda t, x: pushed.append((t, x))) == [{"num": 1, "status": "DONE"}]
    assert pushed and pushed[0][0] == "Fixed: request 1" and "highest" in pushed[0][1]
    assert requests_log.notify(j, push=lambda t, x: pushed.append((t, x))) == []                  # once only
    news = requests_log.news(j)
    assert [n["num"] for n in news] == [1] and "fixed" in news[0]["say"]
    requests_log.mark_told(j, [1])
    assert requests_log.news(j) == []
    items = requests_log.feed_items(j, 0)
    assert any(i["title"].startswith("Request 1: fixed") for i in items) and any("request 2" in i["title"] for i in items)
    with pytest.raises(ValueError):
        requests_log.set_status(j, 99, "DONE")


def test_ananta_mentions_fixed_requests_once_and_flags_wrong_answers():
    j, ex = _jarvis()
    seen = []

    def fake(s, h, u, t, log):
        seen.append(u)
        return json.dumps({"kind": "answer", "answer": "Bitcoin is up a little."}), {"in": 1, "out": 1}

    A = ask.Ask(j, providers={"gemini": fake})
    r = A.ask("o@x.com", "how is bitcoin", mode="everyday")
    L = ask.Lookups(j, thread=r["thread"])
    out = L.call("log_request", {"kind": "bug", "text": "That answer was wrong about the stop.", "last_answer": True})
    assert out["num"] == 1 and "Bitcoin is up a little" in requests_log.get(j, 1)["text"]
    assert j.db.execute("SELECT rating FROM ask_messages WHERE id=?", (r["id"],)).fetchone()[0] == -1
    assert L.call("my_requests", {})["open"] == 1
    requests_log.set_status(j, 1, "DONE", "fixed the stop wording")
    A.ask("o@x.com", "and ethereum?", thread=r["thread"], mode="everyday")
    assert "REPAIR SHOP NEWS" in seen[-1] and "fixed the stop wording" in seen[-1]
    A.ask("o@x.com", "and solana?", thread=r["thread"], mode="everyday")
    assert "REPAIR SHOP NEWS" not in seen[-1]                                    # said once


def test_prices_from_stored_candles():
    j, ex = _jarvis()
    L = ask.Lookups(j)
    coin = next(iter(ex.st["engines"]))
    h = L.call("prices", {"coin": coin, "days": 3})
    assert "error" not in h, h
    assert h["low"] <= h["open"] <= h["high"] and h["low"] <= h["close"] <= h["high"] and h["high_when"]
    h1 = L.call("prices", {"coin": coin, "days": 1})
    assert "by_hour" in h1
    c = L.call("prices", {"days": 2})
    assert c["coins"] and c["coins"][0]["rank"] == 1 and c["leader"]
    assert all(c["coins"][i]["change_pct"] >= c["coins"][i + 1]["change_pct"] for i in range(len(c["coins"]) - 1))
    cov = L.call("prices", {"what": "coverage"})
    assert coin in cov["live_candles"] and "5m" in cov["live_candles"][coin]
    assert "error" in L.call("prices", {"coin": "NOTACOIN"})          # PEPE joined the 120-coin lake; an unknown coin still errors


def test_web_lookup_uses_google_then_claude(monkeypatch):
    from jarvis.service import weblook

    monkeypatch.setenv("GEMINI_API_KEY", "g")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "a")
    calls = []

    def post(url, h, body, timeout=40):
        calls.append(url)
        if "googleapis" in url:
            assert body["tools"] == [{"google_search": {}}]
            return {"candidates": [{"content": {"parts": [{"text": "Nvidia rose 2% today."}]},
                                    "groundingMetadata": {"groundingChunks": [{"web": {"uri": "https://example.com/a", "title": "Example"}}]}}]}
        raise AssertionError("Claude should not be called when Google answered")
    r = weblook.lookup("how is nvidia doing", post=post)
    assert r["answer"].startswith("Nvidia") and r["sources"][0]["url"] == "https://example.com/a" and r["cost_usd"] == 0.0

    def post2(url, h, body, timeout=40):
        if "googleapis" in url:
            raise RuntimeError("503 busy")
        assert body["tools"][0]["type"].startswith("web_search")
        return {"content": [{"type": "server_tool_use"}, {"type": "text", "text": "CPI is due Thursday.",
                                                            "citations": [{"url": "https://example.com/b", "title": "B"}]}],
                "usage": {"input_tokens": 1000, "output_tokens": 100, "server_tool_use": {"web_search_requests": 1}}}
    r2 = weblook.lookup("when is cpi", post=post2)
    assert r2["engine"] == "Claude web search" and r2["sources"][0]["url"] == "https://example.com/b" and r2["cost_usd"] > 0.01
    r3 = weblook.lookup("x", post=lambda *a, **k: (_ for _ in ()).throw(RuntimeError("down")))
    assert "error" in r3


def test_remember_saves_to_notes_and_journal(tmp_path, monkeypatch):
    j, ex = _jarvis()
    notes = tmp_path / "My notes"
    notes.mkdir()
    monkeypatch.setenv("ANANTA_NOTES_DIR", str(notes))
    L = ask.Lookups(j)
    r = L.call("remember", {"text": "I prefer stops under the zone, not inside it.", "about": "stops"})
    assert r["saved"] and "notes" in r["saved_to"]
    f = next(notes.glob("From Ananta*.md"))
    assert "stops under the zone" in f.read_text()
    assert j.db.execute("SELECT COUNT(*) FROM journal WHERE kind='note'").fetchone()[0] == 1
    g = ask.Lookups(j, guest=True)
    assert g.call("remember", {"text": "guest note"})["saved_to"] == "the decision journal"


def test_new_cards_need_confirmation_and_respect_guests():
    from jarvis.service.manual import Manual
    from jarvis.service.mandate import Mandate

    j, ex = _jarvis()
    px = j.prices()
    coin = next(iter(px))
    Mn = Manual(j.db, j.now)
    Mn.execute("o", {"side": "buy", "coin": coin, "usd": 100}, px)
    L = ask.Lookups(j, thread="t1")
    assert "error" in L.call("propose_levels", {"coin": coin, "stop": px[coin] * 1.1})            # a stop above the price
    r = L.call("propose_levels", {"coin": coin, "stop": round(px[coin] * 0.9, 6)})
    assert r["prepared"]["status"] == "PENDING" and "stop at" in r["prepared"]["summary"]
    assert Mn.state(px)["positions"][0]["stop"] is None                                        # nothing changes before the card
    Mn.set_levels("o", coin, round(px[coin] * 0.9, 6), None, px)
    assert Mn.state(px)["positions"][0]["stop"] == round(px[coin] * 0.9, 6)
    Mn.set_levels("o", coin, 0, None, px)                                                       # 0 removes it
    assert Mn.state(px)["positions"][0]["stop"] is None
    assert "error" in L.call("propose_levels", {"coin": "XRP" if coin != "XRP" else "BTC", "stop": 1})   # not in his book
    s = L.call("propose_switch", {"switch": "kill_switch", "on": True})
    assert s["prepared"]["kind"] == "switch" and "ON" in s["prepared"]["summary"]
    assert L.call("propose_switch", {"switch": "autopilot", "on": False})["prepared"]["summary"].startswith("Autopilot OFF")
    assert "error" in L.call("propose_setting", {"key": "daily_budget_usd", "value": "lots"})
    assert L.call("propose_setting", {"key": "daily_budget_usd", "value": "8"})["prepared"]["summary"].startswith("Set the daily Claude budget to $8.00")
    assert "error" in L.call("propose_alert_off", {"alert": "nope"})
    pend = Mandate(j.db, j.now).pending()
    assert {p["kind"] for p in pend} >= {"levels", "switch", "setting"}
    g = ask.Lookups(j, guest=True)
    for name, args in (("propose_switch", {"switch": "kill_switch", "on": True}), ("propose_portfolio_decision", {"decision": "approve"}),
                       ("propose_setting", {"key": "voice_enabled", "value": "0"}), ("news_check", {"coin": coin})):
        assert "error" in g.call(name, args), name


def test_hearing_check_and_voice_turn_skip_noise():
    assert ask.hearing_check("Hmm.", "Here's the trade.") == "filler"
    assert ask.hearing_check("Okay.", "Want the details?") == "ok"                 # an answer to my question
    assert ask.hearing_check("I want to know.", "") == "partial"
    assert ask.hearing_check("And what are...", "") == "partial"
    assert ask.hearing_check("How is Bitcoin doing today?", "") == "ok"
    assert ask.hearing_check("Show me the trades.", "") == "ok"
    assert ask.hearing_check("One sec.", "") == "echo"
    assert ask.hearing_check("Bitcoin is up about two percent today and nothing",
                             "Bitcoin is up about two percent today and nothing needs you right now.") == "echo"
    j, ex = _jarvis()
    asked = []
    A = ask.Ask(j, providers={"gemini": lambda s, h, u, t, log: asked.append(u) or (json.dumps({"kind": "answer", "answer": "Fine."}), {"in": 1, "out": 1})})
    heard = iter(["Hmm.", "I want to know", "how Bitcoin did this week?"])
    A.transcribe = lambda b64, mime="audio/wav": next(heard)
    assert A.voice_turn("o", "x", "audio/wav", None, "everyday", None)["ignored"] == "filler" and not asked
    p = A.voice_turn("o", "x", "audio/wav", None, "everyday", None)
    assert p["partial"] and not asked
    r = A.voice_turn("o", "x", "audio/wav", None, "everyday", None, prefix=p["heard"])
    assert r["heard"] == "I want to know how Bitcoin did this week?" and asked and "I want to know how Bitcoin" in asked[-1]


def test_spoken_text_reads_like_a_person():
    t = speech.for_ear("BTC is at $84,730.80, up +2.48% today (E4 setup on ETH is 4/5). T3 is fine; SD6 holds 1 trade.")
    assert "Bitcoin" in t and "$84,731" in t and "up 2.48 percent" in t and "momentum setup" in t and "Ethereum" in t
    assert "4 of 5" in t and "trend portfolio" in t and "Hunter's book" in t and "the Hunter's" not in t
    assert speech.for_ear("XRP bought at 1.5174031") == "X R P bought at 1.52"
    assert speech.for_ear("Trail starts at +2R.") == "Trail starts at twice the risk."
    assert speech.for_ear("🚀") == "🚀"                                            # never empty
    assert len(speech.norm_sentences(["One.", "", "BTC up 2%."])) == 2           # one spoken sentence per written one
