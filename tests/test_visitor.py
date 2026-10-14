"""A visitor's own account (Madhav, 2026-10-06): setup in order (name, coins, tour, capital, ready, trading), their capital
becomes their book's start, and nothing of the owner's shows in their Books or Markets."""
import tempfile
from pathlib import Path

import pytest

from jarvis.service import appmap, core, visitor
from jarvis.service.manual import Manual


def _guest(d):
    return core.Jarvis(d, owner_email="owner@x.com", password_hash=core.hash_password("correct horse 1"), secret="s" * 40,
                       now=lambda: 1_800_000_000, db_file="jarvis_guest_asha_x_com.sqlite")


def test_setup_stages_in_order_and_capital_is_the_books_start():
    d = Path(tempfile.mkdtemp())
    g = _guest(d)
    assert visitor.me(g)["stage"] == "name"
    assert visitor.update(g, {"name": "  Asha  "})["stage"] == "coins"
    with pytest.raises(ValueError):
        visitor.update(g, {"coins": ["NOPE"]})
    r = visitor.update(g, {"coins": ["sol", "BTC", "SOL"]})
    assert r["profile"]["coins"] == ["SOL", "BTC"] and r["stage"] == "tour"
    assert visitor.update(g, {"tour_done": True})["stage"] == "capital"
    with pytest.raises(ValueError):
        visitor.update(g, {"capital": 5500})
    assert visitor.update(g, {"capital": 2000})["stage"] == "ready"
    assert Manual(g.db, g.now).state({})["start"] == 2000 and Manual(g.db, g.now).state({})["cash"] == 2000
    b = visitor.books(g)
    assert b["visitor"] and b["capital"] == 2000 and not b["started"] and b["book"]["fills"] == []
    assert visitor.update(g, {"start_trading": True, "method": "jarvis"})["stage"] == "trading"
    assert visitor.books(g)["started"] and visitor.books(g)["method"] == "jarvis"
    note = visitor.prompt_note(g, "Asha")
    assert "Solana" in note and "$2,000" in note and "NOT theirs" in note


def test_owner_book_keeps_the_default_start():
    d = Path(tempfile.mkdtemp())
    j = core.Jarvis(d, owner_email="owner@x.com", password_hash=core.hash_password("correct horse 1"), secret="s" * 40, now=lambda: 1)
    assert Manual(j.db, j.now).state({})["start"] == 1000


def test_list_highlights_follow_each_coin_being_read():
    pts = appmap.fill_list_points([{"spot": "markets.coin:BTC", "sentence": 0}],
                                  "Bitcoin is up 2 percent. Solana is down 1 percent. Both look calm. Ethereum is flat.")
    assert [(p["spot"], p["sentence"]) for p in pts] == [("markets.coin:BTC", 0), ("markets.coin:SOL", 1), ("markets.coin:ETH", 3)]
    assert appmap.fill_list_points([{"spot": "home.value", "sentence": 0}], "Bitcoin is up.") == [{"spot": "home.value", "sentence": 0}]
