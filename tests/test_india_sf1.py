"""SF1, the strength-flip shadow (registration india/registrations/sf1_v1.json, frozen 15 Nov 2026): the regime and buckets as written, a row
written once per entry session on a sha chain and never after the open, a scored row never rewritten, the bar's verdicts, and no decision
module importing it."""
import ast
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from india import managed
from india import sf1

ASOF = "2026-11-20"           # a Friday: the entry session is Monday 23 Nov


def _bars(n_sym=45, after=25, seed=3):
    dates = pd.bdate_range(end=ASOF, periods=260).append(pd.bdate_range(start="2026-11-23", periods=after))
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(n_sym):
        drift = (i - n_sym / 2) * 0.0002
        c = 100 * np.cumprod(1 + drift + 0.01 * rng.standard_normal(len(dates)))
        o = np.r_[c[0], c[:-1]] * 1.001
        for d, oo, cc in zip(dates, o, c):
            rows.append({"symbol": f"S{i:02d}", "date": d, "open": oo, "high": max(oo, cc), "low": min(oo, cc), "close": cc, "volume": 1e6, "turnover": 2e8})
    return pd.DataFrame(rows)


def _nifty(kind="FALLING"):
    dates = pd.bdate_range(end=ASOF, periods=260)
    x = np.linspace(0, 1, len(dates))
    v = {"FALLING": 100 + 20 * x - 40 * np.clip(x - 0.85, 0, None) / 0.15, "RISING": 100 + 20 * x}[kind]
    return pd.Series(v, index=dates)


@pytest.fixture
def world(tmp_path, monkeypatch):
    monkeypatch.setenv("INDIA_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(managed, "holidays", lambda: set())
    monkeypatch.setattr(managed, "refuse_late", lambda s: None)
    return tmp_path


def test_regime_follows_the_two_averages():
    assert sf1.regime_of(_nifty("FALLING"), ASOF)["regime"] == "FALLING"
    assert sf1.regime_of(_nifty("RISING"), ASOF)["regime"] == "RISING"
    assert sf1.regime_of(_nifty("RISING"), "2026-11-23")["regime"] == "MISSING"      # no row on the day: never filled
    assert sf1.regime_of(_nifty("RISING").tail(150), ASOF)["regime"] == "MISSING"   # too little history for a 200-day


def test_buckets_as_registered():
    u = pd.DataFrame({"symbol": [f"X{i}" for i in range(30)], "close": [110.0] * 10 + [125.0] * 5 + [90.0] * 15,
                      "sma50": [100.0] * 30, "ret_20": list(np.linspace(0.30, 0.21, 15)) + list(np.linspace(-0.01, -0.30, 15))})
    b = sf1.buckets(u)
    assert set(b["strong"]) <= {f"X{i}" for i in range(10)}                       # 125/100 is 25% above the 50-day: out
    assert b["strong"] and all(u.set_index("symbol").loc[s, "ret_20"] >= b["cuts"]["ret_20_high"] for s in b["strong"])
    assert b["weak"] and all(u.set_index("symbol").loc[s, "close"] < 100 for s in b["weak"])
    assert sf1.buckets(u.head(10))["strong"] == []                                # under 30 names: no buckets


def test_control_is_fixed_by_the_hash():
    syms = [f"S{i}" for i in range(200)]
    a, b = sf1.control(syms, ASOF), sf1.control(list(reversed(syms)), ASOF)
    assert a == b and len(a) == 50 and a != sf1.control(syms, "2026-11-23")


def _rec(bars, kind="FALLING"):
    return sf1.record(day=ASOF, bars=bars, nifty=_nifty(kind), n500=set(bars["symbol"]))


def test_record_once_per_entry_session_on_a_chain(world):
    bars = _bars()
    out = _rec(bars)
    assert out["status"] == "written" and out["entry_session"] == "2026-11-23" and out["regime"] == "FALLING"
    assert _rec(bars, "RISING")["status"] == "kept"                                 # a re-run keeps the first row, whatever changed
    rows = sf1._jsonl(world / "paper" / "shadow" / "sf1" / "rows.jsonl")
    assert len(rows) == 1 and rows[0]["regime"] == "FALLING" and rows[0]["spec_sha"] == sf1.spec_sha()
    assert sf1.chain_ok(rows)[0] and rows[0]["prev_sha"] == ""
    rows[0]["strong"] = rows[0]["strong"][:-1]                                       # an edited row breaks the chain
    (world / "paper" / "shadow" / "sf1" / "rows.jsonl").write_text(json.dumps(rows[0]) + "\n")
    with pytest.raises(RuntimeError, match="breaks the chain"):
        sf1.score(bars=bars)


def test_refused_before_start_and_after_the_open(world, monkeypatch):
    bars = _bars()
    monkeypatch.setattr(sf1, "START", "2026-12-01")
    assert _rec(bars)["status"] == "refused"
    monkeypatch.setattr(sf1, "START", "2026-01-01")
    monkeypatch.setattr(managed, "refuse_late", lambda s: (_ for _ in ()).throw(RuntimeError("the session has opened")))
    with pytest.raises(RuntimeError, match="opened"):
        _rec(bars)
    assert not (world / "paper" / "shadow" / "sf1" / "rows.jsonl").exists()


def test_nothing_before_the_spec_is_frozen_and_never_after_it_changes(world, monkeypatch, tmp_path):
    spec = json.loads(sf1.SPEC.read_text())
    f = tmp_path / "spec.json"
    f.write_text(json.dumps(dict(spec, frozen_at=None)))
    monkeypatch.setattr(sf1, "SPEC", f)
    with pytest.raises(RuntimeError, match="not frozen"):
        _rec(_bars())
    f.write_text(json.dumps(spec))
    assert _rec(_bars())["status"] == "written"
    f.write_text(json.dumps(dict(spec, title="edited")))
    with pytest.raises(RuntimeError, match="changed after its first row"):
        sf1.record(day="2026-11-23", bars=_bars(), nifty=_nifty(), n500=set(_bars()["symbol"]))


def test_score_once_and_by_the_registered_window(world):
    bars = _bars()
    _rec(bars)
    out = sf1.score(bars=bars)
    assert out["new_scores"] == 1 and out["verdict"] == "INSUFFICIENT"
    sc = sf1._jsonl(world / "paper" / "shadow" / "sf1" / "scores.jsonl")[0]
    row = sf1._jsonl(world / "paper" / "shadow" / "sf1" / "rows.jsonl")[0]
    sess = pd.bdate_range(start="2026-11-23", periods=20)
    assert sc["exit_session"] == str(sess[-1].date())
    o = bars.pivot(index="date", columns="symbol", values="open"); c = bars.pivot(index="date", columns="symbol", values="close")
    m = lambda b: 1e4 * np.mean([c.loc[sess[-1], s] / o.loc[sess[0], s] - 1 for s in row[b]])
    assert sc["strong"]["excess_bps"] == pytest.approx(m("strong") - m("control"), abs=0.02)
    assert sc["d_bps"] == pytest.approx(m("strong") - m("weak"), abs=0.03)
    assert sf1.score(bars=bars)["new_scores"] == 0                                 # a scored row is never scored or rewritten again
    assert len(sf1._jsonl(world / "paper" / "shadow" / "sf1" / "scores.jsonl")) == 1


def test_not_scored_before_twenty_sessions(world):
    bars = _bars(after=19)
    _rec(bars)
    assert sf1.score(bars=bars)["new_scores"] == 0


def _scores(regimes_and_d):
    out, day = [], pd.Timestamp("2026-11-16")
    for reg, d in regimes_and_d:
        out.append({"entry_session": str(day.date()), "regime": reg, "d_bps": d, "weak": {"excess_bps": 1.0}, "managed_buys": {"excess_bps": None}})
        day += pd.offsets.BDay(1)
    return out


def _falling(spells, d_fn, gap=5):
    xs = []
    for k in range(spells):
        xs += [("FALLING", d_fn(k, j)) for j in range(20)] + [("RISING", 0.0)] * gap
    return xs


def test_insufficient_until_sixty_falling_evenings_over_three_spells():
    assert sf1.summarise(_scores(_falling(2, lambda k, j: -50.0 + j)), {})["verdict"] == "INSUFFICIENT"   # 40 falling, 2 spells
    few = [("FALLING", -50.0)] * 9 + [("RISING", 0.0)]
    assert sf1.summarise(_scores(few * 8), {})["verdict"] == "INSUFFICIENT"                             # 72 falling, no spell of 10


def test_supported_rejected_and_the_one_reread():
    rng = np.random.default_rng(5)
    assert sf1.summarise(_scores(_falling(3, lambda k, j: -60 + 10 * rng.standard_normal())), {})["verdict"] == "SUPPORTED_FORWARD"
    assert sf1.summarise(_scores(_falling(3, lambda k, j: 40 + 10 * rng.standard_normal())), {})["verdict"] == "REJECTED_FORWARD"
    noisy = lambda k, j: (-5 if k else 4) + 200 * rng.standard_normal()
    state = {}
    first = sf1.summarise(_scores(_falling(3, noisy)), state)
    if first["primary"]["D_bps"] < 0:
        assert first["verdict"] == "INCONCLUSIVE" and state["reread_at"] == 60 + 30
        again = sf1.summarise(_scores(_falling(5, noisy)), state)                                      # 100 falling evenings: read once more
        assert again["verdict"] in ("SUPPORTED_FORWARD", "REJECTED_FORWARD", "CLOSED_INCONCLUSIVE") and state["final"] == again["verdict"]
        assert sf1.summarise(_scores(_falling(3, lambda k, j: -500.0)), state)["verdict"] == state["final"]   # a final verdict is never reopened


def test_newey_west_t():
    assert sf1.nw_t(np.array([1.0, 2.0])) is None
    x = np.random.default_rng(1).standard_normal(400) + 0.5
    assert 4 < sf1.nw_t(x) < 15


def test_no_decision_module_imports_sf1():
    here = Path(sf1.__file__).parent
    for f in here.rglob("*.py"):
        if f.name == "sf1.py":
            continue
        tree = ast.parse(f.read_text())
        for n in ast.walk(tree):
            names = [a.name for a in n.names] if isinstance(n, (ast.Import, ast.ImportFrom)) else []
            mod = (n.module or "") if isinstance(n, ast.ImportFrom) else ""
            assert "sf1" not in mod and not any(x.endswith("sf1") for x in names), f"{f.name} imports sf1"
    src = Path(sf1.__file__).read_text()
    for banned in ("kite", "allocator", "orders", "crypto"):
        assert f"import {banned}" not in src and f", {banned}" not in src.split("from india import")[1].split("\n")[0]
