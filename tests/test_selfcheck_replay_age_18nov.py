"""18 Nov 2026: the nightly replay was stuck from 15 Nov, yet the self-check still called the
14 Nov result "last night's replay". An old replay is now named as old (medium) and dated."""
import datetime as dt
import json

from jarvis import selfcheck


def _write(tmp_path, night, failures):
    d = tmp_path / "docs" / "repair_shop" / "replay"
    d.mkdir(parents=True)
    (d / "latest.json").write_text(json.dumps({"summary": {"night": night}, "failures": failures}))


BAD = [{"source": "never_again", "text": "Why still Friday?", "problems": [{"why": "skips the question"}]}]


def test_old_replay_is_named_old(tmp_path):
    _write(tmp_path, "2026-11-14", BAD)
    out = selfcheck._answers(tmp_path, dt.date(2026, 11, 18))
    assert out[0]["severity"] == "medium"
    assert "has not finished since the night of 2026-11-14 (4 days ago)" in out[0]["what"]
    assert out[1]["what"].startswith("the replay of 2026-11-14 found 1")
    assert not any("last night's" in o["what"] for o in out)


def test_fresh_replay_keeps_last_night(tmp_path):
    _write(tmp_path, "2026-11-17", BAD)
    out = selfcheck._answers(tmp_path, dt.date(2026, 11, 18))
    assert len(out) == 1 and out[0]["severity"] == "low"
    assert out[0]["what"].startswith("last night's replay (2026-11-17) found 1")


def test_fresh_clean_replay_says_nothing(tmp_path):
    _write(tmp_path, "2026-11-17", [])
    assert selfcheck._answers(tmp_path, dt.date(2026, 11, 18)) == []
