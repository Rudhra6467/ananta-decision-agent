"""25 Oct India voice refinement (records side): the reconstruction card's market part survives a decision made on a stale Nifty file, and a
failed job line says when that run ended (the India voice called a fixed job "still failing")."""
import datetime as dt
import json
from pathlib import Path

from india import morning, reconstruct


def test_market_section_fills_a_stale_decision_from_the_read_model(tmp_path, monkeypatch):
    monkeypatch.setattr(reconstruct, "_paper", lambda: tmp_path / "paper")
    monkeypatch.setattr(reconstruct, "_data", lambda: tmp_path)
    (tmp_path / "paper" / "decisions").mkdir(parents=True)
    (tmp_path / "manifests").mkdir()
    (tmp_path / "paper" / "decisions" / "2026-10-23.json").write_text(json.dumps({"context": {"nifty_status": "stale", "breadth200_liq": 0.35}}))
    rm = {"market": {"data_through": "2026-10-23", "nifty_close": 22600.0, "nifty_vs_sma50": -0.034, "nifty_vs_sma200": -0.063, "vix_close": 15.9}}
    s = reconstruct.section_market("2026-10-23", rm)
    assert s["status"] == "ok" and s["nifty_close"] == 22600.0 and s["trend_state"] == "below_both"
    assert "Nifty 22,600" in s["words"] and "stale Nifty file" in s["words"]
    s2 = reconstruct.section_market("2026-10-23", {"market": {}})
    assert s2["status"] == "ok" and "No Nifty close on file" in s2["words"]


def test_autologin_state_carries_its_time(tmp_path: Path):
    log = tmp_path / "kite_autologin.log"
    log.write_text("2026-10-25T14:02:57+00:00 auto sign-in ok: user X until ...\n")
    s = morning.autologin_state(dt.datetime(2026, 10, 25, 12, 0, tzinfo=morning.TOR), log)
    assert s["ok"] and s["t"].hour == 10
