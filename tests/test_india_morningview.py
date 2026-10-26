"""The morning view (india/morningview.py): builds from fixture files, says missing where a source is absent, keeps chances beside their baseline,
scores yesterday's predictions (rule and reviewer) from the ledger, turns the record into lessons for the writer, and keeps the model's words across
a rebuild."""
from __future__ import annotations

import json

import pytest

from india import morningview as mv

SESSION = "2026-10-26"
PREV = "2026-10-23"


@pytest.fixture
def lake(tmp_path, monkeypatch):
    data = tmp_path / "india"
    for d in ("paper/dayplans", "paper/decisions", "paper/sp1", "readmodel", "silver/us", "silver/fo_calendar", "silver/events", "paper/account"):
        (data / d).mkdir(parents=True)
    monkeypatch.setattr(mv.paths, "data_dir", lambda: data)
    monkeypatch.setattr(mv, "REG", tmp_path / "reg")
    monkeypatch.setattr(mv, "PAGE", tmp_path / "reg" / "morningview.md")
    from india import technicals
    monkeypatch.setattr(technicals, "latest_index", lambda names: {})     # 26 Oct: the newest-close read stays out of the fixture lake
    (tmp_path / "reg").mkdir()
    (data / "readmodel" / "latest.json").write_text(json.dumps({"data_through": PREV, "next_session": SESSION,
        "market": {"trend_state": "below_both", "nifty_close": 22688.0, "nifty_vs_sma50": -0.032, "nifty_vs_sma200": -0.06, "breadth_200d_liquid": 0.4, "breadth_50d_liquid": 0.148, "vix_close": 15.7, "vix_vs_sma50": 0.26, "nifty_ret1": -0.0054, "words": "w"},
        "call": {"call": "BULLISH", "scored": 3, "hits": 0, "null_hits": 2}, "sp1": {"status": "lost", "book": {"sessions": 0}}, "reconstruction": {"headline": "last night"}}))
    (data / "paper" / "dayplans" / f"{SESSION}.json").write_text(json.dumps({"session": SESSION, "forecast_id": "FC-rule", "forecast": {"bull": 0.4, "bear": 0.33, "neutral": 0.27},
        "scenarios_text": {"bull": "up", "bear": "down", "neutral": "flat"}, "limits": ["no GIFT Nifty"],
        "overnight": {"NIFTY 50": {"date": PREV, "close": 22688.0, "d1": -0.0054, "vs_sma50": -0.032, "vs_sma200": -0.06}, "INDIA VIX": {"date": PREV, "close": 15.7, "vs_sma50": 0.26},
                      "FII_DII": {"FII/FPI": {"date": PREV, "net_crore": -3458.7}, "DII": {"date": PREV, "net_crore": 2891.3}}, "BRENT_SPOT_EUROPE": {"date": "2026-10-01", "value": 126.0, "change": 0.01, "unit": "return"}}}))
    (data / "paper" / "decisions" / f"{PREV}.json").write_text(json.dumps({"signals": [{"symbol": "AAA", "campaign": "PULL", "close": 10, "liq_rank": 5}, {"symbol": "BBB", "campaign": "REV", "close": 20}, {"symbol": "CCC", "campaign": "CTL"}]}))
    (data / "paper" / "forecasts.jsonl").write_text("\n".join(json.dumps(x) for x in [
        {"kind": "forecast", "forecast_id": "FC-1", "session": PREV, "scenarios": {"bull": 0.4, "bear": 0.33, "neutral": 0.27}, "basis": "climatology"},
        {"kind": "forecast", "forecast_id": "FC-2", "session": PREV, "scenarios": {"bull": 0.3, "bear": 0.45, "neutral": 0.25}, "basis": "reviewer: FIIs selling"},
        {"kind": "score", "ref": "FC-1", "outcome": "bear", "hit": False, "brier": 0.68, "brier_coin_flip": 0.667},
        {"kind": "score", "ref": "FC-2", "outcome": "bear", "hit": True, "brier": 0.42, "brier_coin_flip": 0.667}]) + "\n")
    (data / "paper" / "calls.jsonl").write_text(json.dumps({"kind": "score", "data_through": PREV, "score": -1, "move": -0.0054}) + "\n")
    (data / "paper" / "state.json").write_text(json.dumps({"trades": {"t1": {"book": "exec", "policy": "hold_20d", "entry_date": PREV, "campaign": "PULL", "symbol": "AAA", "entry_adj": 100, "last_close_adj": 98}}}))
    (data / "paper" / "marks.jsonl").write_text(json.dumps({"book": "exec", "policy": "hold_20d", "campaign": "PULL", "closed": 4, "open": 10, "realised_inr": -1200, "win_rate": 0.25}) + "\n")
    (data / "paper" / "allocation_view.json").write_text(json.dumps({"headline": "Ananta manages the split", "suggestions": [{"symbol": "LICI", "action": "TRIM", "why": "w"}], "moves": [{"why": "options were 31%"}]}))
    import pandas as pd
    pd.DataFrame([{"symbol": "SPY", "date": "2026-10-22", "close": 764.0, "ret": -0.012}, {"symbol": "SPY", "date": "2026-10-23", "close": 760.0, "ret": -0.005}, {"symbol": "QQQ", "date": "2026-10-23", "close": 600.0, "ret": 0.0}]).to_parquet(data / "silver" / "us" / "us_close.parquet")
    pd.DataFrame([{"symbol": "NIFTY", "instrument": "OPTIDX", "expiry": "2026-10-27", "is_monthly_last": True}, {"symbol": "BANKNIFTY", "instrument": "OPTIDX", "expiry": SESSION, "is_monthly_last": False}]).to_parquet(data / "silver" / "fo_calendar" / "expiries.parquet")
    pd.DataFrame([{"event_id": "e1", "title": "Riots", "category": "unrest", "first_tradable_session": "2026-10-23", "event_date": "2026-10-23", "status": "OFFICIAL", "known_beforehand": "no", "batch": "x", "scope": "s"}]).to_parquet(data / "silver" / "events" / "events.parquet")
    return data


def test_build_facts_lines_and_page(lake, monkeypatch):
    from india import kite
    monkeypatch.setattr(kite, "_read_token", lambda: None)   # 25 Oct: the Mac's real morning token leaked in once auto sign-in worked
    f = mv.build(SESSION)
    assert f["session"] == SESSION and f["overnight"]["us"]["S&P 500"]["ret"] == -0.005 and "Brent crude" not in f["overnight"]["us"], "stale FRED data is dropped"
    assert f["setup"]["scenario_levels"]["up_above"] == 22756.0 and f["setup"]["expiry"]["today"] == ["BANKNIFTY"] and f["setup"]["expiry"]["next"]["date"] == "2026-10-27"
    assert [p["symbol"] for p in f["plan"]["picks"]] == ["AAA", "BBB"] and f["plan"]["random_picks"] == 1
    assert "cannot trade" in f["plan"]["options_line"]["words"]
    L = f["lines"]
    assert any("Expiry day for BANKNIFTY" in x for x in L["watch"]) and any("above 22,756" in x for x in L["watch"])
    assert "practice" in L["plan"][0] and "not your money" in L["plan"][0]
    assert "coin flip" in L["chances"][0] and "not an edge" in L["chances"][0]
    assert "flat" in L["view"][0], "a 0.0% move reads as flat"
    assert mv.PAGE.exists() and "## Our chances, honestly" in mv.PAGE.read_text()


def test_scorecard_compares_rule_reviewer_and_coin_flip_and_writes_lessons(lake):
    f = mv.build(SESSION)
    sc = f["scorecard"]["forecasts"]
    assert sc["rule"] == {"n": 1, "hits": 0, "brier_mean": 0.68} and sc["reviewer"] == {"n": 1, "hits": 1, "brier_mean": 0.42} and sc["coin_flip_brier_mean"] == 0.667
    y = f["yesterday"]
    assert {p["who"]: p["hit"] for p in y["predictions"]} == {"rule": False, "reviewer": True}
    assert y["picks_first_day"]["n"] == 1 and y["picks_first_day"]["avg_ret"] == -0.02
    assert any("rule forecast favoured 'bull'" in x and "wrong" in x for x in y["lessons"]) and any("reviewer forecast" in x and "right" in x for x in y["lessons"])
    les = f["lessons_for_writer"]
    assert any("daily call is behind the coin flip" in x for x in les) and any("options line has no record" in x for x in les) and les[-1].startswith("Every number")


def test_words_survive_a_rebuild_and_missing_sources_say_so(lake):
    f = mv.build(SESSION)
    p = mv._dir() / f"{SESSION}.json"
    j = json.loads(p.read_text())
    j["words"], j["review"] = "Sir, the note.", "Fair."
    p.write_text(json.dumps(j))
    f2 = mv.build(SESSION)
    assert f2["words"] == "Sir, the note." and f2["review"] == "Fair."
    (lake / "paper" / "dayplans" / f"{SESSION}.json").unlink()
    f3 = mv.build(SESSION)
    assert f3["setup"]["scenarios"]["bull"] is None and not any("Odds for today" in x for x in f3["lines"]["view"])


def test_newest_index_close_replaces_the_day_plans_older_one(lake, monkeypatch):
    """26 Oct: the Mon 26 Oct plan was written Fri 19:00 with the Thu 22 Oct close (22,688); the view must say the Fri 23 Oct close (22,600),
    keep the plan's forecast lines, and say which close those lines came from."""
    from india import technicals
    p = lake / "paper" / "dayplans" / f"{SESSION}.json"
    j = json.loads(p.read_text())
    j["overnight"]["NIFTY 50"]["date"] = "2026-10-22"
    p.write_text(json.dumps(j))
    monkeypatch.setattr(technicals, "latest_index", lambda names: {"NIFTY 50": {"date": PREV, "close": 22600.0, "d1": -0.0039, "vs_sma50": -0.034, "vs_sma200": -0.063}})
    f = mv.build(SESSION)
    n = f["overnight"]["india"]["Nifty"]
    assert n["close"] == 22600.0 and n["date"] == PREV and n["plan_close"] == 22688.0 and n["plan_date"] == "2026-10-22"
    assert any("the day plan had the 2026-10-22 close; the newest is 2026-10-23" in x for x in f["overnight"]["notes"])
    assert any("Nifty closed at 22,600 on 23 Oct" in x for x in f["lines"]["view"])
    assert f["setup"]["scenario_levels"]["up_above"] == 22756.0, "the forecast's lines stay as they were written"
    assert any("from the 22 Oct close of 22,688, not the newer 23 Oct close" in x for x in f["lines"]["watch"])
