"""7 Nov 2026 (Madhav): on Today the index boxes open charts and the portfolio box its performance over time (/v3/chart/PORTFOLIO from the
nightly account benchmark); on Proof the two top cards open an explanation written from the nightly facts, with an Ask Ananta button."""
from __future__ import annotations

import json

from fastapi.testclient import TestClient

from jarvis.india import service, surfaces


def test_the_portfolio_chart_comes_from_the_benchmark_with_a_nifty_500_line_from_the_same_start(tmp_path):
    acct = tmp_path / "paper" / "account"
    acct.mkdir(parents=True)
    rows = [{"day": "2026-10-29", "twin_inr": 160499, "frozen_inr": 160536, "start_inr": 162509, "twin_ret_pct": -1.24, "frozen_ret_pct": -1.21, "nifty500_ret_pct": 1.13},
            {"day": "2026-10-30", "twin_inr": 162645, "frozen_inr": 163076, "start_inr": 162509, "twin_ret_pct": 0.08, "frozen_ret_pct": 0.35, "nifty500_ret_pct": 0.92,
             "managed_inr": 162572, "managed_ret_pct": 0.04, "managed_sessions": 1},
            {"day": "2026-11-06", "twin_inr": 165383, "frozen_inr": 167821, "start_inr": 162509, "twin_ret_pct": 1.77, "frozen_ret_pct": 3.27, "nifty500_ret_pct": 8.12,
             "managed_inr": 163885, "managed_ret_pct": 2.11, "managed_sessions": 5}]
    (acct / "benchmark.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    c = surfaces.portfolio_chart(tmp_path)
    assert c["kind"] == "portfolio" and c["as_of"] == "2026-11-06" and c["sessions"] == 3
    assert c["chart"]["dates"] == ["2026-10-29", "2026-10-30", "2026-11-06"] and c["chart"]["yours"] == [160499, 162645, 165383]
    assert c["chart"]["managed"] == [None, 162572, 163885] and c["chart"]["nifty500"] == [164345, 164004, 175705]
    assert "your holdings on paper ₹1,65,383 (+1.77%)" in c["words"] and "the Nifty 500 +8.12% from the same start" in c["words"]
    assert surfaces.portfolio_chart(tmp_path / "nowhere")["chart"]["dates"] == []


def test_the_proof_explanations_are_written_from_the_facts():
    rm = {"data_through": "2026-11-06",
          "research": {"versions_tested": 1440, "verdicts": {"VALIDATED": 44, "CONDITIONAL": 38, "REJECTED": 511, "OPPOSITE": 158, "INCONCLUSIVE": 661},
                       "exam": {"runs": 6, "passed": 4, "last": {"day": "2026-11-05", "known": 16, "known_of": 18, "unknown": 2, "unknown_of": 7, "why": 5, "why_of": 5,
                                                                  "safety": 38, "plain": 38, "of": 39, "exam_pass": False}}},
          "indicator_knowledge": {"families": {
              "RSI and stochastic": {"tested": [{"what": "RSI(14) over 70 when bought", "verdict": "VALIDATED"}, {"what": "the stochastic under 20", "verdict": "INCONCLUSIVE"}]},
              "MACD": {"tested": [{"what": "study XO1", "verdict": {"REJECTED": 3}}]},
              "breadth": {"tested": [{"what": "a breadth thrust", "verdict": "INCONCLUSIVE"}]},
              "support and resistance": {"tested": [{"what": "selling below the last 5-session low", "verdict": "REJECTED"}, {"what": "study SR1", "verdict": {"OPPOSITE": 1}}]}}}}
    s = surfaces.studies_explain(rm)
    pts = " ".join(s["points"])
    assert "1440 versions were tested on 2000-2017" in pts and "44 held up in both periods, 38 held with conditions, 511 did not hold, 158 showed the opposite" in pts
    assert "RSI(14) over 70 when bought" in pts and "What did not hold" in pts and "MACD, support and resistance" in pts and "breadth" not in pts.split("What did not hold")[1]
    assert s["updated"] == "Fri 6 Nov close" and s["ask"].startswith("Explain the versions tested")
    replay = {"night": "2026-11-06", "today_turns": 4, "today_failed": 0, "bank_checked": 5, "bank_failed": 2, "bank_open": 4, "bank_fixed": 22, "never_again_checked": 33, "never_again_failed": 1}
    e = surfaces.exam_explain(replay, rm["research"])
    pts = " ".join(e["points"])
    assert "Last night (Fri 6 Nov): 4 of 4 of the day's answers passed; the regression bank 3 of 5 (22 fixed for good, 4 still open); the never-again cases 32 of 33" in pts
    assert "The weekly India exam (Thu 5 Nov): knows 16 of 18" in pts and "FAIL; 4 of 6 runs passed" in pts and "Still open: 4" in pts
    assert e["updated"] == "Fri 6 Nov night"
    e2 = surfaces.exam_explain(None, {})
    assert "has not written a result yet" in " ".join(e2["points"])


def test_the_chart_endpoint_serves_the_portfolio(tmp_path, monkeypatch):
    acct = tmp_path / "paper" / "account"
    acct.mkdir(parents=True)
    (acct / "benchmark.jsonl").write_text(json.dumps({"day": "2026-11-05", "twin_inr": 1, "frozen_inr": 1, "start_inr": 1, "nifty500_ret_pct": 0}) + "\n"
                                           + json.dumps({"day": "2026-11-06", "twin_inr": 2, "frozen_inr": 2, "start_inr": 1, "nifty500_ret_pct": 100}) + "\n")
    monkeypatch.setattr(surfaces, "DATA", tmp_path)
    c = TestClient(service.app, client=("127.0.0.1", 50000))
    r = c.get("/v3/chart/portfolio")
    assert r.status_code == 200 and r.json()["chart"]["yours"] == [1, 2] and r.json()["chart"]["nifty500"] == [1, 2]
    assert surfaces.views.ROUTES["chart/portfolio"] is surfaces.portfolio_chart
