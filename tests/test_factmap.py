"""The gate (Madhav, 2 Nov 2026: "everything has to be mapped perfectly to the voice agent ... I'm not sure if it is not gonna miss again").

A new feature that writes a file nothing Ananta reads, and that is not marked internal with a reason, fails the suite: it cannot be committed
(the pre-commit hook runs the tests) until its facts have a route into the Ask, the voice and the screens, or a written reason not to."""
import os
import time
from pathlib import Path

import pytest

from jarvis.india import factmap


def _make(root: Path, rel: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("{}")


def test_a_new_unread_file_has_no_route(tmp_path, monkeypatch):
    monkeypatch.setattr(factmap, "DATA", tmp_path)
    _make(tmp_path, "paper/newbook/view.json")                      # a feature nobody wired into the Ask
    _make(tmp_path, "manifests/cm_bhavcopy.jsonl")                  # an ingest log: internal with its reason
    rows = {r["pattern"]: r for r in factmap.routes(factmap.producers(time.time()))}
    assert rows["paper/newbook/view.json"]["route"] == "NONE"
    assert rows["manifests/cm_bhavcopy.jsonl"]["route"] == "internal"


def test_a_daytime_file_read_only_at_night_is_a_today_gap():
    rows = [{"pattern": "paper/sp1/decisions.jsonl", "route": "nightly", "daytime": True, "mtime": time.time()}]
    out = factmap.behind(rows, "2026-11-02T12:00:00+00:00")
    assert out and out[0]["state"] == "FAIL" and "today gap" in out[0]["check"]


@pytest.mark.skipif(not (Path(os.path.expanduser("~/ananta_data/india")) / "paper").exists(), reason="the India data lives on Madhav's Mac")
def test_every_file_the_india_jobs_write_has_a_route():
    rows = factmap.routes(factmap.producers())
    none = [r["pattern"] for r in rows if r["route"] == "NONE"]
    gaps = [c["check"] for c in factmap.behind(rows, "1970-01-01T00:00:00+00:00") if c["state"] == "FAIL"]
    assert not none, f"files with no route into what Ananta says (wire them into the Ask or mark them internal with a reason): {none}"
    assert not gaps, f"written during the Indian session but read only at night: {gaps}"
