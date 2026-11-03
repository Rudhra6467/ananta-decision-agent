"""3 Nov 2026 (data audit step 3): NSE's board-meetings calendar, kept point in time, joined into the desk's results ahead."""
import datetime as dt
import gzip
import json

from india import boardmeetings as bm


def _row(sym, day, purpose, ts):
    return {"bm_symbol": sym, "sm_isin": "INE" + sym, "sm_name": sym + " Ltd", "bm_date": day, "bm_purpose": purpose, "bm_desc": "to consider", "bm_timestamp": ts}


def _put(p, data):
    p.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(p, "wb") as fh:
        fh.write(json.dumps(data).encode())


def test_table_keeps_the_earliest_intimation_and_results_ahead_reads_the_newest_snapshot(tmp_path, monkeypatch):
    monkeypatch.setenv("INDIA_DATA_DIR", str(tmp_path))
    b = tmp_path / "bronze" / "board_meetings"
    _put(b / "history" / "202210.json.gz", [_row("AAA", "20-Oct-2022", "Financial Results", "10-Oct-2022 18:00:00")])
    _put(b / "ahead" / "20261102.json.gz", {"fetched_at": "2026-11-02T23:00:00+00:00",
                                             "rows": [_row("BBB", "05-Nov-2026", "Financial Results", "20-Oct-2026 10:00:00")]})
    _put(b / "ahead" / "20261103.json.gz", {"fetched_at": "2026-11-03T23:00:00+00:00",
                                             "rows": [_row("BBB", "05-Nov-2026", "Financial Results", "21-Oct-2026 10:00:00"),   # seen again later
                                                      _row("CCC", "05-Nov-2026", "Fund Raising", "01-Nov-2026 10:00:00"),
                                                      _row("DDD", "06-Nov-2026", "Un-audited Financial Results", "01-Nov-2026 10:00:00")]})
    t = bm.table()
    bbb = t[t["symbol"] == "BBB"].iloc[0]
    assert len(t[t["symbol"] == "BBB"]) == 1 and str(bbb["intimated_at"]) == "2026-10-20 10:00:00"
    assert str(bbb["first_seen"])[:10] == "2026-11-02"
    assert bool(t.loc[t["symbol"] == "AAA", "is_results"].iloc[0]) and not bool(t.loc[t["symbol"] == "CCC", "is_results"].iloc[0])
    due, snap = bm.results_ahead([dt.date(2026, 11, 5), dt.date(2026, 11, 6)])
    assert snap == "20261103" and due == {"2026-11-05": ["BBB"], "2026-11-06": ["DDD"]}


def test_nothing_fetched_yet_is_an_empty_answer(tmp_path, monkeypatch):
    monkeypatch.setenv("INDIA_DATA_DIR", str(tmp_path))
    assert bm.results_ahead([dt.date(2026, 11, 5)]) == ({}, None)
    assert bm.table().empty
