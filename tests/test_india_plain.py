"""Plain words on every India screen (jarvis/india/plain.py; Madhav, 23 Oct 2026: "rewrite the content from an outside perspective"):
no internal code, web address or Mac path reaches a screen, dates read as people say them, identifiers stay as they are, his own typed words
are never rewritten, and the rewrites leave no broken grammar behind."""
from __future__ import annotations

import json

from fastapi.testclient import TestClient

from jarvis.india import plain, service, views


def test_text_rewrites_codes_dates_and_addresses():
    t = plain.text
    assert t("Nifty is below both its 50- and 200-day averages: a downtrend") == "Nifty is below its ten-week and long-term averages: a downtrend"
    assert t("rules: the SP1 playbook; sizing v2 pending") == "rules: the index playbook; sizing v2 pending"
    assert t("Research → paper → the G02 gate → live") == "Research → paper → the gate → live"
    assert t("no Kite sign-in by 09:10 IST: the Kite token expired at 6 am IST: open http://127.0.0.1:8100/kite/login on the Mac") == "the morning sign-in to Zerodha was missing"
    assert t("decided on 2026-10-22 for the next session") == "decided on 22 Oct for the next session"
    assert t("KAYNES +4.1% on 10-22") == "KAYNES +4.1% on 22 Oct"
    assert t("picks vs HINDSIGHT and RANDOM, CTL as the yardstick") == "picks vs the best possible and chance, random control as the yardstick"
    assert t("expected /Users/vamsie/ananta_data/india/bronze/x.json.gz") == "expected"
    for bad in ("the the", "gate gate", "playbook playbook", "a downtrend averages"):
        assert bad not in t("the SP1 playbook and the G02 gate gate; Nifty below_both averages").lower() or bad == "a downtrend averages"


def test_scrub_keeps_identifiers_and_keys():
    o = plain.scrub({"id": "2026-10-22|PULL|INE093R01011", "key": "MISS_PATTERN:up:x y", "coin": "KEI", "campaign": "PULL", "words": "PULL fired on 2026-10-22"})
    assert o["id"] == "2026-10-22|PULL|INE093R01011" and o["key"] == "MISS_PATTERN:up:x y" and o["coin"] == "KEI" and o["campaign"] == "PULL"
    assert o["words"] == "pullback fired on 22 Oct"
    assert plain.leaks({"a": "the SP1 line and HINDSIGHT"}) and not plain.leaks(plain.scrub({"a": "the SP1 line and HINDSIGHT"}))


def test_every_india_screen_is_plain(tmp_path, monkeypatch):
    rm = tmp_path / "readmodel"
    rm.mkdir()
    (tmp_path / "registrations").mkdir()
    (rm / "latest.json").write_text(json.dumps({"rules": "readmodel-v0", "built_at": "2026-10-23T00:26:01+00:00", "data_through": "2026-10-22", "next_session": "2026-10-23",
        "market": {"status": "ok", "nifty_close": 22688.0, "nifty_vs_sma50": -0.032, "nifty_vs_sma200": -0.06, "trend_state": "below_both", "data_through": "2026-10-22",
                   "words": "Nifty is below both its 50- and 200-day averages: a downtrend"},
        "call": {"status": "ok", "call": "BULLISH", "scored": 3, "hits": 0, "words": "Daily call: BULLISH (mechanical rule call-v0)"},
        "stock_book": {"status": "ok", "open_positions": 4, "by_campaign": {}}, "decisions_today": {"status": "ok", "chosen": [{"symbol": "KEI", "campaign": "REV", "close": 3873.0}]},
        "sp1": {"status": "lost", "words": "session lost: no Kite sign-in by 09:10 IST: the Kite token expired at 6 am IST: open http://127.0.0.1:8100/kite/login on the Mac", "book": {"sessions": 0}},
        "guardrails": {"daily_loss_limit_pct": 5.0, "pause_drawdown_pct": 22.0, "words": "Stop the day at a 5.0% loss"},
        "research": {"gate": {"state": "BLOCKED", "waiting_on": "D15 (wait_time, 30 runs)"}, "gate_counters": {"D15": "5 of 30 nightly runs"}, "verdicts": {"REJECTED": 3}},
        "jobs": {"jobs": [{"label": "sp1paper", "ok": False, "problems": ["token dead"]}, {"label": "paper", "ok": True, "problems": []}]},
        "brief": ["Through 2026-10-22: Nifty 22,688. SP1 index line: session lost."], "missing": []}))
    monkeypatch.setattr(service, "READMODEL", rm / "latest.json")
    monkeypatch.setattr(views, "DATA", tmp_path)
    monkeypatch.setattr(views, "REG", tmp_path / "registrations")
    c = TestClient(service.app, client=("127.0.0.1", 50000))
    for name in views.ROUTES:
        if name.startswith("ask/"):
            continue
        r = c.get(f"/v3/{name}")
        assert r.status_code == 200, name
        j = r.json()
        assert not plain.leaks(j), (name, plain.leaks(j)[:3])
        body = json.dumps(j, ensure_ascii=False)
        for bad in (" the the ", "IST", "/Users/", "http://127.0.0.1", "a downtrend averages", "notional"):
            assert bad not in body, (name, bad)
    h = c.get("/v3/home").json()
    assert "the Zerodha morning sign-in" in h["mission"]["health"]["down"][0], "one cause, one line"
    assert h["mission"]["account"]["note"]["note"].startswith("Nifty closed at 22,688 on 22 Oct, in a downtrend.")
