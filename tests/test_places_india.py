"""India's places in the redesign (Madhav, 10 Nov 2026: "yes for all your recommendations"; India screens included, screens only): the same
eight rules, the same tap-through and the same coverage as crypto (tests/test_places.py), from fixed inputs. And the fault found while
building them: after midnight IST, before the next open, the Nifty box said "0 (0.0%)" for the last session."""
import datetime as dt
import json

import pytest

from jarvis import placekit as K
from jarvis.india import livesession as L
from jarvis.india import places as IP
from jarvis.india import surfaces as IS
from jarvis.india import views
from tests.test_places import _check_taps

UTC = dt.timezone.utc
HOLD = [{"symbol": "TATAPOWER", "value_inr": 28080, "weight_pct": 23.9, "pnl_pct": 29.4, "grade": "B", "action": "hold", "suggest_inr": 0, "why": "Fine (66/100).", "wrong_if": "it closes under ₹357"},
        {"symbol": "JIOFIN", "value_inr": 27370, "weight_pct": 23.3, "pnl_pct": -15.4, "grade": "C", "action": "trim", "suggest_inr": 9700,
         "why": "Middling (51/100) but 23% of your stocks, -15% on what you paid: more than a middling stock should be. Trim it.", "wrong_if": "it climbs back above ₹238"},
        {"symbol": "LICI", "value_inr": 17567, "weight_pct": 14.9, "pnl_pct": 3.7, "grade": "B", "action": "hold", "suggest_inr": 0, "why": "Fine.", "wrong_if": "x"},
        {"symbol": "IDEA", "value_inr": 1395, "weight_pct": 1.2, "pnl_pct": 13.2, "grade": "A", "action": "tidy", "suggest_inr": 1400, "why": "Only ₹1,395: too small to matter.", "wrong_if": "you want it"}]
MONEY = {"value_inr": 164725, "stocks_inr": 87111, "options_inr": 50000, "cash_inr": 27614, "holdings": HOLD,
         "books": [{"id": "yours", "label": "As you have it", "ret_pct": 5.27}, {"id": "managed", "label": "Managed", "ret_pct": 2.63}, {"id": "index", "label": "Nifty 500", "ret_pct": 7.41}],
         "clock": {"sessions": 6, "of": 60, "words": "Session 6 of 60", "since": "2026-10-29"},
         "plan": {"for_session": "2026-11-11", "brief": "No change on Wednesday: the managed book has nothing new to cut or buy.", "words": "No change for Wednesday 11 Nov.", "cuts": 0, "buys": [], "no_change": True},
         "managed": {"value_inr": 164725, "return_pct": 2.63, "replacements": [{"symbol": "ETERNAL", "for_cut": "TATAPOWER", "value_inr": 10904, "pnl_pct": 5.8}]},
         "options_book": {"set_aside_inr": 50000, "pnl_inr": 7154.0, "sessions": 11, "open": [], "open_words": "No open option positions", "words": "One lot a session.",
                          "by_index": [{"index": "NIFTY", "trades": 2, "rupees": 12406.0}, {"index": "BANKNIFTY", "trades": 10, "rupees": -5252.0}]},
         "options": {"words": "₹50,000 is set aside for options."}}
TODAY = {"session": "2026-11-09", "decision": MONEY["plan"]["brief"], "decision_source": "From the plan written Mon 9 Nov", "running": {"ok": True, "words": "Everything is running"},
         "tiles": [{"id": "market", "pages": [{"label": "Nifty 50", "value": "25,045", "tone": "good", "sub": "+58 (+0.2%)", "sub2": "Mon 9 Nov close"},
                                              {"label": "Bank Nifty", "value": "59,741", "tone": "good", "sub": "+891 (+1.5%)", "sub2": "Mon 9 Nov close"}]}],
         "cards": [{"kind": "close", "points": ["Nifty 25,045 (+0.2%) · Bank Nifty 59,741 (+1.5%) · VIX 17.4"]}]}
MORNING = {"session_words": "9 Nov", "view": ["US: the S&P 500 closed +0.3% (6 Nov), the Nasdaq +1.4%.",
                                              "Nifty closed at 25,030 on 6 Nov (+2.0%), in an uptrend: +7.7% against its ten-week average; 60% of the 250 most-traded stocks are above their long-term average.",
                                              "Yesterday foreign institutions bought ₹13,750 crore and domestic institutions sold ₹5,969 crore."], "chances": [], "watch": []}
PROOF = {"studies": {"run": 1440, "held_up": 44, "conditional": 38}, "exam": {"words": "The India exam (weekly, last run 2026-11-05): FAIL."},
         "clocks": [{"name": "the managed book (cuts replaced on paper)", "done": 6, "need": 60, "finish_words": "Fri 22 Jan 2027"}],
         "missed": {"words": "Of the day's 26 biggest rises it held 14."}, "last_night": {"words": "9 Nov: Nifty in an uptrend."},
         "links": [{"label": "Teachers, tested", "route": "/teachers"}, {"label": "The repair board", "route": "/flags"}]}


@pytest.fixture()
def india(tmp_path, monkeypatch):
    monkeypatch.setattr(IS, "today", lambda full=True: json.loads(json.dumps(TODAY)))
    monkeypatch.setattr(IS, "money", lambda full=True: json.loads(json.dumps(MONEY)))
    monkeypatch.setattr(IS, "proof", lambda full=True: json.loads(json.dumps(PROOF)))
    monkeypatch.setattr(IS, "people", lambda full=True: {"people": [{"name": "Madhav", "relation": "owner", "can": "decides everything"}], "invite": "An invited person is onboarded."})
    monkeypatch.setattr(IS, "_managed", lambda: {"start_inr": 160499, "start_day": "2026-10-30", "positions": 11})
    monkeypatch.setattr(IS, "portfolio_chart", lambda data=None: {"chart": {"dates": ["2026-10-30", "2026-11-09"], "managed": [160558, 164725]}})
    monkeypatch.setattr(views, "morning", lambda: json.loads(json.dumps(MORNING)))
    monkeypatch.setattr(IP, "_clk", lambda: {"state": "before_open", "latest_session": "2026-11-09", "next_session": "2026-11-11", "today_india": "2026-11-11"})
    monkeypatch.setattr(IP, "_spark", lambda key: [1.0, 2.0, 3.0])
    from jarvis.service import places as CP
    monkeypatch.setattr(CP, "change_rows", lambda market, since: [])
    (tmp_path / "paper" / "managed").mkdir(parents=True)
    (tmp_path / "paper" / "sp1").mkdir(parents=True)
    day = (dt.date.today() - dt.timedelta(days=1)).isoformat()
    (tmp_path / "paper" / "managed" / "ledger.jsonl").write_text(json.dumps({"for_session": day, "side": "BUY", "symbol": "ETERNAL", "for_cut": "TATAPOWER", "qty": 30, "price": 343.64,
                                                                             "value_inr": 10309.3, "cost_inr": 12.2, "gap_pct": -0.1, "stop": 319.59, "filled": True, "why": "replaces TATAPOWER"}) + "\n")
    (tmp_path / "paper" / "managed" / "plans.jsonl").write_text(json.dumps({"written_day": day, "for_session": day, "no_change": True, "words": "No change for the session.", "rules": "managed-v1"}) + "\n")
    (tmp_path / "paper" / "sp1" / "outcomes.jsonl").write_text(json.dumps({"date": day, "index": "BANKNIFTY", "dir": -1, "exit": "ATRSTOP",
                                                                           "legs": {"option": {"tradingsymbol": "BANKNIFTY26NOV59100PE", "lot": 30.0, "entry_realistic": 797.6, "exit": 602.4, "net_rs_realistic": -6053.6}}}) + "\n")
    monkeypatch.setattr(IS, "DATA", tmp_path)
    return tmp_path


@pytest.mark.parametrize("name", sorted(IP.PLACES))
def test_every_india_place_keeps_the_rules_and_every_tap_goes_somewhere(india, name):
    p = IP.PLACES[name](full=True)
    assert K.problems(name, p) == []
    assert _check_taps(p, set(IP.PLACES) | {"needs", "notices", "openlist"}) == []


def test_india_home_and_what_moved_down_a_level(india):
    h = IP.home()
    hero = next(p for p in h["parts"] if p["t"] == "hero")
    assert hero["value"] == "₹1,64,725" and hero["tone"] == "good"
    today = next(p for p in h["parts"] if p["t"] == "today")
    assert today["line"] == "No change on Wednesday." and today["label"] == "Before the open · Wed 11 Nov"
    assert any(p["t"] == "needs" for p in h["parts"])                       # the open list fills it (/v3/place/needs)
    box = next(p for p in h["parts"] if p["t"] == "boxes")["items"][0]
    assert box["change"] == "+0.2%" and box["since"] == "Mon 9 Nov"
    did = json.dumps(next(p for p in h["parts"] if p.get("title") == "What Ananta did"), ensure_ascii=False)
    assert "Options · Bank Nifty short" in did and "−₹6,054" in did
    # coverage: holdings with grade and action, the replacements, the options book, the plan
    acct = json.dumps(IP.account(), ensure_ascii=False)
    for fact in ("Tata Power", "Jio Financial", "Eternal", "+₹7,154", "Session 6 of 60: too early", "+5.27%", "+7.41%"):
        assert fact in acct, fact
    page = IP.holding_page(HOLD[1])
    assert any("₹9,700" in i["text"] for p in page["parts"] if p["t"] == "points" for i in p["items"])
    assert K.nwords(next(p for p in page["parts"] if p["t"] == "line")["text"]) <= 22


def _stub(syms):
    # Wednesday 00:10 IST, before the open: Kite has rolled the day over, so each index is the last close against itself
    table = {"NSE:NIFTY 50": (25044.65, 25044.65), "NSE:NIFTY BANK": (59741.25, 59741.25), "NSE:INDIA VIX": (17.42, 17.42)}
    return {s: {"last_price": table[s][0], "ohlc": {"open": table[s][0], "high": table[s][0], "low": table[s][0], "close": table[s][1]}} for s in syms if s in table}


def test_before_the_open_the_index_box_keeps_the_last_sessions_change(tmp_path, monkeypatch):
    monkeypatch.setattr(L, "DATA", tmp_path)
    (tmp_path / "manifests").mkdir()
    (tmp_path / "manifests" / "technicals.json").write_text(json.dumps({"indices": {"NIFTY 50": {"close": 25044.65, "prev_close": 24986.4, "as_of": "2026-11-09"},
                                                                                     "NIFTY BANK": {"close": 59741.25, "prev_close": 58850.65, "as_of": "2026-11-09"}}}))
    L._CACHE.clear()
    clk = L.clock("2026-11-09", dt.datetime(2026, 11, 10, 18, 40, tzinfo=UTC))          # Wed 11 Nov 00:10 IST (Tue 10 Nov was a holiday)
    assert clk["state"] == "before_open"
    i = L.index_now(clk, _stub)
    assert i["rows"]["NIFTY 50"]["change_pct"] == 0.23 and "0.0%" not in i["words"] and "Monday 9 Nov" in i["words"]
    L._CACHE.clear()
