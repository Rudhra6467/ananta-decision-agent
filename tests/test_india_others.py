"""Reference traders against Ananta India (india.others, 22 Oct 2026), on synthetic live days only: the hindsight trips and their classes, the random
band, the informed participants' hit rates, the league, the pattern rule's drafts, and the sealed purpose's refusals."""
from __future__ import annotations

import datetime as dt
import json

import pandas as pd
import pytest

from india import missed, others, paper, sealed


SESS = ["2026-10-16", "2026-10-19", "2026-10-21", "2026-10-22"]
NAMES = [f"S{i:02d}" for i in range(25)]


def _cash() -> pd.DataFrame:
    """Closes chain from session to session: S00 gains 3% a session, S01 loses 5%, the rest gain 1%; no corporate action anywhere."""
    rows = []
    for j, s in enumerate(NAMES):
        close = 100.0 * (1 + j * 0.001)
        for i, d in enumerate(SESS):
            prev = close
            if i:
                close = prev * (1.03 if s == "S00" else 0.95 if s == "S01" else 1.01)
            rows.append({"date": pd.Timestamp(d), "symbol": s, "series": "EQ", "open": prev, "high": max(prev, close) * 1.01, "low": min(prev, close) * 0.99,
                         "close": close, "prev_close": prev, "volume": 1000, "turnover": 1e8 - j * 1e5, "isin": "IN" + s})
    return pd.DataFrame(rows)


def _oi() -> pd.DataFrame:
    rows = []
    for d in SESS:
        for p, net in (("FII", 1000), ("DII", -500), ("Pro", 100), ("Client", -50)):
            rows.append({"date": pd.Timestamp(d), "client_type": p, "future_index_long": max(net, 0) + 10, "future_index_short": max(-net, 0) + 10,
                         "future_stock_long": 5, "future_stock_short": 5, "option_index_call_long": 0, "option_index_put_long": 0, "option_index_call_short": 0,
                         "option_index_put_short": 0, "total_long_contracts": 0, "total_short_contracts": 0})
    return pd.DataFrame(rows)


@pytest.fixture
def lake(tmp_path, monkeypatch):
    pdir = tmp_path / "paper"
    (pdir / "decisions").mkdir(parents=True)
    monkeypatch.setattr(paper, "pdir", lambda: pdir)
    monkeypatch.setattr(others.paths, "manifest_dir", lambda: tmp_path / "manifests")
    monkeypatch.setattr(sealed, "read_others", lambda purpose, since, until=None: {"cash": _cash()[pd.to_datetime(_cash()["date"]).dt.date.astype(str) <= (until or "9999")], "oi": _oi()})
    monkeypatch.setattr(missed, "non_session", lambda day: None)
    uni = {"key": "u", "written_at": "x", "source": "test", "rules": "r", "liq_top": 25, "n": 25,
           "rows": [{"sid": "SID" + s, "symbol": s, "isin": "IN" + s, "liq_rank": i + 1, "ret_1": 0.0, "gap": 0.0, "oc": 0.0, "vol_ratio20": 1.0, "turnover_vs_med60": 1.0,
                     "breakout20": s == "S00", "breakdown20": False, "base20_range": 0.1, "new_high_250": False, "new_low_250": False, "rsi14": 50.0, "rsi14_prev": 50.0,
                     "dist_sma20": 0.0, "dist_sma20_prev": 0.0, "dist_sma200": 0.05, "dist_sma200_prev": 0.05, "ret_20_prev": 0.02, "atr_pct": 0.02} for i, s in enumerate(NAMES)]}
    for d in SESS:
        (pdir / "decisions" / f"{d}.universe.json").write_text(json.dumps(uni))
        (pdir / "decisions" / f"{d}.json").write_text("{}")
    journals = {d: ([{"sid": "SIDS02", "campaign": "BRK", "status": "rejected", "reason": "cap_reached"}], "recorded") for d in SESS}
    monkeypatch.setattr(missed, "_journals", lambda keys: {k: journals.get(k, (None, "missing")) for k in keys})
    trades = pd.DataFrame([{"id": "t1", "campaign": "PULL", "sid": "SIDS00", "symbol": "S00", "policy": "hold_20d", "status": "open", "entry_date": "2026-10-19",
                            "exit_date": None, "signal_date": "2026-10-16", "liq_rank": 1, "notional": 50000.0},
                           {"id": "t2", "campaign": "CTL", "sid": "SIDS03", "symbol": "S03", "policy": "hold_20d", "status": "open", "entry_date": "2026-10-19",
                            "exit_date": None, "signal_date": "2026-10-16", "liq_rank": 4, "notional": 50000.0}])
    monkeypatch.setattr(missed, "_book", lambda: (trades, pd.DataFrame()))
    (pdir / "calls.jsonl").write_text("".join(json.dumps({"kind": "call", "data_through": d, "close": 100.0 * (1.01 ** i), "call": "BULLISH"}) + "\n" for i, d in enumerate(SESS)))
    return tmp_path


def test_hindsight_trips_classes_and_random_band(lake):
    man = others.evening(dt.date(2026, 10, 21), reg=lake / "reg", log=lambda *a: None)
    assert man["status"] == "ok"
    h1 = man["by_h"]["1"]
    assert h1["entry"] == "2026-10-19" and h1["exit"] == "2026-10-21" and h1["eligible"] == 25 and h1["dropped"] == 0
    best = {u["symbol"]: u for u in h1["best"]}
    assert list(best)[0] == "S00" and best["S00"]["class"] == "TAKEN" and "PULL" in best["S00"]["why"]
    assert best["S02"]["class"] == "PASSED" and "cap" in best["S02"]["why"]
    assert best["S03"]["class"] == "CONTROL"
    assert best["S04"]["class"] == "NOT_COVERED"
    assert "S01" not in best and h1["worst"][0]["symbol"] == "S01" and "class" not in h1["worst"][0]
    assert 0 < best["S00"]["net"] < 0.03 and best["S00"]["situation_key"] == "others:H1:breakout_base"
    assert h1["random"]["draws"] == 200 and h1["random"]["p5"] <= h1["random"]["median"] <= h1["random"]["p95"]
    assert h1["ananta_n"] == 1 and h1["ananta_pct_vs_random"] == 1.0      # its one pick (S00) beat every random 20
    assert "5" not in man["by_h"] and "20" not in man["by_h"]            # not enough live sessions yet
    assert (lake / "manifests" / "others_2026-10-21.json").exists() and (lake / "reg" / "others_league.md").exists()


def test_informed_hits_and_ananta_call(lake):
    man = others.evening(dt.date(2026, 10, 21), reg=lake / "reg", log=lambda *a: None)
    t = man["informed"]["table"]
    assert t["FII"]["stance"]["hit_rate"] == 1.0 and t["DII"]["stance"]["hit_rate"] == 0.0     # the index rose every session
    assert t["FII"]["flow"]["n"] == 0                                                           # nets never changed: no flow to score
    assert t["FII"]["latest"]["stance"] == "long" and t["DII"]["latest"]["stance"] == "short"
    assert t["ANANTA_CALL"]["call"]["hit_rate"] == 1.0 and t["ANANTA_CALL"]["call"]["n"] == 2


def test_league_and_pattern_drafts(lake):
    reg = lake / "reg"
    for d in SESS[1:]:
        man = others.evening(dt.date.fromisoformat(d), reg=reg, log=lambda *a: None)
    lg = man["league"]
    assert lg["window_sessions"] == 3 and lg["1"]["sessions"] == 3 and lg["1"]["HINDSIGHT"] > lg["1"]["MARKET"] > -0.01
    assert lg["1"]["coverage"]["TAKEN"] == 3 and lg["1"]["coverage"]["NOT_COVERED"] >= 3 and lg["1"]["took_share"] > 0
    drafts = [json.loads(x) for x in (reg / "missed_drafts.jsonl").read_text().splitlines()]
    assert drafts and all(x["status"] == "DRAFT" and x["kind"] == "reference-traders pattern" for x in drafts)
    keys = {x["key"] for x in drafts}
    assert keys and all(k.startswith("others:H1:") for k in keys) and len(drafts) == len(keys)   # each situation filed once in the window
    assert all(len(x["days"]) >= 3 for x in drafts)
    hist = others.read_history()
    assert [r["date"] for r in hist] == SESS[1:] and "best" not in json.dumps(hist) and "ananta_picks" not in json.dumps(hist)


def test_sealed_others_refuses_history_and_other_purposes(tmp_path, monkeypatch):
    monkeypatch.setattr(sealed.paths, "data_dir", lambda: tmp_path)
    monkeypatch.setattr(sealed.paths, "manifest_dir", lambda: tmp_path / "manifests")
    (tmp_path / "manifests").mkdir()
    with pytest.raises(PermissionError):
        sealed.read_others("paper_review", "2026-10-16")
    with pytest.raises(PermissionError):
        sealed.read_others("others_review", "2026-10-15")
    with pytest.raises(PermissionError):
        sealed.read_others("others_review", "2026-10-19", until="2026-10-16")
    out = sealed.read_others("others_review", "2026-10-16")
    assert set(out) == {"cash", "oi"} and out["cash"].empty and out["oi"].empty
