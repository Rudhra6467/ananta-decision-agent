"""Madhav's reads, live: every coin checked for his three buy setups at each daily close (src/research/reads.py).

    board(j)       -> every coin's reads on the latest closed day: FIRED (all conditions), CLOSE (one missing), NO
    watch(j, push) -> every 15 minutes: when a read fires on a coin for the first time in 20 days, record it, run the AI news
                      check (the blunder guard: Claude Haiku, about a cent) and push one alert to Madhav's phone

A read is evidence, not an order: nothing here trades. The history status of each read (repair-shop review #5) travels with it,
so an alert never sounds more certain than the evidence: "history: not supported" is said out loud.
"""
from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

NAMES = {"BTC": "Bitcoin", "ETH": "Ethereum", "SOL": "Solana", "ADA": "Cardano", "DOGE": "Dogecoin", "AVAX": "Avalanche",
         "BCH": "Bitcoin Cash", "LINK": "Chainlink", "LTC": "Litecoin", "XRP": "XRP"}
STATUS_WORDS = {"SUPPORTED": "history supports it", "NOT_SUPPORTED": "history did not support it (2018-2023)",
                "NOT_CONFIRMED": "worked 2018-2023, not since", "INSUFFICIENT": "too few cases in history to judge",
                "UNTESTED": "not tested yet"}
NEWS_MODEL = "claude-haiku-4-5-20251001"
_CACHE: dict = {}


def _status(j) -> dict:
    from jarvis.service.core import docs_dir

    p = docs_dir(j.dir) / "knowledge" / "reads_status.json"
    try:
        return {k: v["status"] for k, v in json.loads(p.read_text()).get("variants", {}).items()}
    except Exception:  # noqa: BLE001
        return {}


def _daily(j, coin: str) -> list[tuple]:
    from src.research.casebook import live_daily

    return live_daily(str(Path(j.dir) / "explorer_bars.sqlite"), coin)


def board(j) -> dict:
    from src.research import reads as R

    p = Path(j.dir) / "explorer_bars.sqlite"
    if not p.exists():
        return {"coins": [], "note": "The Explorer's candles are not available yet."}
    btc = _daily(j, "BTC")
    if not btc:
        return {"coins": [], "note": "No daily candles yet."}
    key = (str(p), btc[-1][0], p.stat().st_mtime // 900)
    if _CACHE.get("key") == key:
        return _CACHE["board"]
    status = _status(j)
    rows = []
    for coin in R.COINS:
        D = btc if coin == "BTC" else _daily(j, coin)
        if len(D) < 120:
            continue
        r = R.read_coin(D, btc, status)
        best = max(r["reads"], key=lambda x: (x["state"] == "FIRED", x["met"] / max(x["of"], 1)))
        rows.append({"coin": coin, **r, "best": {k: best.get(k) for k in ("variant", "name", "state", "met", "of", "like", "history")}})
    rows.sort(key=lambda r: (-(r["best"]["state"] == "FIRED"), -(r["best"]["state"] == "CLOSE"), -r["best"]["met"] / max(r["best"]["of"], 1)))
    fired = [{"coin": r["coin"], "variant": x["variant"], "name": x["name"]} for r in rows for x in r["reads"] if x["state"] == "FIRED"]
    close = [{"coin": r["coin"], "variant": x["variant"], "name": x["name"],
              "missing": next((c["name"] for c in x["conditions"] if not c["ok"]), "")} for r in rows for x in r["reads"] if x["state"] == "CLOSE"]
    out = {"day": rows[0]["day"] if rows else None, "coins": rows, "fired": fired, "close": close, "recent": recent(j),
           "history": {k: STATUS_WORDS.get(v, v) for k, v in status.items()},
           "note": "Your three buy setups, checked on every coin at each daily close (8 pm Toronto). Evidence for you, not orders: "
                   "nothing here trades."}
    _CACHE.update(key=key, board=out)
    return out


def coin(j, c: str) -> dict | None:
    return next((r for r in board(j)["coins"] if r["coin"] == c.upper()), None)


# ---------------------------------------------------------------------------
# alerts
# ---------------------------------------------------------------------------
def _table(j) -> None:
    j.db.execute("CREATE TABLE IF NOT EXISTS read_fires (id TEXT PRIMARY KEY, t INTEGER, day TEXT, coin TEXT, variant TEXT, name TEXT, "
                 "history TEXT, news TEXT, message TEXT)")


def recent(j, days: int = 30) -> list[dict]:
    try:
        _table(j)
        rows = j.db.execute("SELECT t, day, coin, variant, name, history, news, message FROM read_fires WHERE t >= ? ORDER BY t DESC",
                            (int(j.now()) - days * 86400,)).fetchall()
    except Exception:  # noqa: BLE001
        return []
    return [{"t": t, "day": d, "coin": c, "variant": v, "name": n, "history": h, "news": json.loads(nw or "{}"), "message": m}
            for t, d, c, v, n, h, nw, m in rows]


def news_check(j, c: str) -> dict:
    """The blunder guard for one coin, now. Uses Claude Haiku only when Ask Ananta is on and today's budget has room."""
    from jarvis.service.ask import Ask

    a = Ask(j)
    sp = a.spend()
    if a.setting("ask_enabled") != "1" or sp.get("left_usd", 1) <= 0.02:
        return {"verdict": "NOT_CHECKED", "why": "Ask Ananta is off or today's AI budget is used up, so the news was not checked."}
    import os

    if not os.getenv("ANTHROPIC_API_KEY"):
        return {"verdict": "NOT_CHECKED", "why": "No Claude key on the server."}
    from src.research import news_check as nc

    t0 = time.time()
    try:
        res = nc.live(NAMES.get(c, c), model=NEWS_MODEL)
    except Exception as exc:  # noqa: BLE001
        return {"verdict": "NOT_CHECKED", "why": f"The news search failed ({str(exc)[:80]})."}
    u = res.get("usage") or {}
    cost = (u.get("input_tokens", 0) * 1.0 + u.get("output_tokens", 0) * 5.0) / 1e6
    j.db.execute("INSERT INTO ask_messages (id, thread, t, role, text, reply, provider, model, ms, tokens_in, tokens_out, tools, error, cost_usd, "
                 "mode, note) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                 (uuid.uuid4().hex, "reads:news", int(j.now()), "assistant", f"news check {c}", res.get("verdict", ""), "haiku", NEWS_MODEL,
                  int(1000 * (time.time() - t0)), u.get("input_tokens", 0), u.get("output_tokens", 0), "", None, round(cost, 5), "worker",
                  "blunder guard"))
    j.db.commit()
    return {k: res.get(k) for k in ("verdict", "why", "damage", "supply", "good", "headlines_used")}


def watch(j, push=None, check_news=news_check) -> list[dict]:
    """Record and announce reads that fired on the latest closed day (once per coin and read every 20 days)."""
    b = board(j)
    if not b.get("fired"):
        return []
    _table(j)
    status = _status(j)
    out = []
    for f in b["fired"]:
        c, v = f["coin"], f["variant"]
        last = j.db.execute("SELECT MAX(t) FROM read_fires WHERE coin=? AND variant=?", (c, v)).fetchone()[0]
        if last and j.now() - last < 20 * 86400:
            continue
        row = next(x for r in b["coins"] if r["coin"] == c for x in r["reads"] if x["variant"] == v)
        st = status.get(v, "UNTESTED")
        hist = STATUS_WORDS.get(st, "not tested yet")
        # Review #5's rule: only a read history SUPPORTS rings the phone (with the news check as the last look).
        # The others are recorded and shown in the app; the news check runs there when Madhav taps it.
        loud = st == "SUPPORTED"
        news = check_news(j, c) if loud else {"verdict": "NOT_CHECKED", "why": "Tap 'Check the news' on the coin page to run it."}
        msg = (f"{c}: {row['name']} ({row['like']}). All {row['of']} signs are there at the {b['day']} close. "
               + (f"News check: {news.get('verdict')}{' - ' + news['why'] if news.get('why') else ''} " if loud else "")
               + f"History: {hist}. Stop if it fails: {row['stop_pct']:+.1f}%. Evidence, not an order.")
        j.db.execute("INSERT INTO read_fires VALUES (?,?,?,?,?,?,?,?,?)",
                     (uuid.uuid4().hex, int(j.now()), b["day"], c, v, row["name"], status.get(v, "UNTESTED"), json.dumps(news), msg))
        j.db.commit()
        if push and loud:
            try:
                push(f"{c}: your {row['name'].lower()} setup", msg)
            except Exception:  # noqa: BLE001
                pass
        out.append({"coin": c, "variant": v, "news": news.get("verdict"), "message": msg})
    if out:
        _CACHE.clear()
    return out


def stamp(t: int) -> str:
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d")
