"""The crypto news shadow (25 Oct 2026, Madhav's yes; Rule B: forward, blind, record-only): headlines from the stored news check, an append-only
log, the database opened read-only, and nothing that decides ever reads the log."""
import importlib.util
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("hf_news_shadow", ROOT / "scripts" / "hf_news_shadow.py")
S = importlib.util.module_from_spec(spec)
spec.loader.exec_module(S)


def fake_probs(texts):
    return [[0.7, 0.2, 0.1] if "launch" in t.lower() else [0.1, 0.8, 0.1] for t in texts]


def _db(tmp_path: Path) -> Path:
    db = tmp_path / "jarvis.sqlite"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE news_log (day TEXT, coin TEXT, t INTEGER, verdict TEXT, why TEXT, json TEXT, PRIMARY KEY (day, coin))")
    js = json.dumps({"verdict": "CLEAR", "damage": [], "supply": [{"headline": "ETF shuts down", "note": "x"}], "catalysts": [{"headline": "Labs launch wallet"}]})
    con.execute("INSERT INTO news_log VALUES ('2026-10-25', 'DOGE', 1, 'CLEAR', 'w', ?)", (js,))
    con.execute("INSERT INTO news_log VALUES ('2026-10-25', 'BTC', 1, 'CAUTION', 'w', '{}')")
    con.commit()
    con.close()
    return db


def test_headlines_are_found_anywhere_without_repeats():
    js = json.dumps({"a": [{"headline": "One"}, {"headline": "One"}], "b": {"c": [{"headline": "Two"}]}})
    assert S.headlines(js) == ["One", "Two"]
    assert S.headlines("not json") == []


def test_log_is_append_only_and_the_db_read_only(tmp_path):
    db, log = _db(tmp_path), tmp_path / "news_ratings.jsonl"
    rows = S.pending(db, log)
    assert {(r["day"], r["coin"]) for r in rows} == {("2026-10-25", "DOGE"), ("2026-10-25", "BTC")}
    recs = S.rate(rows, probs=fake_probs)
    assert S.append(recs, log) == 2
    assert S.append(recs, log) == 0                       # never written twice
    assert S.pending(db, log) == []
    doge = next(json.loads(x) for x in log.read_text().splitlines() if '"DOGE"' in x)
    assert doge["check_verdict"] == "CLEAR" and len(doge["headlines"]) == 2 and doge["tone"] is not None
    try:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        con.execute("INSERT INTO news_log VALUES ('x','y',1,'a','b','{}')")
        raise AssertionError("read-only connection wrote")
    except sqlite3.OperationalError:
        pass


def test_nothing_that_decides_reads_the_shadow_log():
    hits = []
    for base in ("jarvis", "src"):
        for f in (ROOT / base).rglob("*.py"):
            t = f.read_text(errors="ignore")
            if "hf_shadow" in t or "news_ratings.jsonl" in t or "hf_news_shadow" in t:
                hits.append(str(f.relative_to(ROOT)))
    assert hits == [], hits
