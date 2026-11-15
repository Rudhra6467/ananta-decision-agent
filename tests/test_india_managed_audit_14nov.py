"""14 Nov 2026 (Madhav, 22:17): the managed book graded against the market, its headline split in three, and the evening decision audit."""
import json

import pandas as pd

from india import managed as m
from india import managed_audit as a


def _n500():
    return pd.Series([100.0, 101.0, 105.0, 110.0], index=pd.to_datetime(["2026-10-30", "2026-11-02", "2026-11-03", "2026-11-09"]))


def test_market_ret_runs_from_the_close_before_the_fill():
    assert round(m._market_ret(_n500(), "2026-11-02", "2026-11-09"), 6) == 10.0
    assert m._market_ret(_n500(), "2026-10-30", "2026-11-09") is None          # no close before the first
    assert m._market_ret(_n500(), "2026-11-10", "2026-11-09") is None          # scored before it filled


def test_split_adds_back_money_moved_into_options(monkeypatch):
    monkeypatch.setattr(m, "next_session", lambda d: pd.Timestamp("2026-11-02").date())
    book = {"start_day": "2026-10-30", "start_inr": 160499.0, "options_inr": 50000.0, "cash_inr": 27614.0,
            "positions": {"X": {"qty": 1, "last": 86086.0}}, "sleeve_moves": [{"inr": 16000.0, "from": "cash", "to": "options"}]}
    s = m.split(book, "2026-11-09", {"result_inr": 17466}, _n500())
    assert s["stocks_cash_start_inr"] == 126499 and s["stocks_cash_inr"] == 3201
    assert s["market_pct"] == 10.0 and s["stocks_vs_market_pct"] == round(s["stocks_cash_pct"] - 10.0, 2)
    assert "options +₹17,466" in s["words"]


def test_audit_flags_idle_cash_and_crowded_cuts(tmp_path, monkeypatch):
    monkeypatch.setenv("INDIA_DATA_DIR", str(tmp_path))
    d = tmp_path / "paper" / "managed"
    d.mkdir(parents=True)
    monkeypatch.setattr(m, "sessions_between", lambda x, y: 8)
    (d / "view.json").write_text(json.dumps({"day": "2026-11-13", "clock": {"sessions": 9},
                                             "split": {"cash_inr": 27614, "cash_share_pct": 21.3, "stocks_vs_market_pct": -5.9, "stocks_cash_pct": 2.5, "market_pct": 8.4, "options_inr": 17466}}))
    (d / "state.json").write_text(json.dumps({"positions": {"A": {}, "B": {}}, "sessions": []}))
    led = [{"plan": "p", "for_session": "2026-11-02", "side": "SELL", "symbol": s, "filled": True, "scored": {"+5": {"vs_market_pct": 1.0, "ret_pct": 3}}} for s in "CDEFG"]
    led.append({"plan": "p", "for_session": "2026-11-02", "side": "BUY", "symbol": "A", "filled": True, "for_cut": "C", "scored": {}})
    (d / "ledger.jsonl").write_text("".join(json.dumps(r) + "\n" for r in led))
    monkeypatch.setattr(m, "_plans", lambda: [{"for_session": "2026-11-02", "cuts": [{"symbol": s} for s in "CDEFG"]}])
    monkeypatch.setattr(m, "chain_ok", lambda: (True, "chain intact"))
    r = {c["check"]: c for c in a.audit()["checks"]}
    assert r["cuts_vs_market_5"]["status"] == "FLAG"                  # 0 of 5 did worse than the market
    assert r["idle_cash"]["status"] == "FLAG"
    assert r["crowded_cuts"]["status"] == "FLAG"                     # 5 cuts out of 6 held before the plan
    assert r["stocks_vs_market"]["status"] == "WATCH"
