"""21 Nov 2026, the outside lock review's answer faults at S2 (lock/lock_review_21nov.md): C-21 (review 42 "not found": the full list of
reviews was cut), TR3b (the account's own wins left out), I-03 and FU2-1 (the managed book's holdings guessed from its cuts), I-04 (the
plan's estimate said for a filled sale). Each test fails on the code before."""
import json

from jarvis.india import ask as iask
from jarvis.service import ask as cask


def test_every_review_is_in_the_index_and_one_is_read_in_full_by_its_id(monkeypatch):
    rows = [{"id": f"R{i}", "title": f"review {i}", "date": "2026-11-11", "verdict": "PASS", "why": "x" * 2000, "question": "q" * 2000,
             "result": "r" * 2000, "changed": ""} for i in range(1, 43)]
    monkeypatch.setattr(cask.views, "evidence_collected", lambda j: {"forwarded": rows})
    monkeypatch.setattr(cask.views, "evidence_forwarded", lambda j: {"in_use": [], "safety_changes": []})
    L = cask.Lookups.__new__(cask.Lookups)
    L.j = None
    idx = L.t_evidence("reviews")
    assert idx["count"] == 42 and idx["reviews"][-1] == {"id": "R42", "date": "2026-11-11", "title": "review 42", "verdict": "PASS"}
    assert len(json.dumps(idx)) < 6000                                  # short enough never to be cut
    assert L.t_evidence(review="42")["review"]["id"] == "R42" and L.t_evidence(review="R7")["review"]["id"] == "R7"
    miss = L.t_evidence(review="99")
    assert miss["review"] is None and "R1 to R42" in miss["words"]


def test_the_accounts_own_wins_are_counted(monkeypatch):
    from jarvis.service import officer

    monkeypatch.setattr(officer, "book_status", lambda j: {"value_cad": 467.55, "closed": [{"pnl_cad": 3.1}] + [{"pnl_cad": -1.0}] * 8})
    s = cask._book_status(None)
    assert s["closed_summary"] == {"closed": 9, "won": 1, "words": "1 of 9 of the account's own closed trades made money"}


def _managed(tmp_path, monkeypatch):
    d = tmp_path / "paper" / "managed"
    d.mkdir(parents=True)
    (d / "view.json").write_text(json.dumps({"stocks_inr": 100000, "holdings": [
        {"symbol": "NIFTYBEES", "value_inr": 20000, "source": "from the account", "pnl_pct": 1.7},
        {"symbol": "TATAPOWER", "value_inr": 15000, "source": "from the account", "pnl_pct": 22.1},
        {"symbol": "AJANTPHARM", "value_inr": 9000, "source": "replacement", "pnl_pct": -4.7}]}))
    (d / "plans.jsonl").write_text(json.dumps({"id": "mp-2026-11-02", "for_session": "2026-11-02", "cuts": [{"symbol": "TATAPOWER", "kind": "TRIM",
                                   "inr": 10600, "why": "middling"}], "buys": [{"symbol": "ETERNAL", "for_cut": "TATAPOWER"}]}) + "\n")
    (d / "ledger.jsonl").write_text(json.dumps({"plan": "mp-2026-11-02", "symbol": "TATAPOWER", "side": "SELL", "qty": 30, "price": 343.76,
                                                "value_inr": 10312.68, "filled": True}) + "\n")
    monkeypatch.setattr(iask, "DATA", tmp_path)


def test_the_managed_books_holdings_are_all_of_them_with_the_index_fund(tmp_path, monkeypatch):
    _managed(tmp_path, monkeypatch)
    h = iask._managed_book()["holdings_now"]
    assert [x["symbol"] for x in h] == ["NIFTYBEES", "TATAPOWER", "AJANTPHARM"]
    assert h[0]["source"].startswith("parked cash") and h[1]["share_pct"] == 15.0 and h[2]["pnl_pct_since_bought_or_start"] == -4.7


def test_a_cut_says_what_it_sold_for_beside_the_plans_estimate(tmp_path, monkeypatch):
    _managed(tmp_path, monkeypatch)
    c = iask._managed_cuts()[0]
    assert c["planned_inr"] == 10600 and c["sold"] == {"qty": 30, "inr": 10312.68, "price": 343.76} and "sold.inr" in c["say"]
