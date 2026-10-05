"""What Ananta knows about every coin of the 120-coin research universe (the lake's agent pack), joined with the live state of
the 30-coin paper tier. Madhav 2026-10-05: "the agent has to be sure of the added 120 coins and their details, like it knows
about the existing 10 coins".

Three levels, never mixed up when Ananta talks:
  LAB10    watched live (Explorer, chain, zones, setups, eye, news) -> the existing lookups answer about them in full
  TOP30    the 30-coin paper tier (T3-B book, H07-T30 watch) -> daily, from Binance daily candles
  ALL      the 120-coin research universe -> history, quality, costs, NDAX availability, futures context, research verdicts

Source: ~/ananta_lake/agent/universe.json and daily.sqlite, written by the lake after each update (src/lake/agent_pack.py). Read
only, standard library only. Fresher daily candles for TOP30 coins come from tier30_bars.sqlite (pulled each daily close).

  card(j, coin)                        everything about one coin
  overview(j, tier, rank_by, days, n)  a tier's coins, optionally ranked (change over N days, from_ath, volatility, volume, funding)
  history(j, coin, days, start, end)   daily price history for a universe coin (the 10 live coins use pricebook instead)
"""
from __future__ import annotations

import json
import os
import sqlite3
import statistics
from datetime import datetime, timezone
from pathlib import Path

DAY = 86400
ALIASES = {"POL": "MATIC", "S": "FTM", "RENDER": "RNDR", "BITCOIN": "BTC", "ETHEREUM": "ETH", "SOLANA": "SOL", "CARDANO": "ADA",
           "DOGECOIN": "DOGE", "AVALANCHE": "AVAX", "BITCOIN CASH": "BCH", "CHAINLINK": "LINK", "LITECOIN": "LTC", "RIPPLE": "XRP",
           "PEPE COIN": "PEPE", "SUI NETWORK": "SUI", "TRON": "TRX", "BINANCE COIN": "BNB", "TONCOIN": "TON", "POLYGON": "MATIC",
           "FANTOM": "FTM", "SONIC": "FTM", "RENDER TOKEN": "RNDR", "HEDERA": "HBAR", "ARBITRUM": "ARB", "UNISWAP": "UNI",
           "NEAR PROTOCOL": "NEAR", "WORLDCOIN": "WLD", "BITTENSOR": "TAO", "DOGWIFHAT": "WIF", "ETHENA": "ENA"}
_CACHE: dict = {}


def pack_dir() -> Path:
    return Path(os.path.expanduser(os.getenv("ANANTA_LAKE", "~/ananta_lake"))) / "agent"


def pack() -> dict:
    p = pack_dir() / "universe.json"
    if not p.exists():
        raise ValueError("the 120-coin universe pack is not built yet (python -m src.lake.cli pack)")
    m = p.stat().st_mtime
    if _CACHE.get("m") != m:
        _CACHE.update(m=m, pack=json.loads(p.read_text()))
    return _CACHE["pack"]


def resolve(name: str | None) -> str | None:
    x = (name or "").upper().replace("/USD", "").replace("USDT", "").strip()
    x = ALIASES.get(x, x)
    return x if x in pack()["cards"] else None


def _db():
    p = pack_dir() / "daily.sqlite"
    return sqlite3.connect(f"file:{p}?mode=ro", uri=True, timeout=10)


def daily(j, coin: str) -> list[tuple]:
    """(t, o, h, l, c, v, tbv) complete UTC days: the lake's, then any newer days from the 30-coin tier's daily pull."""
    con = _db()
    try:
        rows = [tuple(r) for r in con.execute("SELECT t, o, h, l, c, v, tbv FROM bars WHERE coin=? ORDER BY t", (coin,))]
    finally:
        con.close()
    card = pack()["cards"].get(coin) or {}
    t30 = card.get("paper_tier_name")
    p = Path(j.dir) / "tier30_bars.sqlite"
    if t30 and p.exists():
        last = rows[-1][0] if rows else 0
        c2 = sqlite3.connect(f"file:{p}?mode=ro", uri=True, timeout=10)
        try:
            rows += [(*r, None) for r in c2.execute("SELECT t, o, h, l, c, v FROM bars WHERE coin=? AND t > ? ORDER BY t", (t30, last))]
        finally:
            c2.close()
    return rows


def _day(t: int) -> str:
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d")


def _px(x):
    return None if x is None else round(x, 2) if x >= 100 else round(x, 4) if x >= 1 else float(f"{x:.4g}")


def _futures(coin: str) -> dict:
    con = _db()
    try:
        f = [r[0] for r in con.execute("SELECT funding FROM funding WHERE coin=? ORDER BY t DESC LIMIT 365", (coin,))]
        oi = con.execute("SELECT t, oi_value, top_ls FROM futures WHERE coin=? ORDER BY t DESC LIMIT 6", (coin,)).fetchall()
    finally:
        con.close()
    out = {}
    if len(f) >= 7:
        f7 = statistics.mean(f[:7])
        hist = sorted(f[7:])
        pct = round(100 * sum(x <= f7 for x in hist) / len(hist)) if len(hist) >= 90 else None
        out["funding_7d_avg_pct_per_8h"] = round(100 * f7, 4)
        out["funding_percentile_vs_past_year"] = pct
        out["funding_reading"] = ("crowded long (top 20% of its past year)" if pct is not None and pct > 80 else
                                  "shorts paying (negative)" if f7 < 0 else "normal")
    if len(oi) >= 6 and oi[5][1]:
        out["open_interest_usd"] = round(oi[0][1])
        out["open_interest_5d_change_pct"] = round(100 * (oi[0][1] / oi[5][1] - 1), 1)
        out["open_interest_day"] = _day(oi[0][0])
    out["note"] = ("Futures context (Binance USD-M), shown as context only: review #19 decides whether any of it helps a decision."
                   if out else "no futures data for this coin")
    return out


def _tier30_live(j, card: dict) -> dict | None:
    name = card.get("paper_tier_name")
    if not name:
        return None
    out: dict = {"name_in_tier": name}
    p = Path(j.dir) / "portfolio_book_t30.sqlite"
    if p.exists():
        con = sqlite3.connect(f"file:{p}?mode=ro", uri=True, timeout=10)
        try:
            row = con.execute("SELECT json FROM decisions ORDER BY day_t DESC LIMIT 1").fetchone()
            book = con.execute("SELECT json FROM books WHERE name='MAIN'").fetchone()
        finally:
            con.close()
        if row:
            d = json.loads(row[0])
            r = (d.get("ratings") or {}).get(name)
            if r:
                out["t3b_rating"] = {"day": d.get("day"), "rating": r["rating"], "held_by_rule": r["hold"], "why": r["why"]}
        if book:
            units = json.loads(book[0]).get("units", {})
            out["t3b_book_holds_it"] = units.get(name, 0) > 0
    try:
        trades = j.db.execute("SELECT signal_day, entry_day, entry, exit_day, net_usd, status FROM evidence_trades "
                              "WHERE watch='H07-T30' AND coin=? ORDER BY signal_t DESC LIMIT 5", (name,)).fetchall()
        out["h07_t30_trades"] = [dict(zip(("signal_day", "entry_day", "entry", "exit_day", "net_usd", "status"), t)) for t in trades]
    except Exception:  # noqa: BLE001
        out["h07_t30_trades"] = []
    return out


def _research_for(card: dict) -> list[dict]:
    tiers = [t for t in ("LAB10", "TOP30", "ALL") if t in card["tiers"]]
    return [{"idea": r["idea"], "review": r["id"], "doc": r["doc"], **{t: r[t] for t in tiers}} for r in pack()["research"]]


def _taker_share(rows: list[tuple]) -> dict:
    sh = [r[6] / r[5] for r in rows[-187:] if r[6] is not None and r[5]]
    if len(sh) < 30:
        return {}
    s7, base = statistics.mean(sh[-7:]), statistics.median(sh[:-7][-180:])
    return {"taker_buy_share_7d_pct": round(100 * s7, 1), "past_180d_median_pct": round(100 * base, 1),
            "reading": "buyers more aggressive than usual" if s7 > base else "sellers more aggressive than usual"}


def card(j, coin: str) -> dict:
    c = resolve(coin)
    if not c:
        return {"in_universe": False, "coin": coin,
                "note": f"{coin} is not in our 120-coin research universe; use outside_coin (CoinGecko) or web_lookup, and say so."}
    k = pack()["cards"][c]
    rows = daily(j, c)
    out = {"in_universe": True, **{x: k[x] for x in ("coin", "binance_symbol", "rank_by_traded_value", "tiers", "what_ananta_does",
                                                      "history", "costs", "ndax")}}
    if rows:
        last = rows[-1]
        o = {"last_close": _px(last[4]), "last_day": _day(last[0])}
        for n in (7, 30, 90, 365):
            if len(rows) > n:
                o[f"change_{n}d_pct"] = round(100 * (last[4] / rows[-1 - n][4] - 1), 1)
        o.update({x: k["now"].get(x) for x in ("all_time_high", "from_ath_pct", "atr14_pct", "above_50d", "above_200d",
                                                "median_daily_usd_volume_90d", "worst_fall_ever_pct", "volatility_1y_pct")})
        out["now"] = o
        out["buying_pressure"] = _taker_share(rows)
    out["futures_context"] = _futures(c)
    live = _tier30_live(j, k)
    if live:
        out["paper_tier_30"] = live
    out["research_on_its_tiers"] = _research_for(k)
    if "LAB10" in k["tiers"]:
        out["for_live_detail"] = "This is one of the 10 live coins: use chain, zones, setups, reads, market and trades lookups for its live picture."
    out["source"] = f"lake agent pack built {pack()['built_at']}"
    return out


def overview(j, tier: str | None = None, rank_by: str | None = None, days: float | None = None, n: int | None = None) -> dict:
    P = pack()
    tier = (tier or "ALL").upper()
    coins = P["tiers"].get(tier) or P["tiers"]["ALL"]
    days = int(days or 30)
    rows = []
    for c in coins:
        k = P["cards"][c]
        r = {"coin": c, "rank": k["rank_by_traded_value"], "status": k["history"]["status"], "ndax": k["ndax"]["listed_vs_cad"],
             "what": k["what_ananta_does"][0].split(":")[0]}
        if rank_by:
            d = daily(j, c)
            if rank_by.startswith("change"):
                if len(d) <= days or k["history"]["status"] not in ("LISTED", "RENAMED"):
                    continue
                r["change_pct"] = round(100 * (d[-1][4] / d[-1 - days][4] - 1), 1)
                r["last_day"] = _day(d[-1][0])
            elif rank_by == "from_ath":
                r["from_ath_pct"] = k["now"].get("from_ath_pct")
            elif rank_by == "volatility":
                r["volatility_1y_pct"] = k["now"].get("volatility_1y_pct")
            elif rank_by == "volume":
                r["median_daily_usd_volume_90d"] = k["now"].get("median_daily_usd_volume_90d")
            elif rank_by == "funding":
                f = _futures(c)
                if "funding_7d_avg_pct_per_8h" not in f:
                    continue
                r["funding_7d_avg_pct_per_8h"] = f["funding_7d_avg_pct_per_8h"]
        rows.append(r)
    key = {"change": "change_pct", "from_ath": "from_ath_pct", "volatility": "volatility_1y_pct", "volume": "median_daily_usd_volume_90d",
           "funding": "funding_7d_avg_pct_per_8h"}
    kk = next((v for k_, v in key.items() if rank_by and rank_by.startswith(k_)), None)
    if kk:
        rows = [r for r in rows if r.get(kk) is not None]
        rows.sort(key=lambda r: -r[kk])
    btc = next((r.get("change_pct") for r in rows if r["coin"] == "BTC"), None)
    if btc is not None:
        for r in rows:
            r["vs_btc_pct_points"] = round(r["change_pct"] - btc, 1)
    n = int(n or 10)
    out = {"tier": tier, "tier_meaning": P["tier_meaning"].get(tier), "coins_in_tier": len(coins),
           "listed_now": sum(P["cards"][c]["history"]["status"] in ("LISTED", "RENAMED") for c in coins),
           "on_ndax": sum(P["cards"][c]["ndax"]["listed_vs_cad"] for c in coins),
           "ranked_by": f"{rank_by} over {days} days" if rank_by and rank_by.startswith("change") else rank_by,
           "top": rows[:n], "bottom": rows[-n:][::-1] if rank_by and len(rows) > n else [],
           "source": f"lake agent pack built {P['built_at']}; daily candles (TOP30 refreshed each daily close)"}
    if not rank_by:
        out["coins"] = rows
        out.pop("top")
        out.pop("bottom")
    return out


def history(j, coin: str, days: float | None = 30, start: str | None = None, end: str | None = None) -> dict:
    from jarvis.service import pricebook as PB

    c = resolve(coin)
    if not c:
        raise ValueError(f"{coin} is not in our 120-coin universe; use outside_coin or web_lookup")
    rows = daily(j, c)
    if not rows:
        raise ValueError(f"no daily candles for {c}")
    t_end = PB._when(end, rows[-1][0] + DAY)
    t_start = PB._when(start, t_end - float(days or 30) * DAY)
    sel = [r for r in rows if t_start <= r[0] and r[0] + DAY <= t_end + 1]
    if not sel:
        raise ValueError(f"no daily candles for {c} in that window (history {_day(rows[0][0])} to {_day(rows[-1][0])})")
    hi, lo = max(sel, key=lambda r: r[2]), min(sel, key=lambda r: r[3])
    by_day = [{"day": _day(r[0]), "open": _px(r[1]), "high": _px(r[2]), "low": _px(r[3]), "close": _px(r[4]),
               "change_pct": round(100 * (r[4] / r[1] - 1), 2)} for r in sel]
    return {"coin": c, "timeframe_used": "1d", "from": _day(sel[0][0]), "to": _day(sel[-1][0]), "open": _px(sel[0][1]),
            "high": _px(hi[2]), "high_day": _day(hi[0]), "low": _px(lo[3]), "low_day": _day(lo[0]), "close": _px(sel[-1][4]),
            "change_pct": round(100 * (sel[-1][4] / sel[0][1] - 1), 2), "from_high_pct": round(100 * (sel[-1][4] / hi[2] - 1), 2),
            "by_day": by_day[-31:], "best_day": max(by_day, key=lambda d: d["change_pct"]), "worst_day": min(by_day, key=lambda d: d["change_pct"]),
            "what_ananta_does": pack()["cards"][c]["what_ananta_does"],
            "note": "Daily candles (UTC days) from our research lake (Binance spot), refreshed daily for the 30-coin tier and weekly "
                    "for the others; this coin is not watched intraday unless it is one of the 10 live coins."}
