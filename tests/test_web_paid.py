"""Oct 12 review: 22 of 25 paid web searches were gone by 2 AM, spent by the brain's market checks. Background callers now get at
most WEB_PAID_BACKGROUND a day, a person asking can use the whole cap, and every paid search is logged with who and why."""
import json

from jarvis.service import weblook


def _setup(tmp_path, monkeypatch, daily=5, bg=2):
    monkeypatch.setenv("WEB_PAID_FILE", str(tmp_path / "paid.json"))
    monkeypatch.setenv("WEB_PAID_LOG", str(tmp_path / "paid.jsonl"))
    monkeypatch.setattr(weblook, "PAID_DAILY", daily)
    monkeypatch.setattr(weblook, "PAID_BACKGROUND", bg)


def test_background_gets_its_own_smaller_share(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    assert weblook._paid_ok("brain", "market_check: BTC", "429 quota")
    assert weblook._paid_ok("brain", "market_check: ETH")
    assert not weblook._paid_ok("brain", "market_check: SOL")          # background share used
    assert weblook._paid_ok("ask", "lookup: fed")                         # a person still gets answers
    assert weblook._paid_ok("ask")
    assert weblook._paid_ok("ask")
    assert not weblook._paid_ok("ask")                                    # the whole cap (5) is used
    t = weblook.paid_today()
    assert t["used"] == 5 and t["by"] == {"brain": 2, "ask": 3}
    lines = [json.loads(x) for x in (tmp_path / "paid.jsonl").read_text().splitlines()]
    assert len(lines) == 5 and lines[0]["who"] == "brain" and lines[0]["free_failed"] == "429 quota"


def test_old_file_format_still_counts(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    import time

    (tmp_path / "paid.json").write_text(json.dumps({time.strftime("%Y-%m-%d"): 4}))
    assert weblook._paid_ok("ask")
    assert not weblook._paid_ok("ask")


def test_no_paid_key_never_counts_and_tests_never_reach_the_web(tmp_path, monkeypatch):
    """Oct 15: runs without an Anthropic key (tests, scripts) used to count against the live cap before failing."""
    _setup(tmp_path, monkeypatch)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    r = weblook.market_check(None, "ETH", who="brain")
    assert "error" in r and "ANTHROPIC_API_KEY is not set" in r["error"]
    assert weblook.paid_today()["used"] == 0 and not (tmp_path / "paid.jsonl").exists()
    monkeypatch.setenv("GEMINI_API_KEY", "fake")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake")
    r = weblook.lookup("what moved crypto today")
    assert "tests never reach the web" in r["error"] and weblook.paid_today()["used"] == 1     # counted in the test's own file only
