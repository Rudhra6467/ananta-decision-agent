"""The Polymarket shadow (Madhav, 27 Oct 2026 00:05: "yes"): the crowd's probability beside Ananta's (Chronos), read-only, hash-chained,
settled from the public resolution, and scored only after 2026-12-15."""
import json
from datetime import datetime, timezone

import pytest

from src.research import chronos_shadow as C
from src.research import polymarket_shadow as P

Q = "Will the price of Bitcoin be above $78,000 on October 28?"
END = "2026-10-28T16:00:00Z"
FC = {"kind": "forecast", "coin": "BTC", "origin_day": "2026-10-27", "made_at": "2026-10-28T08:20:00+00:00",
      "forecast": {"h1": {"quantiles": [76000, 77000, 77500, 78000, 78500, 79000, 79500, 80000, 81000], "p_up": 0.5},
                   "h5": {"quantiles": [70000, 72000, 74000, 76000, 78000, 80000, 82000, 84000, 86000], "p_up": 0.5}}}


@pytest.fixture
def box(tmp_path, monkeypatch):
    monkeypatch.setenv("ANANTA_POLYMARKET_SHADOW_DIR", str(tmp_path / "pm"))
    monkeypatch.setattr(P, "PAUSE", 0)
    monkeypatch.setattr(P, "latest_forecasts", lambda: {"BTC": FC})
    return datetime(2026, 10, 28, 8, 45, tzinfo=timezone.utc).timestamp()


def _q(question=Q, end=END, p=0.6, mid="1"):
    q = P.parse_question(question, end)
    return {**q, "market_id": mid, "question": question, "slug": "s", "crowd": {"p": p}, "volume": 1.0, "liquidity": 1.0, "resolution_source": ""}


def test_only_simple_above_questions_on_btc_and_eth_are_parsed():
    q = P.parse_question(Q, END)
    assert q == {"coin": "BTC", "threshold": 78000.0, "direction": "above", "resolves_at": "2026-10-28T16:00:00+00:00", "date": "2026-10-28"}
    assert P.parse_question("Will the price of Ethereum be above $2,150.5 on November 1?", "2026-11-01T17:00:00Z")["threshold"] == 2150.5
    for other in ("Will Bitcoin reach $105,000 in October?", "Will the price of Bitcoin be between $76,000 and $78,000 on October 28?",
                  "Will the price of Solana be above $150 on October 28?", "Bitcoin Up or Down on October 27?"):
        assert P.parse_question(other, END) is None


def test_crowd_probability_is_the_mid_else_the_listed_price():
    assert P.crowd_p({"outcomePrices": '["0.8515", "0.1485"]', "outcomes": '["Yes", "No"]', "bestBid": 0.85, "bestAsk": 0.86})["p"] == 0.855
    assert P.crowd_p({"outcomePrices": '["0.8515", "0.1485"]', "outcomes": '["Yes", "No"]'})["p"] == 0.8515


def test_ananta_probability_only_on_the_forecast_horizons():
    a = P.ananta_p(_q(), FC)
    assert a["status"] == "ok" and a["horizon_days"] == 1 and a["gap_hours"] == 8.0
    assert a["p"] == round(C.p_up(FC["forecast"]["h1"]["quantiles"], 78000.0), 4) and a["p"] == 0.6         # 78,000 is the 40% quantile: 60% above
    assert P.ananta_p(_q(end="2026-10-29T16:00:00Z", question="Will the price of Bitcoin be above $78,000 on October 29?"), FC)["status"] == "no forecast"
    assert P.ananta_p(_q(end="2026-11-01T16:00:00Z", question="Will the price of Bitcoin be above $78,000 on November 1?"), FC)["horizon_days"] == 5
    assert P.ananta_p(_q(), None)["status"] == "no forecast"


def test_record_once_per_question_per_forecast_day_and_the_chain(box):
    qs = [_q(), _q(question="Will the price of Bitcoin be above $78,000 on October 29?", end="2026-10-29T16:00:00Z", mid="2")]
    r = P.record(now=box, questions=qs)
    assert r["written"] == 2 and r["with_ananta_p"] == 1 and r["chain"]["ok"]
    assert P.record(now=box + 600, questions=qs)["written"] == 0
    rows = P._rows()
    rows[0]["crowd"]["p"] = 0.99
    (P.shadow_dir() / P.LOG).write_text("\n".join(json.dumps(x) for x in rows) + "\n")
    assert P.verify()["ok"] is False


def test_settle_from_the_public_resolution_with_the_binance_check(box, monkeypatch):
    P.record(now=box, questions=[_q()])
    def fake(url):
        if "/markets/1" in url:
            return {"closed": True, "outcomePrices": '["1", "0"]'}
        return [[int(datetime(2026, 10, 28, 16, tzinfo=timezone.utc).timestamp()) * 1000, "0", "0", "0", "78500.0"]]
    monkeypatch.setattr(P, "_get", fake)
    assert P.settle(now=box + 86400)["settled_now"] == 1
    s = P._rows(P.SETTLED)[0]
    assert s["yes"] == 1 and s["binance_check"]["agrees"] is True
    assert P.settle(now=box + 2 * 86400)["settled_now"] == 0


def test_counts_only_before_the_window_and_the_score_after(box, monkeypatch):
    P.record(now=box, questions=[_q()])
    monkeypatch.setattr(P, "_get", lambda url: {"closed": True, "outcomePrices": '["0", "1"]'} if "/markets/" in url else [])
    P.settle(now=box + 86400)
    st = P.status()
    assert st["questions"] == 1 and st["settled_with_both"] == 1 and "record-only shadow, not evidence until 30+ settled" in st["words"]
    assert "Brier" not in json.dumps(st)
    with pytest.raises(P.Sealed):
        P.results(now=P.SEALED_UNTIL - 1)
    res = P.results(now=P.SEALED_UNTIL + 1)
    assert res["n"] == 1 and res["crowd_brier"] == 0.36 and "needs 30+" in res["words"]


def test_ask_mentions_counts_only_when_he_asks_about_it():
    from jarvis.service import ask
    for q in ("what does polymarket say about bitcoin", "how is the prediction market shadow doing", "crowd's odds vs ours?"):
        assert ask.PM_Q.search(q), q
    assert not ask.PM_Q.search("what is the market doing today")
    src = (P.__file__ and open(ask.__file__).read())
    assert "polymarket_shadow.status()" in src and "results(" not in src.split("PM_Q.search(text)")[1][:600]
