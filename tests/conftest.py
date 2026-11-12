"""Tests never push to a real phone, even when run on the laptop where .env holds the ntfy topic; and they never reach the web
or touch the live paid-search counters."""
import os

import pytest

os.environ["ANANTA_NTFY_TOPIC"] = ""


@pytest.fixture(autouse=True)
def _no_live_web(tmp_path, monkeypatch):
    """Oct 15: a test that reached the brain's web veto made real requests (with fake keys) and counted against the LIVE paid-search
    cap in ~/ananta_runs/web_paid.json: the brain's 8 background searches for Oct 15 were used up by 04:32, partly by test runs.
    Now every test keeps its counters in its own folder, and weblook's network call refuses."""
    from jarvis.service import weblook

    monkeypatch.setenv("WEB_PAID_FILE", str(tmp_path / "web_paid.json"))
    monkeypatch.setenv("WEB_PAID_LOG", str(tmp_path / "web_paid_log.jsonl"))

    def _no_web(*a, **k):
        raise RuntimeError("tests never reach the web")

    monkeypatch.setattr(weblook, "_post", _no_web)
    weblook._MC.clear()


@pytest.fixture(autouse=True)
def _no_live_kite_sign_in(tmp_path, monkeypatch):
    """12 Nov 2026 (the keen outside audit, G-54 and G-57): on the Mac, a test that asked india.kite for a token with none on disk could
    start the real password sign-in (test_kite_token_expiry did, since 22 Oct), and the phone note read its topic from the .env file
    whatever the tests' switch said. No test starts a sign-in, writes the live attempt, refusal or note stamps, or reaches the phone."""
    try:
        from india import kite
    except Exception:  # noqa: BLE001  a checkout without the India package
        return
    monkeypatch.setattr(kite, "AUTO_ENV", tmp_path / "no_auto_sign_in.env")
    monkeypatch.setattr(kite, "ATTEMPTS_FILE", tmp_path / "kite_auto_attempts.json")
    monkeypatch.setattr(kite, "REFUSALS_LOG", tmp_path / "kite_refusals.log")
    monkeypatch.setattr(kite, "NOTE_STAMP", tmp_path / "kite_note_stamp.json")
