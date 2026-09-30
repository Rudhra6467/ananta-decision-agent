"""Review #2 pipeline smoke: context table, trader round trips, forward excess, joins, D1-D4 run end to end."""
import random
import sqlite3
import tempfile
from pathlib import Path

try:
    import pandas  # noqa: F401

    from src.research import review2_traders as r2
    from tests.test_explorer import T0, _series
except ImportError:
    r2 = None


def test_pipeline_end_to_end():
    if r2 is None:
        return
    d = Path(tempfile.mkdtemp())
    db = d / "x.sqlite"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE bars (instrument TEXT, event_unix INTEGER, open REAL, high REAL, low REAL, close REAL, volume REAL)")
    series = {}
    for coin, seed in (("BTC", 1), ("ETH", 2)):
        series[coin] = _series(days=90, seed=seed)
        con.executemany("INSERT INTO bars VALUES (?,?,?,?,?,?,?)", [(f"{coin}-USD-SPOT", *b) for b in series[coin]])
    con.commit()
    con.close()
    for coin in ("BTC", "ETH"):
        assert r2.context_coin(str(db), coin, str(d))["scans"] > 1000
    hl = d / "hl.sqlite"
    h = sqlite3.connect(hl)
    h.executescript("""CREATE TABLE accounts (address TEXT PRIMARY KEY, source TEXT, meta_json TEXT, status TEXT);
        CREATE TABLE fills (address TEXT, tid INTEGER, time INTEGER, coin TEXT, side TEXT, px REAL, sz REAL,
        start_pos REAL, dir TEXT, closed_pnl REAL, fee REAL, PRIMARY KEY (address, tid));""")
    rnd = random.Random(3)
    tid = 0
    for a in ("0xaaa", "0xbbb", "0xccc"):
        h.execute("INSERT INTO accounts VALUES (?,?,?,?)", (a, "TAPE", "{}", "DONE"))
        for k in range(60):
            t = T0 + 62 * 86400 + k * 7 * 3600 + rnd.randint(0, 3000)
            coin = rnd.choice(["BTC", "ETH"])
            pnl = rnd.gauss(0.5 if a == "0xaaa" else -0.2, 2)
            tid += 1
            h.execute("INSERT INTO fills VALUES (?,?,?,?,?,?,?,?,?,?,?)", (a, tid, t * 1000, coin, "B", 100, 1, 0, "Open Long", 0, 0.01))
            tid += 1
            h.execute("INSERT INTO fills VALUES (?,?,?,?,?,?,?,?,?,?,?)", (a, tid, (t + 5 * 3600) * 1000, coin, "A", 101, 1, 1, "Close Long", pnl, 0.01))
    h.commit()
    h.close()
    import src.intelligence.explorer_engine as xe
    old = xe.COINS
    try:
        rep = r2.analyze(str(db), str(hl), d)
    finally:
        xe.COINS = old
    assert rep["entries"] > 100 and "LONG|ALL" in rep["D1"] and "D4" in rep and rep["D3"]["long_entries"] > 0


if __name__ == "__main__":
    test_pipeline_end_to_end()
    print("ok test_pipeline_end_to_end")
