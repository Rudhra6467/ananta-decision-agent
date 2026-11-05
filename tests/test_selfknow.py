"""5 Nov 2026 (Madhav: "how much Ananta does know about what we did here in the back end? That should always be there ... it can tell if
something is not right"): the change book, the parts, the self-check, and the fixes found by the 20-day synopsis."""
import json
import time

from jarvis import selfcheck, selfknow
from jarvis.service.alerts import three_sentences

BOOK = [
    {"date": "2026-10-25", "market": "crypto", "area": "voice", "words": "Ananta now reads who is speaking from each message.",
     "why": "flag 9: Ananta confused who was speaking", "status": "live", "checked": "tests", "commits": ["854f0d4"], "source": "x"},
    {"date": "2026-11-05", "market": "india", "area": "voice", "words": "Ananta starts speaking at its first sentence while it writes the rest.",
     "why": "Madhav: start speaking while it is still writing", "status": "live", "checked": "5.5 s to the first word", "commits": [], "source": "y"},
    {"date": "2026-11-05", "market": "india", "area": "managed_book", "words": "The managed book is compared with your holdings over the same days.",
     "why": "", "status": "live", "checked": "", "commits": [], "source": "z"},
]


def _book(tmp_path, monkeypatch, rows=BOOK):
    p = tmp_path / "changes.jsonl"
    p.write_text("".join(json.dumps(r) + "\n" for r in rows))
    monkeypatch.setattr(selfknow, "CHANGES", p)
    selfknow._CACHE.clear()


def test_change_book_search_by_his_words(tmp_path, monkeypatch):
    _book(tmp_path, monkeypatch)
    hits = selfknow.search("how does your voice work now, do you speak while writing")
    assert hits and hits[0]["date"] == "2026-11-05" and hits[0]["area"] == "voice"
    assert selfknow.say(hits[0]).startswith("5 Nov, India: Ananta starts speaking")
    assert [r["date"] for r in selfknow.for_request(90, 9)] == ["2026-10-25"]
    assert len(selfknow.recent(7, now=time.mktime((2026, 11, 5, 12, 0, 0, 0, 0, -1)))) == 2


def test_about_ananta_has_changes_parts_and_the_self_check(tmp_path, monkeypatch):
    _book(tmp_path, monkeypatch)
    monkeypatch.setattr(selfknow, "VOICE", tmp_path / "voice")
    monkeypatch.setattr(selfknow, "RUNS", tmp_path / "runs")
    monkeypatch.setattr(selfknow, "INDIA", tmp_path / "india")
    monkeypatch.setattr(selfcheck, "FILE", tmp_path / "selfcheck.json")
    a = selfknow.about_ananta("what changed in your voice", "india")
    assert a["changes_on_this"] and "first sentence" in a["changes_on_this"][0]
    assert set(a["parts"]) >= {"voice", "voice_print", "watchdog", "pre_open_read", "phase_study"}
    assert "not run yet" in a["not_right"][0]
    c = selfknow.about_ananta("what changed", "crypto")
    assert "pre_open_read" not in c["parts"] and "as soon as Claude writes it" in c["parts"]["voice"]["speaks_while_writing"]


def test_voice_print_counts_from_enrolment(tmp_path, monkeypatch):
    v = tmp_path / "voice"
    v.mkdir()
    now = time.time()
    (v / "speaker_profile.json").write_text(json.dumps({"count": 6, "enrolled_at": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime(now - 3 * 86400)),
                                                        "thresholds": {"accept": 0.557, "reject": 0.298}, "print": [0.1] * 192}))
    rows = [{"t": now - 5 * 86400, "speaker": "unknown", "speech_s": 3},          # before enrolment: not counted
            {"t": now - 3600, "speaker": "madhav", "speech_s": 4}, {"t": now - 1800, "speaker": "unknown", "speech_s": 2.1},
            {"t": now - 900, "speaker": "unknown", "speech_s": 0.9}]
    (v / "speaker_log.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    monkeypatch.setattr(selfknow, "VOICE", v)
    vp = selfknow._voice_print(now)
    assert vp["last_7_days"] == {"madhav": 1, "unknown": 2, "not_madhav": 0} and vp["unsure_long_clips"] == 1
    assert "Since then 1 voice turns" in vp["words"] and "print" not in json.dumps({k: v for k, v in vp.items() if k != "words"})


def test_self_check_says_what_is_not_right_and_when_it_is_stale(tmp_path, monkeypatch):
    monkeypatch.setattr(selfcheck, "FILE", tmp_path / "selfcheck.json")
    monkeypatch.setattr(selfcheck, "_runs", lambda now: [{"market": "india", "severity": "medium", "source": "lost-runs check",
                                                          "what": "India stock paper book did not run at 4 Nov 21:30 Toronto"}])
    monkeypatch.setattr(selfcheck, "_answers", lambda: [])
    monkeypatch.setattr(selfcheck, "_leftovers", lambda: [])
    monkeypatch.setattr(selfcheck, "_restarts", lambda now: [])

    def down(url, timeout=2):
        raise OSError("no answer")
    c = selfcheck.refresh(now=1793906451, opener=down)
    assert c["items"][0]["severity"] == "high" and "not answering" in c["items"][0]["what"]
    india = selfcheck.check("india", now=1793906451 + 60)
    assert all(x["market"] in ("india", "both") for x in india["items"])
    assert selfcheck.headline(india).startswith("Before we start: the India service is not answering")
    stale = selfcheck.check("crypto", now=1793906451 + 3 * 3600)
    assert "may be out of date" in stale["items"][0]["what"]


def test_self_check_finds_a_test_card_waiting_for_madhav(tmp_path):
    import sqlite3
    db = tmp_path / "j.sqlite"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE pending_actions (id TEXT, t INTEGER, kind TEXT, summary TEXT, payload TEXT, status TEXT, by TEXT, decided_t INTEGER, result TEXT, thread TEXT)")
    con.execute("CREATE TABLE ask_messages (thread TEXT, role TEXT, mode TEXT)")
    con.execute("INSERT INTO pending_actions VALUES ('A1', 1, 'paper_order', 'Paper BUY $100.00 of SOL', '{}', 'PENDING', NULL, NULL, NULL, 'oc1x')")
    con.execute("INSERT INTO ask_messages VALUES ('oc1x', 'user', 'eval:voice:auto')")
    con.commit()
    con.close()
    items = selfcheck._leftovers(db)
    assert len(items) == 1 and items[0]["severity"] == "high" and "SOL" in items[0]["what"]


def test_briefing_keeps_three_sentences_and_never_offers_an_order():
    a = ("Morning, sir. Your $500 account is about C$446, and its core bought its first Bitcoin and Ethereum last night. The dial opened on "
         "a thin 0.5% margin. Nothing needs you today. The Explorer is at about $1,709. No order card was made; say 'prepare it' if you want one.")
    r = three_sentences({"answer": a, "breakdown": ["Open trades: none"]})
    assert r["answer"].endswith("Nothing needs you today.") and "order card" not in r["answer"]
    assert r["breakdown"][0] == "The Explorer is at about $1,709." and r["breakdown"][-1] == "Open trades: none"


def test_self_check_says_when_claude_credit_has_run_out():
    """5 Nov 14:53 Toronto: the Anthropic credit ran out and nothing said so."""
    import io
    import urllib.error

    def empty(req, timeout=15):
        raise urllib.error.HTTPError(req.full_url, 400, "Bad Request", {}, io.BytesIO(
            b'{"type":"error","error":{"type":"invalid_request_error","message":"Your credit balance is too low to access the Anthropic API."}}'))

    def busy(req, timeout=15):
        raise urllib.error.HTTPError(req.full_url, 529, "Overloaded", {}, io.BytesIO(b'{"error":{"type":"overloaded_error"}}'))
    out = selfcheck.credit_probe("k", empty)
    assert out and out[0]["severity"] == "high" and "credit has run out" in out[0]["what"]
    assert selfcheck.credit_probe("k", busy) == [] and selfcheck.credit_probe("", empty) == []
