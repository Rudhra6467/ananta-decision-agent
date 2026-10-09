"""Jarvis's brain: one decision-maker with its own paper book (Madhav's OK, 2026-10-04).

Madhav: "one intelligent agent using all knowledge with an objective, not filters, not many watches" and "we have to make sure
we are not making it dumb by asking it to trade only if every filter says good".

How it works
  wake(j, coin, trigger)   the fast parts call it when something worth a decision happens: price enters a zone (the eye), a
                           setup fires (the Explorer, the daily watches, Hunter), a coin's attention turns HIGH, the market
                           turns allowed again. Calls are queued; nothing waits on the model.
  process(j)               the worker takes the queue: at most DAILY_MAX decisions a day (about 2 cents each with Claude
                           Sonnet), one per coin every 6 hours, at most 2 open trades per coin and 20 open in all (TK4), only with AI budget left.
  decide(j, coin, ...)     builds the evidence pack (price, trend, zones and what history says about them, the market regime,
                           every signal on the coin today with that watch's live record, the news check, what the repair shop
                           found, the moves we keep missing, and its own record) and asks the model to WEIGH it: strong points
                           add confidence, weak points lower the size, only red flags stop. It writes the full plan BEFORE the
                           outcome: entry, stop, target or trail, time limit, size, confidence and the knowledge it used.
  TAKE                     a paper trade in its own evidence book (watch JARVIS, $100 standard so it compares with every other
                           watch, with the chosen size kept for the sized result), managed live by the eye: stop, target and
                           trailing stop on the live price, time exit on the daily close.
  the fair baseline        every TAKE also opens JARVIS_RANDOM: a random other coin at the same moment with the same plan in
                           daily ranges (stop, target, trail, days). Jarvis only counts as smart if it beats that.
  PASS                     recorded too, and scored later (what the coin did over the next day and five days), so passing on
                           a move is also evidence; big moves it passed on feed the missed-move loop.
  learning                 each closed trade credits the knowledge pieces the plan cited (report()), and confidence is
                           checked against results (calibration).

Paper only: nothing here reaches Hands or an exchange. Code enforces the red flags and the limits; the model never can
override them.
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time
import uuid
from typing import Any, Callable

DAILY_MAX = int(os.getenv("BRAIN_DAILY_MAX", "80"))      # TK4 (Madhav, 2026-10-05): 20 -> 40; engine plan D2 (2026-10-09): a ceiling only
DAILY_USD = float(os.getenv("BRAIN_DAILY_USD", "1.00"))  # engine plan D2: the day's AI budget for decisions, spent on the best-ranked wakes
MIN_SCORE = 2.0                                           # below this a wake is logged as not reviewed (ranked too low), never sent
TRIGGER_POINTS = {"zone_entry": 2.0, "attention_high": 2.0, "hunter": 1.0, "squeeze": 1.0, "explorer": 0.0,
                  "setup:H07": 3.0, "setup:M1a": 2.0, "setup:M2a-G": 2.0}   # evidence behind each kind of moment (Universe Rule v2, D6)
COIN_COOLDOWN = 6 * 3600
STALE_S = 45 * 60
MIN_BUDGET = 0.10
MAX_OPEN = 20                                             # TK4: 8 -> 20
MAX_PER_COIN = 2                                          # TK4: a wake on a held coin is decided (a TAKE adds a second trade)
MODEL = os.getenv("BRAIN_MODEL", "claude-sonnet-5-5")
PRICE = (2.0, 10.0)                                  # $ per million tokens in / out (Sonnet, as in ask.MODELS)
EVERY = 20
WATCH, BASE = "JARVIS", "JARVIS_RANDOM"
STATE: dict[str, Any] = {"running": False, "last_run": None, "last_error": None}
_lock = threading.Lock()

# What the repair shop found, one line each with its id: the model cites these ids in knowledge_used, and closed trades credit
# them. Kept in step with docs/KNOWLEDGE_INDEX.md and knowledge/PLAYBOOK.md (a test checks the ids are unique).
KNOWLEDGE = [
    ("REGIME", "PASSED", "Bitcoin above its 50-day average = market allowed. Inside support zones 68% held when allowed vs 50% when not (review #7). The strongest single fact we have."),
    ("T3", "PASSED", "Trend portfolio: coins in their own uptrend while Bitcoin is above its 50-day, 20-day exit. Confirmed on the lake: 10 coins and the 30 most-traded coins pass (2024-26 +19% vs buy-and-hold -24% on the 30); on all 120 coins it only cut losses (-14% vs -66%) (reviews #4, #15). Re-sizing only coins far from their share (T3-B) is a little better (review #20). Its crash insurance is the Bitcoin gate: fully in cash through LUNA (review #18). Survivorship check (review #22): on the top 30 as it really was each month it lost 22.5% in 2024-26 while holding lost 76%: on altcoins it loses much less, it does not reliably make money."),
    ("ZONES", "PASSED", "Support zones hold a little more often than random price bands. On 120 coins the 200-day average and new swing zones pass (z 4.4); overlapping zones no longer do (reviews #6, #16). Entering a zone is not a trade by itself."),
    ("LOOKOUT", "FAILED", "Inside a zone, the day's wick, a close back above, volume, divergence and relative strength added nothing beyond arithmetic (review #7)."),
    ("EXITS", "PASSED", "Selling at the next zone cut the winners (0% vs +5.8% for holding 20 days): gains come from a few big moves; the stop goes beyond the zone, the next zone is a review point, not a target (review #10)."),
    ("TRAIL", "MIXED", "Looser trailing exits won big in 2018-23 and lost in 2024-26; a 20-day time exit survived both (review #12)."),
    ("H07", "PASSED_LIQUID", "Short RSI dip: RSI(10) under 30 while above the 200-day, exit when RSI(10) is back over 40 or after 10 days. Passes on the 30 most-traded coins (+6.0% / +3.6% over ordinary uptrend days, z 3.5 / 3.2), fails on all 120: a liquid-coin edge (reviews #14, #15). Works best with no stop; if a stop is required use a structural one, never a tight 3% (review #18). On the top 30 as it really was each month it misses the bar by a hair (z 2.45 before 2024, strong after: +5.1%, z 4.8; review #22)."),
    ("M2A_G", "DROPPED", "Madhav's higher-low retest with the market allowed looked promising on 10 coins (review #8) but was not supported on 30 or 120 coins (review #15). M1a capitulation passed on 120 coins right on the bar (3 recent events)."),
    ("READS", "NOT_BETTER", "Madhav's three setups caught all four of his buys, but on their own were not better than a random day in 2018-23 (review #5)."),
    ("EXPLORER", "FAILED", "The 15-minute Explorer setups lost money after costs over 7 years; zones do not rescue hours-long trades (review #9); costs are the whole loss."),
    ("COSTS", "FACT", "Paper costs: NDAX 0.20% plus half the spread each side, so 0.5-1% for a round trip depending on the coin (costs_round_trip_pct in the pack). A plan whose likely move is a few tenths of a percent cannot pay."),
    ("TEACHER_50D", "FAILED", "A dip to the 50-day average did worse than an ordinary uptrend day (review #11)."),
    ("BREAKOUT_VOL", "WEAK", "Breakouts through zones on volume were positive in both periods but not reliable (review #11)."),
    ("STOPS", "SUPPORTED", "A stop 1 ATR under the structure beats a tight percent stop: a 3% stop was hit in 70-85% of dip trades (review #18, H14)."),
    ("FILTERS", "FAILED", "Filtering coins by strength against Bitcoin hurt the trend portfolio in both periods; market breadth helped 2024-26 but hurt 2018-23 (review #17). Do not require a coin to beat Bitcoin."),
    ("STOP_ZONE", "RULE", "The stop for a zone trade: a daily close half a daily range under the zone (the decision chain)."),
    ("NEWS", "RULE", "Check the news before buying (Madhav's lesson L1, Yes Bank): real damage news on the coin itself is a red flag."),
    ("MISSED", "CANDIDATE", "Patterns from the moves we keep missing (the missed-move loop): picked after the fact, so they are ideas to test on paper, not proof."),
    ("LIVE_BOOKS", "FORWARD", "The live evidence books (the scoreboard): every watch's paper results since early October 2026, against random; small numbers until 10 events."),
]
RED_FLAGS = ["no live price or stale candles", "the stop is missing, above the entry, or more than 15% away", "news check says AVOID (damage news on the coin itself)",
             "already 2 open trades on this coin in this book", "the daily limit or AI budget is used up"]

SYSTEM = """You are Jarvis's decision brain for one paper trading book (crypto, long only, spot). Your objective: make money after
costs on these trades, measured against a random coin traded with the same plan at the same moment. Paper evidence only: Madhav
reads every decision later, so be honest and specific.

How to decide (this matters more than anything):
- WEIGH the evidence; it is not a checklist. Strong points add confidence, weak or contrary points lower the size, and only a
  real red flag stops a trade. Never refuse just because one indicator disagrees or one filter is not perfect.
- Use what the repair shop measured (the knowledge list, with status) above teacher ideas and pattern names. PASSED and PROMISING
  items carry weight; FAILED items should not be the reason for a trade.
- Rules and teacher ideas are direction, not filters. The market regime is the strongest single fact: in a risk-off market,
  prefer smaller size or pass unless the case is strong; in an allowed market, a reasonable case deserves a small trade.
- This book is meant to be aggressive and learn: when the case is mixed but reasonable, TAKE it small (size 25-50) rather than
  pass. PASS when the case is weak, the plan cannot beat costs, or a red flag is present.
- Exposure: my_record.open_coins are already held; our coins move together, so several open trades in one market move are one
  bet. Size down (or pass) when a new trade would only add more of the same bet.
- Plans: the stop sits where the idea is wrong (beyond the zone, about half a daily range under it), not a random percent.
  Big gains come from a few big moves: prefer a trailing stop or a time exit over a near target (review #10). Typical time limit
  2-20 days. Use daily ranges (ATR) for distances.

Reply with ONE JSON object only:
{"action": "TAKE" | "PASS",
 "confidence": 0-100 (chance this trade beats the random baseline after costs),
 "size_pct": 25-100 (of the $100 standard stake; 0 for PASS),
 "stop": price, "target": price or null, "trail_atr": number of daily ranges for a trailing stop or null, "days": 2-30,
 "thesis": "one or two sentences: why this trade, now",
 "for": ["the strongest points for"], "against": ["the points against, and how the plan handles them"],
 "red_flags": [], "knowledge_used": ["ids from the knowledge list that moved the decision"],
 "change_mind": "what would make this wrong / what would make a PASS a TAKE"}"""


# ---------------------------------------------------------------------------
# tables
# ---------------------------------------------------------------------------
def _table(j) -> None:
    j.db.execute("CREATE TABLE IF NOT EXISTS brain_queue (id TEXT PRIMARY KEY, t INTEGER, coin TEXT, trigger TEXT, detail TEXT, state TEXT)")
    j.db.execute("CREATE TABLE IF NOT EXISTS brain_decisions (id TEXT PRIMARY KEY, t INTEGER, coin TEXT, triggers TEXT, action TEXT, confidence REAL, "
                 "size_pct REAL, price REAL, plan TEXT, thesis TEXT, knowledge TEXT, model TEXT, cost_usd REAL, trade_id TEXT, random_id TEXT, "
                 "after_1d_pct REAL, after_5d_pct REAL, note TEXT)")
    from jarvis.service import watch_engine

    watch_engine._table(j)


def _today0(j) -> int:
    from datetime import datetime
    from zoneinfo import ZoneInfo

    return int(datetime.fromtimestamp(j.now(), ZoneInfo("America/Toronto")).replace(hour=0, minute=0, second=0, microsecond=0).timestamp())


def wake(j, coin: str, trigger: str, detail: dict | None = None) -> bool:
    """Queue a moment for a decision. Same coin already waiting: the trigger is added to it."""
    _table(j)
    coin = (coin or "").upper()
    if not coin:
        return False
    row = j.db.execute("SELECT id, trigger, detail FROM brain_queue WHERE coin=? AND state='NEW'", (coin,)).fetchone()
    if row:
        trig = row[1].split("|")
        if trigger not in trig:
            d = json.loads(row[2] or "{}")
            d[trigger] = detail or {}
            j.db.execute("UPDATE brain_queue SET trigger=?, detail=? WHERE id=?", ("|".join(trig + [trigger]), json.dumps(d, default=str), row[0]))
            j.db.commit()
        return True
    j.db.execute("INSERT INTO brain_queue VALUES (?,?,?,?,?,?)", (uuid.uuid4().hex[:12], int(j.now()), coin, trigger,
                                                              json.dumps({trigger: detail or {}}, default=str), "NEW"))
    j.db.commit()
    return True


# ---------------------------------------------------------------------------
# the evidence pack
# ---------------------------------------------------------------------------
def _pct(a, b) -> float | None:
    return round(100 * (a / b - 1), 1) if a and b else None


def _is_lab(coin: str) -> bool:
    from src.research import reads as R

    return coin in R.COINS


def _coin_daily(j, coin: str) -> list[tuple]:
    """The 10 use the Explorer's candles (as before); every other coin the universe feed's daily candles."""
    if _is_lab(coin):
        from jarvis.service.reads_watch import _daily

        return _daily(j, coin)
    from jarvis.service import feed

    return feed.daily(j, coin)


def _live_px(j, coin: str) -> float | None:
    from jarvis.service import eye, feed

    if _is_lab(coin):
        p = (eye.STATE.get("prices") or {}).get(coin)
        if p is not None:
            return p
    try:
        return feed.prices(j).get(coin)
    except Exception:  # noqa: BLE001
        return None


def _feed_intraday(j, coin: str) -> dict:
    """For coins outside the 10: hourly and 4-hour picture from the feed's 5-minute candles."""
    from jarvis.service import feed
    from src.research import reads as R

    out = {}
    try:
        h1 = feed.bars(j, coin, "1h", 60)
        h4 = feed.bars(j, coin, "4h", 30)
        if len(h1) >= 25:
            c = [b[4] for b in h1]
            out.update(change_1h_pct=_pct(c[-1], c[-2]), change_24h_pct=_pct(c[-1], c[-25]), rsi1h=round((R.rsi(c, 14)[-1] or 0), 0))
        if len(h4) >= 7:
            c4 = [b[4] for b in h4]
            out["trend_4h"] = "UP" if c4[-1] > sum(c4[-6:]) / 6 else "DOWN"
    except Exception as exc:  # noqa: BLE001
        out["error"] = str(exc)[:80]
    return out


def _explorer_state(j, coin: str) -> dict:
    """The Explorer's last 15-minute read of the coin (trend on 15m/1h/4h, RSI, volume, in support)."""
    from pathlib import Path

    p = Path(j.dir) / "explorer_decisions.jsonl"
    if not p.exists():
        return {}
    try:
        with open(p, "rb") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - 120_000))
            lines = f.read().decode(errors="ignore").splitlines()[1:]
    except OSError:
        return {}
    for ln in reversed(lines):
        if f'"coin": "{coin}"' in ln:
            try:
                d = json.loads(ln)
            except ValueError:
                continue
            s = d.get("state") or {}
            return {k: s.get(k) for k in ("S1", "S2", "trend_4h", "daily_above_ema50", "rsi15", "rsi1h", "roc_pct", "vol1h", "vol15",
                                          "contracted_now", "in_support", "expensive")} | {"setups_now": d.get("setups") or []}
    return {}


def _signals_today(j, coin: str, since: int) -> list[dict]:
    out = []
    ex = None
    try:
        ex = j._explorer()
    except Exception:  # noqa: BLE001
        pass
    if ex:
        for (js,) in ex.store.book.execute("SELECT json FROM events WHERE t >= ? AND coin=? AND kind IN ('ORDER','SIGHTING') ORDER BY seq", (since, coin)):
            e = json.loads(js)
            if e.get("shadow") == "RANDOM":
                continue
            out.append({"source": "explorer", "setup": e.get("setup"), "kind": e["kind"].lower(), "blocked": e.get("shadow")})
    for (w, why, st) in j.db.execute("SELECT watch, why, status FROM evidence_trades WHERE coin=? AND signal_t >= ? AND watch NOT LIKE 'RANDOM%' AND watch NOT LIKE 'JARVIS%'",
                                     (coin, since - 2 * 86400)):
        out.append({"source": "daily watch", "setup": w, "why": why, "status": st})
    try:
        for (kind, title) in j.db.execute("SELECT kind, title FROM eye_events WHERE coin=? AND t >= ? AND kind IN ('ZONE_ENTRY','ZONE_TOUCH')", (coin, since)):
            out.append({"source": "eye", "setup": kind, "why": title})
    except Exception:  # noqa: BLE001
        pass
    seen, uniq = set(), []
    for s in out:
        k = (s["source"], s["setup"], s.get("kind"))
        if k not in seen:
            seen.add(k)
            uniq.append(s)
    return uniq[:20]


def pack(j, coin: str, triggers: dict) -> dict:
    """Everything the brain may weigh, compact. Facts only from our stores."""
    from jarvis.service import eye, scoreboard, zones_watch
    from jarvis.service.reads_watch import _daily
    from src.research import reads as R

    _table(j)
    now = int(j.now())
    lab = _is_lab(coin)
    if lab:
        live = (eye.STATE.get("prices") or {}).get(coin)
        live_age = time.time() - eye.STATE["last_t"] if eye.STATE.get("last_t") else None
        if live is None or (live_age is not None and live_age > 300):
            try:
                live = (j.prices() or {}).get(coin)
                live_age = None
            except Exception:  # noqa: BLE001
                pass
    else:
        live = _live_px(j, coin)
    D, btc = _coin_daily(j, coin), _daily(j, "BTC")
    from jarvis.service import registry, watch_engine

    p: dict[str, Any] = {"coin": coin, "time_utc": time.strftime("%Y-%m-%d %H:%M", time.gmtime(now)), "price": live,
                         "triggers": triggers, "costs_round_trip_pct": round(200 * (R.cost(coin) if lab else watch_engine._cost(coin, WATCH)), 2)}
    if not lab:
        k = registry.card(j, coin) or {}
        p["universe_tier"] = {"tier": k.get("tier"), "median_daily_usd_30d": k.get("median_usd_30d"), "can_buy_ndax": k.get("ndax"),
                              "can_buy_kraken": k.get("kraken"), "meaning": "A over $20M a day, B $1M-$20M (Universe Rule v2); one of the "
                              "10 live coins it is not, so its intraday picture comes from the universe feed"}
    if len(D) >= 60 and len(btc) >= 60:
        S, B = R.Series(D), R.Series(btc)
        i = len(D) - 1
        c = S.c[i]
        r14 = S.rsi[i]
        r10 = R.rsi(S.c, 10)[i]
        p["daily"] = {"last_close": c, "change_1d_pct": _pct(c, S.c[i - 1]), "change_7d_pct": _pct(c, S.c[i - 7]), "change_30d_pct": _pct(c, S.c[i - 30]),
                      "vs_50d_pct": _pct(c, S.ema50[i]), "vs_200d_pct": _pct(c, S.sma200[i]) if S.sma200[i] else None,
                      "rsi14": round(r14, 0) if r14 is not None else None, "rsi10": round(r10, 0) if r10 is not None else None,
                      "atr": S.atr[i], "atr_pct": round(100 * S.atr[i] / c, 2) if S.atr[i] else None,
                      "from_90d_high_pct": _pct(c, max(S.h[-90:])), "from_90d_low_pct": _pct(c, min(S.l[-90:])),
                      "volume_vs_20d": round(S.v[i] / (sum(S.v[-21:-1]) / 20), 2) if sum(S.v[-21:-1]) else None,
                      "candle_closed_utc": time.strftime("%Y-%m-%d", time.gmtime(S.t[i])), "price_vs_last_close_pct": _pct(live, c) if live else None}
        bc = B.c[-1]
        p["market"] = {"regime": "ALLOWED" if bc > B.ema50[-1] else "RISK_OFF", "btc_vs_50d_pct": _pct(bc, B.ema50[-1]),
                       "btc_change_7d_pct": _pct(bc, B.c[-8]), "btc_live_vs_50d_pct": _pct((eye.STATE.get("prices") or {}).get("BTC"), B.ema50[-1])}
        p["data_age_h"] = round((now - S.t[i]) / 3600 - 24, 1)
    p["intraday"] = _explorer_state(j, coin) if lab else _feed_intraday(j, coin)
    if not lab:
        try:
            from jarvis.service import universe_watch

            zs = (universe_watch._armed(j).get("zones") or {}).get(coin) or []
            px0 = live or (D[-1][4] if D else None)
            if px0:
                p["zones"] = {"inside": [z for z in zs if z["bot"] <= px0 <= z["top"]][:2],
                              "next_support": max((z for z in zs if z["top"] < px0), key=lambda z: z["top"], default=None)}
        except Exception as exc:  # noqa: BLE001
            p["zones_error"] = str(exc)[:100]
    try:
        row = next((r for r in zones_watch.board(j).get("coins", []) if r["coin"] == coin), None) if lab else None
        if row:
            pick = lambda z: {k: z.get(k) for k in ("bot", "top", "kinds", "history", "state", "distance_pct", "touches", "held")}  # noqa: E731
            p["zones"] = {"inside": [pick(z) for z in row.get("inside") or []], "next_support": pick(row["next_support"]) if row.get("next_support") else None,
                          "next_resistance": pick(row["next_resistance"]) if row.get("next_resistance") else None,
                          "attention": row.get("attention")}
    except Exception as exc:  # noqa: BLE001
        p["zones_error"] = str(exc)[:100]
    p["signals_last_24h"] = _signals_today(j, coin, now - 86400)
    try:
        b = scoreboard.board(j)
        names = {s["setup"] for s in p["signals_last_24h"]} | {"ZONE_TOUCH", "H07", "M2a-G", WATCH, BASE, "RANDOM_15M", "RANDOM_20D"}
        p["live_books"] = [{k: w.get(k) for k in ("id", "name", "closed", "events", "avg_usd", "vs_random_usd", "verdict")}
                           for w in b["watches"] if w["id"] in names]
    except Exception:  # noqa: BLE001
        pass
    if not lab:
        try:
            from jarvis.service import universe_watch

            tier = (p.get("universe_tier") or {}).get("tier")
            p["universe_books"] = [{k: w.get(k) for k in ("watch", "closed", "events", "avg_usd", "vs_random_usd", "verdict")}
                                   for w in universe_watch.scoreboard(j)["watches"] if w["tier"] == tier and w["closed"]]
        except Exception:  # noqa: BLE001
            pass
    try:
        from jarvis.service import news_watch

        n = news_watch.latest(j, coin, 2)
        p["news"] = n[0] if n else {"verdict": "NOT_CHECKED"}
    except Exception:  # noqa: BLE001
        p["news"] = {"verdict": "NOT_CHECKED"}
    try:
        from jarvis.service import missed

        p["moves_we_keep_missing"] = missed.patterns(j, 30)[:5]
    except Exception:  # noqa: BLE001
        pass
    try:
        from jarvis.service import universe

        u = universe.card(j, coin)
        if u.get("in_universe"):
            p["universe"] = {"tiers": u["tiers"], "what_ananta_does": u["what_ananta_does"], "ndax": u["ndax"],
                             "history_since": u["history"]["first"], "data_grade": u["history"]["quality_grade"],
                             "from_all_time_high_pct": (u.get("now") or {}).get("from_ath_pct"),
                             "volatility_1y_pct": (u.get("now") or {}).get("volatility_1y_pct"),
                             "buying_pressure": u.get("buying_pressure"), "futures_context": u.get("futures_context"),
                             "paper_tier_30": u.get("paper_tier_30")}
    except Exception as exc:  # noqa: BLE001
        p["universe_error"] = str(exc)[:100]
    cards = status_cards()
    p["knowledge"] = [{"id": k, "status": s, "what": w, "evidence": (cards.get(k) or {}).get("evidence"),
                       "permission": (cards.get(k) or {}).get("permission")} for k, s, w in KNOWLEDGE]
    p["my_record"] = record(j)
    p["red_flags_enforced_by_code"] = RED_FLAGS
    return p


# ---------------------------------------------------------------------------
# the model
# ---------------------------------------------------------------------------
def _call_claude(system: str, user: str, post=None) -> tuple[str, dict]:
    from jarvis.service import ask

    key = os.getenv("ANTHROPIC_API_KEY", "")
    if not key:
        raise RuntimeError("no Claude key")
    post = post or ask._post
    # cost layer (2026-10-09): the brain's rules are the same on every wake, so they stay cached for an hour (read at a tenth of the price)
    sysb = [{"type": "text", "text": system, "cache_control": {"type": "ephemeral", "ttl": "1h"}}]
    r = post("https://api.anthropic.com/v1/messages", {"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
             {"model": MODEL, "max_tokens": 2500, "system": sysb, "messages": [{"role": "user", "content": user}]})
    u = r.get("usage") or {}
    text = "".join(c.get("text", "") for c in r.get("content") or [] if c.get("type") == "text")
    return text, {"in": u.get("input_tokens", 0), "out": u.get("output_tokens", 0), "model": MODEL,
                  "cache_read": u.get("cache_read_input_tokens", 0) or 0, "cache_write": u.get("cache_creation_input_tokens", 0) or 0}


def _price(u: dict) -> float:
    """Dollars for one call: fresh input, cached reads (a tenth), cache writes (twice, for the hour-long cache) and output."""
    return round((u.get("in", 0) * PRICE[0] + u.get("cache_read", 0) * PRICE[0] * 0.1 + u.get("cache_write", 0) * PRICE[0] * 2.0
                  + u.get("out", 0) * PRICE[1]) / 1e6, 5)


def _json_block(text: str) -> str | None:
    """The first complete {...} in a reply: fences and words around it are ignored, braces inside strings are respected."""
    t = (text or "").strip()
    i = t.find("{")
    while i >= 0:
        depth, inq, esc = 0, False, False
        for k in range(i, len(t)):
            ch = t[k]
            if inq:
                esc = (ch == "\\" and not esc)
                if ch == '"' and not esc:
                    inq = False
                continue
            if ch == '"':
                inq = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return t[i:k + 1]
        i = t.find("{", i + 1)
    return None


def _parse(text: str) -> dict:
    blk = _json_block(text)
    if not blk:
        raise ValueError("no JSON in the reply" + (" (it was cut off)" if "{" in (text or "") else ""))
    d = json.loads(blk)
    if d.get("action") not in ("TAKE", "PASS"):
        raise ValueError("action must be TAKE or PASS")
    return d


_CARDS: dict = {}
# Evidence records, not ideas: citing the live books or the missed-move log is never "using a failed rule" (status check, Oct 8).
NOT_IDEAS = {"LIVE_BOOKS", "MISSED"}


def status_cards() -> dict:
    """docs/knowledge/status_cards.json by id: each idea's evidence (how strong) and permission (what it may do)."""
    try:
        from pathlib import Path

        f = Path(__file__).resolve().parents[2] / "docs" / "knowledge" / "status_cards.json"
        key = f.stat().st_mtime
        if _CARDS.get("key") != key:
            _CARDS.update(key=key, cards={c["id"]: c for c in json.loads(f.read_text())["cards"]})
        return _CARDS["cards"]
    except Exception:  # noqa: BLE001
        return {}


def permission_check(ids: list[str]) -> tuple[list[str], list[str]]:
    """(ids that may not be a reason to trade, ids that may)."""
    cards = status_cards()
    ids = [k for k in ids if k not in NOT_IDEAS]
    bad = [k for k in ids if (cards.get(k) or {}).get("permission") in ("CONTEXT", "OFF")]
    ok = [k for k in ids if (cards.get(k) or {}).get("permission") in ("PAPER", "LIVE_PROVEN")]
    return bad, ok


def check_plan(d: dict, price: float | None, atr: float | None, news: str | None, holding: int) -> list[str]:
    """The red flags code enforces whatever the model says."""
    flags = []
    if not price:
        flags.append("no live price")
    stop = d.get("stop")
    if d.get("action") == "TAKE":
        if not isinstance(stop, (int, float)) or not price or stop >= price:
            flags.append("the stop is missing or not under the entry")
        elif (price - stop) / price > 0.15:
            flags.append("the stop is more than 15% away")
        t = d.get("target")
        if t is not None and (not isinstance(t, (int, float)) or (price and t <= price)):
            flags.append("the target is not above the entry")
    if news == "AVOID":
        flags.append("the news check says AVOID")
    if holding >= MAX_PER_COIN:
        flags.append(f"already {MAX_PER_COIN} open trades on this coin in this book")
    return flags


def _random_coin(j, coin: str, t: int, coins: list[str]) -> str | None:
    others = sorted(c for c in coins if c != coin)
    if not others:
        return None
    return others[int(hashlib.sha1(f"{coin}|{t}".encode()).hexdigest(), 16) % len(others)]


def _open(j, watch: str, coin: str, price: float, stop: float, target: float | None, trail_atr: float | None, days: int, atr: float,
          detail: dict, regime: str | None) -> dict:
    from jarvis.service import watch_engine

    t = int(j.now())
    row = {"id": uuid.uuid4().hex[:12], "watch": watch, "coin": coin, "source": "brain", "signal_t": t, "signal_day": watch_engine._day(t), "entry_t": t,
           "entry_day": watch_engine._day(t), "entry": float(price), "stop": float(stop), "status": "OPEN", "why": detail.get("thesis", "")[:300],
           "regime": regime, "detail": json.dumps({**detail, "target": target, "trail_atr": trail_atr, "atr": atr, "high": float(price), "days": days,
                                                   "stop0": float(stop)}, default=str)}
    watch_engine._insert(j, row)
    j.db.commit()
    return row


def decide(j, coin: str, triggers: dict, call: Callable | None = None, push: Callable | None = None) -> dict:
    """One decision: the pack, the model's weighing, the code's red flags, then a paper trade (and its random twin) or a PASS."""
    from jarvis.service import eye
    from src.research import reads as R

    _table(j)
    p = pack(j, coin, triggers)
    price = p.get("price")
    atr = (p.get("daily") or {}).get("atr")
    holding = j.db.execute("SELECT COUNT(*) FROM evidence_trades WHERE watch=? AND coin=? AND status='OPEN'", (WATCH, coin)).fetchone()[0]
    user = ("Decide on this moment. The evidence pack (JSON):\n" + json.dumps(p, default=str)[:24000])
    if holding:
        user += (f"\n\nYou already hold {holding} open trade(s) on this coin (my_record.open_coins). A TAKE adds another $100 trade "
                 f"(at most {MAX_PER_COIN} per coin); take it only if this moment is a new, separate reason, not the same move again.")
    call = call or (lambda u: _call_claude(SYSTEM, u))
    t0 = time.time()
    text, usage = call(user)
    cost = _price(usage)
    _log_cost(j, coin, usage, cost, int(1000 * (time.time() - t0)))
    did = uuid.uuid4().hex[:12]
    try:
        d = _parse(text)
    except (ValueError, json.JSONDecodeError):
        # Status check, Oct 8: 21 of 100 decisions were lost to unreadable replies (mostly cut off). Ask once more, JSON only.
        try:
            text, u2 = call(user + "\n\nYour last reply could not be read. Reply with ONLY the JSON object, nothing before or after it, "
                                   "and keep every text field short (thesis under 60 words).")
            c2 = _price(u2)
            _log_cost(j, coin, u2, c2, 0)
            cost += c2
        except Exception:  # noqa: BLE001
            pass
    try:
        d = _parse(text)
    except (ValueError, json.JSONDecodeError) as exc:
        j.db.execute("INSERT INTO brain_decisions (id, t, coin, triggers, action, price, model, cost_usd, note) VALUES (?,?,?,?,?,?,?,?,?)",
                     (did, int(j.now()), coin, json.dumps(triggers, default=str), "ERROR", price, usage.get("model"), cost, f"unreadable reply: {exc}"[:200]))
        j.db.commit()
        return {"id": did, "action": "ERROR", "note": str(exc)}
    flags = check_plan(d, price, atr, (p.get("news") or {}).get("verdict"), holding)
    action = d["action"]
    note = ""
    if action == "TAKE" and flags:
        action, note = "PASS", "code red flag: " + "; ".join(flags)
    size = max(25.0, min(100.0, float(d.get("size_pct") or 50))) if action == "TAKE" else 0.0
    conf = max(0.0, min(100.0, float(d.get("confidence") or 0)))
    know = [k for k in (d.get("knowledge_used") or []) if isinstance(k, str)][:8]
    bad, ok = permission_check(know)
    if action == "TAKE" and bad and not ok:            # only context-only / switched-off ideas moved it: refused (acceptance gate)
        action, note = "PASS", (note + "; " if note else "") + "permission: only context-only ideas supported it (" + ", ".join(bad) + ")"
    elif bad:
        note = (note + "; " if note else "") + "cited context-only ideas: " + ", ".join(bad)
    plan = {k: d.get(k) for k in ("stop", "target", "trail_atr", "days", "for", "against", "red_flags", "change_mind")}
    trade = rnd = None
    if action == "TAKE":
        days = int(max(2, min(30, d.get("days") or 10)))
        trail = float(d["trail_atr"]) if isinstance(d.get("trail_atr"), (int, float)) and d["trail_atr"] > 0 else None
        target = float(d["target"]) if isinstance(d.get("target"), (int, float)) else None
        regime = (p.get("market") or {}).get("regime")
        det = {"decision": did, "thesis": d.get("thesis", ""), "confidence": conf, "size_pct": size, "knowledge": know}
        trade = _open(j, WATCH, coin, price, float(d["stop"]), target, trail, days, atr or 0.0, det, regime)
        # the random twin: same moment, another coin, the same plan in its own daily ranges
        if _is_lab(coin):
            px_all = dict(eye.STATE.get("prices") or {}) or (j.prices() or {})
            pool = [c for c in R.COINS if c in px_all]
        else:                                            # outside the 10: the twin comes from the same tier (Universe Rule v2)
            from jarvis.service import feed, registry

            px_all = feed.prices(j)
            pool = [c for c in registry.members(j, registry.tier_of(j, coin) or "C") if c in px_all and not _is_lab(c)]
        rc = _random_coin(j, coin, int(j.now()), pool)
        if rc and atr:
            ratr = ((eye.STATE.get("armed") or {}).get("atr", {}).get(rc) if _is_lab(rc) else None) or _atr(j, rc)
            if ratr:
                rp = px_all[rc]
                k_stop = (price - float(d["stop"])) / atr
                rt = rp + (target - price) / atr * ratr if target else None
                rnd = _open(j, BASE, rc, rp, rp - k_stop * ratr, rt, trail, days, ratr, {"decision": did, "twin_of": trade["id"], "thesis": f"random twin of {coin}"}, regime)
        if push:
            try:
                push(f"Jarvis paper trade: {coin}", f"About ${price:,.6g}, stop ${float(d['stop']):,.6g}"
                     + (f", target ${target:,.6g}" if target else "") + (f", trailing {trail:g} daily ranges" if trail else "")
                     + f", {days} days max. Confidence {conf:.0f}%, size {size:.0f}%. {d.get('thesis', '')}"[:480])
            except Exception:  # noqa: BLE001
                pass
    j.db.execute("INSERT INTO brain_decisions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                 (did, int(j.now()), coin, json.dumps(triggers, default=str), action, conf, size, price, json.dumps(plan, default=str),
                  (d.get("thesis") or "")[:600], json.dumps(know), usage.get("model"), cost, trade["id"] if trade else None, rnd["id"] if rnd else None,
                  None, None, note or None))
    j.db.commit()
    return {"id": did, "action": action, "confidence": conf, "size_pct": size, "thesis": d.get("thesis"), "flags": flags,
            "trade": trade["id"] if trade else None, "random_twin": rnd["coin"] if rnd else None, "cost_usd": cost}


def _atr(j, coin: str) -> float | None:
    from src.research import reads as R

    D = _coin_daily(j, coin)
    return R.Series(D).atr[-1] if len(D) > 20 else None


def _log_cost(j, coin: str, usage: dict, cost: float, ms: int) -> None:
    """Into ask_messages, so the day's AI budget sees it like every other answer."""
    try:
        j.db.execute("INSERT INTO ask_messages (id, thread, t, role, text, reply, provider, model, ms, tokens_in, tokens_out, tools, error, cost_usd, "
                     "mode, note) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                     (uuid.uuid4().hex, "brain", int(j.now()), "assistant", f"brain decision {coin}", "", "sonnet", usage.get("model"), ms,
                      usage.get("in", 0) + usage.get("cache_read", 0) + usage.get("cache_write", 0), usage.get("out", 0), "", None, cost, "worker", "decision brain"))
        j.db.commit()
    except Exception:  # noqa: BLE001  a test database may not have the table
        pass


# ---------------------------------------------------------------------------
# the worker
# ---------------------------------------------------------------------------
def can_decide(j) -> tuple[bool, str]:
    if os.getenv("BRAIN_ENABLED", "1") != "1":
        return False, "the brain is switched off (BRAIN_ENABLED)"
    n = j.db.execute("SELECT COUNT(*) FROM brain_decisions WHERE t >= ? AND action != 'ERROR'", (_today0(j),)).fetchone()[0]
    if n >= DAILY_MAX:
        return False, f"today's {DAILY_MAX} decisions are used"
    try:
        from jarvis.service.ask import Ask

        a = Ask(j)
        if a.setting("ask_enabled") != "1":
            return False, "Ask Ananta (the AI) is switched off"
        if a.spend().get("left_usd", 1) < MIN_BUDGET:
            return False, "today's AI budget is used up"
    except Exception:  # noqa: BLE001
        pass
    return True, ""


def spent_today(j) -> float:
    return float(j.db.execute("SELECT COALESCE(SUM(cost_usd), 0) FROM brain_decisions WHERE t >= ?", (_today0(j),)).fetchone()[0] or 0.0)


def paced_budget(j) -> float:
    """The day's decision budget unlocks through the day (a quarter at midnight Toronto, the rest evenly), so a strong moment in
    the evening still finds money left (engine plan D2)."""
    frac = max(0.0, min(1.0, (j.now() - _today0(j)) / 86400))
    return round(DAILY_USD * (0.25 + 0.75 * frac), 4)


_REGIME: dict = {"t": 0, "v": None}


def _regime_now(j) -> str | None:
    if time.time() - _REGIME["t"] > 900:
        try:
            from jarvis.service import watch_engine
            from src.research import reads as R

            btc = _coin_daily(j, "BTC")
            _REGIME.update(t=time.time(), v=watch_engine.regime_at(R.Series(btc), int(j.now())) if len(btc) >= 60 else None)
        except Exception:  # noqa: BLE001
            _REGIME.update(t=time.time(), v=None)
    return _REGIME["v"]


def score(j, coin: str, trigger: str, detail: dict) -> tuple[float, list[str]]:
    """How much a wake deserves the AI (engine plan U4.3): the evidence behind its kind of moment, the coin's tier, the market
    regime, room to beat costs, and how much of the same bet is already open. Rules, not AI; logged with every wake."""
    from jarvis.service import registry, universe_watch

    pts, why = [], []
    for t in (trigger or "").split("|"):
        key = t
        if t.startswith("explorer"):
            key = "explorer"
        elif t.startswith("setup:"):
            sp = universe_watch.split(t[6:])
            key = "setup:" + (sp[0] if sp else t[6:]).split(".")[0]      # a rule's new version ranks like its parent
        p = TRIGGER_POINTS.get(key, 1.0)
        if key == "zone_entry" and ((detail or {}).get("zone_entry") or {}).get("history") == "SUPPORTED":
            p += 1.0
        if t.startswith("setup:") and t[6:] in universe_watch.promoted(j):      # promoted on the ladder (Madhav's sign-off)
            p += 1.0
        pts.append(p)
    s = (max(pts) + 0.5 * (len(pts) - 1)) if pts else 0.0
    why.append(f"moment {s:g}")
    tier = "LAB10" if _is_lab(coin) else registry.tier_of(j, coin) or "C"
    tp = {"LAB10": 2.0, "A": 2.0, "B": 1.0}.get(tier, -5.0)
    s += tp
    why.append(f"tier {tier} {tp:+g}")
    if _regime_now(j) == "ALLOWED":
        s += 1.0
        why.append("market allowed +1")
    try:
        D = _coin_daily(j, coin)
        if len(D) > 20:
            from src.research import reads as R
            from jarvis.service import watch_engine

            atr_pct = R.Series(D).atr[-1] / D[-1][4]
            cost = R.cost(coin) if _is_lab(coin) else watch_engine._cost(coin, WATCH)
            if atr_pct >= 4 * 2 * cost:
                s += 0.5
                why.append("room to beat costs +0.5")
    except Exception:  # noqa: BLE001
        pass
    n_open = j.db.execute("SELECT COUNT(*) FROM evidence_trades WHERE watch=? AND status='OPEN'", (WATCH,)).fetchone()[0]
    if n_open:
        s -= 0.1 * n_open
        why.append(f"{n_open} open already -{0.1 * n_open:g}")
    return round(s, 2), why


def _unreviewed(j, qid: str, t: int, coin: str, trig: str, sc: float | None, reason: str) -> None:
    """A wake the AI never reviewed: logged with its price, scored later like a PASS (did the ranking throw away good ones?)."""
    j.db.execute("CREATE TABLE IF NOT EXISTS brain_unreviewed (id TEXT PRIMARY KEY, t INTEGER, coin TEXT, trigger TEXT, score REAL, reason TEXT, "
                 "price REAL, after_1d_pct REAL, after_5d_pct REAL)")
    j.db.execute("INSERT OR REPLACE INTO brain_unreviewed VALUES (?,?,?,?,?,?,?,?,?)", (qid, t, coin, trig, sc, reason, _live_px(j, coin), None, None))
    j.db.execute("UPDATE brain_queue SET state=? WHERE id=?", ("NOT_REVIEWED: " + reason, qid))
    j.db.commit()


def settle_unreviewed(j) -> int:
    try:
        rows = j.db.execute("SELECT id, t, coin, price FROM brain_unreviewed WHERE after_5d_pct IS NULL AND t <= ?", (int(j.now()) - 86400,)).fetchall()
    except Exception:  # noqa: BLE001
        return 0
    n, now, cache = 0, int(j.now()), {}
    for uid, t, coin, price in rows:
        if not price:
            continue
        D = cache.setdefault(coin, _coin_daily(j, coin))
        a1 = next((b[4] for b in D if b[0] >= t), None)
        a5 = next((b[4] for b in D if b[0] + 86400 >= t + 5 * 86400), None) if now >= t + 5 * 86400 else None
        if a1 is None:
            continue
        j.db.execute("UPDATE brain_unreviewed SET after_1d_pct=?, after_5d_pct=? WHERE id=?", (_pct(a1, price), _pct(a5, price) if a5 else None, uid))
        n += 1
    j.db.commit()
    return n


def ranking_audit(j, days: int = 30) -> dict:
    """Decided against not reviewed: what the coins did over 5 days after each (engine plan U5.2)."""
    since = int(j.now()) - days * 86400
    out = {}
    try:
        u = [r[0] for r in j.db.execute("SELECT after_5d_pct FROM brain_unreviewed WHERE t >= ? AND after_5d_pct IS NOT NULL", (since,))]
    except Exception:  # noqa: BLE001
        u = []
    d = [r[0] for r in j.db.execute("SELECT after_5d_pct FROM brain_decisions WHERE t >= ? AND after_5d_pct IS NOT NULL", (since,))]
    for k, xs in (("not_reviewed", u), ("passed", d)):
        out[k] = {"n": len(xs), "avg_5d_pct": round(sum(xs) / len(xs), 2) if xs else None, "ran_5pct": sum(1 for x in xs if x >= 5)}
    try:
        out["not_reviewed_today"] = j.db.execute("SELECT COUNT(*) FROM brain_unreviewed WHERE t >= ?", (_today0(j),)).fetchone()[0]
    except Exception:  # noqa: BLE001
        out["not_reviewed_today"] = 0
    return out


def process(j, call: Callable | None = None, push: Callable | None = None, max_n: int = 3) -> list[dict]:
    """Take the queue (engine plan D2): blocked items are dropped with the reason; the rest are ranked, and the best get a decision
    while the paced daily budget allows. Low-ranked wakes, and wakes that waited past 45 minutes because better ones took the
    budget, are logged as not reviewed and scored later."""
    _table(j)
    now = int(j.now())
    out = []
    ranked = []
    for qid, t, coin, trig, det in j.db.execute("SELECT id, t, coin, trigger, detail FROM brain_queue WHERE state='NEW' ORDER BY t").fetchall():
        why = ""
        detail = json.loads(det or "{}")
        if now - t > STALE_S:
            sc, _ = score(j, coin, trig, detail)
            _unreviewed(j, qid, t, coin, trig, sc, "waited 45 minutes; the budget went to better-ranked moments")
            continue
        elif j.db.execute("SELECT COUNT(*) FROM evidence_trades WHERE watch=? AND coin=? AND status='OPEN'", (WATCH, coin)).fetchone()[0] >= MAX_PER_COIN:
            why = f"already holding {MAX_PER_COIN} trades on it"
        elif j.db.execute("SELECT 1 FROM brain_decisions WHERE coin=? AND t >= ? AND action != 'ERROR'", (coin, now - COIN_COOLDOWN)).fetchone():
            why = "decided on this coin in the last 6 hours"
        elif j.db.execute("SELECT COUNT(*) FROM evidence_trades WHERE watch=? AND status='OPEN'", (WATCH,)).fetchone()[0] >= MAX_OPEN:
            why = f"{MAX_OPEN} trades already open"
        else:
            ok, why = can_decide(j)
            why = "" if ok else why
        if why:
            j.db.execute("UPDATE brain_queue SET state=? WHERE id=?", ("DROPPED: " + why, qid))
            j.db.commit()
            continue
        sc, sw = score(j, coin, trig, detail)
        if sc < MIN_SCORE:
            _unreviewed(j, qid, t, coin, trig, sc, f"ranked too low ({sc:g}: {', '.join(sw)})")
            continue
        ranked.append((sc, t, qid, coin, det, sw))
    ranked.sort(key=lambda x: (-x[0], x[1]))
    for sc, t, qid, coin, det, sw in ranked:
        if len(out) >= max_n:
            break
        if spent_today(j) >= paced_budget(j):
            break                                          # the rest wait for budget; past 45 minutes they are logged as not reviewed
        if j.db.execute("SELECT 1 FROM brain_decisions WHERE coin=? AND t >= ? AND action != 'ERROR'", (coin, now - COIN_COOLDOWN)).fetchone():
            j.db.execute("UPDATE brain_queue SET state=? WHERE id=?", ("DROPPED: decided on this coin in the last 6 hours", qid))
            j.db.commit()
            continue
        d0 = json.loads(det or "{}")
        d0["_rank"] = {"score": sc, "why": sw}
        det = json.dumps(d0, default=str)
        j.db.execute("UPDATE brain_queue SET state='DECIDING' WHERE id=?", (qid,))
        j.db.commit()
        try:
            r = decide(j, coin, json.loads(det or "{}"), call=call, push=push)
            state = "DONE"
        except Exception as exc:  # noqa: BLE001
            r, state = {"error": str(exc)[:160]}, "FAILED: " + str(exc)[:80]
        j.db.execute("UPDATE brain_queue SET state=? WHERE id=?", (state, qid))
        j.db.commit()
        out.append({"coin": coin, **r})
    return out


def start(get_j: Callable[[], Any], push: Callable | None = None, every: float = EVERY) -> bool:
    with _lock:
        if STATE.get("running"):
            return False
        STATE["running"] = True

    def loop():
        while STATE.get("running"):
            try:
                STATE["last"] = process(get_j(), push=push)
                STATE["last_run"] = time.time()
            except Exception as exc:  # noqa: BLE001
                STATE["last_error"] = str(exc)[:160]
            time.sleep(every)

    threading.Thread(target=loop, name="ananta-brain", daemon=True).start()
    return True


# ---------------------------------------------------------------------------
# what wakes it (called from the 15-minute jobs; the eye calls wake() directly on zone entries)
# ---------------------------------------------------------------------------
def _kv(j, k: str, v: str | None = None) -> str | None:
    if v is None:
        r = j.db.execute("SELECT v FROM engine_state WHERE k=?", (k,)).fetchone()
        return r[0] if r else None
    j.db.execute("INSERT OR REPLACE INTO engine_state VALUES (?,?)", (k, v))
    return v


def scan(j, daily_opened: list[dict] | None = None) -> list[str]:
    """New Explorer orders (blocked ones too), Hunter's TAKEs, new daily-watch signals and coins whose attention turned HIGH."""
    from pathlib import Path

    _table(j)
    woke = []
    try:
        ex = j._explorer()
    except Exception:  # noqa: BLE001
        ex = None
    if ex:
        last = _kv(j, "brain:explorer_seq")
        top = ex.store.book.execute("SELECT MAX(seq) FROM events").fetchone()[0] or 0
        if last is not None:
            for (js,) in ex.store.book.execute("SELECT json FROM events WHERE seq > ? AND kind='ORDER' ORDER BY seq", (int(last),)):
                e = json.loads(js)
                if e.get("shadow") in ("RANDOM",) or e.get("catch_up"):
                    continue
                wake(j, e["coin"], f"explorer:{e.get('setup')}", {"blocked": e.get("shadow"), "type": e.get("type")})
                woke.append(e["coin"])
        _kv(j, "brain:explorer_seq", str(top))
    p = Path(j.dir) / "agent_decisions.sqlite"                # Hunter's and Squeeze's TAKEs from the hourly watch
    if p.exists():
        import sqlite3

        last = _kv(j, "brain:hunter_ts")
        con = sqlite3.connect(f"file:{p}?mode=ro", uri=True, timeout=10)
        try:
            newest = con.execute("SELECT MAX(ts_utc) FROM decisions").fetchone()[0]
            if last is not None:
                for coin, setup in con.execute("SELECT instrument, setup FROM decisions WHERE ts_utc > ? AND decision='TAKE'", (last,)):
                    wake(j, coin, "hunter" if "hunter" in (setup or "") else "squeeze", {"card": setup})
                    woke.append(coin)
            if newest:
                _kv(j, "brain:hunter_ts", newest)
        except sqlite3.Error:
            pass
        finally:
            con.close()
    for o in daily_opened or []:
        if not o["watch"].startswith(("RANDOM", "JARVIS")):
            wake(j, o["coin"], f"setup:{o['watch']}", {"day": o.get("day")})
            woke.append(o["coin"])
    try:
        from jarvis.service import zones_watch

        day = time.strftime("%Y-%m-%d", time.gmtime(j.now()))
        for r in zones_watch.board(j).get("coins", []):
            if (r.get("attention") or {}).get("level") == "HIGH" and _kv(j, f"brain:high:{r['coin']}") != day:
                _kv(j, f"brain:high:{r['coin']}", day)
                wake(j, r["coin"], "attention_high", {"why": (r.get("attention") or {}).get("why", [])[:3]})
                woke.append(r["coin"])
    except Exception:  # noqa: BLE001
        pass
    j.db.commit()
    return woke


# ---------------------------------------------------------------------------
# live management (the eye calls this every look)
# ---------------------------------------------------------------------------
def manage_live(j, px: dict[str, float]) -> list[dict]:
    """Stops, targets and trailing stops of the brain's trades and their random twins, on the live price."""
    from jarvis.service import watch_engine

    _table(j)
    out = []
    rows = j.db.execute("SELECT id, watch, coin, stop, entry, detail FROM evidence_trades WHERE status='OPEN' AND source='brain'").fetchall()
    for tid, w, coin, stop, entry, dj in rows:
        p = px.get(coin)
        if p is None:
            continue
        d = json.loads(dj or "{}")
        why = None
        if stop is not None and p <= stop:
            why = "trailing stop" if stop > d.get("stop0", stop) else "stop"
        elif d.get("target") and p >= d["target"]:
            why = "target"
        if why:
            r = watch_engine.close_at(j, tid, p, f"{why} (live price)")
            if r:
                out.append({**r, "watch": w, "why": why})
            continue
        if p > d.get("high", entry):
            d["high"] = p
            new = stop
            if d.get("trail_atr") and d.get("atr"):
                new = max(stop or 0, p - d["trail_atr"] * d["atr"])
            if new != stop:            # the only change a plan allows after it is written: its own trailing rule, logged (request 12)
                moves = d.setdefault("stop_moves", [])
                if len(moves) < 200:
                    moves.append({"t": int(j.now()), "from": stop, "to": round(new, 8), "rule": f"trail {d['trail_atr']} x ATR under the high"})
            j.db.execute("UPDATE evidence_trades SET stop=?, detail=? WHERE id=?", (new, json.dumps(d, default=str), tid))
    j.db.commit()
    return out


# ---------------------------------------------------------------------------
# learning: passes scored, knowledge credit, calibration
# ---------------------------------------------------------------------------
def settle_passes(j) -> int:
    """What each PASS's coin did over the next day and five days (the Explorer's candles; the feed's for other coins)."""
    _daily = _coin_daily

    _table(j)
    n = 0
    now = int(j.now())
    rows = j.db.execute("SELECT id, t, coin, price FROM brain_decisions WHERE action='PASS' AND after_5d_pct IS NULL AND t <= ?", (now - 86400,)).fetchall()
    cache: dict[str, list] = {}
    for did, t, coin, price in rows:
        if not price:
            continue
        D = cache.setdefault(coin, _daily(j, coin))
        a1 = next((b[4] for b in D if b[0] >= t), None)                         # the first daily close a full day or more later
        a5 = next((b[4] for b in D if b[0] + 86400 >= t + 5 * 86400), None) if now >= t + 5 * 86400 else None
        if a1 is None:
            continue
        j.db.execute("UPDATE brain_decisions SET after_1d_pct=?, after_5d_pct=? WHERE id=?", (_pct(a1, price), _pct(a5, price) if a5 else None, did))
        n += 1
    j.db.commit()
    try:
        n += settle_unreviewed(j)
    except Exception:  # noqa: BLE001
        pass
    return n


def _closed(j, watch: str) -> list[dict]:
    rows = j.db.execute("SELECT id, coin, net_usd, detail, exit_why, entry_t, exit_t FROM evidence_trades WHERE watch=? AND status='CLOSED'", (watch,)).fetchall()
    out = []
    for tid, coin, net, dj, xw, et, xt in rows:
        d = json.loads(dj or "{}")
        out.append({"id": tid, "coin": coin, "net": net or 0.0, "sized": round((net or 0.0) * d.get("size_pct", 100) / 100, 2), "conf": d.get("confidence"),
                    "knowledge": d.get("knowledge") or [], "exit_why": xw, "entry_t": et, "exit_t": xt, "decision": d.get("decision")})
    return out


def record(j) -> dict:
    """The short version for the evidence pack: how its own trades went, so it can learn from them."""
    _table(j)
    c = _closed(j, WATCH)
    r = _closed(j, BASE)
    n = len(c)
    return {"closed": n, "open": j.db.execute("SELECT COUNT(*) FROM evidence_trades WHERE watch=? AND status='OPEN'", (WATCH,)).fetchone()[0],
            "avg_usd_per_100": round(sum(x["net"] for x in c) / n, 2) if n else None,
            "random_twin_avg_usd": round(sum(x["net"] for x in r) / len(r), 2) if r else None,
            "open_coins": [r[0] for r in j.db.execute("SELECT coin FROM evidence_trades WHERE watch=? AND status='OPEN'", (WATCH,))],
            "wins": sum(1 for x in c if x["net"] > 0), "last_5": [{k: x[k] for k in ("coin", "net", "exit_why", "knowledge")} for x in
                                                                   sorted(c, key=lambda x: x["exit_t"] or 0)[-5:]]}


def calibration(rows: list[dict]) -> list[dict]:
    """Does a higher confidence mean better results? Buckets of the confidence it stated before each trade."""
    out = []
    for lo, hi in ((0, 50), (50, 65), (65, 80), (80, 101)):
        sub = [x for x in rows if x.get("conf") is not None and lo <= x["conf"] < hi]
        if sub:
            out.append({"confidence": f"{lo}-{min(hi, 100)}", "trades": len(sub), "win_rate": round(sum(1 for x in sub if x["net"] > 0) / len(sub), 2),
                        "avg_usd": round(sum(x["net"] for x in sub) / len(sub), 2)})
    return out


def credit(rows: list[dict]) -> list[dict]:
    """Each knowledge piece the plans cited, with the results of the trades that cited it."""
    by: dict[str, list] = {}
    for x in rows:
        for k in x["knowledge"]:
            by.setdefault(k, []).append(x["net"])
    return sorted([{"knowledge": k, "trades": len(v), "avg_usd": round(sum(v) / len(v), 2), "wins": sum(1 for n in v if n > 0)} for k, v in by.items()],
                  key=lambda r: -r["trades"])


def _px(j) -> dict:
    from jarvis.service import eye

    px = dict(eye.STATE.get("prices") or {})
    if not px:
        try:
            px = j.prices() or {}
        except Exception:  # noqa: BLE001
            px = {}
    return px


def open_trades(j) -> list[dict]:
    """Jarvis's open trades with the live price: P&L now, the stop's distance, the plan, its random twin."""
    px = _px(j)
    out = []
    for tid, coin, entry, stop, et, dj in j.db.execute("SELECT id, coin, entry, stop, entry_t, detail FROM evidence_trades WHERE watch=? AND status='OPEN' "
                                                       "ORDER BY entry_t", (WATCH,)).fetchall():
        d = json.loads(dj or "{}")
        now = px.get(coin)
        twin = j.db.execute("SELECT coin FROM evidence_trades WHERE watch=? AND detail LIKE ?", (BASE, f'%"twin_of": "{tid}"%')).fetchone()
        out.append({"id": tid, "coin": coin, "entry": entry, "stop": stop, "now": now, "entry_t": et,
                    "pnl_pct": round(100 * (now / entry - 1), 2) if now and entry else None,
                    "stop_pct": round(100 * (stop / entry - 1), 1) if stop and entry else None, "stop_raised": bool(stop and stop > d.get("stop0", stop)),
                    "trail_atr": d.get("trail_atr"), "target": d.get("target"), "days": d.get("days"), "confidence": d.get("confidence"),
                    "size_pct": d.get("size_pct"), "thesis": d.get("thesis"), "twin": twin[0] if twin else None})
    return out


def running(mine: list[dict], twins: list[dict]) -> dict:
    """Running totals per $100 after costs, me against the twins, by exit time (the 'am I beating random' chart)."""
    def run(rows):
        tot, xs = 0.0, []
        for x in sorted(rows, key=lambda x: x["exit_t"] or 0):
            tot += x["net"]
            xs.append({"t": x["exit_t"], "v": round(tot, 2)})
        return xs
    return {"me": run(mine), "twins": run(twins)}


def trade_detail(j, trade_id: str) -> dict:
    """One evidence trade in full (Jarvis's or any other watch's): the plan written before, what woke it, its twin, the price
    around it (hourly), the zone it was about, and the review once it has one."""
    import sqlite3
    from pathlib import Path

    from jarvis.service import watch_engine

    _table(j)
    row = j.db.execute(f"SELECT {', '.join(watch_engine.COLS)} FROM evidence_trades WHERE id=?", (trade_id,)).fetchone()
    if not row:
        raise ValueError("no such trade")
    t = dict(zip(watch_engine.COLS, row))
    d = json.loads(t.pop("detail") or "{}")
    out: dict[str, Any] = {"trade": t, "detail": d}
    now = _px(j).get(t["coin"])
    if t["status"] == "OPEN" and now and t["entry"]:
        out["now"] = now
        out["pnl_pct"] = round(100 * (now / t["entry"] - 1), 2)
        out["pnl_usd"] = round(100 * (now / t["entry"] - 1), 2)
    dec = j.db.execute("SELECT t, triggers, action, confidence, size_pct, plan, thesis, knowledge, cost_usd FROM brain_decisions WHERE id=?",
                       (d.get("decision"),)).fetchone() if d.get("decision") else None
    if dec:
        out["decision"] = {"t": dec[0], "triggers": json.loads(dec[1] or "{}"), "action": dec[2], "confidence": dec[3], "size_pct": dec[4],
                           "plan": json.loads(dec[5] or "{}"), "thesis": dec[6], "knowledge": json.loads(dec[7] or "[]"), "cost_usd": dec[8]}
        trig = out["decision"]["triggers"]
        z = next((v.get("zone") for v in trig.values() if isinstance(v, dict) and v.get("zone")), None)
        if z:
            out["zone"] = z
    if t["watch"] == WATCH:
        tw = j.db.execute("SELECT id, coin, entry, stop, status, net_usd FROM evidence_trades WHERE watch=? AND detail LIKE ?",
                          (BASE, f'%"twin_of": "{trade_id}"%')).fetchone()
        if tw:
            out["twin"] = dict(zip(("id", "coin", "entry", "stop", "status", "net_usd"), tw))
    if "zone" not in out:
        try:
            from jarvis.service import zones_watch

            row_z = next((r for r in zones_watch.board(j).get("coins", []) if r["coin"] == t["coin"]), None)
            zz = (row_z or {}).get("inside") or []
            if zz:
                out["zone"] = [zz[0]["bot"], zz[0]["top"]]
        except Exception:  # noqa: BLE001
            pass
    p = Path(j.dir) / "explorer_bars.sqlite"
    if p.exists():
        con = sqlite3.connect(f"file:{p}?mode=ro", uri=True, timeout=10)
        try:
            t0 = int((t["entry_t"] or t["signal_t"]) - 48 * 3600)
            t1 = int((t["exit_t"] or j.now()) + 24 * 3600)
            out["hourly"] = [{"t": a, "c": c} for a, c in con.execute("SELECT t, c FROM bars WHERE coin=? AND tf='1h' AND t >= ? AND t <= ? ORDER BY t",
                                                                       (t["coin"], t0, t1))]
        finally:
            con.close()
    try:
        from jarvis.service import reviews

        reviews._table(j)
        rv = j.db.execute("SELECT text, tags FROM trade_reviews WHERE id=?", (f"ev:{trade_id}",)).fetchone()
        if rv:
            out["review"] = {"text": rv[0], "tags": json.loads(rv[1] or "[]")}
    except Exception:  # noqa: BLE001
        pass
    return out


def report(j, days: int = 30) -> dict:
    """Jarvis's own book for the app and Ask: results against its random twins, calibration, knowledge credit, recent decisions."""
    _table(j)
    c, r = _closed(j, WATCH), _closed(j, BASE)
    since = int(j.now()) - days * 86400
    dec = [dict(zip(("id", "t", "coin", "triggers", "action", "confidence", "size_pct", "price", "thesis", "trade_id", "after_1d_pct", "after_5d_pct", "note"), x))
           for x in j.db.execute("SELECT id, t, coin, triggers, action, confidence, size_pct, price, thesis, trade_id, after_1d_pct, after_5d_pct, note "
                                 "FROM brain_decisions WHERE t >= ? ORDER BY t DESC LIMIT 40", (since,))]
    for d in dec:
        d["triggers"] = [k for k in json.loads(d["triggers"] or "{}") if not k.startswith("_")]
    today = j.db.execute("SELECT action, COUNT(*) FROM brain_decisions WHERE t >= ? GROUP BY 1", (_today0(j),)).fetchall()
    passes = [d for d in dec if d["action"] == "PASS" and d["after_5d_pct"] is not None]
    n = len(c)
    avg, ravg = (round(sum(x["net"] for x in c) / n, 2) if n else None), (round(sum(x["net"] for x in r) / len(r), 2) if r else None)
    from jarvis.service import scoreboard

    ev = scoreboard._events([{"entry_t": x["entry_t"]} for x in c], daily=True) if c else 0
    return {"closed": n, "open": open_trades(j), "running": running(c, r),
            "avg_usd_per_100": avg, "random_twin_avg_usd": ravg, "vs_random_usd": round(avg - ravg, 2) if avg is not None and ravg is not None else None,
            "sized_net_usd": round(sum(x["sized"] for x in c), 2), "events": ev,
            "verdict": ("too early" if ev < 10 else "ahead of its random twins" if (avg or 0) > (ravg or 0) else "not ahead of its random twins"),
            "calibration": calibration(c), "knowledge_credit": credit(c),
            "passes_scored": len(passes), "passes_that_ran_5pct": [{"coin": d["coin"], "after_5d_pct": d["after_5d_pct"], "thesis": d["thesis"]}
                                                                  for d in passes if d["after_5d_pct"] >= 5][:5],
            "today": {a: k for a, k in today}, "daily_limit": DAILY_MAX, "decisions": dec[:15],
            "budget": {"daily_usd": DAILY_USD, "spent_today_usd": round(spent_today(j), 3), "unlocked_now_usd": paced_budget(j),
                       "how": "The AI decides the best-ranked moments across every coin while the day's budget lasts; the rest are logged "
                              "as not reviewed and scored the same way (engine plan D2)."},
            "ranking_audit": ranking_audit(j),
            "how_to_read": "Jarvis weighs everything we know at each moment and writes its plan before the outcome. Each trade is $100 on "
                           "paper (its chosen size is kept as 'sized'); each one has a random twin (another coin, same moment, same plan), "
                           "so 'vs random' is the honest score. It needs 10 independent events before any verdict."}
