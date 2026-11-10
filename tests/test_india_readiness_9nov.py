"""9 Nov 2026 (the outsider readiness review; Madhav: "yes, lets complete"): GIFT Nifty before the open, the options line's plan in words,
the holdings' filings (weekends too), and one calendar for the voice, the view and the options line's event flag."""
import datetime as dt
import gzip
import json

from india import announce, calendar_ahead, desk, giftnifty, sp1plan

IST = giftnifty.IST


# ---------------------------------------------------------------------------------------------------------------- GIFT Nifty
BARS = [["2026-11-09T15:28:00+0530", 1, 1, 1, 25037.5, 0], ["2026-11-09T15:29:00+0530", 1, 1, 1, 25029.5, 0], ["2026-11-09T15:30:00+0530", 1, 1, 1, 25031.0, 0],
        ["2026-11-11T08:29:00+0530", 1, 1, 1, 25123.0, 0]]


def test_gift_nifty_is_read_against_its_own_level_at_the_last_close():
    r = giftnifty.read(None, "2026-11-09", 25044.65, dt.datetime(2026, 11, 11, 8, 30, tzinfo=IST), BARS)
    assert r["ref"] == 25029.5 and r["last"] == 25123.0 and r["change_pct"] == 0.37 and r["bucket"] == "up" and r["trading_now"]
    assert r["indicated_nifty"] == round(25044.65 * 1.0037)                  # the change is applied to the Nifty's close, never the future's level
    assert "up 0.4%" in r["words"] and "nothing trades on it" in r["words"] and "not trading now" not in r["words"]


def test_gift_nifty_says_when_it_is_stale_or_missing():
    r = giftnifty.read(None, "2026-11-09", 25044.65, dt.datetime(2026, 11, 11, 9, 30, tzinfo=IST), BARS)
    assert not r["trading_now"] and "not trading now" in r["words"]
    assert giftnifty.read(None, "2026-11-09", 1.0, dt.datetime(2026, 11, 11, 8, 30, tzinfo=IST), BARS[:2])["error"].startswith("no GIFT Nifty print since")
    assert giftnifty.read(None, None)["error"]

    class Dead:
        def get(self, *a, **k):
            raise RuntimeError("no sign-in")
    assert "RuntimeError" in giftnifty.read(Dead(), "2026-11-09")["error"]
    assert giftnifty.words({"error": "x"}) is None


def test_the_gap_lines_are_the_options_lines_own():
    assert [giftnifty.bucket(x) for x in (-0.25, -0.24, 0.0, 0.24, 0.25)] == ["down", "flat", "flat", "flat", "up"]
    assert [sp1plan.bucket(x) for x in (-0.25, -0.24, 0.0, 0.24, 0.25)] == ["down", "flat", "flat", "flat", "up"]


# ---------------------------------------------------------------------------------------------------------------- the options line's plan
def _plan():
    lv = {"trend": "up", "vix": "high", "us": "up", "positioning": "low", "event": "none", "expiry": "no"}
    short = {"action": 7, "exit": "ATRSTOP", "dir": -1, "qualifies": True}
    return {"date": "2026-11-09", "made_at": "2026-11-09T07:30:41+05:30", "stale": {"us_qqq": False, "participant_oi": False, "cm_bhavcopy": True},
            "overnight": {"NIFTY": {"us_qqq_ret": 0.014, "us_qqq_date": "2026-11-06"}},
            "d0_by_gap_bucket": {"NIFTY": {b: {"choice": None, "levels": {**lv, "expiry": "yes", "gap": b}} for b in ("down", "flat", "up")},
                                 "BANKNIFTY": {"down": {"choice": None, "levels": lv}, "flat": {"choice": None, "levels": lv}, "up": {"choice": short, "levels": lv}}}}


def test_the_plan_is_said_for_each_way_the_market_can_open():
    w = sp1plan.words(_plan(), {"NIFTY": 0.36, "BANKNIFTY": 0.65})
    assert w["ready"] and "Nifty: no trade at the open, whichever way it opens." in w["words"]
    assert "Bank Nifty: if it opens 0.25% or more up, a short (a put option, one lot), with a stop" in w["words"] and "if it opens down or flat, no trade" in w["words"]
    assert "the Nasdaq +1.4% on Fri 6 Nov" in w["words"] and "expiry day for Nifty options" in w["words"]
    assert "Missing when it was planned: the cash-market file" in w["words"]
    assert w["row"]["BANKNIFTY"]["bucket"] == "up" and "a short (a put option" in w["row"]["BANKNIFTY"]["words"]
    assert w["row"]["NIFTY"]["choice"] == "no trade"
    assert "ATRSTOP" not in w["words"] and "D0" not in w["words"]               # no code reaches the words


def test_no_plan_file_is_said_as_not_ready():
    assert sp1plan.words(None) == {"ready": False, "words": None, "short": None}


# ---------------------------------------------------------------------------------------------------------------- the one calendar
def test_first_session_is_worked_out_from_the_date_the_time_and_the_holidays():
    hol = {dt.date(2026, 11, 10)}
    us_cpi = {"date": "2026-11-10", "time_ist": "19:00", "kind": "release", "what": "US inflation"}
    assert calendar_ahead.first_session(us_cpi, hol) == dt.date(2026, 11, 11)
    assert calendar_ahead.first_session({"date": "2026-11-12", "time_ist": "16:00", "what": "x"}, hol) == dt.date(2026, 11, 13)        # after the close
    assert calendar_ahead.first_session({"date": "2026-11-28", "what": "x"}, hol) == dt.date(2026, 11, 30)                            # a Saturday
    assert calendar_ahead.first_session({"date": "2026-12-04", "time_ist": "10:00", "what": "x"}, hol) == dt.date(2026, 12, 4)        # during the session


def test_the_options_lines_event_days_come_from_the_published_calendar():
    days = calendar_ahead.scheduled_ahead(hol=set())
    assert dt.date(2026, 12, 4) in days and dt.date(2027, 2, 5) in days          # the RBI's published MPC decision days
    assert dt.date(2027, 2, 1) not in days                                       # the Budget is by convention until the government names the day
    assert all(r.get("source") for r in calendar_ahead.rows())
    s = calendar_ahead.for_session("2026-12-04", hol=set())
    assert s["options_line_event_day"] and any("RBI" in e["what"] for e in s["during"]) and any("US jobs" in e["what"] for e in s["after_close"])
    assert any("US inflation" in e["what"] for e in calendar_ahead.for_session("2026-11-11", hol={dt.date(2026, 11, 10)})["first_session_for"])


def test_the_scenario_flag_reads_the_calendar_ahead(monkeypatch, tmp_path):
    import pandas as pd
    from india import scenario
    (tmp_path / "silver" / "events").mkdir(parents=True)
    row = {"category": "rbi_policy", "first_tradable_session": "2026-10-07", "event_date": "2026-10-07", "known_beforehand": "scheduled"}
    pd.DataFrame([{**row, "status": "OFFICIAL", "batch": "batch_2023_2026.json"}, {**row, "status": "DUPLICATE", "batch": "calendar_rbi.json"}]
                 ).to_parquet(tmp_path / "silver" / "events" / "events.parquet")
    monkeypatch.setattr(scenario.paths, "data_dir", lambda: tmp_path)
    monkeypatch.setattr(calendar_ahead, "_holidays", lambda: set())
    days = scenario.scheduled_dates()
    assert dt.date(2026, 10, 7) in days and dt.date(2026, 12, 4) in days


# ---------------------------------------------------------------------------------------------------------------- announcements
def test_a_day_is_whole_only_when_fetched_after_it_ended_in_india():
    d = dt.date(2026, 11, 9)
    assert not announce._complete(d, "2026-11-09T10:20:00+00:00")        # 15:50 IST the same day: the evening's filings are still to come
    assert announce._complete(d, "2026-11-09T18:30:00+00:00")            # midnight in India
    assert announce._complete(d, None)                                   # rows from before the field


def test_recent_days_are_fetched_again_until_whole_weekends_included(monkeypatch, tmp_path):
    monkeypatch.setattr(announce.paths, "data_dir", lambda: tmp_path)
    monkeypatch.setattr(announce.paths, "manifest_dir", lambda: tmp_path / "manifests")
    monkeypatch.setattr(announce.paths, "bronze", lambda name: tmp_path / "bronze" / name)
    monkeypatch.setattr(announce.paths, "ensure", lambda: (tmp_path / "manifests").mkdir(parents=True, exist_ok=True))
    asked = []

    class F:
        def get(self, url):
            asked.append(url.split("from_date=")[1][:10])
            return 200, json.dumps([{"symbol": "TATACHEM"}]).encode(), 0.1
    today = dt.datetime.now(announce.IST).date()
    r = announce.fetch_recent(days_back=3, fetcher=F(), today=today)
    assert len(asked) == 4 and [x["complete"] for x in r["fetched"]] == [True, True, True, False]          # every calendar day; today is not whole yet
    asked.clear()
    announce.fetch_recent(days_back=3, fetcher=F(), today=today)
    assert asked == [f"{today:%d-%m-%Y}"]                                                                   # only the day that was not whole


# ---------------------------------------------------------------------------------------------------------------- holdings first
def test_one_line_for_each_holding_that_filed_since_the_close(monkeypatch, tmp_path):
    monkeypatch.setattr(desk.paths, "data_dir", lambda: tmp_path)
    (tmp_path / "readmodel").mkdir()
    (tmp_path / "readmodel" / "latest.json").write_text(json.dumps({"data_through": "2026-11-06"}))
    news = {"TATACHEM": [{"at": "2026-11-07 17:10", "kind": "results", "what": "Outcome of Board Meeting", "text": "has submitted the financial results for the period ended September 30, 2026"}],
            "MARICO": [{"at": "2026-11-06 17:20", "kind": "deal", "what": "Acquisition", "text": "Please find attached"}, {"at": "2026-11-06 17:16", "kind": "deal", "what": "Acquisition", "text": "x"},
                       {"at": "2026-11-05 10:00", "kind": "results", "what": "Outcome of Board Meeting", "text": "old"}],
            "NATIONALUM": [{"at": "2026-11-07 09:00", "kind": "other", "what": "Copy of Newspaper Publication", "text": "x"}]}
    qb = {"as_of": "2026-11-06", "quotes": {"TATACHEM": {"chg_1d": -0.004}, "IRFC": {"chg_1d": 0.038}, "MARICO": {"chg_1d": 0.005}}}
    h = desk.holdings_news(held=["IRFC", "MARICO", "NATIONALUM", "TATACHEM"], by_sym=news, ahead={"2026-11-11": ["IRFC", "ZZZ"]}, qb=qb)
    assert h["since"] == "2026-11-06 15:30" and [r["symbol"] for r in h["rows"]] == ["TATACHEM", "MARICO"]            # results first
    assert "TATACHEM: filed its results for the period ended September 30 (Outcome of Board Meeting, Sat 7 Nov 17:10 IST)" in h["lines"][0]
    assert "2 filings" in h["lines"][1] and "old" not in h["lines"][1]                                                 # before the close: not news
    assert any("from the other 2: IRFC, NATIONALUM" in x for x in h["lines"])                                          # routine filings are not a line
    assert any("Moved 2% or more" in x and "IRFC +3.8%" in x for x in h["lines"])
    assert any("Results meetings ahead for your stocks: IRFC on Wed 11 Nov" in x for x in h["lines"]) and "ZZZ" not in " ".join(h["lines"])


def test_the_announcement_files_read_cover_a_weekend(tmp_path, monkeypatch):
    monkeypatch.setattr(desk.paths, "data_dir", lambda: tmp_path)
    d = tmp_path / "bronze" / "announce_api" / "2026"
    d.mkdir(parents=True)
    with gzip.open(d / "20261107.json.gz", "wb") as fh:
        fh.write(json.dumps([{"symbol": "TATACHEM", "desc": "Outcome of Board Meeting", "attchmntText": "approved the financial results for the quarter ended September 30, 2026",
                              "an_dt": "07-Nov-2026 17:10:00"}]).encode())
    by, _ = desk.news()
    assert by["TATACHEM"][0]["kind"] == "results" and by["TATACHEM"][0]["at"] == "2026-11-07 17:10"


def test_the_newer_of_the_read_model_and_the_quote_book_is_the_last_close(monkeypatch, tmp_path):
    """9 Nov 2026, found while building: the quote book held Monday's moves while the read model was still on Friday, and Monday's move was
    labelled 'on Fri 6 Nov'."""
    monkeypatch.setattr(desk.paths, "data_dir", lambda: tmp_path)
    (tmp_path / "readmodel").mkdir()
    (tmp_path / "readmodel" / "latest.json").write_text(json.dumps({"data_through": "2026-11-06"}))
    news = {"MARICO": [{"at": "2026-11-06 17:20", "kind": "deal", "what": "Acquisition", "text": "x"}], "TATACHEM": [{"at": "2026-11-09 18:05", "kind": "order", "what": "Award of Order", "text": "x"}]}
    h = desk.holdings_news(held=["MARICO", "TATACHEM"], by_sym=news, ahead={}, qb={"as_of": "2026-11-09", "quotes": {"TATACHEM": {"chg_1d": 0.012}}})
    assert h["since"] == "2026-11-09 15:30" and [r["symbol"] for r in h["rows"]] == ["TATACHEM"]          # Friday's filing was Monday's news, not Wednesday's
    assert "It closed +1.2% on Mon 9 Nov." in h["lines"][0]


def test_a_plan_older_than_a_holdings_filing_says_so():
    from india import morningview as mv
    f = {"overnight": {}, "setup": {}, "scorecard": {}, "yesterday": {}, "session": "2026-11-11", "premarket": {},
         "plan": {"picks": [], "options_line": {"words": "x"}, "managed_book": {"brief": "Sell TATACHEM, buy ZZZ.", "cuts": ["TATACHEM"], "buys": [{"symbol": "ZZZ"}]}},
         "holdings_news": {"lines": ["TATACHEM: filed its results (Outcome of Board Meeting, Sat 7 Nov 17:10 IST)."], "rows": [{"symbol": "TATACHEM", "kinds": ["results"]}, {"symbol": "MARICO", "kinds": ["deal"]}]}}
    L = mv.lines(f)
    assert L["holdings"][0].startswith("TATACHEM: filed its results")                                   # holdings first
    assert any(x.startswith("Newer than that plan: TATACHEM has filed since the close it was written from") for x in L["plan"])
    assert not any("MARICO" in x for x in L["plan"])                                                     # not in today's plan: nothing to say beside it
    assert not any("Odds for today" in x for x in L["view"]) and not any("max pain" in x for x in L["watch"])      # the strip list


def test_the_last_regular_session_comes_from_the_calendar_not_the_nightly_build():
    """Found on the first live read (10 Nov, 06:06 IST): the read model was still on Friday, so GIFT Nifty was set against Friday's close."""
    from india import premarket
    hol = {dt.date(2026, 11, 10)}
    assert premarket.last_regular_session(dt.date(2026, 11, 11), hol) == dt.date(2026, 11, 9)       # Wednesday, after Tuesday's holiday
    assert premarket.last_regular_session(dt.date(2026, 11, 9), hol) == dt.date(2026, 11, 6)        # Monday: Friday (Sunday's Muhurat hour is not a regular session)
    assert premarket.last_regular_session(dt.date(2026, 11, 12), hol) == dt.date(2026, 11, 11)
