"""24 Nov 2026 (Madhav's yes in the app, flag 237): while crypto is on hold, India answers do not end with crypto items."""
from jarvis import selfcheck
from jarvis.service import crypto_hold

CRYPTO = {"market": "crypto", "severity": "medium", "source": "cost check",
          "what": "41 NDAX coins cost more a side than the paper books charge"}
INDIA = {"market": "india", "severity": "medium", "source": "options scoring",
         "what": "3 options trades scored this week at an entry more than 0.1% from the decision's own"}


def test_on_hold_the_india_nudge_names_only_india_items(monkeypatch, tmp_path):
    monkeypatch.setattr(crypto_hold, "on", lambda: True)
    monkeypatch.setattr(selfcheck, "check", lambda market, now=None: {"items": [INDIA, CRYPTO]})
    said = selfcheck.nudge("india", tmp_path / "india.json", "t1")
    assert "options trades" in said and "NDAX" not in said and "crypto side" not in said


def test_on_hold_a_crypto_only_list_gives_no_india_nudge(monkeypatch, tmp_path):
    monkeypatch.setattr(crypto_hold, "on", lambda: True)
    monkeypatch.setattr(selfcheck, "check", lambda market, now=None: {"items": [CRYPTO]})
    assert selfcheck.nudge("india", tmp_path / "india.json", "t1") == ""


def test_without_the_hold_the_other_side_is_still_named(monkeypatch, tmp_path):
    monkeypatch.setattr(crypto_hold, "on", lambda: False)
    monkeypatch.setattr(selfcheck, "check", lambda market, now=None: {"items": [CRYPTO]})
    assert "on the crypto side, 41 NDAX" in selfcheck.nudge("india", tmp_path / "india.json", "t1")


def test_the_crypto_side_keeps_its_own_items_on_hold(monkeypatch, tmp_path):
    monkeypatch.setattr(crypto_hold, "on", lambda: True)
    monkeypatch.setattr(selfcheck, "check", lambda market, now=None: {"items": [CRYPTO]})
    assert "NDAX" in selfcheck.nudge("crypto", tmp_path / "crypto.json", "t1")
