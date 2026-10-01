"""The checklist must agree with the engine: all conditions met <=> the engine fired the setup."""
from src.intelligence import setup_checklist as sc
from tests.test_explorer import _series
from src.research import explorer_replay as xr
from src.intelligence import explorer_engine as xe


def test_checklist_parity_with_engine():
    eng = xe.CoinEngine("AAA", on_event=lambda e: None)
    eng.random_rate = 0.0
    ev = xr.event_stream(_series())
    i, checked, fired_n = 0, 0, 0
    while i < len(ev):
        T = ev[i][0]
        while i < len(ev) and ev[i][0] == T:
            eng.on_bar(ev[i][2], ev[i][3])
            i += 1
        if T % 900 == 0 and eng.ready():
            st = eng.state(T)
            fired = {f[0] for f in eng.setups(st, all_=True)}
            done = {r["setup"] for r in sc.checklist(eng, st) if r["complete"]}
            assert fired == done, (T, fired, done)
            checked += 1
            fired_n += bool(fired)
            eng.scan(T)
    assert checked > 1000 and fired_n > 20
    d = sc.describe_state(st)
    assert d["trend_1h"] in ("uptrend", "downtrend", "no clear trend")
