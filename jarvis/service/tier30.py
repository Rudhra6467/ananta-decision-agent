"""The 30-coin paper tier (Madhav, 2026-10-04: "give paper slots in the 30-coin tier, separately").

Review #15 (docs/research/REVIEW_15_RESULTS.md in the research repo) passed two ideas on the top 30 coins but not on all 120:
  * T3, the trend portfolio   -> its own book, portfolio_book_t30.sqlite (AUTO: paper only, no approvals), $2000 start
  * H07, the short dip trade  -> its own watch, H07-T30, in the shared evidence book (evidence_trades), $100 per signal
Both are kept apart from the 10-coin books, so the 10-coin evidence is never mixed with the 30-coin evidence.

Coins: the top 30 of universe rule v1 (~/ananta_lake/reports/universe_v1.json). Four of them no longer trade under that ticker:
MATIC -> POL, FTM -> S, RNDR -> RENDER (the same projects, renamed); BCHABC is the old BCH, already in the list, so dropped.
That leaves 29 coins.

Candles: Binance spot daily candles (public market data, no keys), closed days only, stored in tier30_bars.sqlite and refreshed
once per new UTC day. The 10-coin books keep using the Explorer's candles. Costs: NDAX 0.20% a side plus the measured half
spread for the lab 10 and 0.40% for every other coin (the review #15 assumption). Many of these coins are not on NDAX: this
is evidence, not a list of things to buy. Nothing here reaches Hands or an exchange.

  refresh(j)   pull new closed daily candles (once a day)
  run(j)       refresh, then the T3 book's daily decision and the H07-T30 watch
  status(j)    both books for the app and Ask
"""
from __future__ import annotations

import json
import sqlite3
import time
import urllib.request
from pathlib import Path

TIER = "T30"
COINS = ["BTC", "ETH", "SOL", "XRP", "DOGE", "BNB", "SUI", "PEPE", "TRX", "ADA", "POL", "ENA", "AVAX", "LINK", "LTC", "TAO",
         "TRUMP", "NEAR", "WIF", "S", "WLD", "AAVE", "UNI", "RENDER", "HBAR", "ARB", "TON", "BONK", "BCH"]
RENAMED = {"MATIC": "POL", "FTM": "S", "RNDR": "RENDER", "BCHABC": None}
T3_DB = "portfolio_book_t30.sqlite"
H07_WATCH = "H07-T30"
DAY = 86400
URL = "https://api.binance.com/api/v3/klines?symbol={s}USDT&interval=1d&limit=1000"


def _con(j) -> sqlite3.Connection:
    con = sqlite3.connect(str(Path(j.dir) / "tier30_bars.sqlite"), timeout=30)
    con.execute("CREATE TABLE IF NOT EXISTS bars (coin TEXT, t INTEGER, o REAL, h REAL, l REAL, c REAL, v REAL, PRIMARY KEY (coin, t))")
    con.execute("CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT)")
    return con


def _fetch(coin: str, now: float) -> list[tuple]:
    with urllib.request.urlopen(URL.format(s=coin), timeout=20) as r:
        rows = json.loads(r.read())
    return [(int(k[0]) // 1000, float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5])) for k in rows if int(k[6]) / 1000 < now]


def refresh(j, force: bool = False) -> dict:
    """Pull closed daily candles for every coin, once per new UTC day (a coin that fails keeps its old candles)."""
    now = j.now() if hasattr(j, "now") else time.time()
    today = int(now // DAY * DAY)
    con = _con(j)
    try:
        r = con.execute("SELECT v FROM meta WHERE k='done_day'").fetchone()
        if r and int(r[0]) >= today and not force:
            return {"skip": "already pulled today"}
        ok, failed = 0, {}
        for c in COINS:
            try:
                rows = _fetch(c, now)
                con.executemany("INSERT OR REPLACE INTO bars VALUES (?,?,?,?,?,?,?)", [(c, *x) for x in rows])
                ok += 1
            except Exception as exc:  # noqa: BLE001  one coin never stops the others
                failed[c] = str(exc)[:120]
        if not failed:
            con.execute("INSERT OR REPLACE INTO meta VALUES ('done_day', ?)", (str(today),))
        con.commit()
        return {"pulled": ok, "failed": failed}
    finally:
        con.close()


def daily(j, coin: str) -> list[tuple]:
    con = _con(j)
    try:
        return [tuple(r) for r in con.execute("SELECT t, o, h, l, c, v FROM bars WHERE coin=? ORDER BY t", (coin,))]
    finally:
        con.close()


def _layer(j):
    from src.intelligence import portfolio_layer as pl

    layer = pl.PortfolioLayer(j.dir, db=T3_DB)
    if not layer.con.execute("SELECT 1 FROM meta WHERE k='mode'").fetchone():
        layer.set_mode("AUTO", by="Madhav 2026-10-04: paper slot for the 30-coin tier (paper only, no approvals)")
    return layer


def _views(j) -> tuple[dict, dict]:
    from src.intelligence import portfolio_layer as pl
    from src.intelligence.explorer_engine import TfState

    views, px = {}, {}
    for c in COINS:
        D = daily(j, c)
        if len(D) < 60:
            continue
        tf = TfState("1d")
        for b in D:
            tf.add(*b)
        v = pl.daily_view(tf)
        if v:
            views[c], px[c] = v, D[-1][4]
    return views, px


def run(j) -> dict:
    from jarvis.service import watch_engine

    out = {"bars": refresh(j)}
    views, px = _views(j)
    if "BTC" in views:
        d = _layer(j).decide(views, px, int(j.now() if hasattr(j, "now") else time.time()))
        out["t3"] = {k: d[k] for k in ("skip", "day", "btc_gate") if k in d}
        if "fills" in d:
            out["t3"]["fills"] = len(d["fills"])
            out["t3"]["holding"] = sorted(c for c, r in d["ratings"].items() if r["hold"])
    out["h07"] = watch_engine.run(j, watches=(H07_WATCH,), coins=COINS, daily_fn=daily, live_trades=False)
    return out


def buy_hold(j) -> dict:
    """The fair comparison for the 30-coin trend book (status check, Oct 8: it had none): equal money in every tier coin at the
    close before the book's first decision, held to the latest close. A coin whose daily data stopped (older than 3 days) is
    left out and named."""
    import sqlite3 as _sq
    from pathlib import Path as _P

    p = _P(j.dir) / "portfolio_book_t30.sqlite"
    if not p.exists():
        return {}
    con = _sq.connect(f"file:{p}?mode=ro", uri=True, timeout=10)
    try:
        first = con.execute("SELECT min(day_t) FROM decisions").fetchone()[0]
    finally:
        con.close()
    if not first:
        return {}
    newest = max((D[-1][0] for D in (daily(j, c) for c in COINS) if D), default=0)
    chg, stale = [], []
    for c in COINS:
        D = daily(j, c)
        if not D or D[-1][0] < newest - 3 * 86400:
            stale.append(c)
            continue
        base = next((b[4] for b in reversed(D) if b[0] < first), None)
        if base:
            chg.append(100 * (D[-1][4] / base - 1))
    return {"pct": round(sum(chg) / len(chg), 2) if chg else None, "coins": len(chg), "stale": stale, "since_t": first}


def status(j) -> dict:
    from jarvis.service import watch_engine

    _, px = _views(j)
    t3 = _layer(j).status(px)
    rows = watch_engine.trades(j, H07_WATCH, 200)
    done = [r for r in rows if r["status"] == "CLOSED"]
    return {"tier": TIER, "coins": COINS, "renamed": RENAMED,
            "t3": {"name": "Trend portfolio (T3), 30-coin paper book", "mode": t3["mode"], "books": t3["books"],
                   "last_day": (t3["last_decision"] or {}).get("day")},
            "h07": {"name": "Short dip trade (H07), 30-coin paper watch", "open": sum(r["status"] == "OPEN" for r in rows),
                    "waiting": sum(r["status"] == "WAITING" for r in rows), "closed": len(done),
                    "net_usd": round(sum(r["net_usd"] for r in done), 2) if done else 0.0, "trades": rows[:30]},
            "history": "review #15: T3 +19.0% vs buy-and-hold -23.7% (2024-Jul 2026) on the top 30; H07 33 events, +6.0% excess, z 3.5 "
                       "(2018-23) and +3.6%, z 3.2 (2024-26). Both failed on all 120 coins. Review #22 (the top 30 as it was each month): T3-B -22.5% vs "
                       "holding -76% (fails its profit rule), H07 z 2.45 (just under the bar): today's top-30 numbers were flattered.",
            "note": "Paper only. Kept apart from the 10-coin books. Many of these coins are not on NDAX."}
