"""27 Nov 2026 (flag 290, Madhav 26 Nov 22:22): the account page says what Ananta's own decisions added or cost against the two twins."""
import json

from jarvis import placekit as K
from jarvis.india import places as P
from jarvis.india import surfaces as IS


def test_the_block_reads_the_twins(tmp_path, monkeypatch):
    d = tmp_path / "paper" / "managed"
    d.mkdir(parents=True)
    (d / "twins.json").write_text(json.dumps({"status": "ok", "start_day": "2026-10-30", "day": "2026-11-26", "held_inr": 130177, "index_inr": 138477,
                                              "decisions_vs_held_inr": -1063, "decisions_vs_index_inr": -9363}))
    monkeypatch.setattr(IS, "DATA", tmp_path)
    b = P.twins_block()
    assert b["t"] == "kv" and b["title"] == "What its decisions did"
    flat = json.dumps(b, ensure_ascii=False)
    assert "Against holding still" in flat and "−₹1,063" in flat and "Against the index fund" in flat and "−₹9,363" in flat
    assert K.nwords(b.get("foot")) <= K.MAX["foot"]


def test_no_twins_file_no_block(tmp_path, monkeypatch):
    monkeypatch.setattr(IS, "DATA", tmp_path)
    assert P.twins_block() is None
