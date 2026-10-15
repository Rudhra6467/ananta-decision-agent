"""Fix A7 (Oct 15): every exam run asks two market questions twice, minutes apart; a material flip without a stated reason fails it."""
from jarvis.service import exam


def _spec(cid):
    return next(c for c in exam.CONSISTENCY if c[0] == cid)


def test_labels_and_flips_are_judged_by_code():
    _, _, how_b, pats_b = _spec("can_buy")
    _, _, how_v, pats_v = _spec("view")
    assert exam.label("Yes. The dial is open, so buying is allowed; no setup has fired yet.", how_b, pats_b) == "YES"
    assert exam.label("No: the dial is closed, cash is the position.", how_b, pats_b) == "NO"
    assert exam.label("It depends on the setups.", how_b, pats_b) == "UNCLEAR"
    assert exam.label("Constructive: an uptrend with broad strength.", how_v, pats_v) == "UP"
    assert exam.label("Cautious: weak breadth and a pullback.", how_v, pats_v) == "DOWN"
    assert exam.label("Higher highs but weak breadth.", how_v, pats_v) == "MIXED"
    same = exam.judge_pair("Yes, the dial is open.", "Yes, buying is allowed.", how_b, pats_b)
    assert same["ok"] and not same["flip"]
    flip = exam.judge_pair("Yes, the dial is open.", "No, stay in cash.", how_b, pats_b)
    assert flip["flip"] and not flip["ok"]
    excused = exam.judge_pair("Yes, the dial is open.", "No: the dial changed at the new daily close, so no new buys.", how_b, pats_b)
    assert excused["flip"] and excused["excused"] and excused["ok"]
    assert not exam.judge_pair("Constructive uptrend.", "Higher prices but weak breadth.", how_v, pats_v)["flip"]   # MIXED is no flip


def test_each_pair_is_asked_first_and_last_and_an_unexplained_flip_fails(tmp_path, monkeypatch):
    monkeypatch.setattr(exam, "OUT", tmp_path)                 # never touch the real exam files
    asked = []

    class FakeAsk:
        def ask(self, who, q, thread=None, mode=None, source=None):
            asked.append(q)
            n = asked.count(q)
            if q.startswith("Can we buy"):
                return {"answer": "Yes, the dial is open." if n == 1 else "No, stay in cash."}
            if q.startswith("In one or two sentences"):
                return {"answer": "Constructive: an uptrend."}
            return {"answer": "I don't know."}
    out = exam.run(None, ask=FakeAsk())
    assert len(asked) == 2 + len(exam.KNOWS) + len(exam.UNKNOWNS) + len(exam.WHY) + 2
    assert asked[0].startswith("Can we buy") and asked[-1].startswith("In one or two sentences")
    assert out["consistent_of"] == 2 and out["consistent"] == 1 and out["flipped"] == 1
    assert out["consistency_pass"] is False and out["exam_pass"] is False
    assert exam.flip_rate() == {"runs": 1, "pairs": 2, "flips": 1, "failed": 1, "rate": 0.5}
    rj = exam.rejudge()
    assert rj["consistent"] == 1 and rj["flipped"] == 1
    assert exam.flip_rate()["runs"] == 1                       # a rejudge is not a new run
