"""The header every lake review prints (research audit LAKE-1, LAKE-3, LAKE-4): coins alive per year, days dropped, swaps cut, grades."""
import json

import pytest

duckdb = pytest.importorskip("duckdb")

DAY = 86400


def _coin(tmp_path, sym, t0, n, half_days=()):
    d = tmp_path / "clean" / "binance" / "spot" / "1d" / f"symbol={sym}" / "year=2024"
    d.mkdir(parents=True)
    share = ", CASE WHEN i IN (" + ",".join(str(i) for i in half_days) + ") THEN 0.5 ELSE 1.0 END AS share" if half_days else ""
    duckdb.sql(f"COPY (SELECT {t0} + i * {DAY} AS t, 1.0 AS o, 1.1 AS h, 0.9 AS l, 1.05 AS c, 10.0 AS v, 10.5 AS qv{share} "
               f"FROM range({n}) r(i)) TO '{d / 'data_0.parquet'}' (FORMAT PARQUET)")


def _grade(tmp_path, sym, grade):
    q = tmp_path / "reports" / "quality"
    q.mkdir(parents=True, exist_ok=True)
    (q / f"spot_1m_{sym}.json").write_text(json.dumps({"grade": grade}))


def test_the_header_counts_coins_per_year_dropped_days_swaps_and_grades(tmp_path, monkeypatch):
    from src.lake import research as L

    monkeypatch.setenv("ANANTA_LAKE", str(tmp_path))
    until = 1_735_689_600                                           # 2025-01-01
    _coin(tmp_path, "AAAUSDT", 1_672_531_200, 400, half_days=(3, 10))          # 2023-01-01, two half-covered days
    _coin(tmp_path, "BBBUSDT", 1_717_200_000, 100)                              # 2024-06-01, no share column
    _grade(tmp_path, "AAAUSDT", "A")
    _grade(tmp_path, "BBBUSDT", "C")
    D = {"AAA": L.daily("AAAUSDT", until=until), "BBB": L.daily("BBBUSDT", until=until)}
    assert len(D["AAA"]) == 398 and len(D["BBB"]) == 100
    assert L.coins_alive_per_year(D) == {2023: 1, 2024: 2}
    assert L.dropped_days("AAAUSDT", until) == (2, 400) and L.dropped_days("BBBUSDT", until) == (0, 100)
    h = L.lake_header(D, ["AAAUSDT", "BBBUSDT"], until)
    assert h["coins"] == 2 and h["dropped_days"] == 2 and h["days_in_files"] == 500 and h["dropped_pct"] == 0.4
    assert h["grades"] == {"A": 1, "B": 0, "C": 1, "none": 0}
    assert "COCOSUSDT" in h["breaks"] and "LUNAUSDT" in h["ends"]
    text = L.format_header(h)
    assert "Coins alive per year: 2023: 1, 2024: 2." in text
    assert "2 of 500 (0.4%)" in text and "COCOSUSDT" in text and "LUNAUSDT" in text and "A 1, B 0, C 1" in text


def test_a_coin_with_no_file_adds_nothing_to_the_dropped_count_and_a_missing_report_is_counted_as_none(tmp_path, monkeypatch):
    from src.lake import research as L

    monkeypatch.setenv("ANANTA_LAKE", str(tmp_path))
    until = 1_735_689_600
    _coin(tmp_path, "AAAUSDT", 1_672_531_200, 50)
    D = {"AAA": L.daily("AAAUSDT", until=until), "GHOST": [(1_700_000_000, 1, 1, 1, 1, 1)]}
    h = L.lake_header(D, ["AAAUSDT", "GHOSTUSDT"], until)
    assert h["dropped_days"] == 0 and h["days_in_files"] == 50
    assert h["grades"]["none"] == 2
    assert "none 2" in L.format_header(h)
