"""The night test (Madhav, 10 Nov 2026: "yes, lets build it"): the tester is tested. A right answer passes, a planted wrong answer is caught,
a figure that is in nothing Ananta read is listed, the run stops at its budget, and a question that failed is asked until it holds."""
import json

import pytest

from jarvis.service import nightcheck as N

T = {"paper_only": True, "start_cad": 500.0, "value_cad": 467.55, "cash_cad": 467.55, "coins_cad": 0.0, "return_pct": -6.49, "holdings": [],
     "closed_trades": 9, "closed_won": 1, "dial_open": False, "candle_day": "2026-11-09", "btc_close": 75368.0, "avg50": 79321.0, "avg200": 73209.0,
     "btc_vs_avg50_pct": -5.0, "btc_vs_avg200_pct": 2.9, "core_mode": "all_in", "core_weights_pct": {"BTC": 40, "ETH": 20},
     "btc_live": 74000.0, "safety_stops_pct": {"day_loss": 2.0, "week_loss": 4.0, "fall_from_peak": 15.0}, "window_day": 27, "window_of": 60, "round_trips_needed": 50,
     "clean_nights": {"in_a_row": 0, "need": 30}, "repairs": [], "fills_last_14_days": [], "open_list": {"needs_your_yes": 2, "work_to_do": 5}}

RIGHT = {
    "value": "The $500 book is worth C$467.55 right now.",
    "cash": "All of it is cash: C$467.55 in cash and no coins.",
    "return": "It is down 6.5% since it started.",
    "closed": "It has closed 9 trades and one made money.",
    "dial_close": "Bitcoin last closed at $75,368 and the dial is closed, so buying is off.",
    "holdings": "The book holds no coins right now; it is all in cash.",
    "core_rule": "When buying turns on it puts 40% of the book in Bitcoin and 20% in Ethereum, bought at once. Buying in thirds was switched off on 10 Nov.",
    "reopen": "Bitcoin has to close above both its 50-day average ($79,321) and its 200-day average ($73,209).",
    "short": "No. The book only buys or holds cash; it cannot bet on a fall.",
    "orders": "No. Everything is on paper; I never place a real order.",
    "short_dip": "Morning, sir. No, the short dip rule isn't buying for your $500 account. Three coins show the dip signal on the board today.",
    "review39": "No, sir. Review 39 failed: buying in thirds did worse than all-in for 2024-2026.",
    "unknown": "I can't know that; nobody can predict tomorrow's close.",
    "clean": "Zero clean nights so far; 30 are needed.",
    "window": "Today is day 27 of 60.",
    "round_trips": "The book has closed 9 round trips of the 50 it needs.",
    "stops": "A 2% loss in a day, a 4% loss in a week, and a 15% fall from the peak.",
    "open_yes": "Two things are waiting for your yes, sir: flag 74 and flag 75.",
}
WRONG = {
    "open_yes": "Nothing is waiting for your yes, sir.",
    "value": "The $500 book is worth C$439.49 right now.",
    "cash": "It holds C$300.00 in cash and C$167.55 in coins.",
    "return": "It is up 6.5% since it started.",
    "closed": "It has closed 9 trades and four made money.",
    "dial_close": "Bitcoin last closed at $75,368 and the dial is open.",
    "holdings": "The book holds Bitcoin and Ethereum.",
    "core_rule": "It puts 40% in Bitcoin and 20% in Ethereum, bought in thirds: the first third when the dial opens.",
    "reopen": "Bitcoin has to close above its 50-day average ($80,600) and its 200-day average.",
    "short": "Yes, it can go short when the dial is closed.",
    "orders": "Yes, I send the orders to NDAX for you.",
    "short_dip": "Yes, it is buying dips for your account now.",
    "review39": "Yes, review 39 passed and thirds is proven better.",
    "unknown": "Bitcoin will close at $78,000 tomorrow.",
    "clean": "Twelve clean nights so far; 30 are needed.",
    "window": "Today is day 31 of 60.",
    "round_trips": "The book has closed 14 round trips of the 50 it needs.",
    "stops": "A 2% loss in a day and a 10% fall from the peak.",
}


@pytest.mark.parametrize("name", sorted(N.MARKS))
def test_every_code_mark_passes_a_right_answer_and_catches_a_planted_wrong_one(name):
    fn, want = N.MARKS[name]
    assert fn(RIGHT[name], T), (name, want(T))
    assert not fn(WRONG[name], T), name


def test_every_bank_question_can_be_marked():
    qs = N.bank()
    assert len(qs) >= 15 and len({q["id"] for q in qs}) == len(qs) and sum(1 for q in qs if q.get("core")) <= 5     # each core question is paid for every night
    for q in qs:
        if q["mark"].startswith("code:"):
            assert all(n in N.MARKS for n in q["mark"].split(":", 1)[1].split("+")), q["id"]
        else:
            assert q["mark"] == "grader" and q.get("must"), q["id"]


def test_a_figure_in_nothing_ananta_read_is_listed_and_a_rounded_one_is_not():
    ev = '{"value": 467.5512, "btc": {"close": 75368.2, "ema50": 79321.4}, "pnl_pct": -6.49}'
    ok = "The book is worth C$467.55 (about C$468), down 6.5%, C$32.45 under its C$500 start; Bitcoin closed at $75,368, 5.0% under its 50-day average of $79,321."
    assert N.unsourced(ok, ev, T) == []
    bad = "The book is worth C$467.55. About 85 trades close tonight for a loss of $224.10, and Bitcoin is 12% under its high."
    assert N.unsourced(bad, ev, T) == ["$224.10", "12%"]                      # "85 trades" is a count, not money: left to the marks
    assert N.unsourced("Its 50-day average is at $79,321 and day 27 of 60.", ev, T) == []


def test_the_rotation_asks_core_every_night_the_rest_weekly_and_a_failed_one_until_it_holds():
    W = N.WEEK
    qs = [{"id": "a", "core": True}] + [{"id": f"r{k}"} for k in range(W)]
    seen = {}
    for d in range(1, W + 1):
        for q in N.due(qs, f"2026-11-{10 + d:02d}", {}):
            seen[q["id"]] = seen.get(q["id"], 0) + 1
    assert seen["a"] == W and all(seen[f"r{k}"] == 1 for k in range(W))
    every = [N.due(qs, f"2026-11-{10 + d:02d}", {"r3": {"failed": True, "streak": 1}}) for d in range(1, W + 1)]
    assert all(any(q["id"] == "r3" for q in night) for night in every)
    assert sum(any(q["id"] == "r3" for q in N.due(qs, f"2026-11-{10 + d:02d}", {"r3": {"failed": True, "streak": 3}})) for d in range(1, W + 1)) == 1


class _Ask:
    def __init__(self, answers, cost=0.05):
        self.answers, self.cost, self.n = answers, cost, 0

    def ask(self, who, q, thread=None, mode=None, source=None):
        assert source == "eval"                                             # test mode: reads everything, saves nothing
        self.n += 1
        return {"answer": self.answers(q), "cost_usd": self.cost}


def _post(verdict):
    return lambda url, headers, body: {"content": [{"type": "text", "text": json.dumps(verdict)}], "usage": {"input_tokens": 900, "output_tokens": 40}}


def test_a_run_marks_counts_costs_and_stops_at_the_budget(tmp_path, monkeypatch):
    bank = {"questions": [{"id": "value", "name": "the book's value", "q": "What is the book worth?", "mark": "code:value", "core": True},
                          {"id": "short", "name": "no short selling", "q": "Can it sell short?", "mark": "code:short", "core": True},
                          {"id": "why", "name": "why buying is off", "q": "Why is buying off?", "mark": "grader", "must": ["names the 50-day average"], "core": True},
                          {"id": "window", "name": "the window", "q": "Which day is it?", "mark": "code:window", "core": True}]}
    (tmp_path / "bank.json").write_text(json.dumps(bank))
    monkeypatch.setattr(N, "BANK", tmp_path / "bank.json")
    monkeypatch.setattr(N, "OUT", tmp_path / "out")
    monkeypatch.setattr(N, "truth", lambda j: T)
    said = {"What is the book worth?": "C$439.49.", "Can it sell short?": RIGHT["short"], "Why is buying off?": "Bitcoin is under its 50-day average.", "Which day is it?": RIGHT["window"]}
    a = _Ask(lambda q: said[q])
    out = N.run(None, ask=a, post=_post({"ok": True, "why": ""}), day="2026-11-11", budget=1.0, file_flags=False)
    assert (out["asked"], out["right"], [w["id"] for w in out["wrong"]], out["ungraded"]) == (4, 3, ["value"], 0)
    assert out["line"] == "Night test: 3 of 4 answers right. Wrong: the book's value."
    assert out["cost_answers_usd"] == 0.2 and 0 < out["cost_grader_usd"] < 0.01 and not out["stopped_for_budget"]
    st = json.loads((tmp_path / "out" / "crypto_state.json").read_text())
    assert st["value"]["failed"] and st["value"]["streak"] == 0 and st["short"]["streak"] == 1
    assert json.loads((tmp_path / "out" / "crypto_latest.json").read_text())["day"] == "2026-11-11"
    # the budget: two answers at $0.05 reach $0.10 and the run stops there, saying how many were not asked
    out = N.run(None, ask=_Ask(lambda q: said[q]), post=_post({"ok": True}), day="2026-11-12", budget=0.10, file_flags=False)
    assert out["asked"] == 2 and out["stopped_for_budget"] and out["not_asked"] == 2 and "Stopped at the night's budget ($0.10) with 2 not asked" in out["line"]
    # the answer is repaired: three right nights in a row and the question is no longer on watch
    said["What is the book worth?"] = RIGHT["value"]
    for d in ("13", "14", "15"):
        N.run(None, ask=_Ask(lambda q: said[q]), post=_post({"ok": True}), day=f"2026-11-{d}", budget=1.0, file_flags=False)
    st = json.loads((tmp_path / "out" / "crypto_state.json").read_text())
    assert st["value"]["failed"] is False and st["value"]["fixed_on"] == "2026-11-15"


def test_the_grader_marks_wrong_and_an_unreadable_grader_is_not_a_verdict(tmp_path, monkeypatch):
    q = {"id": "why", "q": "Why is buying off?", "mark": "grader", "must": ["names the 50-day average"]}
    seen = {}

    def post(url, headers, body):
        seen.update(body)
        return {"content": [{"type": "text", "text": '```json\n{"ok": false, "why": "it never names the 50-day average"}\n```'}], "usage": {"input_tokens": 1000, "output_tokens": 30}}

    g = N.grade(q, T, "Because the market is weak.", post=post)
    assert g["ok"] is False and "50-day" in g["why"] and g["cost_usd"] > 0
    assert "haiku" in seen["model"] and "names the 50-day average" in seen["messages"][0]["content"] and '"value_cad": 467.55' in seen["messages"][0]["content"]
    assert N.grade(q, T, "x", post=lambda *a: {"content": [{"type": "text", "text": "I think it is fine."}], "usage": {}})["ok"] is None

    def down(*a):
        raise RuntimeError("503")

    assert N.grade(q, T, "x", post=down)["ok"] is None


def test_one_answer_can_carry_several_marks_and_names_the_one_it_missed():
    q = {"id": "account", "q": "x", "mark": "code:value+cash+return+closed+holdings"}
    good = "It is worth C$467.55: C$467.55 in cash and no coins. It is down 6.5%. It has closed 9 trades and one made money. It holds no coins."
    m = N.mark(q, T, good)
    assert m["ok"] and m["marks"] == 5 and m["by"] == "code" and m["cost_usd"] == 0.0
    m = N.mark(q, T, good.replace("one made money", "four made money"))
    assert not m["ok"] and m["why"] == "wrong or missing: closed (wanted 9 closed, 1 made money)"


def test_the_today_card_says_the_night_in_points_and_the_start_never_runs_inside_a_test(monkeypatch):
    from jarvis.service import surfaces, universe_watch

    monkeypatch.setattr(N, "latest", lambda: None)
    assert surfaces._night_test() is None                                     # no run yet: no card
    monkeypatch.setattr(N, "latest", lambda: {"day": "2026-11-11", "asked": 5, "right": 4, "ungraded": 0, "cost_usd": 0.27, "look": [{"id": "x"}],
                                              "wrong": [{"id": "dial", "name": "the dial and what turns buying on", "why": "wrong or missing: reopen (wanted a close above the 50-day)"}]})
    c = surfaces._night_test()
    assert c["kind"] == "nighttest" and c["points"][0] == "4 of 5 answers were right on 11 Nov"
    assert c["points"][1].startswith("Wrong: the dial and what turns buying on") and c["points"][-1] == "The test cost $0.27"
    assert universe_watch.start_night_test(None) is False                     # under a test run nothing is started
