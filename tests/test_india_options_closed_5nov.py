"""5 Nov 2026 (Madhav's chat): a Bank Nifty short closed by its stop was described as still open at today's option price."""
import json

from jarvis.india import livesession as ls


def test_a_trade_the_line_scored_as_stopped_is_said_as_closed(tmp_path, monkeypatch):
    dec = {"date": "2026-11-05", "kind": "decision", "index": "BANKNIFTY", "point": "D0", "decided_at": "2026-11-05T09:15:30+05:30",
           "choice": {"dir": -1, "exit": "ATRSTOP"}, "entry_estimate": 57086.7,
           "contracts": {"option": {"tradingsymbol": "BANKNIFTY26NOV57100PE", "strike": 57100, "type": "PE", "lot": 30, "expiry": "2026-11-23"}},
           "quotes_at_decision": {"NFO:BANKNIFTY26NOV57100PE": 770.75}}
    p = tmp_path / "decisions.jsonl"
    p.write_text(json.dumps(dec) + "\n")
    out = {("BANKNIFTY", "D0"): {"index_proxy": {"stopped": True, "net_bps": -69.4},
                                 "legs": {"option": {"entry_realistic": 811.05, "exit": 577.25, "net_rs_realistic": -7252.7}}}}
    monkeypatch.setattr(ls, "_scored", lambda day: out)
    fetch = lambda syms: {s: {"last_price": 478.0 if "PE" in s else 57773.65, "ohlc": {"close": 55913.6}} for s in syms}  # noqa: E731
    clk = {"latest_session": "2026-11-05", "latest_session_words": "Thursday 5 Nov", "state": "closed", "today_india": "2026-11-05"}
    monkeypatch.setattr(ls, "DATA", tmp_path / "data")
    (tmp_path / "data" / "paper" / "sp1").mkdir(parents=True)
    (tmp_path / "data" / "paper" / "sp1" / "decisions.jsonl").write_text(p.read_text())
    r = ls.options_today(clk, fetch)
    w = r["words"]
    assert "CLOSED: its stop was hit" in w and "Rs -7,253" in w and "577.25" in w
    assert "478" not in w and "ATRSTOP" not in w
