"""SF1, the strength-flip shadow (registration india/registrations/sf1_v1.json, frozen 15 Nov 2026): the regime and buckets as written, a row
written once per entry session on a sha chain and never after the open, a scored row never rewritten, the bar's verdicts, and no decision
module importing it."""
import ast
import datetime as dt
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from india import managed
from india import sf1

REAL_REFUSE = managed.refuse_late
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
    monkeypatch.setattr(managed, "holidays", lambda: {dt.date(2026, 1, 26)})
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


NXT = lambda d: (pd.Timestamp(d) + pd.offsets.BDay(1)).date().isoformat()


def _scores(regimes_and_d, start="2026-11-16"):
    out, day = [], pd.Timestamp(start)
    for reg, d in regimes_and_d:
        out.append({"entry_session": str(day.date()), "regime": reg, "d_bps": d, "strong": {"n": 10}, "weak": {"n": 10, "excess_bps": 1.0},
                    "control": {"n": 50}, "managed_buys": {"excess_bps": None}})
        day += pd.offsets.BDay(1)
    return out


def _falling(spells, d_fn, length=20, gap=5):
    xs = []
    for k in range(spells):
        xs += [("FALLING", d_fn(k, j)) for j in range(length)] + [("RISING", 0.0)] * gap
    return xs


def _read(scores, state):
    o = sf1.summarise(scores, state, nxt=NXT)
    state.pop("events", None)
    return o


def test_insufficient_until_sixty_evenings_in_three_long_spells():
    assert _read(_scores(_falling(2, lambda k, j: -50.0 + j)), {})["verdict"] == "INSUFFICIENT"           # 40 counted, 2 spells
    short = [("FALLING", -100.0)] * 9 + [("RISING", 0.0)]
    o = _read(_scores(short * 10 + _falling(3, lambda k, j: 30.0, length=10)), {})
    assert o["primary"]["counted_falling_evenings"] == 30 and o["verdict"] == "INSUFFICIENT"           # 9-evening spells never count


def test_a_missed_evening_or_a_void_breaks_or_skips_a_spell():
    sc = _scores([("FALLING", -10.0)] * 12)
    del sc[6]                                                                                           # no row that evening: two spells of 6 and 5
    assert [len(r["rows"]) for r in sf1.runs(sc, NXT)] == [6, 5]
    sc = _scores([("FALLING", -10.0)] * 12)
    sc[6]["void"] = "the entry session did not trade"
    assert [len(r["rows"]) for r in sf1.runs(sc, NXT)] == [6, 5]


def test_supported_and_rejected():
    rng = np.random.default_rng(5)
    assert _read(_scores(_falling(3, lambda k, j: -60 + 10 * rng.standard_normal())), {})["verdict"] == "SUPPORTED_FORWARD"
    assert _read(_scores(_falling(3, lambda k, j: 40 + 10 * rng.standard_normal())), {})["verdict"] == "REJECTED_FORWARD"


def _flat_noise(k, j, n=20, seed=11):
    x = 100 * np.random.default_rng(seed + k).standard_normal(n)
    return float(x[j] - x.mean() - 2.0)                                                                 # each spell's mean is exactly -2


def test_one_reread_then_closed_and_never_reopened():
    state = {}
    base = _falling(3, _flat_noise)
    o = _read(_scores(base), state)
    assert o["verdict"] == "INCONCLUSIVE" and state["reread_at"] == 90
    for extra in (10, 20):                                                                              # 70 and 80 counted: nothing is read
        o = _read(_scores(base + _falling(1, lambda k, j: 500.0, length=extra)), state)
        assert o["verdict"] == "INCONCLUSIVE" and "final" not in state
    o = _read(_scores(base + _falling(1, lambda k, j: 500.0, length=30)), state)                         # 90 counted: the one re-read
    assert o["verdict"] == "REJECTED_FORWARD" and state["final"] == "REJECTED_FORWARD"
    assert _read(_scores(_falling(6, lambda k, j: -500.0)), state)["verdict"] == "REJECTED_FORWARD"      # a final verdict is never reopened


def test_verdict_persists_through_score_on_its_own_chain(world, monkeypatch):
    bars = _bars()
    _rec(bars)
    sf1.score(bars=bars)
    d = world / "paper" / "shadow" / "sf1"
    def fake(sc, st, nxt=None):                                                                        # a study that closes on this read
        if not st.get("final"):
            st["final"] = "REJECTED_FORWARD"
            st.setdefault("events", []).append({"event": "final", "value": "REJECTED_FORWARD"})
        return {"verdict": st["final"], "words": "closed"}
    monkeypatch.setattr(sf1, "summarise", fake)
    sf1.score(bars=bars)
    vs = sf1._jsonl(d / "verdicts.jsonl")
    assert [v["value"] for v in vs] == ["REJECTED_FORWARD"] and sf1.chain_ok(vs)[0]
    assert sf1._state(vs) == {"final": "REJECTED_FORWARD"}
    (d / "verdicts.jsonl").unlink()
    with pytest.raises(RuntimeError, match="not reopened"):
        sf1.score(bars=bars)


def test_edited_score_row_is_caught(world):
    bars = _bars()
    _rec(bars)
    sf1.score(bars=bars)
    p = world / "paper" / "shadow" / "sf1" / "scores.jsonl"
    r = json.loads(p.read_text())
    r["d_bps"] = -999.0
    p.write_text(json.dumps(r) + "\n")
    with pytest.raises(RuntimeError, match="breaks the chain"):
        sf1.score(bars=bars)


def test_void_missing_entry_bar_and_last_close(world):
    bars = _bars()
    _rec(bars)
    row = sf1._jsonl(world / "paper" / "shadow" / "sf1" / "rows.jsonl")[0]
    gone, halted = row["strong"][0], row["weak"][0]
    sess = pd.bdate_range(start="2026-11-23", periods=20)
    b = bars[~((bars["symbol"] == gone) & (bars["date"] == sess[0]))]                                   # no bar on the entry session
    b = b[~((b["symbol"] == halted) & (b["date"] >= sess[15]))]                                         # halted: last close inside the window
    sf1.score(bars=b)
    sc = sf1._jsonl(world / "paper" / "shadow" / "sf1" / "scores.jsonl")[0]
    assert sc["strong"]["left_out"] == 1 and sc["strong"]["n"] == len(row["strong"]) - 1
    o = b.pivot(index="date", columns="symbol", values="open"); c = b.pivot(index="date", columns="symbol", values="close")
    assert sf1.stock_ret(o[halted], c[halted], sess[0], sess[-1]) == pytest.approx(c[halted].loc[sess[14]] / o[halted].loc[sess[0]] - 1)


def test_void_when_the_entry_session_did_not_trade(world):
    bars = _bars()
    _rec(bars)
    b = bars[bars["date"] != pd.Timestamp("2026-11-23")]
    sf1.score(bars=b)
    sc = sf1._jsonl(world / "paper" / "shadow" / "sf1" / "scores.jsonl")[0]
    assert sc["void"] and sc["d_bps"] is None


def test_floors_and_the_strong_edges():
    c = {"min_price_inr": 10, "min_turnover_cr": 5.0}
    f = pd.DataFrame({"symbol": ["A", "B", "C", "D"], "date": [ASOF] * 4, "close": [9.0, 50.0, 50.0, 50.0], "turnover_med60": [1e9, 1e7, 1e9, None],
                      "sma50": [10.0] * 4, "ret_20": [0.1] * 4})
    assert sf1.universe(f, {"A", "B", "C", "D"}, ASOF, c)["symbol"].tolist() == ["C"]                    # price floor, turnover floor, no turnover
    g = f.drop(columns=["turnover_med60"])
    assert sf1.universe(g, {"A", "B", "C", "D"}, ASOF, c)["symbol"].tolist() == ["B", "C", "D"]          # no turnover column: no turnover floor
    assert sf1.universe(pd.DataFrame(), {"A"}, ASOF, c).empty                                            # no name with 210 bars: no crash
    u = pd.DataFrame({"symbol": [f"E{i}" for i in range(30)], "sma50": [100.0] * 30,
                      "close": [100.0, 120.0, 120.0001] + [110.0] * 27, "ret_20": [0.9, 0.9, 0.9] + list(np.linspace(-0.2, 0.2, 27))})
    st = sf1.buckets(u)["strong"]
    assert "E0" not in st and "E1" in st and "E2" not in st                                              # 0% is out, exactly 20% is in


class _Clock(dt.datetime):
    at = None

    @classmethod
    def now(cls, tz=None):
        return cls.at.astimezone(tz) if tz else cls.at


@pytest.mark.parametrize("hhmm,ok", [("06:50", True), ("09:14", True), ("09:15", False)])
def test_the_real_0915_refusal(world, monkeypatch, hhmm, ok):
    monkeypatch.setattr(managed, "refuse_late", REAL_REFUSE)
    h, m = map(int, hhmm.split(":"))
    _Clock.at = dt.datetime(2026, 11, 23, h, m, tzinfo=managed.IST)
    fake = type("dtmod", (), {"datetime": _Clock, "date": dt.date, "time": dt.time, "timedelta": dt.timedelta, "timezone": dt.timezone})
    monkeypatch.setattr(managed, "dt", fake)
    if ok:
        assert _rec(_bars())["status"] == "written"
    else:
        with pytest.raises(RuntimeError, match="opened"):
            _rec(_bars())
        assert not (world / "paper" / "shadow" / "sf1" / "rows.jsonl").exists()


def test_no_calendar_no_row(world, monkeypatch):
    monkeypatch.setattr(managed, "holidays", lambda: set())
    with pytest.raises(RuntimeError, match="holiday calendar"):
        _rec(_bars())


def test_newey_west_t():
    assert sf1.nw_t(np.array([1.0, 2.0])) is None
    x = np.random.default_rng(1).standard_normal(400) + 0.5
    assert 4 < sf1.nw_t(x) < 15


def test_no_decision_module_imports_sf1():
    root = Path(sf1.__file__).parents[1]
    for f in root.rglob("*.py"):
        rel = f.relative_to(root).parts
        if f.name == "sf1.py" or rel[0] in ("tests", ".venv", "venv", "node_modules") or "site-packages" in rel:
            continue
        src = f.read_text(errors="ignore")
        tree = ast.parse(src)
        for n in ast.walk(tree):
            names = [a.name for a in n.names] if isinstance(n, (ast.Import, ast.ImportFrom)) else []
            mod = (n.module or "") if isinstance(n, ast.ImportFrom) else ""
            assert "sf1" not in mod and not any(x.endswith("sf1") for x in names), f"{f} imports sf1"
        assert "india.sf1" not in src and "\"sf1\"" not in src.replace("'", '"'), f"{f} names sf1 (importlib or a string import)"
    src = Path(sf1.__file__).read_text()
    imports = [l for l in src.splitlines() if l.startswith(("import ", "from "))]
    for banned in ("kite", "allocator", "orders", "crypto", "jarvis"):
        assert not any(banned in l for l in imports), banned
