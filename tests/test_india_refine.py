"""25 Oct India voice refinement, from Madhav's own chats of 23-25 Oct: one source per answer, no codes read aloud, picks and flags that
carry their context, code answers for the common questions, and India's own speech-to-text words."""
import json

import pytest

from jarvis.india import ask as A
from jarvis.india import voice as V


def test_family_codes_and_field_names_become_words():
    s = A.plain_codes("10 PULL, 10 REV, 5 CTL and 0 BRK. The index line (SP1) lost. REV (oversold reversal) picks. realised_inr and open_unrealised_inr.")
    assert "PULL" not in s and "REV" not in s and "CTL" not in s and "SP1" not in s and "_" not in s
    assert "10 pullbacks" in s and "5 random controls" in s and "The index line lost" in s and "oversold reversal picks" in s
    assert A.plain_codes("see https://x.com/a_b and file a_b.json") == "see https://x.com/a_b and file a_b.json"


def test_signoff_only_when_the_question_is_about_trading():
    assert A.finish({"answer": "Sir, the call is up. Paper only; nothing is placed from chat."}, "what is the call", True)["answer"] == "Sir, the call is up."
    assert A.finish({"answer": "Sir, no. Paper only, not advice."}, "should I buy it now", True)["answer"].endswith("not advice.")
    assert A.finish({"answer": "Nothing is sold until you say so. Paper only."}, "analyze", False)["answer"].endswith("Paper only.")   # code answers keep theirs


def test_almost_json_reply_is_not_shown_raw():
    d = A._parse('{"kind":"answer","stage":"learning","answer":"Sir, the reviewer called it "fair" and accurate.","breakdown":["a","b"],"follow_ups":["x?"]}')
    assert d["answer"] == 'Sir, the reviewer called it "fair" and accurate.' and d["breakdown"] == ["a", "b"] and "{" not in d["answer"]


def test_picks_from_his_words():
    opts = [{"title": "Add tap-to-pick buttons on choices"}, {"title": "Treat 'use one' as picking first"}, {"title": "Ask which problem when the note is vague"}]
    assert A._picks("Use one and fix it.", opts) == [1]
    long = ("So here in the Ask Ananta screen, when I'm talking to you, your message is going up and I can see a screen like, you know, "
            "message flags for you, which is unnecessary.")
    assert A._picks(long, opts) == []                       # 25 Oct: this complaint was taken as fix 3
    assert A._picks("maybe two will do good", opts) == [2] and A._picks("Second bot's answer is basically the same.", opts) == []


def test_old_fix_list_expires(tmp_path, monkeypatch):
    monkeypatch.setattr(A, "ASK_DIR", tmp_path)
    A._set_pending("t1", {"num": 101, "at": 1, "options": [{"title": "x"}]})
    assert A._pending("t1") is None
    A._set_pending("t1", {"num": 101, "options": [{"title": "x"}]})        # pending rows written before 25 Oct have no time: still honoured
    assert A._pending("t1")["num"] == 101


def test_bare_flag_it_files_the_problem_before_it(tmp_path, monkeypatch):
    monkeypatch.setattr(A, "ASK_DIR", tmp_path)
    A._append("t2", {"role": "user", "text": "I still see the flags for you box in the chat", "t": 1})
    A._append("t2", {"role": "assistant", "answer": 'Sorry sir. Say "flag it: remove the flags for you panel from the Ask Ananta chat" to file it.', "t": 2})
    sent = {}

    def post(url, body):
        sent.update(body)
        return {"num": 104, "label": "flag 23", "options": []}
    r = A.fix_flow("Yeah, flag it.", "t2", "tok", {}, post=post, get=lambda u: {})
    assert sent["text"] == "remove the flags for you panel from the Ask Ananta chat" and "flag 23" in r["answer"]
    sent.clear()
    A.fix_flow("Flag it please.", "t3", "tok", {}, post=post, get=lambda u: {})
    assert sent["text"] == "Flag it please."                   # nothing before it: his words as they are


def test_cut_off_turns_get_a_listening_reply():
    assert A.fragment_flow("Hey Ananta in here. Ah, so...")["answer"] == "I'm listening, sir. Go on."
    assert "question one" in A.fragment_flow("Question one.")["answer"]
    assert A.fragment_flow("Hey Ananta")["answer"].startswith("Yes, sir")
    assert A.fragment_flow("What is the Nifty doing?") is None and A.fragment_flow("Why did it fall...?") is None


def test_why_did_a_stock_move_reads_the_nightly_files(tmp_path, monkeypatch):
    monkeypatch.setattr(A, "DATA", tmp_path)
    (tmp_path / "paper" / "reconstruction" / "netnotes").mkdir(parents=True)
    (tmp_path / "manifests").mkdir()
    (tmp_path / "paper" / "reconstruction" / "netnotes" / "2026-10-22.jsonl").write_text(json.dumps({"symbol": "KEI", "note": "it fell after its results missed estimates", "grade": "B"}) + "\n")
    (tmp_path / "manifests" / "missed_2026-10-22.json").write_text(json.dumps({"movers": [{"symbol": "KEI", "side": "down", "cc": -0.085, "situation": "gapped down", "status": "missed", "class": "b"}]}))
    monkeypatch.setattr(A.views, "readmodel", lambda: {"decisions_today": {"chosen": [{"symbol": "KEI", "campaign": "REV"}]}})
    a1 = A.mover_flow("Why did KEI fall last night?")["answer"]
    a2 = A.mover_flow("why did kei fall")["answer"]
    assert a1 == a2 and "fell 8.5% on 22 Oct" in a1 and "Public reports say: it fell after its results missed estimates (two news outlets agree)" in a1
    assert "no rule of Ananta's was watching it" in a1 and "oversold reversals" in a1
    assert A.mover_flow("Why did KEI fall, and what drafts are waiting?") is None        # two questions: the model answers both
    assert A.mover_flow("Why did the Nifty fall?") is None


def test_an_old_daily_call_is_not_called_the_next_one():
    rm = {"data_through": "2026-10-23", "call": {"call": "BULLISH", "data_through": "2026-10-22", "hits": 0, "scored": 3, "null_hits": 2}}
    s = A.call_state(rm)
    assert not s["is_for_next_session"] and s["words"].startswith("No daily call has been made yet for the next session") and "22 Oct" in s["words"]
    rm["call"]["data_through"] = "2026-10-23"
    assert A.call_state(rm)["words"].startswith("The daily call for the next session is bullish")
    from jarvis.india import views
    b = views.plain_brief({"data_through": "2026-10-23", "call": {"call": "BULLISH", "data_through": "2026-10-22", "hits": 0, "scored": 3, "null_hits": 2}})
    assert any(x.startswith("No call yet for the next session") for x in b)


def test_decision_and_book_answers_match_the_screens(monkeypatch):
    rm = {"data_through": "2026-10-23", "next_session": "2026-10-26", "market": {"trend_state": "below_both"},
          "call": {"call": "BULLISH", "data_through": "2026-10-23", "hits": 0, "scored": 3, "null_hits": 2}, "sp1": {"status": "lost"},
          "decisions_today": {"chosen": [{"symbol": "AAA", "campaign": "PULL"}, {"symbol": "BBB", "campaign": "REV"}, {"symbol": "CCC", "campaign": "CTL"}],
                              "inputs": {"marked": True, "stale": ["Nifty 50: stale: last row 2026-10-22"]}}}
    monkeypatch.setattr(A.views, "readmodel", lambda: rm)
    d = A.decide_flow("What did you decide for the next session, and why?")["answer"]
    assert "buys 2 stocks" in d and "plus 1 random control" in d and "stale data (Nifty 50)" in d and "next session is bullish" in d
    monkeypatch.setattr(A.views, "exec_marks", lambda: {"PULL": {"closed": 2, "realised_inr": -10000, "win_rate": 0.0}})
    monkeypatch.setattr(A.views, "open_positions", lambda: [1, 2, 3])
    monkeypatch.setattr(A.views, "books", lambda: {"per_trade_pct": -10.0})
    b = A.book_flow("How is the stock paper book doing?")["answer"]
    assert "not your money" in b and "-10.0% each" in b and "pullbacks -10.0% (2 closed)" in b and "Rs" not in b
    assert A.book_flow("How is my portfolio doing?") is None


def test_india_speech_uses_india_words():
    seen = {}

    def post(url, body):
        seen.update(body)
        return {"text": "How did the Nifty close today?"}
    assert V.transcribe("eA==", "audio/wav", post) == "How did the Nifty close today?"
    assert seen["context"] == "india" and seen["names"] == "Madhav"      # 27 Oct: no ticker list (Whisper looped on it)
    out = V.check(post=lambda url, body: {"text": "nifty bank nifty zerodha sign tata power trim jio rated lakh rupees expiry week straddle fix one flag wrong morning view pullback trade"},
                  speak=lambda said, d, k: b"x")
    assert out["understood"] == out["of"] == 12 and out["pass"]


def test_known_mishearings_are_put_right():
    assert V.fix_heard("Why is GIO Financial rated D?") == "Why is Jio Financial rated D?"
    assert V.fix_heard("Did the Ziradha sign in work? Should I trim Tadah power? worth one lock 8,000 rupees") == \
        "Did the Zerodha sign in work? Should I trim Tata Power? worth one lakh 8,000 rupees"
    assert V.fix_heard("lock the door") == "lock the door" and V.fix_heard("geography") == "geography"


def test_voice_server_prompt_by_market():
    srv = pytest.importorskip("jarvis.voice.server")
    assert "Nifty" in srv.stt_prompt("", "india") and "Bitcoin" not in srv.stt_prompt("", "india")
    assert "Bitcoin" in srv.stt_prompt("") and srv.stt_prompt("TATAPOWER, GVT&D", "india").endswith("Names: TATAPOWER, GVT&D.")
