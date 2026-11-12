"""12 Nov 2026, the outside check of audit repair 4 (~/ananta_runs/keen_audit/recheck/pkg4_check.md): its new finds on the India app's
side. N1 the stocks' own line took the options line's result for stock gains; N2 How it compares said the book's figure with the options
result in it beside holdings that keep theirs flat, and no word said so; N3 Ananta's own book check would cry a false alarm every day;
N4 the totals that carry the options result never said a trade is left out (Madhav's G-01: every total does); N5 "the line's value" had
two meanings; N8 three readers still gave Rs 50,000 as the options part; N10 a weekly option had no strike or expiry; N12 a trade whose
option expired still said "not scored yet"; and Markets still said "Your holdings". Each check failed against the code before (b3c4032).
No live data: the files are made here."""
import datetime as dt
import json

from jarvis import placekit as K
from jarvis.india import ask as IA
from jarvis.india import compare, selfparts
from jarvis.india import places as IP
from jarvis.india import surfaces as IS
from tests.test_places_india import MONEY, india

_FIXTURES = (india,)                                                                     # the places fixture, used by name below
SAID = "Options count at ₹50,000 set aside and +₹33,000 from 2 trades since the book began (30 Oct)."
NOTE = {"kind": "outcome", "date": "2026-11-06", "index": "BANKNIFTY", "point": "D0", "action": 10,
        "note": "the study's outcome is not defined for this day (e.g. NEXTOPEN with no usable next session)"}


def _money(monkeypatch):
    mo = json.loads(json.dumps(MONEY))
    mo.update({"value_inr": 87111 + 83000 + 27614, "options_value_inr": 83000, "options_result_inr": 33000, "options_counted": SAID})
    monkeypatch.setattr(IS, "money", lambda full=True: json.loads(json.dumps(mo)))
    return mo


def _note(india):
    with (india / "paper" / "sp1" / "outcomes.jsonl").open("a") as f:
        f.write(json.dumps(NOTE) + "\n")


# ------------------------------------------------------------------------------------------------ N1: the stocks' own line
def test_the_stocks_line_takes_the_options_result_out_with_the_money_set_aside(india, monkeypatch):
    (india / "paper" / "managed" / "ledger.jsonl").write_text("")                         # no fills: the cash stays as it is
    (india / "paper" / "account").mkdir(parents=True, exist_ok=True)
    rows = [{"day": "2026-11-02", "managed_inr": 50000 + 20000 + 100000 + 429, "managed_options_inr": 429},
            {"day": "2026-11-03", "managed_inr": 50000 + 20000 + 101000 + 5429, "managed_options_inr": 5429}]
    (india / "paper" / "account" / "benchmark.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    monkeypatch.setattr(IP.views, "DATA", india)
    monkeypatch.setattr(IS, "_managed", lambda: {"cash_inr": 20000, "options_inr": 50000, "stocks_inr": 101000, "day": "2026-11-03",
                                                 "start_day": "2026-10-30", "start_inr": 160499, "positions": 11})
    assert IP.stock_points() == [("2026-11-02", 100000), ("2026-11-03", 101000)]      # it read 100,429: the options' gain as the stocks'


# ------------------------------------------------------------------------------------------------ N2: How it compares, like for like
def test_how_it_compares_says_the_options_result_is_in_the_books_figure(tmp_path):
    (tmp_path / "paper" / "account").mkdir(parents=True)
    (tmp_path / "paper" / "managed").mkdir(parents=True)
    (tmp_path / "paper" / "account" / "view.json").write_text(json.dumps({"benchmark": {"managed_start_day": "2026-10-30", "managed_sessions": 9}}))
    rows = [{"day": "2026-10-29", "frozen_inr": 160000, "nifty500_ret_pct": 0.0},
            {"day": "2026-10-30", "frozen_inr": 160000, "nifty500_ret_pct": 0.5},
            {"day": "2026-11-11", "frozen_inr": 169440, "nifty500_ret_pct": 9.0, "managed_ret_pct": 17.88, "managed_inr": 189196,
             "managed_options_inr": 24391, "managed_sessions": 9}]
    (tmp_path / "paper" / "account" / "benchmark.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    (tmp_path / "paper" / "account" / "frozen.json").write_text(json.dumps({"cash_inr": 20000, "options_inr": 50000}))
    (tmp_path / "paper" / "managed" / "view.json").write_text(json.dumps({"stocks_inr": 100000, "value_inr": 189196}))
    sw = compare.same_window(tmp_path)
    assert sw["managed_pct"] == 17.88 and sw["managed_like_for_like_pct"] == 2.68
    assert sw["options_words"] == "The book counts the options line's result (+₹24,391, about 15.2 points); with its options flat, as yours are, it is +2.68%."
    assert len(sw["options_words"].split()) <= K.MAX["page_line"] and sw["options_words"] in sw["words"]


def test_the_account_page_says_it_under_how_it_compares(india, monkeypatch):
    mo = json.loads(json.dumps(MONEY))
    mo["books_options"] = "The book counts the options line's result (+₹24,391, about 15.2 points); with its options flat, as yours are, it is +2.68%."
    monkeypatch.setattr(IS, "money", lambda full=True: json.loads(json.dumps(mo)))
    page = IP.account()
    assert any(p.get("t") == "line" and p.get("text") == mo["books_options"] for p in page["parts"]) and K.problems("account", page) == []


# ------------------------------------------------------------------------------------------------ N3: Ananta's own book check
def test_the_book_check_counts_the_options_line_as_the_value_does(tmp_path):
    d = tmp_path / "paper" / "managed"
    d.mkdir(parents=True)
    (d / "state.json").write_text(json.dumps({"positions": {"TATAPOWER": {"qty": 10, "last": 100.0, "source": "twin"}}, "cash_inr": 1000.0,
                                              "options_inr": 50000.0, "trades": [], "costs_inr": 0.0}))
    (d / "view.json").write_text(json.dumps({"value_inr": 1000 + 50000 + 1000 + 24391, "options_result_inr": 24391}))
    assert selfparts.managed_book_check(tmp_path / "paper") == []                         # it cried "the two disagree" every day
    (d / "view.json").write_text(json.dumps({"value_inr": 1000 + 50000 + 1000 + 24391 + 500, "options_result_inr": 24391}))
    assert "the two disagree" in selfparts.managed_book_check(tmp_path / "paper")[0]["what"]   # a real gap still rings


# ------------------------------------------------------------------------------------------------ N4 and N5: a total says what it leaves out
def test_every_total_with_the_options_result_says_the_trade_it_leaves_out(india, monkeypatch):
    _money(monkeypatch)
    home = IP.home()
    box = next(p for p in home["parts"] if p.get("t") == "boxes")["items"][1]["pages"][1]
    assert box["caption"] == "Since the book began"                                       # it said "At the line's value", a second meaning
    _note(india)
    home = IP.home()
    box = next(p for p in home["parts"] if p.get("t") == "boxes")["items"][1]["pages"][1]
    hero = next(p for p in home["parts"] if p.get("t") == "hero")
    assert box["caption"] == "1 options trade left out" and hero["since"].endswith("; 1 options trade left out")
    page = IP.account()
    assert next(p for p in page["parts"] if p.get("t") == "hero")["since"].endswith("; 1 options trade left out")
    assert next(p for p in page["parts"] if p.get("t") == "split")["parts"][1]["label"] == "Options, since the book began"
    assert K.problems("home", home) == [] and K.problems("account", page) == []


def test_the_voice_gives_the_options_part_at_the_lines_value_and_the_trade_left_out(india, monkeypatch):
    _note(india)
    monkeypatch.setattr(IA, "DATA", india)
    (india / "paper" / "managed" / "view.json").write_text(json.dumps({"value_inr": 197725, "return_pct": 23.2, "stocks_inr": 87111, "options_inr": 50000,
                                                                       "options_value_inr": 83000, "options_counted": SAID, "cash_inr": 27614,
                                                                       "positions": 11, "day": "2026-11-11"}))
    a = IA._account_value()
    assert a["options_inr"] == 83000 and a["stocks_inr"] + a["options_inr"] + a["cash_inr"] == a["value_inr"]   # it gave 50,000: no sum
    assert a["options_set_aside_inr"] == 50000 and a["options_counted"] == SAID
    assert a["left_out"].startswith("1 trade left out: Fri 6 Nov Bank Nifty")


# ------------------------------------------------------------------------------------------------ N8: the tiles' options part
def test_the_account_tile_gives_the_options_part_at_the_lines_value():
    mb = {"value_inr": 197725, "stocks_inr": 87111, "cash_inr": 27614, "options_inr": 50000, "options_value_inr": 83000, "positions": 11}
    t = IS._account_tile(mb, {}, None)
    assert t["pages"][1]["value"] == IS._inr(83000)                                       # it said ₹50,000 beside a total holding 83,000


# ------------------------------------------------------------------------------------------------ N10: a weekly option's strike and expiry
def test_a_weekly_option_says_its_strike_and_expiry_day():
    weekly = {"index": "NIFTY", "legs": {"option": {"tradingsymbol": "NIFTY26N0323300CE", "lot": 75, "entry_realistic": 94.0}}}
    assert IP._option_bought(weekly) == ("Nifty call", "23,300, expiring 3 Nov, paid ₹7,050")
    monthly = {"index": "BANKNIFTY", "legs": {"option": {"tradingsymbol": "BANKNIFTY26NOV59100PE", "lot": 30, "entry_realistic": 797.6}}}
    assert IP._option_bought(monthly)[1].startswith("59,100 Nov, paid ")


# ------------------------------------------------------------------------------------------------ N12: after its option expired
def test_a_trade_left_out_after_its_option_expired_says_it_was_never_scored(india):
    _note(india)
    today = dt.date.today()
    gone, live = (today - dt.timedelta(days=2)).isoformat(), (today + dt.timedelta(days=30)).isoformat()
    dec = lambda exp: {"kind": "decision", "date": "2026-11-06", "index": "BANKNIFTY", "contracts": {"option": {"expiry": exp}}}   # noqa: E731
    (india / "paper" / "sp1" / "decisions.jsonl").write_text(json.dumps(dec(live)) + "\n")
    assert IS.sp1_left_out_words() == "1 trade left out: Fri 6 Nov Bank Nifty, not scored yet"
    (india / "paper" / "sp1" / "decisions.jsonl").write_text(json.dumps(dec(gone)) + "\n")
    assert IS.sp1_left_out_words() == f"1 trade left out: Fri 6 Nov Bank Nifty, never scored (its option expired {IS._dw(gone)})"


# ------------------------------------------------------------------------------------------------ item 3's small thing: one name on Markets
def test_markets_names_the_real_holdings_as_account_and_your_stocks_do(india):
    titles = [p.get("title") for p in IP.markets()["parts"] if p.get("t") == "rows"]
    assert "Your Zerodha holdings" in titles and "Your holdings" not in titles
