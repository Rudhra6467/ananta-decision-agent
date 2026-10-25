"""HF-CHRONOS (25 Oct 2026): the Hugging Face forecaster. The research path reads the research tree only; the forward step writes scored,
never-traded rows to the forecast ledger; the morning scorecard keeps Chronos apart from the rule and the reviewer. No model is loaded here."""
import ast
import datetime as dt
import json
from pathlib import Path

import numpy as np
import pandas as pd

from india import hf_chronos as H

SRC = Path(H.__file__)


def test_probabilities_from_quantiles():
    q = np.array([90, 92, 94, 96, 100, 104, 106, 108, 110], dtype=float)
    assert abs(H.p_up(q, 100.0) - 0.5) < 1e-9
    assert H.p_up(q, 89.0) > 0.9 and H.p_up(q, 111.0) < 0.1
    s = H.scenarios(q, 100.0, 0.003)
    assert abs(sum(s.values()) - 1) < 1e-9 and min(s.values()) >= 0 and abs(s["bull"] - s["bear"]) < 1e-9


def test_spec_and_code_agree():
    spec = json.loads(H.SPEC.read_text())
    assert spec["variants"] == H.VARIANTS and spec["model"]["revision"] == H.REVISION and H.UNION_K == 10
    assert "300" in spec["method"]["context"] and H.CONTEXT == 300


def test_research_path_never_reads_the_sealed_tree(tmp_path, monkeypatch):
    tree = ast.parse(SRC.read_text())
    top_imports = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    assert not any("sealed" in ast.unparse(n) for n in top_imports), "sealed is imported only inside forward()"
    for fn in (n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name != "forward"):
        for n in ast.walk(fn):
            assert not (isinstance(n, ast.Name) and n.id == "sealed"), f"{fn.name} uses the sealed module"
            assert not (isinstance(n, ast.alias) and "sealed" in n.name), f"{fn.name} imports sealed"
            assert not (isinstance(n, ast.Constant) and isinstance(n.value, str) and "sealed/" in n.value), f"{fn.name} names a sealed path"
    silver = tmp_path / "silver" / "kite_index" / "day"
    silver.mkdir(parents=True)
    dates = pd.bdate_range("2023-12-20", "2024-01-10")
    pd.DataFrame({"index_name": "NIFTY 50", "date": dates.date, "close": np.arange(len(dates), dtype=float) + 100}).to_parquet(silver / "day.parquet")
    monkeypatch.setenv("INDIA_DATA_DIR", str(tmp_path))
    c = H.research_closes("NIFTY 50")
    assert len(c) and c.index.max() < pd.Timestamp("2024-01-01")


def test_call_rule_matches_dailycall():
    c = pd.Series([100.0] * 60 + [90.0, 120.0, 118.0], index=pd.bdate_range("2020-01-01", periods=63))
    r = H.call_rule(c)
    assert r.iloc[-3] == "BULLISH" and r.iloc[-2] == "BEARISH" and pd.isna(r.iloc[0])


def _fake_ix(session: dt.date, hol: set) -> pd.DataFrame:
    last = H._prev_session(session, hol)
    dates = pd.bdate_range(end=pd.Timestamp(last), periods=320)
    rows = []
    for name in H.NAMES.values():
        rows += [{"index_name": name, "date": d, "close": 20000.0 + i} for i, d in enumerate(dates)]
    return pd.DataFrame(rows)


def test_forward_writes_scored_rows_once_and_skips_stale(tmp_path, monkeypatch):
    from india import forecast, sealed

    monkeypatch.setenv("INDIA_DATA_DIR", str(tmp_path))
    (tmp_path / "manifests").mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(forecast, "LEDGER", tmp_path / "paper" / "forecasts.jsonl")
    monkeypatch.setattr(H, "_holidays", lambda: set())
    session = H._next_session(set())
    calls = []
    monkeypatch.setattr(sealed, "read_index", lambda purpose, since, names: calls.append(purpose) or _fake_ix(session, set()))
    monkeypatch.setattr(H, "predict", lambda ctx, pipe=None: np.tile(np.linspace(0.99, 1.01, 9), (len(ctx), H.PRED_LEN, 1)) * ctx[0][-1])
    r = H.forward()
    assert calls == ["paper_context"] and len(r["written"]) == 4 and not r["skipped"]
    rows = [json.loads(x) for x in forecast.LEDGER.read_text().splitlines()]
    assert all(x["basis"].startswith("chronos") and abs(sum(x["scenarios"].values()) - 1) < 1e-6 for x in rows)
    assert {(x["subject"], x["horizon_sessions"]) for x in rows} == {(n, h) for n in H.NAMES.values() for h in H.HORIZONS}
    assert len(H.forward()["written"]) == 0                                   # a second run writes nothing
    assert forecast.verify()["ok"]
    monkeypatch.setattr(sealed, "read_index", lambda purpose, since, names: _fake_ix(session - dt.timedelta(days=7), set()))
    monkeypatch.setattr(forecast, "LEDGER", tmp_path / "paper" / "f2.jsonl")
    r = H.forward()
    assert not r["written"] and all("stale" in s["why"] for s in r["skipped"])


def test_scorecard_keeps_chronos_apart(tmp_path, monkeypatch):
    from india import morningview as mv

    monkeypatch.setenv("INDIA_DATA_DIR", str(tmp_path))
    p = tmp_path / "paper"
    p.mkdir(parents=True)
    fc = [{"kind": "forecast", "forecast_id": "A", "basis": "climatology", "subject": "NIFTY 50", "horizon_sessions": 1},
          {"kind": "forecast", "forecast_id": "B", "basis": "chronos: x", "subject": "NIFTY 50", "horizon_sessions": 1},
          {"kind": "forecast", "forecast_id": "C", "basis": "chronos: x", "subject": "NIFTY BANK", "horizon_sessions": 5}]
    sc = [{"kind": "score", "ref": k, "hit": True, "brier": 0.5, "brier_coin_flip": 0.67} for k in ("A", "B", "C")]
    (p / "forecasts.jsonl").write_text("".join(json.dumps(x) + "\n" for x in fc + sc))
    monkeypatch.setattr(mv, "_paper", lambda: p)
    rec = mv.scorecard({})["forecasts"]
    assert rec["rule"]["n"] == 1 and rec["chronos"]["n"] == 1 and rec["reviewer"]["n"] == 0
