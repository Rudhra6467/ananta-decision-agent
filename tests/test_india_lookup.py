"""jarvis/india/lookup.py: stocks, sectors, gold, mutual funds and rules for the India Ask (27 Oct 2026, the outside review's data gaps).
Everything runs on small fixture files; the network is never touched."""
import datetime as dt
import json
import time

import pytest

from jarvis.india import lookup as L


def _q(sym, name, close, **kw):
    base = {"symbol": sym, "name": name, "kind": "stock", "as_of": "2026-10-27", "close": close, "chg_1d": -0.015, "chg_1w": 0.015, "chg_1m": 0.199,
            "chg_3m": 0.088, "chg_ytd": -0.221, "chg_1y": -0.191, "vs_nifty_1y": -0.067, "high_52w": 3350.0, "vs_high_52w": -0.25, "vs_sma50": 0.108,
            "vs_sma200": 0.022, "rsi14": 69.0, "vol_60d": 0.33, "biggest_day_60d": {"date": "2026-09-15", "move": 0.02}, "price_jump_unadjusted": False,
            "price_jump": None}
    base.update(kw)
    return base


@pytest.fixture
def data(tmp_path, monkeypatch):
    man = tmp_path / "manifests"
    man.mkdir()
    quotes = {"TCS": _q("TCS", "Tata Consultancy Services Limited", 2496.9),
              "INFY": _q("INFY", "Infosys Limited", 1400.0),
              "HDFCBANK": _q("HDFCBANK", "HDFC Bank Limited", 680.2),
              "SBIN": _q("SBIN", "State Bank of India", 800.0),
              "TMPV": _q("TMPV", "Tata Motors Passenger Vehicles Limited", 261.2, price_jump_unadjusted=True, price_jump={"date": "2025-10-14", "move": -0.4}),
              "TMCV": _q("TMCV", "Tata Motors Limited", 380.0),
              "IDEA": _q("IDEA", "Vodafone Idea Limited", 8.0),
              "TATACHEM": _q("TATACHEM", "Tata Chemicals Limited", 599.0, vol_60d=0.57, biggest_day_60d={"date": "2026-09-15", "move": 0.2}),
              "GOLDBEES": _q("GOLDBEES", "Nippon India Gold BeES ETF", 115.64, kind="etf")}
    sectors = [{"index": f"S{i}", "name": n, "as_of": "2026-10-27", "chg_3m": v, "rank_3m": i + 1}
               for i, (n, v) in enumerate([("IT", 0.093), ("Media", 0.033), ("Pharma", 0.012), ("Banks", -0.02), ("FMCG", -0.13), ("Railway PSUs", -0.139)])]
    broad = [{"index": "NIFTY MIDCAP 150", "name": "Nifty Midcap 150", "chg_1y": -0.048, "vs_high_52w": -0.11},
             {"index": "NIFTY SMLCAP 250", "name": "Nifty Smallcap 250", "chg_1y": -0.023, "vs_high_52w": -0.09}]
    qb = {"as_of": "2026-10-27", "nifty": {"chg_3m": -0.052, "chg_1y": -0.124}, "quotes": quotes, "sectors": sectors, "broad": broad,
          "gold": {"gold": {"symbol": "GOLDBEES", "as_of": "2026-10-27", "chg_1m": -0.071, "chg_3m": -0.025, "chg_ytd": 0.05, "chg_1y": 0.155, "vs_high_52w": -0.22}},
          "gold_note": "via Gold BeES"}
    names = {"TCS": {"name": "Tata Consultancy Services Limited", "aliases": ["tcs", "tata consultancy"], "norm": "tata consultancy services"},
             "INFY": {"name": "Infosys Limited", "aliases": ["infosys"], "norm": "infosys"},
             "HDFCBANK": {"name": "HDFC Bank Limited", "aliases": ["hdfc bank"], "norm": "hdfc bank"},
             "SBIN": {"name": "State Bank of India", "aliases": ["sbi", "state bank"], "norm": "state bank of"},
             "TMPV": {"name": "Tata Motors Passenger Vehicles Limited", "aliases": ["tata motors", "tata motors pv"], "norm": "tata motors passenger vehicles"},
             "TMCV": {"name": "Tata Motors Limited", "aliases": ["tata motors cv"], "norm": "tata motors"},
             "IDEA": {"name": "Vodafone Idea Limited", "aliases": ["vodafone idea", "vi"], "norm": "vodafone idea"},
             "TATACHEM": {"name": "Tata Chemicals Limited", "aliases": [], "norm": "tata chemicals"},
             "GOLDBEES": {"name": "Nippon India Gold BeES ETF", "aliases": ["gold bees", "goldbees"], "norm": "nippon gold bees etf"},
             "SLEEPY": {"name": "Sleepy Traders Limited", "aliases": [], "norm": "sleepy traders"}}
    rows = []
    for code, name, amc, cat, plan, opt in [(119788, "SBI GOLD FUND", "SBI Mutual Fund", "Other Scheme - FoF Domestic", "Direct", "Growth"),
                                            (115676, "SBI GOLD FUND", "SBI Mutual Fund", "Other Scheme - FoF Domestic", "Regular", "Growth"),
                                            (119789, "SBI GOLD FUND", "SBI Mutual Fund", "Other Scheme - FoF Domestic", "Direct", "IDCW"),
                                            (122639, "Parag Parikh Flexi Cap Fund", "PPFAS Mutual Fund", "Equity Scheme - Flexi Cap Fund", "Direct", "Growth"),
                                            (122640, "Parag Parikh Flexi Cap Fund", "PPFAS Mutual Fund", "Equity Scheme - Flexi Cap Fund", "Regular", "Growth"),
                                            (120465, "Axis Large Cap Fund", "Axis Mutual Fund", "Equity Scheme - Large Cap Fund", "Direct", "Growth"),
                                            (149373, "Axis Nifty 50 Index Fund", "Axis Mutual Fund", "Other Scheme - Index Funds", "Direct", "Growth"),
                                            (120716, "UTI Nifty 50 Index Fund", "UTI Mutual Fund", "Other Scheme - Index Funds", "Direct", "Growth"),
                                            (147625, "Motilal Oswal Nifty 500 Index Fund", "Motilal Oswal Mutual Fund", "Other Scheme - Index Funds", "Direct", "Growth"),
                                            (140088, "Nippon India ETF Gold BeES", "Nippon India Mutual Fund", "Other Scheme - Gold ETF", "Direct", "")]:
        rows.append({"code": code, "name": name, "amc": amc, "type": "Open Ended Schemes", "category": cat, "plan": plan, "option": opt, "nav": 50.0,
                     "date": "2026-10-27", "isin": "INF0"})
    (man / "quotebook.json").write_text(json.dumps(qb))
    (man / "quotebook_names.json").write_text(json.dumps(names))
    (man / "mf_schemes.json").write_text(json.dumps({"rows": rows}))
    rules = tmp_path / "rules.json"
    rules.write_text(json.dumps({"facts": [
        {"id": "equity_capital_gains", "topics": ["ltcg", "capital gains", "tax"], "fact": "12.5% above Rs 1.25 lakh", "as_of": "2026-10-27", "source": "x"},
        {"id": "fno_losses", "topics": ["f&o", "futures", "options"], "fact": "91% lost", "as_of": "2026-10-27", "source": "y"}]}))
    monkeypatch.setattr(L, "MAN", man)
    monkeypatch.setattr(L, "DATA", tmp_path)
    monkeypatch.setattr(L, "CACHE", tmp_path / "mf_cache")
    monkeypatch.setattr(L, "RULES_FILE", rules)
    L._files.clear()
    yield tmp_path
    L._files.clear()


def _navs(start="2013-01-01", end="2026-10-26", growth=0.10, dip=None):
    """Daily NAVs growing `growth` a year; dip = (from, to, depth) drops and recovers linearly."""
    d0, d1 = dt.date.fromisoformat(start), dt.date.fromisoformat(end)
    out, d = [], d0
    while d <= d1:
        if d.weekday() < 5:
            v = 10 * (1 + growth) ** ((d - d0).days / 365.25)
            if dip and dip[0] <= d <= dip[1]:
                mid = dip[0] + (dip[1] - dip[0]) / 2
                frac = 1 - abs((d - mid).days) / max(1, (mid - dip[0]).days)
                v *= 1 - dip[2] * frac
            out.append((d, v))
        d += dt.timedelta(days=1)
    return out


def _mfapi_body(navs):
    return {"meta": {}, "data": [{"date": d.strftime("%d-%m-%Y"), "nav": f"{v:.4f}"} for d, v in reversed(navs)]}


# ------------------------------------------------------------------------------------------------------------------------------ stocks
def test_find_names(data):
    assert L.find_names("What's the current price of TCS and is it a good buy now?") == ["TCS"]
    assert L.find_names("Is HDFC Bank cheap or expensive right now?") == ["HDFCBANK"]
    assert set(L.find_names("Should I buy tata motors or infosys?")) == {"TMPV", "TMCV", "INFY"}     # both Tata Motors companies
    assert L.find_names("Should I buy tata motors pv?") == ["TMPV"]
    assert L.find_names("Is the IDEA a good one") == ["IDEA"]
    for t in ("What is RSI?", "What do FII flows mean?", "any idea what the market will do", "Is my SIP in an ETF okay?", "what is the PE of the NIFTY",
              "Is it okay to put all my money in one stock?", "I'm sleepy"):
        assert L.find_names(t) == [], t
    assert L.find_names("compare TCS, INFY, HDFCBANK, SBIN, IDEA and TMCV", limit=5) == ["TCS", "INFY", "HDFCBANK", "SBIN", "IDEA"]


def test_quote_words(data):
    f = L.quote_facts(["TCS", "TMPV", "TATACHEM", "SLEEPY", "NOPE"])
    w = f["TCS"]["words"]
    assert "Rs 2,496.90" in w and "Tue 27 Oct" in w and "1 year -19.1%" in w and "behind the Nifty" in w and "52-week high" in w and "RSI 69" in w
    assert "Caution" in f["TMPV"]["words"] and "2025" in f["TMPV"]["words"] and f["TMPV"]["price_jump"]["date"] == "2025-10-14"
    assert "57% a year" in f["TATACHEM"]["words"] and "+20.0% on Tue 15 Sep" in f["TATACHEM"]["words"]
    assert f["SLEEPY"]["status"] == "thin" and f["NOPE"]["status"] == "unknown"


def test_sectors_and_gold(data):
    s = L.sector_facts()
    assert s["words"].startswith("Sectors by their 3-month change") and "strongest IT +9.3%" in s["words"] and "Railway PSUs -13.9%" in s["words"]
    assert "small caps (Nifty Smallcap 250) are 9% below" in s["words"]
    g = L.gold_facts()
    assert "Gold in rupees" in g["words"] and "1 year +15.5%" in g["words"]


# ------------------------------------------------------------------------------------------------------------------------------ funds: finding
def test_find_funds(data):
    f = L.find_funds("Is SBI Gold Fund good to hold?")
    assert [x["code"] for x in f] == [119788] and f[0]["assumed_plan"] and f[0]["sibling_code"] == 115676
    f = L.find_funds("my friend has Parag Parikh Flexi Cap fund regular plan")
    assert f[0]["code"] == 122640 and f[0]["plan"] == "Regular" and not f[0]["assumed_plan"]
    assert L.find_funds("SBI gold fund dividend")[0]["code"] == 119789
    assert L.find_funds("axis bluechip fund")[0]["code"] == 120465                                   # renamed scheme
    for t in ("Is a Nifty 50 index fund better than an active fund?", "What is a mutual fund NAV?", "Should I start a SIP in an ELSS fund?",
              "Is HDFC Bank cheap?", "gold fund or gold ETF?"):
        assert L.find_funds(t) == [], t


# ------------------------------------------------------------------------------------------------------------------------------ funds: maths
def test_xirr_and_cagr_maths():
    t0 = dt.date(2020, 1, 1)
    assert L._xirr([(t0, -1000.0), (t0 + dt.timedelta(days=round(365.25 * 2)), 1210.0)]) == pytest.approx(0.10, abs=1e-4)
    nav = _navs(growth=0.10)
    m = L._metrics(nav)
    assert m["cagr_3y"] == pytest.approx(0.10, abs=0.002) and m["cagr_5y"] == pytest.approx(0.10, abs=0.002)
    assert m["ret_1y"] == pytest.approx(0.10, abs=0.003) and m["sip_xirr_3y"] == pytest.approx(0.10, abs=0.005)
    assert m["worst_drawdown"] == pytest.approx(0.0, abs=1e-9) and m["vol_3y"] < 0.01
    dip = L._metrics(_navs(growth=0.10, dip=(dt.date(2020, 2, 1), dt.date(2020, 6, 1), 0.3)))
    assert -0.32 < dip["worst_drawdown"] < -0.25 and dip["worst_drawdown_to"].startswith("2020-0")
    assert L._metrics(_navs(start="2025-01-01"))["cagr_3y"] is None                                 # too young: no 3-year figure


def test_with_amfi_adds_newer_nav(data):
    nav = [(dt.date(2026, 10, 23), 10.0), (dt.date(2026, 10, 26), 10.1)]
    out = L._with_amfi(119788, nav)
    assert out[-1] == (dt.date(2026, 10, 27), 50.0)
    assert L._with_amfi(119788, [(dt.date(2026, 10, 27), 10.0)]) == [(dt.date(2026, 10, 27), 10.0)]


def test_fund_facts_with_benchmark_and_plan_gap(data, monkeypatch):
    hist = {122639: _navs(growth=0.14), 122640: _navs(growth=0.13), 147625: _navs(growth=0.10), 119788: _navs(growth=0.12),
            115676: _navs(growth=0.115), 140088: _navs(growth=0.12)}
    monkeypatch.setattr(L, "_fetch_nav", lambda code: hist[code])
    monkeypatch.setattr(L, "_with_amfi", lambda code, navs: navs)
    r = L.fund_facts(L.find_funds("Parag Parikh Flexi Cap fund") + L.find_funds("SBI Gold Fund"))
    pp, sb = r["funds"]["122639"], r["funds"]["119788"]
    assert pp["status"] == "ok" and pp["benchmark"]["name"] == "Nifty 500" and pp["cagr_3y"] == pytest.approx(0.14, abs=0.003)
    assert pp["direct_minus_regular"]["cagr_3y"] == pytest.approx(0.01, abs=0.002)
    assert "Nifty 500 for comparison" in pp["words"] and "Direct plan earned about" in pp["words"] and "plan not stated" in pp["words"]
    assert sb["benchmark"]["name"].startswith("gold") and "not available" in sb["expense_ratio"]
    assert r["seconds"] < 3


def test_fund_facts_never_waits_long(data, monkeypatch):
    monkeypatch.setattr(L, "FUND_BUDGET_S", 0.3)

    def slow(code):
        time.sleep(2)
        return _navs()
    monkeypatch.setattr(L, "_fetch_nav", slow)
    t = time.time()
    r = L.fund_facts(L.find_funds("SBI Gold Fund"))
    assert time.time() - t < 1.2
    f = r["funds"]["119788"]
    assert f["status"] == "history_unavailable" and "not available" in f["words"] and "50.0" in f["words"]


def test_fund_facts_uses_an_older_cache_when_offline(data, monkeypatch):
    L.CACHE.mkdir(parents=True)
    old = (dt.date.today() - dt.timedelta(days=3)).isoformat()
    (L.CACHE / "119788.json").write_text(json.dumps({"fetched": old, "body": _mfapi_body(_navs(growth=0.12))}))

    def offline(code):
        raise OSError("offline")
    monkeypatch.setattr(L, "_fetch_nav", offline)
    f = L.fund_facts(L.find_funds("SBI Gold Fund"))["funds"]["119788"]
    assert f["status"] == "ok" and f["cagr_3y"] is not None


def test_fetch_caches_for_the_day(data, monkeypatch):
    calls = []

    class R:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return _mfapi_body(_navs(start="2024-01-01"))

    def get(url, timeout):
        calls.append(url)
        return R()
    monkeypatch.setattr(L.requests, "get", get)
    assert L._fetch_nav(119788)[-1][0] == dt.date(2026, 10, 26)
    assert L._cached_nav(119788, 0) and len(calls) == 1


# ------------------------------------------------------------------------------------------------------------------------------ rules, facts_for
def test_rules_facts(data):
    assert [r["id"] for r in L.rules_facts("How is LTCG tax worked out on shares?")] == ["equity_capital_gains"]
    assert L.rules_facts("Should I trade options?")[0]["id"] == "fno_losses"
    assert L.rules_facts("What is a golden cross?") == []


def test_facts_for_only_what_is_needed(data, monkeypatch):
    monkeypatch.setattr(L, "_fetch_nav", lambda code: _navs(growth=0.12))
    assert L.facts_for("What is a golden cross?") == {}
    r = L.facts_for("Is SBI Gold Fund good to hold?")
    assert "mutual_funds" in r and "gold" in r and "stocks" not in r                                # "SBI" here is the fund house, not SBIN
    r = L.facts_for("How has TCS done, and which sectors are strongest?")
    assert list(r["stocks"]) == ["TCS"] and "sectors" in r and "how_to_say_it" in r
    r = L.facts_for("Is the Axis Jubilee Opportunities fund good?")                                 # a fund house but no such scheme
    assert r["mutual_funds"]["funds"] == {} and "no scheme" in r["mutual_funds"]["words"]
