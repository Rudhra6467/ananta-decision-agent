"""The nightly backup keeps the files that are not databases but cannot be rebuilt (research audit, Oct 15): the Explorer's live state
(trades finished but not yet saved to its book) and the paid-search log and counter."""
import importlib.util
import sqlite3
import tarfile
from pathlib import Path

SPEC = importlib.util.spec_from_file_location("backup_db", Path(__file__).resolve().parents[1] / "scripts" / "backup_db.py")
B = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(B)


def _home(tmp_path, monkeypatch, with_counter=True):
    agent = tmp_path / "home" / "code" / "ananta-decision-agent"
    runs = tmp_path / "home" / "ananta_runs"
    agent.mkdir(parents=True)
    runs.mkdir(parents=True)
    with sqlite3.connect(agent / "jarvis.sqlite") as c:
        c.execute("CREATE TABLE evidence_trades (id TEXT)")
        c.execute("INSERT INTO evidence_trades VALUES ('T1')")
    (agent / "explorer_state.pkl").write_bytes(b"state")
    (agent / "notes.txt").write_text("not an extra")
    (runs / "web_paid_log.jsonl").write_text('{"t": 1}\n')
    if with_counter:
        (runs / "web_paid.json").write_text('{"2026-10-15": 3}')
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path / "home"))
    monkeypatch.setattr(B, "AGENT", agent)
    monkeypatch.setattr(B, "OUT", tmp_path / "backups")
    (tmp_path / "backups").mkdir()
    return agent


def test_the_backup_copies_the_state_file_and_the_paid_search_log_beside_the_databases(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    d = B.backup("2026-10-15")
    assert sorted(p.name for p in d.iterdir()) == ["explorer_state.pkl", "jarvis.sqlite", "web_paid.json", "web_paid_log.jsonl"]
    assert (d / "explorer_state.pkl").read_bytes() == b"state" and (d / "web_paid_log.jsonl").read_text() == '{"t": 1}\n'
    with sqlite3.connect(d / "jarvis.sqlite") as c:
        assert c.execute("SELECT COUNT(*) FROM evidence_trades").fetchone()[0] == 1


def test_an_extra_that_does_not_exist_yet_is_skipped_not_fatal(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch, with_counter=False)
    assert [p.name for p in B.extras()] == ["explorer_state.pkl", "web_paid_log.jsonl"]
    assert "web_paid.json" not in [p.name for p in B.backup("2026-10-16").iterdir()]


def test_the_archive_sent_to_r2_holds_every_file_of_the_day(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    tgz = B.pack(B.backup("2026-10-15"))
    with tarfile.open(tgz) as t:
        assert sorted(t.getnames()) == ["2026-10-15/explorer_state.pkl", "2026-10-15/jarvis.sqlite", "2026-10-15/web_paid.json",
                                        "2026-10-15/web_paid_log.jsonl"]
