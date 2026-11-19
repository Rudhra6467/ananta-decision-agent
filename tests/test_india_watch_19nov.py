"""19 Nov 2026 (Madhav): watchlists on Markets, and a stock page behind the search."""
import json

import pytest

from jarvis import placekit as K
from jarvis.india import views
from jarvis.india import watch as W


@pytest.fixture
def data(tmp_path, monkeypatch):
    monkeypatch.setattr(views, "DATA", tmp_path)
    (tmp_path / "manifests").mkdir()
    (tmp_path / "manifests" / "quotebook_names.json").write_text(json.dumps({"TCS": {"name": "TATA CONSULTANCY SERVICES LIMITED", "kind": "stock"},
                                                                           "INFY": {"name": "Infosys Limited", "kind": "stock"}}))
    (tmp_path / "manifests" / "quotebook.json").write_text(json.dumps({"quotes": {"TCS": {"as_of": "2026-11-19", "close": 2342.7, "chg_1d": -0.0155, "high_52w": 3000.0},
                                                                                  "INFY": {"as_of": "2026-11-19", "close": 1500.0, "chg_1d": 0.01}}}))
    W._NAMES.update(at=0.0, v={})
    monkeypatch.setattr(W, "quotes", lambda syms: {s: {"last": 1.0, "change_pct": 1.0, "as_of": "2026-11-19", "live": False} for s in syms})
    return tmp_path


def test_a_watchlist_is_created_renamed_filled_and_deleted(data):
    r = W.act({"action": "create"})
    assert r["id"] == "w1" and W.lists()[0]["name"] == "Watchlist 1"
    W.act({"action": "rename", "id": "w1", "name": "IT names"})
    W.act({"action": "add", "id": "w1", "sym": "tcs"})
    W.act({"action": "add", "id": "w1", "sym": "TCS"})                      # added once
    assert W.lists()[0] == {"id": "w1", "name": "IT names", "symbols": ["TCS"]}
    W.act({"action": "remove", "id": "w1", "sym": "TCS"})
    assert W.lists()[0]["symbols"] == []
    W.act({"action": "delete", "id": "w1"})
    assert W.lists() == []
    with pytest.raises(KeyError):
        W.act({"action": "add", "id": "w9", "sym": "TCS"})


def test_markets_gets_a_box_and_sections_per_list(data):
    W.act({"action": "create", "sym": "TCS"})
    assert [b["label"] for b in W.boxes()] == ["Watchlist 1"]
    secs = W.sections()
    assert any((s.get("tags") or []) == ["watchlist"] and s.get("title") == "Watchlist 1" for s in secs)
    page = W.watchlist_page("w1")
    assert page["parts"][0]["t"] == "watchmanage" and not K.problems("watchlist", page)


def test_the_search_list_and_a_stock_page(data):
    assert {r["s"] for r in W.stocklist()["rows"]} == {"TCS", "INFY"}
    p = W.stock_page("tcs", full=False)
    assert p["title"] == "Tata Consultancy Services" and not any(x.get("t") == "watchadd" for x in p["parts"])   # a guest cannot add
    assert not K.problems("stock", p)
    with pytest.raises(KeyError):
        W.stock_page("NOPE")
