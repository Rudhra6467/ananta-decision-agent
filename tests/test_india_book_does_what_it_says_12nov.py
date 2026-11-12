"""12 Nov 2026, the keen outside audit, audit repair 4 (open-list flag 120): the managed paper book does what its words say. G-07: a cut
is sized from the book's own shares (Jio Financial was sold 59 of 73, 81%, under "halving it", because the cut was sized in rupees from
the real account's 119 shares). G-17 (Madhav's yes of 12 Nov 01:52): a holding with no price study is "not graded" and never cut
(Karur Vysya was halved "if the slide continues" with no slide measured). Each check failed against the code before."""
import json

from india import allocator, managed


def _view(tmp_path, monkeypatch, suggestions):
    monkeypatch.setenv("INDIA_DATA_DIR", str(tmp_path))
    (tmp_path / "paper").mkdir(parents=True, exist_ok=True)
    (tmp_path / "paper" / "allocation_view.json").write_text(json.dumps({"suggestions": suggestions}))


C = {"reentry_sessions": 5, "min_cut_inr": 1000}


def test_a_halving_halves_the_books_own_position_not_the_real_accounts(tmp_path, monkeypatch):
    real_qty, book_qty, last = 119, 73, 230.0                        # Jio Financial on 30 Oct: 119 real shares, 73 in the paper book
    _view(tmp_path, monkeypatch, [{"symbol": "JIOFIN", "action": "REDUCE", "grade": "D", "value_inr": real_qty * last,
                                   "suggest_inr": round(real_qty * last * 0.5 / 100) * 100, "why": "Weak. Halving it limits the damage."}])
    book = {"positions": {"JIOFIN": {"qty": book_qty, "last": last, "avg": 260.0}}, "cut_days": {}}
    cut = managed.cut_list(book, "2026-10-30", C)[0]
    share = cut["inr"] / (book_qty * last)
    assert 0.49 <= share <= 0.51, share                              # it was 13,700 of 16,790: 82% of the book's shares
    assert int(cut["inr"] // (last * (1 - 0.001))) in (36, 37)       # about 36 of 73 shares at the open, not 59


def test_a_trim_takes_the_same_share_and_a_suggestion_without_the_real_value_cuts_nothing(tmp_path, monkeypatch):
    _view(tmp_path, monkeypatch, [{"symbol": "TATAPOWER", "action": "TRIM", "value_inr": 60000.0, "suggest_inr": 15000, "why": "Trim to 18%."},
                                  {"symbol": "LICI", "action": "REDUCE", "suggest_inr": 9000, "why": "an old view without value_inr"}])
    book = {"positions": {"TATAPOWER": {"qty": 78, "last": 400.0}, "LICI": {"qty": 44, "last": 900.0}}, "cut_days": {}}
    cuts = {c["symbol"]: c for c in managed.cut_list(book, "2026-10-30", C)}
    assert cuts["TATAPOWER"]["inr"] == round(78 * 400.0 * 0.25)      # a quarter of the book's own, as of the real holding
    assert "LICI" not in cuts                                         # no share to apply: no cut, never the real rupees


def test_a_holding_with_no_price_study_is_not_graded_and_never_cut():
    r = allocator.rule()
    h = {"tradingsymbol": "KARURVYSYA", "exchange": "NSE", "last_price": 245.0, "average_price": 50.4, "quantity": 13, "pnl": 2530}
    x = allocator.rate_holding(h, 0.04, None, "below_both", r)       # no row: not among the 250 most-traded stocks
    assert x["grade"] == "not graded" and x["action"] == "HOLD" and x["suggest_inr"] == 0 and not x["rated"]
    assert "Not graded" in x["why"] and "slide" not in x["why"] and "Halving" not in x["why"]
    tiny = allocator.rate_holding({**h, "quantity": 1}, 0.001, None, "below_both", r)
    assert tiny["action"] == "HOLD"                                  # not cut even when small: no data, no cut
    row = {"dist_sma20": 0.02, "dist_sma200": 0.1, "rsi14": 55, "atr_pct": 0.02, "liq_rank": 40}
    assert allocator.rate_holding({**h, "quantity": 1}, 0.001, row, "mixed", r)["action"] == "TIDY"   # a graded tiny one is still tidied
    rated = allocator.rate_holding({**h, "tradingsymbol": "X", "average_price": 400.0}, 0.04,
                                   {"dist_sma20": -0.05, "dist_sma200": -0.15, "rsi14": 30, "atr_pct": 0.06, "liq_rank": 200}, "below_both", r)
    assert rated["grade"] in "ABCD" and rated["action"] == "REDUCE"  # a holding with a price study is graded and cut as before


def test_a_holding_not_graded_is_never_near_another_grade():
    near = allocator.watch({"market": {}}, [{"symbol": "KARURVYSYA", "rated": False, "score": 40.0},
                                            {"symbol": "RATED", "rated": True, "score": 41.0}], {}, "mixed")
    row = next(w for w in near if w["what"] == "Holdings close to a different rating")
    assert row["now"] == "RATED"


def test_the_decision_is_in_the_pinned_rule_with_his_words():
    rule = allocator.rule()
    a = next(x for x in rule["amended"] if x["date"] == "2026-11-12")
    assert "Yes to all your recommendations" in a["by"] and "not graded" in a["change"] and "never cut" in a["change"]


def test_the_options_words_take_the_lines_own_count_and_claim_no_cash_they_cannot_see(tmp_path, monkeypatch):
    """G-10: the Options page said '11 so far' beside '12 of 20' and '12 sessions so far', and 'most of this money waits as cash' while one
    Bank Nifty premium takes about half of it."""
    monkeypatch.setenv("INDIA_DATA_DIR", str(tmp_path))
    (tmp_path / "paper" / "sp1").mkdir(parents=True)
    (tmp_path / "paper" / "sp1" / "book.json").write_text(json.dumps({"sessions": 12, "by_index": {}}))
    rm = {"sp1": {"book": {"sessions": 11}}, "market": {"vix_close": 12.0}}       # the read model, rebuilt only at night
    o = allocator.rate_options(rm, allocator.rule(), 50000)
    assert o["sessions"] == 12 and "11" not in o["words"] and "so far" not in o["words"]
    assert "most of this money waits as cash" not in o["words"] and "premium" in o["words"]
    rec = next(w for w in allocator.watch(rm, [], {}, "mixed") if w["what"] == "The options line's record")
    assert rec["now"] == "12 sessions"


def test_the_two_old_cuts_are_marked_once_by_the_code_beside_the_ledger(tmp_path, monkeypatch):
    """12 Nov 2026 (the outside check of repair 4, N9): the marks depended on a hand step at go-live; the code that writes the view now
    writes them, once, append-only, and only beside a ledger row that is there."""
    monkeypatch.setenv("INDIA_DATA_DIR", str(tmp_path))
    d = tmp_path / "paper" / "managed"
    d.mkdir(parents=True)
    led = [{"plan": "mp-2026-11-02", "for_session": "2026-11-02", "symbol": "JIOFIN", "side": "SELL", "qty": 59, "filled": True},
           {"plan": "mp-2026-11-02", "for_session": "2026-11-02", "symbol": "TATAPOWER", "side": "SELL", "qty": 30, "filled": True},
           {"plan": "mp-2026-11-02", "for_session": "2026-11-02", "symbol": "KARURVYSYA", "side": "SELL", "qty": 6, "filled": True}]
    (d / "ledger.jsonl").write_text("".join(json.dumps(r) + "\n" for r in led))
    before = (d / "ledger.jsonl").read_text()
    assert managed.ensure_marks() == 2 and managed.ensure_marks() == 0               # once
    marks = [json.loads(x) for x in (d / "marks.jsonl").read_text().splitlines()]
    assert [(x["symbol"], x["by"]) for x in marks] == [("JIOFIN", "G-07"), ("KARURVYSYA", "G-17")]
    assert "119 shares, not the book's 73" in marks[0]["mark"] and "not graded and never cut" in marks[1]["mark"]
    assert (d / "ledger.jsonl").read_text() == before                                  # the ledger is never rewritten
    (d / "marks.jsonl").unlink()
    (d / "ledger.jsonl").write_text(json.dumps(led[1]) + "\n")
    assert managed.ensure_marks() == 0 and not (d / "marks.jsonl").exists()             # no row, no mark
