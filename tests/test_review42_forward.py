"""Review 42's forward test on live paper (docs/research/REVIEW_42_FORWARD.md): the NDAX side of a sighting is read from the worker
Mac's recorded quotes, a missing day is "waiting" until a later day exists and "no data" after, and the order fills only when NDAX's ask
trades through it. Recording only: nothing here can trade."""
import sqlite3

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("duckdb")

from src.research import review42_forward as F  # noqa: E402

D0 = 1794441600            # 2026-11-12 00:00 UTC


def _day_file(dirp, day0, rows):
    import time
    f = dirp / f"l1_{time.strftime('%Y-%m-%d', time.gmtime(day0))}.sqlite"
    con = sqlite3.connect(f)
    con.execute("CREATE TABLE ndax (t INTEGER, coin TEXT, bid REAL, ask REAL, last REAL, notional24_cad REAL, ex_ms INTEGER)")
    con.executemany("INSERT INTO ndax (t, coin, bid, ask) VALUES (?,?,?,?)", rows)
    con.commit()
    con.close()


def test_the_ndax_side_fills_only_when_the_ask_trades_through_and_sells_at_the_bid(tmp_path, monkeypatch):
    monkeypatch.setattr(F, "WORKER", tmp_path)
    d = D0 + 3600                                           # a drop detected at 01:00 UTC
    rows = [(D0 + m * 60, "SOL", 100.0, 100.4) for m in range(0, 1440)]
    rows = [(t, c, b, a) if not (d + 60 + 600 <= t <= d + 60 + 660) else (t, c, 96.0, 96.5) for t, c, b, a in rows]   # ten minutes in, the ask dips
    _day_file(tmp_path, D0, rows)
    nd = F.ndax_side("SOL", d, 0.03, newest_day=D0 // 86400)
    assert nd["status"] == "filled" and round(nd["limit"], 4) == round(100.2 * 0.97, 4)
    assert nd["fill_t"] == d + 60 + 600 and nd["exit_t"] == nd["fill_t"] + 240 * 60
    assert round(nd["net"], 6) == round(100.0 / nd["limit"] - 1 - 0.004, 6)
    shallow = F.ndax_side("SOL", d, 0.05, newest_day=D0 // 86400)          # 95.19 is never reached by an ask of 96.5
    assert shallow["status"] == "not filled"


def test_a_missing_day_waits_until_a_later_day_exists(tmp_path, monkeypatch):
    monkeypatch.setattr(F, "WORKER", tmp_path)
    d = D0 + 23 * 3600                                      # the window and the 4-hour hold run into the next UTC day
    _day_file(tmp_path, D0, [(D0 + m * 60, "SOL", 100.0, 100.4) for m in range(0, 1440)])
    assert F.ndax_side("SOL", d, 0.03, newest_day=D0 // 86400)["status"] == "waiting"
    assert F.ndax_side("SOL", d, 0.03, newest_day=D0 // 86400 + 2)["status"] == "no data"


def test_it_starts_after_the_pass_and_reads_no_outcome_early():
    src = (F.__file__ and open(F.__file__).read())
    assert F.FROM == D0 and F.CUT_IDX == 2 and F.DEPTH == 0.5 and F.HOLD == 240 and F.GOAL == 30
    assert "counts only" in src and "no returns are totalled before the goal" in src
