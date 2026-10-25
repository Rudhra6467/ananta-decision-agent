"""HFN1 (25 Oct 2026): the FinBERT news reading. Cache by text hash, the timing rule, no 2024+ or sealed reads in research, and a forward record
that is append-only, live-days-only and read by nothing that decides."""
import ast
import datetime as dt
import gzip
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from india import hf_news as H

ROOT = Path(__file__).resolve().parents[1]


class FakeReader:
    def __init__(self):
        self.calls = 0

    def probs(self, texts):
        self.calls += len(texts)
        return np.array([[0.8, 0.1, 0.1] if "award" in t.lower() else [0.1, 0.8, 0.1] if "default" in t.lower() else [0.1, 0.1, 0.8] for t in texts])


@pytest.fixture
def lake(tmp_path, monkeypatch):
    monkeypatch.setenv("INDIA_DATA_DIR", str(tmp_path))
    for d in ("gold/studies", "gold/features", "gold/bars", "silver/pr", "silver/kite_index/day", "paper", "manifests"):
        (tmp_path / d).mkdir(parents=True, exist_ok=True)
    return tmp_path


def test_cache_rates_each_text_once(lake):
    r = FakeReader()
    texts = {H.text_hash(t): t for t in ("Letter of award from NHAI", "Payment default on bonds", "Credit rating")}
    out = H.rate_texts(texts, reader=r)
    assert r.calls == 3 and len(out) == 3 and H.cache_path().exists()
    H.rate_texts(texts, reader=r)
    assert r.calls == 3                                       # nothing re-rated: the cache holds them
    c = H.load_cache().set_index("h")
    assert c.loc[H.text_hash("Letter of award from NHAI"), "p_pos"] == pytest.approx(0.8)


def test_research_never_reads_2024_or_sealed(lake):
    pd.DataFrame({"date": pd.to_datetime(["2023-12-28", "2024-01-02", "2023-12-28"]).date, "symbol": ["AAA", "AAA", "BBB"],
                  "company": "x", "subject": "s", "category": ["order_win", "order_win", "nav"], "text": ["award", "award", "nav"]}).to_parquet(lake / "silver/pr/announcements.parquet")
    pd.DataFrame({"date": pd.to_datetime(["2023-12-28", "2024-01-02", "2023-12-28"]), "sid": ["A", "A", "B"], "symbol": ["AAA", "AAA", "BBB"], "liq_rank": 1}).to_parquet(lake / "gold/features/daily.parquet")
    a = H.announcements()
    assert list(a["date"].dt.year) == [2023] and set(a["category"]) == {"order_win"}      # 2024 dropped, NAV notices dropped
    src = (ROOT / "india" / "hf_news.py").read_text()
    consts = [n.value for n in ast.walk(ast.parse(src)) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    assert not any("sealed/" in s or s.strip() == "sealed_dir" for s in consts)


def test_drift_runs_from_the_close_of_the_announcement_day(lake):
    days = pd.bdate_range("2023-01-02", periods=30)
    c = np.linspace(100, 129, 30)
    pd.DataFrame({"sid": "A", "date": days, "c": c}).to_parquet(lake / "gold/bars/adj_daily.parquet")
    pd.DataFrame({"index_name": "NIFTY 50", "date": days, "close": 100.0}).to_parquet(lake / "silver/kite_index/day/day.parquet")
    d = H.drifts(pd.DataFrame({"date": [days[3]], "sid": ["A"]}))
    assert d.loc[0, "drift5"] == pytest.approx(c[8] / c[3] - 1)       # close of day d to close of d+5; the same-day move is not counted
    assert d.loc[0, "drift20"] == pytest.approx(c[23] / c[3] - 1)


def test_quarter_series_spread_and_within_category():
    q = pd.to_datetime(["2019-01-10", "2019-01-11", "2019-01-14", "2019-01-15"])
    sd = pd.DataFrame({"date": q, "sid": list("ABCD"), "tone": [0.7, -0.7, 0.6, -0.5], "label": ["positive", "negative", "positive", "negative"],
                       "drift5": [0.02, -0.01, 0.04, -0.03], "drift20": [0.05, -0.02, 0.03, -0.04]})
    cats = pd.DataFrame({"date": q, "sid": list("ABCD"), "category": ["results", "results", "legal", "legal"], "ctone": 0.0,
                         "cpos": [True, False, True, False], "cneg": [False, True, False, True]})
    s = H.quarter_series(sd, cats)
    assert s["spread|drift20"].iloc[0] == pytest.approx(np.mean([0.05, 0.03]) - np.mean([-0.02, -0.04]))
    assert s["within_cat|drift20"].iloc[0] == pytest.approx(np.mean([0.05 + 0.02, 0.03 + 0.04]))


def _file(lake, day: dt.date, rows):
    p = lake / "bronze" / "announce_api" / str(day.year) / f"{day:%Y%m%d}.json.gz"
    p.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(p, "wt") as fh:
        json.dump(rows, fh)
    return p


def test_forward_is_live_only_and_append_only(lake):
    old = _file(lake, dt.date(2025, 3, 3), [{"symbol": "AAA", "desc": "Award", "attchmntText": "award"}])
    with pytest.raises(PermissionError):
        H.forward_day(dt.date(2025, 3, 3), old, FakeReader())
    day = dt.date(2026, 10, 23)
    src = _file(lake, day, [{"symbol": "AAA", "desc": "Letter of Award", "attchmntText": "received an award"}, {"symbol": "BBB", "desc": "Default", "attchmntText": "default"}])
    r1 = H.forward_day(day, src, FakeReader())
    assert r1["counts"] == {"positive": 1, "negative": 1, "neutral": 0}
    _file(lake, day, [{"symbol": "ZZZ", "desc": "x", "attchmntText": "changed later"}])
    assert H.forward_day(day, src, FakeReader()) == r1            # written once: a later file never rewrites the day
    log = (H.news_dir() / "log.jsonl").read_text().splitlines()
    assert len(log) == 1
    note = H.read_note(str(day), {"AAA": 1})
    assert note["counts"]["positive"] == 1 and note["counts"]["negative"] == 0 and "never a reason to trade" in note["words"]


def test_nothing_that_decides_reads_the_news_record():
    readers = []
    for f in (ROOT / "india").glob("*.py"):
        if f.name in ("hf_news.py", "reconstruct.py"):
            continue
        t = f.read_text()
        if "news_read" in t or "hf_news" in t:
            readers.append(f.name)
    assert readers == [], readers                          # only the reconstruction card shows the counts, as a note
