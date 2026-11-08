"""8 Nov 2026 (morning self-scan): the card's headline is built before tonight's drafts reach the queue, so it must count them itself:
the 6 Nov card said "1 new idea tonight; nothing waits for you" while that one draft waited."""
from __future__ import annotations

from india import reconstruct as rx


def _card(findings):
    return {"day": "2026-11-06", "findings": findings, "market": {}, "ananta": {}, "not_done": {}, "reviews": {}}


def test_tonights_draft_counts_as_waiting(monkeypatch):
    monkeypatch.setattr(rx, "queue", lambda: [])
    h = rx._headline(_card([{"key": "ALLOC_WRONG:regime_table", "lane": "DECISION", "state": "DRAFT"}]))
    assert "1 new idea tonight; 1 draft waits for your yes or skip." in h
    assert "nothing waits for you" not in h


def test_a_draft_already_in_the_queue_is_counted_once(monkeypatch):
    monkeypatch.setattr(rx, "queue", lambda: [{"key": "K1", "lane": "DECISION", "state": "DRAFT"}, {"key": "K0", "lane": "DECISION", "state": "DRAFT"},
                                              {"key": "K9", "lane": "DECISION", "state": "SKIPPED"}])
    h = rx._headline(_card([{"key": "K1", "lane": "DECISION", "state": "DRAFT"}]))
    assert "1 new idea tonight; 2 drafts wait for your yes or skip." in h


def test_nothing_new_and_nothing_queued(monkeypatch):
    monkeypatch.setattr(rx, "queue", lambda: [])
    assert "no new idea tonight; nothing waits for you." in rx._headline(_card([]))
