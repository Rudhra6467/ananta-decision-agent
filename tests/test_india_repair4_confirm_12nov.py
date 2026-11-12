"""12 Nov 2026, audit repair 4's confirm check (~/ananta_runs/keen_audit/recheck/pkg4_confirm.md), the India app's side:
C2, the portfolio chart's words gave the managed book's +15.87% with no word that about 12.9 points are the options line's paper result or
    that a trade is left out;
C3, How it compares, the Today card's point and the voice's comparison carry the options result but never said a trade is left out;
C4, after its option expired, the options line's record still said the trade had "no result yet";
C6, the comparison alone read the home folder's data, whatever folder the India screens were set to.
Each check failed against the code before (d2f6c33). No live data: the files are made here."""
import json

from jarvis import placekit as K
from jarvis.india import ask as IA
from jarvis.india import compare, views
from jarvis.india import surfaces as IS

NOTE = {"kind": "outcome", "date": "2026-11-06", "index": "BANKNIFTY", "point": "D0", "action": 10,
        "note": "the study's outcome is not defined for this day (e.g. NEXTOPEN with no usable next session)"}
DECISION = {"kind": "decision", "date": "2026-11-06", "index": "BANKNIFTY", "contracts": {"option": {"expiry": "2026-11-23"}}}


def _folder(tmp_path, noted: bool = True):
    for sub in ("account", "managed", "sp1"):
        (tmp_path / "paper" / sub).mkdir(parents=True, exist_ok=True)
    (tmp_path / "paper" / "account" / "view.json").write_text(json.dumps({"benchmark": {"managed_start_day": "2026-10-30", "managed_sessions": 9}}))
    rows = [{"day": "2026-10-29", "frozen_inr": 160000, "nifty500_ret_pct": 0.0},
            {"day": "2026-10-30", "frozen_inr": 160000, "nifty500_ret_pct": 0.5, "managed_inr": 160499, "managed_ret_pct": 0.0},
            {"day": "2026-11-11", "frozen_inr": 169440, "nifty500_ret_pct": 9.0, "managed_ret_pct": 17.88, "managed_inr": 189196,
             "managed_options_inr": 24391, "managed_sessions": 9, "frozen_ret_pct": 5.9}]
    (tmp_path / "paper" / "account" / "benchmark.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    (tmp_path / "paper" / "account" / "frozen.json").write_text(json.dumps({"day": "2026-10-29", "cash_inr": 20000, "options_inr": 50000}))
    (tmp_path / "paper" / "managed" / "view.json").write_text(json.dumps({"stocks_inr": 100000, "value_inr": 189196}))
    (tmp_path / "paper" / "sp1" / "outcomes.jsonl").write_text(json.dumps(NOTE) + "\n" if noted else "")
    (tmp_path / "paper" / "sp1" / "decisions.jsonl").write_text(json.dumps(DECISION) + "\n")
    return tmp_path


def test_how_it_compares_says_the_trade_it_leaves_out_and_reads_the_screens_folder(tmp_path, monkeypatch):
    # C3 and C6
    _folder(tmp_path)
    sw = compare.same_window(tmp_path)
    assert sw["left_out"] == 1 and sw["left_out_words"] == "1 options trade left out"
    assert sw["options_words"] == ("The book counts the options line's result (+₹24,391, about 15.2 points); with options flat, like yours, "
                                   "+2.68%; 1 options trade left out.")
    assert len(sw["options_words"].split()) <= K.MAX["page_line"] and sw["options_words"] in sw["words"]
    monkeypatch.setattr(views, "DATA", tmp_path)                                     # the folder the India screens read
    monkeypatch.setattr(IS, "DATA", tmp_path)
    assert compare.same_window()["managed_pct"] == 17.88                             # it read the home folder's copy, whatever was set
    # nothing left out: the words as before
    _folder(tmp_path, noted=False)
    sw = compare.same_window(tmp_path)
    assert sw["left_out"] == 0 and sw["left_out_words"] == "" and sw["options_words"].endswith("with its options flat, as yours are, it is +2.68%.")


def test_the_today_card_and_the_voice_say_the_trade_left_out_with_the_comparison(tmp_path, monkeypatch):
    # C3
    _folder(tmp_path)
    monkeypatch.setattr(views, "DATA", tmp_path)
    monkeypatch.setattr(IS, "DATA", tmp_path)
    pts = IS._holdings_points([], {})
    assert pts[0] == ("Since 30 Oct: managed +17.88% (+2.68% with its options flat, as yours; 1 options trade left out) · your holdings +5.90% · "
                      "Nifty 500 +8.46%")
    monkeypatch.setattr(IA, "DATA", tmp_path)
    b = IA._books_benchmark()
    assert b["left_out_words"] == "1 options trade left out" and "when left_out_words is given, say it with the managed figure" in b["how"]


def test_the_portfolio_charts_words_say_the_options_result_and_the_trade_left_out(tmp_path):
    # C2
    _folder(tmp_path)
    w = IS.portfolio_chart(tmp_path)["words"]
    assert ("+17.88% since it started on Fri 30 Oct (9 sessions). Of that, about 15.2 points are the options line's paper result; with its "
            "options flat, like the untouched holdings, +2.68%; 1 options trade left out. From the snapshot") in w


def test_after_its_option_expires_the_options_lines_record_says_never_scored(tmp_path, monkeypatch):
    # C4: "Not in these figures: 1 trade with no result yet" after the contract had expired
    _folder(tmp_path)
    monkeypatch.setattr(IS, "DATA", tmp_path)
    (tmp_path / "paper" / "sp1" / "book.json").write_text(json.dumps({"updated": "2026-11-23T17:30:07+05:30", "sessions": 14,
                                                                       "by_index": {"BANKNIFTY": {"trades": 9, "option_1lot_rs_realistic_fill": 10000.0}}}))
    monkeypatch.setattr(IS, "_today_ist", lambda: "2026-11-24", raising=False)
    cl = [{"name": "the options line", "done": 10, "so_far": "x"}]
    IS._sp1_clock(cl)
    assert "Not in these figures: 1 trade (Fri 6 Nov Bank Nifty, never scored (its option expired Mon 23 Nov))." in cl[0]["so_far"]
    assert "no result yet" not in cl[0]["so_far"]
    assert IS.sp1_left_out_words() == "1 trade left out: Fri 6 Nov Bank Nifty, never scored (its option expired Mon 23 Nov)"
    monkeypatch.setattr(IS, "_today_ist", lambda: "2026-11-13", raising=False)
    cl = [{"name": "the options line", "done": 10, "so_far": "x"}]
    IS._sp1_clock(cl)
    assert "Not in these figures: 1 trade (Fri 6 Nov Bank Nifty, not scored yet)." in cl[0]["so_far"]
