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
    assert cuts["TATAPOWER"]["share"] == 0.25                        # 13 Nov: the share itself, which the fill now takes
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


def test_a_cut_is_a_share_of_the_books_own_shares_at_the_fill_whatever_the_open(tmp_path, monkeypatch):
    """13 Nov 2026 (Madhav, 13:16 Toronto: "Yes to your recommendation"; open-list flag 156): a cut was sized in rupees at the last price
    the book had and turned back into shares at the next open, so a halving sold more than half when the stock opened lower."""
    import pandas as pd
    _view(tmp_path, monkeypatch, [{"symbol": "AAA", "action": "REDUCE", "grade": "D", "value_inr": 100 * 50.0, "suggest_inr": 2500,
                                   "why": "Weak. Halving it limits the damage."}])
    (tmp_path / "paper" / "managed").mkdir(parents=True, exist_ok=True)
    cfg = dict(C, slippage_pct=0.1, max_gap_pct=3, stop_pct=12, min_hold_sessions=5)

    def book():
        return {"positions": {"AAA": {"qty": 73, "last": 50.0, "avg": 60.0}}, "cut_days": {}, "filled_plans": [], "trades": [], "cash_inr": 0.0,
                "costs_inr": 0.0}
    b = book()
    cut = managed.cut_list(b, "2026-11-03", cfg)[0]
    assert cut["share"] == 0.5 and cut["inr"] == round(73 * 50.0 * 0.5)
    df = pd.DataFrame([{"symbol": "AAA", "date": pd.Timestamp("2026-11-04"), "open": 40.0, "close": 41.0}])   # it opens a fifth lower
    monkeypatch.setattr(managed, "_plans", lambda: [{"id": "P1", "for_session": "2026-11-04", "cuts": [cut], "buys": []}])
    done = managed.fill(b, "2026-11-04", df, cfg)
    assert done[0]["filled"] and done[0]["qty"] == 36 and b["positions"]["AAA"]["qty"] == 37     # half of 73, not the 45 (62%) that Rs 1,825 is at 40
    assert done[0]["sized"] == "share" and done[0]["share"] == 0.5                                # the sale row says how it was sized
    up = pd.DataFrame([{"symbol": "AAA", "date": pd.Timestamp("2026-11-04"), "open": 60.0, "close": 61.0}])   # and half when it opens higher (30 in rupees)
    b = book()
    monkeypatch.setattr(managed, "_plans", lambda: [{"id": "P2", "for_session": "2026-11-04", "cuts": [cut], "buys": []}])
    assert managed.fill(b, "2026-11-04", up, cfg)[0]["qty"] == 36
    # a plan written before this day carries no share: it is filled in rupees, as it was written
    b = book()
    monkeypatch.setattr(managed, "_plans", lambda: [{"id": "P0", "for_session": "2026-11-04", "cuts": [{k: v for k, v in cut.items() if k != "share"}], "buys": []}])
    done = managed.fill(b, "2026-11-04", df, cfg)
    assert done[0]["qty"] == 45 and done[0]["sized"] == "rupees" and "share" not in done[0]
    # an exit (stop, weak, tidy) is all of it, as before
    b = book()
    monkeypatch.setattr(managed, "_plans", lambda: [{"id": "P3", "for_session": "2026-11-04", "cuts": [dict(cut, all=True)], "buys": []}])
    done = managed.fill(b, "2026-11-04", df, cfg)
    assert done[0]["qty"] == 73 and done[0]["sized"] == "all" and "AAA" not in b["positions"]
    # the nearest whole share, a tie going down: the allocator rounds its rupees to 100, so "half" arrives as 0.4982 or 0.5016
    for held, share, sold in ((100, 0.4982, 50), (100, 0.5016, 50), (73, 0.25, 18), (4, 0.496, 2), (30, 0.3333, 10), (3, 0.5, 1), (2, 0.5, 1),
                              (1, 0.5, 1), (10, 1.0, 10)):
        b = {"positions": {"AAA": {"qty": held, "last": 50.0, "avg": 60.0}}, "cut_days": {}, "filled_plans": [], "trades": [], "cash_inr": 0.0,
             "costs_inr": 0.0}
        monkeypatch.setattr(managed, "_plans", lambda s=share: [{"id": f"Q{s}", "for_session": "2026-11-04", "cuts": [dict(cut, share=s)], "buys": []}])
        assert managed.fill(b, "2026-11-04", df, cfg)[0]["qty"] == sold, (held, share)


def test_a_replacement_buy_spends_at_most_what_its_own_cut_freed_and_waits_when_its_cut_was_skipped(tmp_path, monkeypatch):
    """13 Nov 2026 (Madhav, 19:41 Toronto: "yes"; open-list flag 158): the buy was sized from the cut's planned rupees, so with spare cash
    it spent more than the sale brought in, and a cut skipped for the day still had its replacement bought."""
    import pandas as pd
    _view(tmp_path, monkeypatch, [])
    (tmp_path / "paper" / "managed").mkdir(parents=True, exist_ok=True)
    cfg = dict(C, slippage_pct=0.1, max_gap_pct=3, stop_pct=12, min_hold_sessions=5)
    cut = {"symbol": "AAA", "kind": "REDUCE", "all": False, "inr": 1825, "share": 0.5}

    def book():
        return {"positions": {"AAA": {"qty": 73, "last": 50.0, "avg": 60.0}}, "cut_days": {}, "filled_plans": [], "trades": [], "cash_inr": 5000.0,
                "costs_inr": 0.0}

    def bars(aaa_open):
        rows = [{"symbol": "BBB", "date": pd.Timestamp("2026-11-03"), "open": 100.0, "close": 100.0},
                {"symbol": "BBB", "date": pd.Timestamp("2026-11-04"), "open": 100.0, "close": 101.0}]
        if aaa_open:
            rows.append({"symbol": "AAA", "date": pd.Timestamp("2026-11-04"), "open": aaa_open, "close": aaa_open})
        return pd.DataFrame(rows)

    def run(aaa_open, for_cut="AAA", plan="P"):
        b = book()
        monkeypatch.setattr(managed, "_plans", lambda: [{"id": plan, "for_session": "2026-11-04", "cuts": [cut],
                                                         "buys": [{"symbol": "BBB", "inr": 1825, "for_cut": for_cut}]}])
        done = managed.fill(b, "2026-11-04", bars(aaa_open), cfg)
        return b, next(t for t in done if t["side"] == "SELL"), next(t for t in done if t["side"] == "BUY")

    b, sell, buy = run(40.0, plan="P1")                                  # the stock opens a fifth lower: the cut brings in less than planned
    brought = sell["value_inr"] - sell["cost_inr"]
    assert buy["filled"] and buy["value_inr"] + buy["cost_inr"] <= brought + 0.01 < 1825        # it spent 128% of this before
    assert buy["capped_at_freed_inr"] == round(brought, 2) and abs(b["cash_inr"] - 5000.0) < brought   # the spare cash is not drawn on
    assert b["cash_inr"] >= 5000.0 - 0.01
    b, sell, buy = run(60.0, plan="P2")                                  # it opens higher: the buy stays at the plan, the rest stays in cash
    assert buy["filled"] and buy["value_inr"] + buy["cost_inr"] <= 1825 and "capped_at_freed_inr" not in buy
    b, sell, buy = run(None, plan="P3")                                  # no bar for the cut today: it is skipped, and so is its replacement
    assert sell["skipped"].startswith("no bar") and buy["skipped"] == "its cut was not sold today"
    assert b["cash_inr"] == 5000.0 and "BBB" not in b["positions"] and b["positions"]["AAA"]["qty"] == 73
    b, sell, buy = run(40.0, for_cut="AAA+ZZZ", plan="P4")               # pooled from two cuts, one of them not sold: what the sold one freed
    assert buy["filled"] and buy["value_inr"] + buy["cost_inr"] <= sell["value_inr"] - sell["cost_inr"] + 0.01


def test_the_buy_caps_small_finds_and_the_halving_rule_14nov(tmp_path, monkeypatch):
    """14 Nov 2026 (the buy cap's outside check, C1, C3, C4, C5; and the halving rule, left to the builder by Madhav's word of 14 Nov
    09:59): two buys naming one cut spent it twice; the cap's mark did not say the plan; the skip reasons were cut short on the phone;
    and a halving of 3 shares sold 1 or 2, as the allocator's rounding to Rs 100 fell."""
    import pandas as pd
    (tmp_path / "paper" / "managed").mkdir(parents=True, exist_ok=True)
    cfg = dict(C, slippage_pct=0.1, max_gap_pct=3, stop_pct=12, min_hold_sessions=5)

    def bars(aaa_open=40.0, bbb=True):
        rows = [{"symbol": "BBB", "date": pd.Timestamp("2026-11-03"), "open": 100.0, "close": 100.0},
                {"symbol": "CCC", "date": pd.Timestamp("2026-11-03"), "open": 100.0, "close": 100.0},
                {"symbol": "CCC", "date": pd.Timestamp("2026-11-04"), "open": 100.0, "close": 100.0}]
        if bbb:
            rows.append({"symbol": "BBB", "date": pd.Timestamp("2026-11-04"), "open": 100.0, "close": 101.0})
        if aaa_open:
            rows.append({"symbol": "AAA", "date": pd.Timestamp("2026-11-04"), "open": aaa_open, "close": aaa_open})
        return pd.DataFrame(rows)

    def run(plan, cut, buys, cash=5000.0, df=None):
        _view(tmp_path, monkeypatch, [])
        b = {"positions": {"AAA": {"qty": 73, "last": 50.0, "avg": 60.0}}, "cut_days": {}, "filled_plans": [], "trades": [], "cash_inr": cash,
             "costs_inr": 0.0}
        monkeypatch.setattr(managed, "_plans", lambda: [{"id": plan, "for_session": "2026-11-04", "cuts": [cut], "buys": buys}])
        done = managed.fill(b, "2026-11-04", bars() if df is None else df, cfg)
        return b, [t for t in done if t["side"] == "SELL"], [t for t in done if t["side"] == "BUY"]

    half = {"symbol": "AAA", "kind": "REDUCE", "all": False, "inr": 1825, "share": 0.5}
    spent = lambda buys: sum(t["value_inr"] + t["cost_inr"] for t in buys if t.get("filled"))   # noqa: E731
    # C1: two buys naming the same cut share what it freed; the spare cash is not drawn on (it was 3,373.55 of 5,000 left)
    b, sells, buys = run("T1", half, [{"symbol": "BBB", "inr": 1825, "for_cut": "AAA"}, {"symbol": "CCC", "inr": 1825, "for_cut": "AAA"}])
    brought = sells[0]["value_inr"] - sells[0]["cost_inr"]
    assert spent(buys) <= brought + 0.01 and b["cash_inr"] >= 5000.0 - 0.01
    assert buys[0]["filled"] and buys[1].get("skipped") == "its cut freed less than one share"
    # C3: a capped buy says the plan's rupees beside the cap
    assert buys[0]["planned_inr"] == 1825.0 and buys[0]["capped_at_freed_inr"] == round(brought, 2)
    # C4: both skip reasons fit the phone's row (44 characters, places.py)
    b, sells, buys = run("T2", half, [{"symbol": "BBB", "inr": 1825, "for_cut": "AAA"}], df=bars(aaa_open=None))
    assert buys[0]["skipped"] == "its cut was not sold today" and all(len(x) <= 37 for x in ("its cut was not sold today", "its cut freed less than one share"))
    # C5: a cut marked all, a cut on the old rupee rule, cash under what was freed, the gap rule, a buy with no cut of its own
    for n, cut in enumerate(({"symbol": "AAA", "kind": "TIDY", "all": True, "inr": 3650}, {"symbol": "AAA", "kind": "REDUCE", "all": False, "inr": 1825})):
        b, sells, buys = run(f"T3{n}", cut, [{"symbol": "BBB", "inr": 3650, "for_cut": "AAA"}])
        assert buys[0]["filled"] and spent(buys) <= sells[0]["value_inr"] - sells[0]["cost_inr"] + 0.01 and b["cash_inr"] >= 5000.0 - 0.01
    b, sells, buys = run("T4", half, [{"symbol": "BBB", "inr": 1825, "for_cut": "AAA"}], cash=-1200.0)
    assert b["cash_inr"] >= 0 and spent(buys) <= sells[0]["value_inr"] - sells[0]["cost_inr"] - 1200.0 + 0.01
    gap = bars()
    gap.loc[(gap["symbol"] == "BBB") & (gap["date"] == pd.Timestamp("2026-11-04")), "open"] = 110.0
    b, sells, buys = run("T5", half, [{"symbol": "BBB", "inr": 1825, "for_cut": "AAA"}], df=gap)
    assert "not chased" in buys[0]["skipped"] and abs(b["cash_inr"] - (5000.0 + sells[0]["value_inr"] - sells[0]["cost_inr"])) < 0.01
    b, sells, buys = run("T6", half, [{"symbol": "BBB", "inr": 1825}], cash=1825.0 - (sells[0]["value_inr"] - sells[0]["cost_inr"]))
    assert buys[0]["filled"] and spent(buys) <= 1825.0 and "capped_at_freed_inr" not in buys[0]
    # the halving rule: a suggestion within Rs 50 of half the real holding is exactly half, so 3 shares sell 1, never 2
    for suggest in (30100, 30050, 30000, 29950, 29900):                  # half of 60,100 is 30,050; the allocator rounds to 100
        _view(tmp_path, monkeypatch, [{"symbol": "AAA", "action": "REDUCE", "value_inr": 60100, "suggest_inr": suggest}])
        book = {"positions": {"AAA": {"qty": 3, "last": 1000.0, "avg": 900.0}}, "cut_days": {}, "filled_plans": [], "trades": [], "cash_inr": 0.0,
                "costs_inr": 0.0}
        cut = managed.cut_list(book, "2026-11-03", cfg)[0]
        want = 0.5 if abs(suggest - 30050) <= 50 else round(suggest / 60100, 4)
        assert cut["share"] == want, (suggest, cut["share"])
        monkeypatch.setattr(managed, "_plans", lambda c=cut, s=suggest: [{"id": f"H{s}", "for_session": "2026-11-04", "cuts": [c], "buys": []}])
        sold = managed.fill(book, "2026-11-04", pd.DataFrame([{"symbol": "AAA", "date": pd.Timestamp("2026-11-04"), "open": 1000.0, "close": 1000.0}]), cfg)
        assert sold[0]["qty"] == 1, (suggest, sold[0]["qty"])
    _view(tmp_path, monkeypatch, [{"symbol": "AAA", "action": "TRIM", "value_inr": 60000, "suggest_inr": 15000}])   # a quarter stays a quarter
    book = {"positions": {"AAA": {"qty": 40, "last": 1000.0, "avg": 900.0}}, "cut_days": {}, "filled_plans": [], "trades": [], "cash_inr": 0.0, "costs_inr": 0.0}
    assert managed.cut_list(book, "2026-11-03", cfg)[0]["share"] == 0.25
