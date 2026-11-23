"""23 Nov 2026 (India morning review): with the Claude credit empty the 10:20 opening update crashed with HTTP 400 and wrote nothing.
It now sends the live facts in their own words and says the model could not run."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load():
    spec = importlib.util.spec_from_file_location("india_morningview_t23", ROOT / "scripts" / "india_morningview.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_the_opening_update_goes_out_with_the_facts_when_the_model_fails(monkeypatch):
    mv = _load()
    live = {"clock": {"words": "Monday 23 Nov, 10:20 in India, the market is open"}, "index_now": {"words": "Nifty 25,900 (+0.4%)"},
            "options_today": {"words": "8 decisions, no trade", "taken": []}}

    def get(path):
        return {"session": "2026-11-23", "lines": {}} if path == "/v3/morning/facts" else live

    def broken(*a, **k):
        raise RuntimeError("HTTP Error 400: Bad Request")

    sent, pushed = [], []
    monkeypatch.setattr(mv, "_get", get)
    monkeypatch.setattr(mv, "_ist_today", lambda: "2026-11-23")
    monkeypatch.setattr(mv, "claude", broken)
    monkeypatch.setattr(mv, "_post", lambda url, body, *a, **k: sent.append(body) or {})
    monkeypatch.setattr(mv, "_push", lambda t, b: pushed.append(b))
    assert mv.opening() == 0
    words = sent[-1]["opening"]
    assert "could not run" in words and "credit" in words
    assert "Nifty 25,900" in words and "no trade" in words
    assert pushed


def test_no_live_block_says_so():
    mv = _load()
    w = mv.opening_from_facts({"opening_decisions": [{"note": "x"}]}, "timeout")
    assert "could not be read" in w and "credit" not in w
