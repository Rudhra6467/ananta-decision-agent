"""The managed paper book (Madhav, 30 Oct 2026: "pick the replacements and trade them in paper so you know how your reasoning was"; his yes to
the plan the same evening): the cut list frees rupees; a replacement passes every proved filter; the plan is written before the open on a sha
chain; fills at the open with the no-chase check; the fixed stop; the replacement ledger scores the reasoning."""
import datetime as dt
import json

import numpy as np
import pandas as pd
import pytest

from india import managed as m

DAY = "2026-10-30"


def _bars(symbols: dict) -> pd.DataFrame:
    """260 sessions of synthetic closes per symbol. symbols: name -> (daily drift, daily noise) ; the last close is shaped by the spec."""
    dates = pd.bdate_range(end=DAY, periods=260)
    rows = []
    rng = np.random.default_rng(1)
    for sym, (drift, noise) in symbols.items():
        c = 100 * np.cumprod(1 + drift + noise * rng.standard_normal(len(dates)))
        o = np.r_[c[0], c[:-1]] * (1 + 0.001)
        for d, oo, cc in zip(dates, o, c):
            rows.append({"symbol": sym, "date": d, "open": oo, "high": max(oo, cc) * 1.005, "low": min(oo, cc) * 0.995, "close": cc, "volume": 1e6, "turnover": 2e8})
    return pd.DataFrame(rows)


@pytest.fixture
def world(tmp_path, monkeypatch):
    monkeypatch.setenv("INDIA_DATA_DIR", str(tmp_path))
    (tmp_path / "paper" / "account").mkdir(parents=True)
    (tmp_path / "paper" / "managed").mkdir(parents=True)
    (tmp_path / "manifests").mkdir()
    twin = {"snapshot_day": "2026-10-22", "positions": {"WEAK": {"qty": 400, "avg": 120.0, "last": 100.0}, "FINE": {"qty": 200, "avg": 90.0, "last": 100.0}, "TINY": {"qty": 5, "avg": 50.0, "last": 100.0}},
            "cash_inr": 30000.0, "options_inr": 34000.0}
    (tmp_path / "paper" / "account" / "state.json").write_text(json.dumps(twin))
    sug = [{"symbol": "WEAK", "action": "REDUCE", "grade": "D", "suggest_inr": 5000, "why": "Weak (21/100): below its averages. Halving it limits the damage.", "wrong_if": "x"},
           {"symbol": "TINY", "action": "TIDY", "grade": "C", "suggest_inr": 500, "why": "Only ₹500: too small to matter either way.", "wrong_if": "x"},
           {"symbol": "FINE", "action": "TRIM", "grade": "C", "suggest_inr": 400, "why": "a ₹400 trim", "wrong_if": "x"}]
    (tmp_path / "paper" / "allocation_view.json").write_text(json.dumps({"suggestions": sug}))
    bars = _bars({"WEAK": (-0.001, 0.01), "FINE": (0.0003, 0.01), "TINY": (0.0, 0.01),
                  "CALM": (0.0006, 0.006), "WILD": (0.0012, 0.03), "DOWN": (-0.002, 0.01), "STRETCH": (0.004, 0.004)})
    monkeypatch.setattr(m, "bars", lambda: bars)
    monkeypatch.setattr(m, "nifty500", lambda: {"CALM": "Healthcare", "WILD": "IT", "DOWN": "Metals", "STRETCH": "Realty", "WEAK": "Power", "FINE": "FMCG", "TINY": "Media"})
    monkeypatch.setattr(m, "holidays", lambda: set())
    return tmp_path


def test_the_plan_cuts_the_weak_names_and_buys_a_calm_replacement_before_the_open(world, monkeypatch):
    monkeypatch.setattr(m, "refuse_late", lambda s: None)
    v = m.run(DAY)
    p = v["plan"]
    assert p["for_session"] == "2026-11-02" and not p.get("error")
    cuts = {c["symbol"]: c for c in p["cuts"]}
    assert set(cuts) == {"WEAK", "TINY"}                       # the ₹400 trim is noise (min_cut_inr); TIDY sells all
    assert cuts["TINY"]["all"] and not cuts["WEAK"]["all"] and cuts["WEAK"]["inr"] == 5000
    assert [b["symbol"] for b in p["buys"]] == ["CALM"]         # WILD is not calm, DOWN is under its averages, STRETCH is stretched
    assert p["buys"][0]["for_cut"] == "WEAK" and p["buys"][0]["inr"] == 5000 and "calm" in p["buys"][0]["why"]
    assert p["sha"] and p["prev_sha"] == "" and m.chain_ok()[0]
    assert "replaces WEAK" in p["brief"] and "7% stop" in p["brief"]
    assert v["clock"]["sessions"] == 1 and v["clock"]["of"] == 60 and "session 60" in v["clock"]["words"]


def test_fills_at_the_next_open_with_the_no_chase_check_and_the_stop(world, monkeypatch):
    monkeypatch.setattr(m, "refuse_late", lambda s: None)
    m.run(DAY)
    bars = m.bars()
    nxt = pd.Timestamp("2026-11-02")
    last = bars[bars["date"] == pd.Timestamp(DAY)].set_index("symbol")
    add = []
    for sym in last.index:
        c = float(last.loc[sym, "close"])
        o = c * (1.05 if sym == "CALM" else 1.0)            # CALM gaps 5% up: not chased
        add.append({"symbol": sym, "date": nxt, "open": o, "high": o * 1.01, "low": o * 0.99, "close": o, "volume": 1e6, "turnover": 2e8})
    bars2 = pd.concat([bars, pd.DataFrame(add)], ignore_index=True)
    monkeypatch.setattr(m, "bars", lambda: bars2)
    v = m.run("2026-11-02")
    fills = {t["symbol"]: t for t in v["filled_today"]}
    assert fills["WEAK"]["filled"] and fills["WEAK"]["side"] == "SELL" and fills["TINY"]["filled"]
    assert fills["CALM"].get("skipped", "").startswith("opened +5.0% above") and "not chased" in fills["CALM"]["skipped"]
    book = json.loads((world / "paper" / "managed" / "state.json").read_text())
    assert "TINY" not in book["positions"] and book["positions"]["WEAK"]["qty"] < 400 and "CALM" not in book["positions"]
    led = [json.loads(x) for x in (world / "paper" / "managed" / "ledger.jsonl").read_text().splitlines()]
    assert {r["symbol"] for r in led} == {"WEAK", "TINY", "CALM"} and all(r["for_session"] == "2026-11-02" for r in led)
    # a flat open fills the buy and sets the 7% stop
    bars3 = bars2.copy()
    bars3.loc[(bars3["symbol"] == "CALM") & (bars3["date"] == nxt), ["open", "close"]] = float(last.loc["CALM", "close"])
    monkeypatch.setattr(m, "bars", lambda: bars3)
    book["filled_plans"] = []
    (world / "paper" / "managed" / "state.json").write_text(json.dumps(book))
    v = m.run("2026-11-02")
    f = {t["symbol"]: t for t in v["filled_today"]}
    assert f["CALM"]["filled"] and f["CALM"]["stop"] == round(f["CALM"]["price"] * 0.93, 2)
    assert v["replacements"][0]["symbol"] == "CALM" and v["replacements"][0]["for_cut"] == "WEAK"


def test_a_plan_is_refused_once_the_session_has_opened():
    with pytest.raises(RuntimeError):
        m.refuse_late("2020-01-01")


def test_the_chain_breaks_when_a_plan_is_edited(world, monkeypatch):
    monkeypatch.setattr(m, "refuse_late", lambda s: None)
    m.run(DAY)
    p = world / "paper" / "managed" / "plans.jsonl"
    rows = [json.loads(x) for x in p.read_text().splitlines()]
    rows[0]["buys"] = []
    p.write_text(json.dumps(rows[0]) + "\n")
    ok, why = m.chain_ok()
    assert not ok and "breaks the chain" in why


def test_the_ledger_scores_cut_right_and_replacement_rose(world, monkeypatch):
    led = [{"plan": "mp-2026-10-01", "for_session": "2026-10-01", "side": "SELL", "symbol": "WEAK", "price": 110.0, "filled": True, "scored": {}},
           {"plan": "mp-2026-10-01", "for_session": "2026-10-01", "side": "BUY", "symbol": "CALM", "for_cut": "WEAK", "price": 95.0, "filled": True, "scored": {}}]
    (world / "paper" / "managed" / "ledger.jsonl").write_text("".join(json.dumps(r) + "\n" for r in led))
    out = m.score(DAY)
    rows = [json.loads(x) for x in (world / "paper" / "managed" / "ledger.jsonl").read_text().splitlines()]
    assert all("+5" in r["scored"] and "+20" in r["scored"] for r in rows)
    buy = next(r for r in rows if r["side"] == "BUY")
    assert "minus_cut_pct" in buy["scored"]["+20"] and out["fills"] == 2 and out["cuts_scored_5"] == 1
