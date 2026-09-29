from src.intelligence.paper_path import decide, issued_from_paper, run_fixture


def test_fixture_is_not_a_market_trade(tmp_path):
    report = run_fixture(tmp_path / "proof.json")
    assert report["status"] == "FIXTURE_PASS"
    assert report["not_a_market_trade"] is True
    assert report["cases"]["fixture_squeeze"]["issued"] == "TAKE"
    assert report["cases"]["fixture_squeeze"]["evidence_class"] == "FIXTURE"
    assert report["cases"]["fixture_squeeze"]["market"] is False
    assert report["cases"]["fixture_squeeze"]["m2"] is False
    assert report["cases"]["fixture_squeeze"]["exec"] is False
    assert report["cases"]["family_match_not_setup"]["issued"] == "NO_TRADE"
    assert report["cases"]["continuation"]["issued"] == "SHADOW_PAPER"
    assert report["cases"]["set16"]["issued"] == "WATCH"
    assert report["cases"]["forced_take_without_receipt"]["issued"] == "NO_TRADE"


def test_live_after_proof_is_paper_not_authority(tmp_path):
    proof = tmp_path / "proof.json"
    assert run_fixture(proof)["status"] == "FIXTURE_PASS"
    live = decide({"asset": "BTC", "tf": "1h", "regime": "COMPRESSION", "direction": "NONE", "source": "LIVE", "squeeze_qualifying": True}, proof_path=proof)
    assert issued_from_paper(live) == "TAKE"
    assert live["evidence_class"] == "LIVE_PAPER"
    assert live["exec"] is False
    assert live["counts_for_m2"] is False
    assert live["authority_granted"] is False
    assert live["not_validated"] is True
