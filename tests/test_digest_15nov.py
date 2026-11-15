"""The twice-daily digest (15 Nov 2026): routine notes wait and arrive together; anything else, and every WARN/ERROR/TEST, goes at once;
nothing is lost (queue kept word for word, full digest written, a failed send retried, a missed digest caught up)."""
import json

import pytest

from src.intelligence import digest as d
from src.intelligence import paper_watch as w


@pytest.fixture
def phone(tmp_path, monkeypatch):
    sent = []
    monkeypatch.setenv("ANANTA_NTFY_TOPIC", "test-topic")
    monkeypatch.setenv("ANANTA_APPLE_PUSH", "0")
    monkeypatch.setenv("ANANTA_DIGEST", "1")
    monkeypatch.setattr(w, "_ntfy_send", lambda topic, t, b, lvl, post: sent.append((t, b, lvl)) or "sent")
    return sent


@pytest.mark.parametrize("title,level,routine", [
    ("Ananta morning brief", "EVENT", True), ("Ananta's note", "EVENT", True), ("Jarvis: my day in review", "EVENT", True),
    ("Ananta's night test", "EVENT", True), ("Ananta nightly check", "EVENT", True), ("Morning view · 11-16", "EVENT", True),
    ("Pre-open · 11-16", "EVENT", True), ("Opening · 11-16", "EVENT", True), ("Planned: flag 12", "EVENT", True), ("Fixed: flag 3", "EVENT", True),
    ("Ananta morning brief", "WARN", False), ("Flag 164", "EVENT", False), ("Back: Hands", "EVENT", False),
    ("Ananta: Hands has gone quiet", "EVENT", False), ("Ananta: something is not right", "EVENT", False), ("BTC crossed 90,000", "EVENT", False),
    ("Ananta test alert", "TEST", False), ("Ananta's notebook", "EVENT", False)])
def test_routine_list(title, level, routine):
    assert d.is_routine(title, level) is routine


def test_routine_waits_and_the_rest_goes_now(phone):
    assert w.push_phone("Ananta's note", "The book is flat. Nothing to do.", level="EVENT") == "queued for the digest"
    assert w.push_phone("Ananta: Hands has gone quiet", "No answer twice.", level="EVENT") == "sent"
    assert w.push_phone("Ananta morning brief", "x", level="WARN") == "sent"
    assert [s[0] for s in phone] == ["Ananta: Hands has gone quiet", "Ananta morning brief"]
    assert [r["title"] for r in d.pending()] == ["Ananta's note"]


def test_digest_off_means_every_note_goes_at_once(phone, monkeypatch):
    monkeypatch.setenv("ANANTA_DIGEST", "0")
    assert w.push_phone("Ananta's note", "x", level="EVENT") == "sent" and not d.pending()


def test_no_phone_path_queues_nothing(monkeypatch):
    monkeypatch.setenv("ANANTA_NTFY_TOPIC", "")
    monkeypatch.setenv("ANANTA_APPLE_PUSH", "0")
    w.push_phone("Ananta's note", "x", level="EVENT")
    assert not d.QUEUE.exists()


def test_one_push_with_flags_grouped_and_the_full_text_kept(phone):
    for n in (151, 152, 150):
        w.push_phone(f"Planned: flag {n}", "planned", level="EVENT")
    w.push_phone("Ananta evening brief", "BTC held its 50-day. ETH lagged; nothing to do tonight.", level="EVENT")
    w.push_phone("Fixed: flag 9", "fixed", level="EVENT")
    assert d.send("night", lambda t, b: w.push_phone(t, b, level="EVENT")) == "sent 5 notes (sent)"
    title, body, lvl = phone[-1]
    assert title == "Ananta · night digest (5 notes)"
    assert body.splitlines() == ["• Planned: flags 150, 151, 152", "• Ananta evening brief: BTC held its 50-day.", "• Fixed: flag 9"]
    md = next(d.DIGESTS.glob("*-night.md")).read_text()
    assert "ETH lagged; nothing to do tonight." in md                       # word for word in the full digest
    assert d.pending() == [] and d.send("morning", lambda t, b: "sent") == "nothing new"
    assert len(phone) == 1                                                  # nothing new sends nothing


def test_a_failed_send_keeps_the_notes_waiting(phone):
    w.push_phone("Ananta's note", "x", level="EVENT")
    assert d.send("night", lambda t, b: "failed: HTTP 500").startswith("not sent")
    assert len(d.pending()) == 1
    assert d.send("morning", lambda t, b: "sent").startswith("sent 1")


def test_a_long_digest_fits_the_phone_and_says_how_many_more(phone):
    for i in range(30):
        w.push_phone("Ananta's night test", f"Night {i}: 12 of 12 passed, the bank 40 of 41 passed and one is still open for review.", level="EVENT")
    d.send("night", lambda t, b: w.push_phone(t, b, level="EVENT"))
    body = phone[-1][1]
    assert len(body) <= d.BODY_MAX and body.rstrip().endswith("more in the app")


def test_a_missed_digest_is_caught_up_by_the_next_routine_note(phone, monkeypatch):
    old = "2026-01-01T00:00:00.000000+00:00"
    d._append(d.QUEUE, {"ts": old, "title": "Ananta's note", "body": "old", "level": "EVENT"})
    r = w.push_phone("Ananta morning brief", "new", level="EVENT")
    assert r.startswith("queued; sent 2") and phone[-1][0] == "Ananta · catch-up digest (2 notes)"


def test_the_india_night_replay_note_waits(monkeypatch, tmp_path):
    from jarvis.india import replay

    monkeypatch.setenv("ANANTA_NTFY_TOPIC", "x")
    monkeypatch.setenv("ANANTA_DIGEST", "1")
    monkeypatch.setattr(replay.requests, "post", lambda *a, **k: (_ for _ in ()).throw(AssertionError("pushed directly")))
    replay._ntfy("Ananta nightly check", "2 of 30 failed")
    assert [r["title"] for r in d.pending()] == ["Ananta nightly check"]
