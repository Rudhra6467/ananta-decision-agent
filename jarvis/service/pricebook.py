"""Price history from the candles Ananta already stores (explorer_bars.sqlite, read-only): answers like "what was the high
this week", "how did each coin do over 7 days", "which days were good", "where was Bitcoin on Tuesday".

Madhav's conversations (2026-10-01..03) asked this kind of question about 8 times and Ananta had to say "I can't": the candles
were there, nobody had given it a way to read them. Closed candles only, for our 10 coins; times in UTC and Toronto.

  history(j, coin, days, start, end)  one coin: open/high/low/close and change over the window, when the high and low happened,
                                      the best and worst day, and day-by-day (or hour-by-hour for 2 days or less)
  compare(j, days, start, end)        all 10 coins over the window, ranked, each against Bitcoin
  coverage(j)                         the first and last stored candle per coin and timeframe
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

COINS = ["BTC", "ETH", "SOL", "ADA", "DOGE", "AVAX", "BCH", "LINK", "LTC", "XRP"]
TF_S = {"5m": 300, "15m": 900, "1h": 3600, "4h": 14400, "1d": 86400}
TZ = ZoneInfo("America/Toronto")
NAMES = {"BTC": "Bitcoin", "ETH": "Ethereum", "SOL": "Solana", "ADA": "Cardano", "DOGE": "Dogecoin", "AVAX": "Avalanche",
         "BCH": "Bitcoin Cash", "LINK": "Chainlink", "LTC": "Litecoin", "XRP": "XRP"}


def _con(j) -> sqlite3.Connection:
    p = Path(j.dir) / "explorer_bars.sqlite"
    if not p.exists():
        raise ValueError("the Explorer's candles are not available on this machine")
    return sqlite3.connect(f"file:{p}?mode=ro", uri=True, timeout=10)


def _coin(c: str | None) -> str:
    x = (c or "").upper().replace("/USD", "").strip()
    alias = {v.upper(): k for k, v in NAMES.items()}
    x = alias.get(x, x)
    if x not in COINS:
        raise ValueError(f"{c} is not one of our 10 coins ({', '.join(COINS)}); for other coins use outside_coin or web_lookup")
    return x


def _when(s: str | None, default: float) -> float:
    """ISO date or date-time ('2026-10-02', '2026-10-02 14:00', Toronto time unless it ends in Z/UTC); empty = default."""
    if not s:
        return default
    t = str(s).strip().replace("T", " ")
    utc = t.upper().endswith(("Z", "UTC"))
    t = t.upper().removesuffix("UTC").removesuffix("Z").strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            d = datetime.strptime(t, fmt)
            return d.replace(tzinfo=timezone.utc if utc else TZ).timestamp()
        except ValueError:
            continue
    raise ValueError(f"could not read the time '{s}'; use YYYY-MM-DD or YYYY-MM-DD HH:MM (Toronto)")


def _fmt(t: float) -> str:
    return datetime.fromtimestamp(t, TZ).strftime("%a %b %d, %I:%M %p").replace(" 0", " ") + " Toronto"


def _px(x: float) -> float:
    return round(x, 2) if x >= 100 else round(x, 4) if x >= 1 else round(x, 6)


def coverage(j) -> dict:
    con = _con(j)
    out: dict = {}
    for coin, tf, t0, t1, n in con.execute("SELECT coin, tf, MIN(t), MAX(t), COUNT(*) FROM bars GROUP BY coin, tf"):
        out.setdefault(coin, {})[tf] = {"first": datetime.fromtimestamp(t0, timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
                                        "last": datetime.fromtimestamp(t1, timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), "bars": n}
    res = {}
    try:
        import json as _json

        from jarvis.service.core import docs_dir

        res = _json.loads((docs_dir(j.dir) / "research" / "data_coverage.json").read_text())
    except Exception:  # noqa: BLE001
        pass
    return {"live_candles": out, "research_history": res,
            "note": "live_candles = what the Explorer stored from Hands (Kraken) for live trading; research_history = the 5-minute "
                    "dataset the repair shop tests on (first candle per coin)."}


def _bars(con, coin: str, start: float, end: float, finest: bool = True) -> tuple[str, list[tuple]]:
    """The finest timeframe whose stored candles cover the whole window (else the longest one available)."""
    best = None
    for tf in (["5m", "15m", "1h", "4h", "1d"] if finest else ["1h", "4h", "1d"]):
        first = con.execute("SELECT MIN(t) FROM bars WHERE coin=? AND tf=?", (coin, tf)).fetchone()[0]
        if first is None:
            continue
        rows = con.execute("SELECT t, o, h, l, c FROM bars WHERE coin=? AND tf=? AND t >= ? AND t + ? <= ? ORDER BY t",
                           (coin, tf, int(start) - TF_S[tf] + 1, TF_S[tf], int(end) + 1)).fetchall()
        if first <= start + TF_S[tf] and rows:
            if tf in ("5m", "15m") and (end - start) / TF_S[tf] > 6000:
                continue                                       # long windows: hourly is plenty
            return tf, rows
        if rows and (best is None or len(rows) > len(best[1])):
            best = (tf, rows)
    if best:
        return best
    raise ValueError(f"no stored candles for {coin} in that window")


def _summary(coin: str, tf: str, rows: list[tuple]) -> dict:
    hi = max(rows, key=lambda r: r[2])
    lo = min(rows, key=lambda r: r[3])
    o, c = rows[0][1], rows[-1][4]
    return {"coin": coin, "name": NAMES[coin], "timeframe_used": tf, "from": _fmt(rows[0][0]), "to": _fmt(rows[-1][0] + TF_S[tf]),
            "open": _px(o), "high": _px(hi[2]), "high_when": _fmt(hi[0]), "low": _px(lo[3]), "low_when": _fmt(lo[0]), "close": _px(c),
            "change_pct": round(100 * (c / o - 1), 2), "range_pct": round(100 * (hi[2] / lo[3] - 1), 2),
            "from_high_pct": round(100 * (c / hi[2] - 1), 2), "from_low_pct": round(100 * (c / lo[3] - 1), 2)}


def history(j, coin: str, days: float | None = 7, start: str | None = None, end: str | None = None) -> dict:
    coin = _coin(coin)
    t_end = _when(end, j.now())
    t_start = _when(start, t_end - float(days or 7) * 86400)
    if t_start >= t_end:
        raise ValueError("the start must be before the end")
    con = _con(j)
    tf, rows = _bars(con, coin, t_start, t_end)
    out = _summary(coin, tf, rows)
    span = t_end - t_start
    if span <= 2 * 86400:                                     # hour by hour
        h_tf, h_rows = _bars(con, coin, t_start, t_end, finest=False)
        out["by_hour"] = [{"hour": datetime.fromtimestamp(r[0], TZ).strftime("%a %I %p").replace(" 0", " "), "close": _px(r[4]),
                           "change_pct": round(100 * (r[4] / r[1] - 1), 2)} for r in h_rows if h_tf == "1h"][-48:]
    else:                                                     # day by day (UTC days: each closes at 8 pm Toronto in summer)
        d_rows = con.execute("SELECT t, o, h, l, c FROM bars WHERE coin=? AND tf='1d' AND t >= ? AND t + 86400 <= ? ORDER BY t",
                             (coin, int(t_start) - 86399, int(t_end) + 1)).fetchall()
        days_out = [{"day": datetime.fromtimestamp(r[0], timezone.utc).strftime("%a %b %d"), "open": _px(r[1]), "high": _px(r[2]),
                     "low": _px(r[3]), "close": _px(r[4]), "change_pct": round(100 * (r[4] / r[1] - 1), 2)} for r in d_rows]
        if days_out:
            out["by_day"] = days_out[-31:]
            out["best_day"] = max(days_out, key=lambda d: d["change_pct"])
            out["worst_day"] = min(days_out, key=lambda d: d["change_pct"])
            out["up_days"] = sum(d["change_pct"] > 0 for d in days_out)
            out["days_counted"] = len(days_out)
    out["note"] = "From our stored closed candles (Kraken via Hands). Days are UTC days, closing at 8 pm Toronto (7 pm in winter)."
    return out


def compare(j, days: float | None = 7, start: str | None = None, end: str | None = None) -> dict:
    t_end = _when(end, j.now())
    t_start = _when(start, t_end - float(days or 7) * 86400)
    con = _con(j)
    rows = []
    for c in COINS:
        try:
            tf, b = _bars(con, c, t_start, t_end, finest=False)
            rows.append(_summary(c, tf, b))
        except ValueError:
            continue
    btc = next((r["change_pct"] for r in rows if r["coin"] == "BTC"), None)
    rows.sort(key=lambda r: -r["change_pct"])
    for i, r in enumerate(rows, start=1):
        r["rank"] = i
        r["vs_btc_pct_points"] = None if btc is None else round(r["change_pct"] - btc, 2)
    slim = [{k: r[k] for k in ("rank", "coin", "name", "change_pct", "vs_btc_pct_points", "high", "low", "close", "from_high_pct", "range_pct")} for r in rows]
    return {"window": f"{_fmt(t_start)} to {_fmt(t_end)}", "coins": slim, "btc_change_pct": btc,
            "leader": slim[0]["coin"] if slim else None, "laggard": slim[-1]["coin"] if slim else None,
            "note": "Relative strength = change minus Bitcoin's change over the same window. From our stored closed candles."}
