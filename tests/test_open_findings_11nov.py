"""11 Nov 2026 (Madhav: "i dont want to wait, when we have everything we need, just get it done"): the open findings of the earlier audits
that the records were enough to repair. One test per finding; nothing here calls a model or the network."""
import calendar
import json
import time
from pathlib import Path

from jarvis import selfcheck
from jarvis.india import ask, askprompt, livesession, selfparts
from jarvis.service import runcheck
from jarvis.service.runcheck_parts import PARTS


# ---------------------------------------------------------------- R-007: a greeting in front of another question
def test_a_greeting_before_another_question_is_answered_not_the_morning_view(monkeypatch):
    view = {"ready": True, "session": "2099-01-01", "session_words": "Thu 1 Jan", "view": ["The view."], "plan": ["The plan."],
            "chances": ["The chances."], "watch": ["The levels."]}
    monkeypatch.setattr(ask.views, "morning", lambda: view)
    assert ask.morning_flow("Good morning Ananta, what happened in the Indian market today and what did we do?", "owner") is None
    assert ask.morning_flow("Good morning, how are my holdings doing today?", "owner") is None
    assert ask.morning_flow("Good morning", "owner") is not None
    assert ask.morning_flow("Good morning Ananta", "owner") is not None
    assert "The plan." in ask.morning_flow("Good morning Ananta, what's the plan today?", "owner")["answer"]
    assert ask.morning_flow("morning view please", "owner") is not None


# ---------------------------------------------------------------- R-059, R-033, R-095: the live instructions
def test_the_instructions_say_points_why_it_moved_and_whose_rule():
    s = askprompt.SYSTEM_V2
    assert "1c. A recap asked for in points" in s and "a line break between them, no labels or marks" in s and "4 to 6 short lines" in s
    assert '1d. "Why did the index move"' in s and "breadth" in s
    assert '"The risk rule" or "the stop"' in s and "stops_whose" in s and "never one level alone" in s


# ---------------------------------------------------------------- the nudge names the other market's side
def test_the_nudge_names_the_side_of_the_other_markets_item(monkeypatch, tmp_path):
    item = {"market": "crypto", "severity": "high", "source": "lost-runs check",
            "what": "Explorer: a scan of all 10 coins every 15 minutes ran with an error at 10 Nov 19:45 Toronto"}
    monkeypatch.setattr(selfcheck, "check", lambda market, now=None: {"items": [item]})
    said = selfcheck.nudge("india", tmp_path / "india.json", "t1")
    assert "on the crypto side, Explorer: a scan" in said
    said = selfcheck.nudge("crypto", tmp_path / "crypto.json", "t1")
    assert "crypto side" not in said and "explorer: a scan" in said


# ---------------------------------------------------------------- the lost-runs check: one blip of a frequent part
NOW = calendar.timegm((2026, 11, 11, 12, 0, 0))


def _log(tmp: Path, special: dict) -> dict:
    paths = {k: str(tmp / k) for k in ("agent", "runs", "repo", "worker", "backups", "india")}
    for v in paths.values():
        Path(v).mkdir(parents=True, exist_ok=True)
    lines, t = [], NOW - 2 * 86400
    t -= t % 900
    while t <= NOW:
        scans, errs = special.get(t, (10, "[]"))
        lines.append(f"[{time.strftime('%Y-%m-%d %H:%M', time.gmtime(t + 60))}] scans={scans} open=0 pending=0 equity=1702.58 errors={errs}")
        t += 900
    Path(paths["runs"], "explorer_live.log").write_text("\n".join(lines) + "\n")
    return paths


def test_one_errored_scan_followed_by_a_clean_one_is_a_low_blip(tmp_path):
    part = dict(next(x for x in PARTS if x["id"] == "explorer_scans"))
    blip = NOW - 10 * 3600 - (NOW - 10 * 3600) % 900
    paths = _log(tmp_path, {blip: (9, "[\"XRP: HTTPConnectionPool(host='127.0.0.1', port=8001): Max retries exceeded\"]")})
    res = runcheck.run(paths, NOW, [part])
    ms = [m for m in res["windows"]["24h"]["misses"] if m["part"] == "explorer_scans"]
    assert len(ms) == 1 and ms[0]["kind"] == "errored"
    assert ms[0]["severity"] == "low" and "the next run was clean" in ms[0]["detail"]


def test_two_errored_scans_in_a_row_stay_high(tmp_path):
    part = dict(next(x for x in PARTS if x["id"] == "explorer_scans"))
    a = NOW - 10 * 3600 - (NOW - 10 * 3600) % 900
    paths = _log(tmp_path, {a: (9, "['XRP: refused']"), a + 900: (9, "['XRP: refused']")})
    res = runcheck.run(paths, NOW, [part])
    ms = [m for m in res["windows"]["24h"]["misses"] if m["part"] == "explorer_scans"]
    assert ms and all(m["severity"] == "high" for m in ms)


# ---------------------------------------------------------------- R-016: before the open, after the 08:00 IST booking
CLK = {"state": "before_open", "today_is_session": True, "today_india": "2026-11-12", "latest_session": "2026-11-11",
       "latest_session_words": "Wed 11 Nov", "next_session": "2026-11-12", "next_session_words": "Thu 12 Nov"}


def test_before_the_open_the_managed_book_says_its_plan():
    plan = {"for_session": "2026-11-12", "cuts": [{"symbol": "IDEA"}], "buys": [{"symbol": "ITC", "for_cut": "IDEA"}]}
    w = livesession.managed_today(CLK, plan)["words"]
    assert w.startswith("The managed book's plan for Thu 12 Nov") and "1 cuts and 1 buys" in w and "IDEA -> ITC" in w
    w = livesession.managed_today(CLK, {"for_session": "2026-11-12", "cuts": [], "buys": []})["words"]
    assert w.endswith("no change at the open.")


def test_before_the_open_the_practice_book_says_what_the_booking_left(tmp_path):
    (tmp_path / "decisions").mkdir()
    st = {"trades": {"a": {"book": "exec", "policy": "hold_20d", "status": "open", "campaign": "S1", "symbol": "SBIN", "last_date": "2026-11-11"},
                     "b": {"book": "exec", "policy": "hold_20d", "status": "closed", "campaign": "S1", "symbol": "TCS", "last_date": "2026-11-11"}},
          "decisions": {"2026-11-11": {"status": "pending"}}}
    (tmp_path / "state.json").write_text(json.dumps(st))
    (tmp_path / "decisions" / "2026-11-11.json").write_text(json.dumps({"signals": [{"symbol": "RAIN", "campaign": "S1"},
                                                                                     {"symbol": "ZZZ", "campaign": "CTL"}]}))
    r = livesession.practice_today(CLK, path=tmp_path / "state.json")
    assert "Wed 11 Nov session is booked" in r["words"] and "1 trades open" in r["words"]
    assert "RAIN" in r["words"] and "ZZZ" not in r["words"]


# ---------------------------------------------------------------- R-027: one start day on the account page
def test_the_account_page_says_one_start_day():
    src = Path(__file__).resolve().parents[1].joinpath("jarvis", "india", "places.py").read_text()
    assert "the same start as above (counted from the" in src


# ---------------------------------------------------------------- R-062: India's managed book against its own records
def _book(tmp: Path, value: float = 1650.0, led_extra: list | None = None, qty_itc: int = 3) -> Path:
    m = tmp / "paper" / "managed"
    m.mkdir(parents=True)
    trades = [{"plan": "mp-1", "day": "2026-11-02", "side": "SELL", "symbol": "IDEA", "qty": 10, "price": 10.0, "cost_inr": 1.0},
              {"plan": "mp-1", "day": "2026-11-02", "side": "BUY", "symbol": "ITC", "qty": 3, "price": 400.0, "cost_inr": 2.0}]
    st = {"cash_inr": 200.0, "options_inr": 50.0, "costs_inr": 3.0, "trades": trades,
          "positions": {"ITC": {"qty": qty_itc, "last": 400.0, "source": "managed"}, "JIOFIN": {"qty": 1, "last": 200.0, "source": "twin"}}}
    (m / "state.json").write_text(json.dumps(st))
    (m / "view.json").write_text(json.dumps({"value_inr": value}))
    led = [{**t, "filled": True} for t in trades] + (led_extra or [])
    (m / "ledger.jsonl").write_text("\n".join(json.dumps(x) for x in led) + "\n")
    return tmp / "paper"


def test_the_india_book_check_is_quiet_when_the_records_agree(tmp_path):
    assert selfparts.managed_book_check(_book(tmp_path)) == []


def test_the_india_book_check_names_each_disagreement(tmp_path):
    out = selfparts.managed_book_check(_book(tmp_path, value=1750.0, qty_itc=4,
                                             led_extra=[{"plan": "mp-2", "side": "BUY", "symbol": "LT", "qty": 2, "filled": True}]))
    words = " | ".join(x["what"] for x in out)
    assert "value reads Rs 1,750 but its cash, options money and holdings add up to Rs 2,050" in words
    assert "BUY 2 LT (mp-2)" in words
    assert "holds 4 ITC but its trades add up to 3" in words
    assert all(x["market"] == "india" and x["source"] == "India book check" for x in out)


def test_the_self_check_lists_the_india_book_check():
    assert "india_book" in dict(selfcheck.CHECKS) and selfcheck.SOURCE_CHECK["India book check"] == "india_book"


# ---------------------------------------------------------------- R-144 and R-149: the corrected nights, the like-for-like line
def test_the_corrected_nights_are_read_and_drawn():
    import sqlite3
    from types import SimpleNamespace
    from jarvis.service import surfaces
    db = sqlite3.connect(":memory:")
    j = SimpleNamespace(db=db)
    assert surfaces._night_fixes(j) == {}                      # no table: nothing corrected
    db.execute("CREATE TABLE book500_night_fixes (day TEXT PRIMARY KEY, add_cad REAL, in_coins INTEGER, why TEXT, t INTEGER, by TEXT)")
    db.execute("INSERT INTO book500_night_fixes VALUES ('2026-10-28', 27.36, 1, 'w', 0, 'b'), ('2026-11-06', 28.06, 0, 'w', 0, 'b')")
    assert surfaces._night_fixes(j) == {"2026-10-28": {"add_cad": 27.36, "in_coins": True}, "2026-11-06": {"add_cad": 28.06, "in_coins": False}}
    src = Path(surfaces.__file__).read_text()
    assert 'rec[close_day] = round(float(v) + (nf.get(str(day)[:10]) or {}).get("add_cad", 0.0), 2)' in src
    assert "nights before it are drawn with it put back" in src
    assert "Like for like (Bitcoin bought at the book's first NDAX price and held, in C$)" in src
    places = Path(surfaces.__file__).with_name("places.py").read_text()
    assert 'foot=((S._safe(S.like_for_like, j, default="") or "") + "Nothing is read into the gap before 14 Dec.").strip()' in places


# ---------------------------------------------------------------- R-034: the Nifty against a second source
def test_the_fact_map_checks_the_nifty_against_the_nightly_close(monkeypatch):
    from jarvis.india import factmap
    monkeypatch.setattr(ask, "latest_closes", lambda rm: {"NIFTY 50": {"date": "2026-11-11", "close": 25255.0, "source": "newer closes"}})
    t = {"clock": {"state": "closed", "latest_session": "2026-11-11", "latest_session_words": "Wed 11 Nov"},
         "index_now": {"kind": "close", "rows": {"NIFTY 50": {"last": 24986.0}}}}
    r = factmap.nifty_second_source(t, {})
    assert r["state"] == "FAIL" and "can agree and both be wrong" in r["words"]
    t["index_now"]["rows"]["NIFTY 50"]["last"] = 25255.4
    assert factmap.nifty_second_source(t, {})["state"] == "PASS"
    assert factmap.nifty_second_source({**t, "clock": {**t["clock"], "state": "open"}}, {}) is None
    assert factmap.nifty_second_source({**t, "clock": {**t["clock"], "latest_session": "2026-11-12"}}, {}) is None


# ---------------------------------------------------------------- R-147: the night's value against what the fills say it holds
def test_the_book_check_asks_whether_the_night_is_explained_by_its_holdings(tmp_path):
    import sqlite3
    db = tmp_path / "j.sqlite"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE book500_fills (t INTEGER, coin TEXT, side TEXT, qty REAL, px REAL, fee REAL, sleeve TEXT)")
    con.execute("CREATE TABLE book500 (k TEXT, v TEXT)")
    con.execute("CREATE TABLE officer_notes (day TEXT, facts TEXT)")
    t26, t28 = calendar.timegm((2026, 10, 26, 0, 5, 42)), calendar.timegm((2026, 10, 28, 0, 5, 52))
    con.executemany("INSERT INTO book500_fills VALUES (?,?,?,?,?,?,?)", [(t26, "ETH", "BUY", 0.008315, 3271.4, 0.05, "EDGE"),
                                                                       (t28, "ETH", "BUY", 0.009683, 3304.71, 0.06, "CORE")])
    con.execute("INSERT INTO book500 VALUES ('state', ?)", (json.dumps({"cash": 400.0, "pos": {"ETH": {"qty": 0.017998, "last": 3290.23}},
                                                                      "value": 459.22}),))
    facts = {"account": {"value_cad": 431.86, "cash_cad": 400.0, "last_step": "2026-10-28 00:05",
                         "positions": {"ETH": {"last_price_cad": 3290.23}}}}
    con.execute("INSERT INTO officer_notes VALUES ('2026-10-28', ?)", (json.dumps(facts),))
    con.commit()
    words = " | ".join(x["what"] for x in selfcheck._book500(db))
    assert "the night's change is not explained by its holdings" in words and "C$431.86" in words and "C$459.22" in words
    facts["account"]["value_cad"] = 459.22
    con.execute("UPDATE officer_notes SET facts=?", (json.dumps(facts),))
    con.commit()
    con.close()
    assert "not explained by its holdings" not in " | ".join(x["what"] for x in selfcheck._book500(db))


# ---------------------------------------------------------------- R-059: the recap's lines stay lines (the 8 Nov join undid them)
def test_a_recap_of_short_lines_stays_lines_without_labels():
    r = ask.finish({"answer": "Market: the Nifty rose 0.8%.\nAnanta: the options line bought a Bank Nifty call\n- Portfolio: no change.\nNext: CPI "
                              "comes out on Thursday."}, "How did the market go today? Simple points please.", True)
    lines = r["answer"].split("\n")
    assert len(lines) == 4 and not any(x.split(":")[0] in ("Market", "Ananta", "Portfolio", "Next") for x in lines)
    assert lines == ["The Nifty rose 0.8%.", "The options line bought a Bank Nifty call.", "No change.", "CPI comes out on Thursday."]
    two = ask.finish({"answer": "Sir, the Nifty rose.\nThat is all."}, "How did the Nifty close?", True)["answer"]
    assert "\n" not in two
