"""One market feed for every coin in the registry (engine plan U2): Binance public market data, no keys.

  5-minute candles   every 5 minutes, closed candles only, kept 14 days; 15-minute, hourly and 4-hour candles are built from them
  daily candles      after each UTC close, full history on first sight (up to 1,000 days), with the traded value (quote volume)
  live prices        every 10 seconds, every registry coin in a few small calls
Separate database (universe_bars.sqlite in the agent folder) so the 10-coin books and their candles are never touched.
Parallel requests stay far inside Binance's request-weight allowance (6,000 a minute; the feed uses about 4%).

  start(get_j, on_prices)  the background loop (one thread inside the Jarvis service)
  daily(j, coin)           closed daily candles (t, o, h, l, c, v) for the rule engine (same shape as tier30.daily)
  daily_qv(j, coin)        (t, quote volume) for the registry's tiers
  bars(j, coin, tf, n)     5m / 15m / 1h / 4h candles from the 5-minute store
  prices(j)                the latest live prices {coin: price}
  status(j)                freshness and timings for Health and the Evidence page
Read-only; nothing here trades.
"""
from __future__ import annotations

import json
import sqlite3
import threading
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable

API = "https://api.binance.com"
DB = "universe_bars.sqlite"
DAY, M5 = 86400, 300
KEEP_5M_DAYS = 14
WORKERS = 8
PRICE_EVERY = 10
TF = {"5m": 300, "15m": 900, "30m": 1800, "1h": 3600, "4h": 14400}
STATE: dict[str, Any] = {"running": False, "weight": 0, "errors": {}, "last": {}}
_lock = threading.RLock()
_PX: dict = {"t": 0.0, "px": {}}


def _get(path: str, params: dict | None = None, timeout: int = 15):
    url = API + path + ("?" + urllib.parse.urlencode(params) if params else "")
    last = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ananta-feed/1"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                w = r.headers.get("x-mbx-used-weight-1m")
                if w:
                    STATE["weight"] = int(w)
                return json.loads(r.read())
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(1 + 2 * attempt)
    raise last


def _con(j) -> sqlite3.Connection:
    con = sqlite3.connect(str(Path(j.dir) / DB), timeout=30, check_same_thread=False)
    con.execute("PRAGMA journal_mode=WAL")
    con.executescript("""
        CREATE TABLE IF NOT EXISTS d1 (coin TEXT, t INTEGER, o REAL, h REAL, l REAL, c REAL, v REAL, qv REAL, PRIMARY KEY (coin, t));
        CREATE TABLE IF NOT EXISTS m5 (coin TEXT, t INTEGER, o REAL, h REAL, l REAL, c REAL, v REAL, PRIMARY KEY (coin, t));
        CREATE TABLE IF NOT EXISTS px (coin TEXT PRIMARY KEY, price REAL, t INTEGER);
        CREATE TABLE IF NOT EXISTS hx (coin TEXT, tf TEXT, t INTEGER, o REAL, h REAL, l REAL, c REAL, v REAL, PRIMARY KEY (coin, tf, t));
        CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT);
    """)
    return con


def _ro(j) -> sqlite3.Connection:
    p = Path(j.dir) / DB
    if not p.exists():
        _con(j).close()
    return sqlite3.connect(f"file:{p}?mode=ro", uri=True, timeout=30)


def _meta(con, k: str, v: str | None = None):
    if v is None:
        r = con.execute("SELECT v FROM meta WHERE k=?", (k,)).fetchone()
        return r[0] if r else None
    con.execute("INSERT OR REPLACE INTO meta VALUES (?,?)", (k, v))
    return v


def _symbol(j, coin: str) -> str:
    from jarvis.service import registry

    return (registry.card(j, coin) or {}).get("symbol") or f"{coin}USDT"


def _klines(symbol: str, interval: str, limit: int, start: int | None = None) -> list:
    p = {"symbol": symbol, "interval": interval, "limit": limit}
    if start is not None:
        p["startTime"] = start * 1000
    return _get("/api/v3/klines", p)


def _parallel(fn: Callable, items: list) -> dict:
    out, errs = {}, {}
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(fn, x): x for x in items}
        for f, x in futs.items():
            try:
                out[x] = f.result()
            except Exception as exc:  # noqa: BLE001  one coin failing never stops the others
                errs[x] = str(exc)[:120]
    return {"ok": out, "errors": errs}


def pull_daily(j, coins: list[str], now: float | None = None) -> dict:
    """New closed daily candles for every coin (the whole history the first time)."""
    now = now or time.time()
    con = _con(j)
    try:
        last = dict(con.execute("SELECT coin, MAX(t) FROM d1 GROUP BY coin").fetchall())
        today0 = int(now // DAY * DAY)
        todo = [c for c in coins if (last.get(c) or 0) < today0 - DAY]   # yesterday not stored yet

        def one(c):
            lt = last.get(c)
            rows = _klines(_symbol(j, c), "1d", 1000, start=(lt + DAY) if lt else None)
            return [(c, int(k[0]) // 1000, float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5]), float(k[7]))
                    for k in rows if int(k[6]) / 1000 < now]

        t0 = time.time()
        res = _parallel(one, todo)
        with _lock:
            for rows in res["ok"].values():
                con.executemany("INSERT OR REPLACE INTO d1 VALUES (?,?,?,?,?,?,?,?)", rows)
            _meta(con, "daily_done", str(int(now)))
            con.commit()
        out = {"coins": len(todo), "errors": len(res["errors"]), "seconds": round(time.time() - t0, 1)}
        STATE["last"]["daily"] = out
        if res["errors"]:
            STATE["errors"]["daily"] = dict(list(res["errors"].items())[:10])
        return out
    finally:
        con.close()


def pull_5m(j, coins: list[str], now: float | None = None) -> dict:
    """New closed 5-minute candles for every coin; two days on first sight; 14 days kept."""
    now = now or time.time()
    con = _con(j)
    try:
        last = dict(con.execute("SELECT coin, MAX(t) FROM m5 GROUP BY coin").fetchall())
        cut = int(now // M5 * M5) - M5                     # open time of the newest closed candle

        def one(c):
            lt = last.get(c)
            if lt is not None and lt >= cut:
                return []
            n = 576 if lt is None else min(1000, int((now - lt) // M5) + 2)
            rows = _klines(_symbol(j, c), "5m", n)
            return [(c, int(k[0]) // 1000, float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5]))
                    for k in rows if int(k[6]) / 1000 < now]

        t0 = time.time()
        res = _parallel(one, coins)
        with _lock:
            for rows in res["ok"].values():
                con.executemany("INSERT OR REPLACE INTO m5 VALUES (?,?,?,?,?,?,?)", rows)
            con.execute("DELETE FROM m5 WHERE t < ?", (int(now) - KEEP_5M_DAYS * DAY,))
            on_time = sum(1 for c in coins if (con.execute("SELECT MAX(t) FROM m5 WHERE coin=?", (c,)).fetchone()[0] or 0) >= cut)
            _meta(con, "m5_done", str(int(now)))
            con.commit()
        out = {"coins": len(coins), "on_time": on_time, "errors": len(res["errors"]), "seconds": round(time.time() - t0, 1),
               "weight_1m": STATE.get("weight")}
        STATE["last"]["m5"] = out
        if res["errors"]:
            STATE["errors"]["m5"] = dict(list(res["errors"].items())[:10])
        return out
    finally:
        con.close()


HX_FIRST = {"1h": 300, "4h": 200}


def pull_hx(j, coins: list[str], tf: str, now: float | None = None) -> dict:
    """Hourly and 4-hour candles straight from Binance (the 5-minute store keeps only 14 days, too short for the 4-hour warm-up)."""
    now = now or time.time()
    step = TF[tf]
    con = _con(j)
    try:
        last = dict(con.execute("SELECT coin, MAX(t) FROM hx WHERE tf=? GROUP BY coin", (tf,)).fetchall())
        cut = int(now // step * step) - step
        todo = [c for c in coins if (last.get(c) or 0) < cut]

        def one(c):
            lt = last.get(c)
            n = HX_FIRST[tf] if lt is None else min(1000, int((now - lt) // step) + 2)
            return [(c, tf, int(k[0]) // 1000, float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5]))
                    for k in _klines(_symbol(j, c), tf, n) if int(k[6]) / 1000 < now]

        res = _parallel(one, todo) if todo else {"ok": {}, "errors": {}}
        with _lock:
            for rows in res["ok"].values():
                con.executemany("INSERT OR REPLACE INTO hx VALUES (?,?,?,?,?,?,?,?)", rows)
            con.commit()
        return {"tf": tf, "coins": len(todo), "errors": len(res["errors"])}
    finally:
        con.close()


def pull_prices(j, coins: list[str]) -> dict[str, float]:
    """Every coin's live price in chunks of 150 symbols (a few small calls)."""
    syms = {_symbol(j, c): c for c in coins}
    keys = list(syms)
    px = {}
    for i in range(0, len(keys), 150):
        chunk = keys[i:i + 150]
        rows = _get("/api/v3/ticker/price", {"symbols": json.dumps(chunk, separators=(",", ":"))})
        for r in rows:
            c = syms.get(r["symbol"])
            if c:
                px[c] = float(r["price"])
    t = int(time.time())
    _PX.update(t=t, px=px)
    con = _con(j)
    try:
        with _lock:
            con.executemany("INSERT OR REPLACE INTO px VALUES (?,?,?)", [(c, p, t) for c, p in px.items()])
            con.commit()
    finally:
        con.close()
    return px


def prices(j) -> dict[str, float]:
    if _PX["px"] and time.time() - _PX["t"] < 60:
        return dict(_PX["px"])
    con = _ro(j)
    try:
        return {c: p for c, p, t in con.execute("SELECT coin, price, t FROM px") if time.time() - t < 600}
    finally:
        con.close()


def daily(j, coin: str) -> list[tuple]:
    con = _ro(j)
    try:
        return [tuple(r) for r in con.execute("SELECT t, o, h, l, c, v FROM d1 WHERE coin=? ORDER BY t", (coin,))]
    finally:
        con.close()


def last_closes(j) -> dict[str, float]:
    """Each coin's last daily close (yesterday's UTC close), one query."""
    con = _ro(j)
    try:
        return {c: px for c, px in con.execute("SELECT d.coin, d.c FROM d1 d JOIN (SELECT coin, MAX(t) t FROM d1 GROUP BY coin) m "
                                               "ON d.coin = m.coin AND d.t = m.t")}
    finally:
        con.close()


def daily_qv(j, coin: str) -> list[tuple]:
    con = _ro(j)
    try:
        return [tuple(r) for r in con.execute("SELECT t, qv FROM d1 WHERE coin=? ORDER BY t", (coin,))]
    finally:
        con.close()


def bars(j, coin: str, tf: str = "15m", n: int = 200) -> list[tuple]:
    """Candles (t, o, h, l, c, v): hourly and 4-hour from Binance's own candles when stored, else built from the 5-minute store;
    only complete candles."""
    step = TF[tf]
    con = _ro(j)
    try:
        if tf in HX_FIRST:
            rows = con.execute("SELECT t, o, h, l, c, v FROM hx WHERE coin=? AND tf=? ORDER BY t DESC LIMIT ?", (coin, tf, n)).fetchall()
            if rows:
                return [tuple(r) for r in rows[::-1]]
        rows = con.execute("SELECT t, o, h, l, c, v FROM m5 WHERE coin=? ORDER BY t DESC LIMIT ?", (coin, n * step // M5 + step // M5)).fetchall()
    finally:
        con.close()
    rows = rows[::-1]
    if step == M5:
        return [tuple(r) for r in rows][-n:]
    out, cur = [], None
    for t, o, h, lo, c, v in rows:
        b = t // step * step
        if cur is None or cur[0] != b:
            if cur and cur[6] == step // M5:
                out.append(tuple(cur[:6]))
            cur = [b, o, h, lo, c, v, 1]
        else:
            cur[2], cur[3], cur[4], cur[5], cur[6] = max(cur[2], h), min(cur[3], lo), c, cur[5] + v, cur[6] + 1
    if cur and cur[6] == step // M5:
        out.append(tuple(cur[:6]))
    return out[-n:]


def status(j) -> dict:
    con = _ro(j)
    try:
        n_d1 = con.execute("SELECT COUNT(DISTINCT coin) FROM d1").fetchone()[0]
        n_m5 = con.execute("SELECT COUNT(DISTINCT coin) FROM m5").fetchone()[0]
        px_n, px_t = con.execute("SELECT COUNT(*), MAX(t) FROM px").fetchone()
        m5_done = _meta(con, "m5_done")
        d_done = _meta(con, "daily_done")
    finally:
        con.close()
    return {"running": STATE.get("running"), "coins_with_daily": n_d1, "coins_with_5m": n_m5, "prices": px_n,
            "price_age_s": round(time.time() - px_t) if px_t else None, "last_5m_pull": STATE["last"].get("m5"),
            "last_daily_pull": STATE["last"].get("daily"), "m5_done_t": int(m5_done) if m5_done else None,
            "daily_done_t": int(d_done) if d_done else None, "weight_1m": STATE.get("weight"),
            "errors": STATE.get("errors"), "source": "Binance public market data (spot, against USDT)"}


def cycle(j, now: float | None = None, on_daily: Callable | None = None) -> dict:
    """One 5-minute round: registry + daily candles after the UTC close, then 5-minute candles for every coin."""
    from jarvis.service import registry

    now = now or time.time()
    out: dict = {}
    reg = registry.load(j)
    if not reg.get("built_at") or int(reg["built_at"] // DAY) < int(now // DAY) and now % DAY >= 300:
        if not reg.get("built_at"):
            out["registry"] = registry.build(j)                        # first time: membership, then tiers once history is in
        coins = registry.members(j)
        out["daily"] = pull_daily(j, coins, now)
        out["registry"] = registry.build(j, daily_qv=lambda c: daily_qv(j, c))
        if on_daily:
            try:
                out["on_daily"] = on_daily(j)
            except Exception as exc:  # noqa: BLE001
                out["on_daily_error"] = str(exc)[:200]
    out["m5"] = pull_5m(j, registry.members(j), now)
    for tf in HX_FIRST:
        try:
            out[tf] = pull_hx(j, registry.members(j), tf, now)
        except Exception as exc:  # noqa: BLE001
            out[tf] = {"error": str(exc)[:120]}
    return out


def start(get_j: Callable[[], Any], on_prices: Callable | None = None, on_daily: Callable | None = None, on_5m: Callable | None = None) -> bool:
    """Prices every 10 seconds; a 5-minute round 20 seconds after each 5-minute close."""
    with _lock:
        if STATE.get("running"):
            return False
        STATE["running"] = True

    def loop():
        from jarvis.service import registry

        next_round = 0.0
        while STATE.get("running"):
            t0 = time.time()
            j = get_j()
            try:
                if t0 >= next_round:
                    STATE["last"]["cycle"] = cycle(j, on_daily=on_daily)
                    if on_5m:
                        try:
                            STATE["last"]["on_5m"] = on_5m(j)
                        except Exception as exc:  # noqa: BLE001
                            STATE["errors"]["on_5m"] = str(exc)[:200]
                    next_round = (time.time() // M5 + 1) * M5 + 20
                coins = registry.members(j)
                if coins:
                    px = pull_prices(j, coins)
                    if on_prices:
                        try:
                            on_prices(j, px)
                        except Exception as exc:  # noqa: BLE001
                            STATE["errors"]["on_prices"] = str(exc)[:200]
            except Exception as exc:  # noqa: BLE001
                STATE["errors"]["loop"] = f"{time.strftime('%H:%M:%S')} {str(exc)[:200]}"
            time.sleep(max(1.0, PRICE_EVERY - (time.time() - t0)))

    threading.Thread(target=loop, name="ananta-feed", daemon=True).start()
    return True
