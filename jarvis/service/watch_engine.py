"""The daily section of the watch registry (docs/knowledge/watches.json): every daily bar-close watch, run after each
closed daily candle into its own evidence book (one table, evidence_trades). Madhav, 2026-10-03: "if every watch trades,
only then we can measure its performance".

Each signal is a $100 paper trade with the watch's own exit and NDAX costs; watches never compete for slots (one open trade
per watch per coin, so a signal that repeats while its trade runs is the same signal). The rule functions are the SAME ones
the history tests used (src/research/reads.py), with the same entry (next day's open) and exits, so live results can be put
next to the repair shop's numbers. Two random baselines (one coin a day, held 10 or 30 days) give the live bar to beat.

Trades from the eye (live level-cross watches, jarvis/service/eye.py) and from Jarvis's brain (jarvis/service/brain.py) are stored
in the same table; their time exits and a second check of their stop (and the brain's target) on daily candles happen here.

Paper only: nothing here reaches Hands or an exchange.

  run(j)            catch up every daily close not processed yet: new signals, fills at the next open, exits
  open_eye_trade()  called by the eye for a level-cross entry at the live price
  close_at()        called by the eye when a live stop is hit
  trades(j, ...)    rows for the scoreboard and the app
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone

DAY = 86400
EPISODE_DAYS = 20                 # same coin, same read, within 20 days = one episode (review #5)
STAKE = 100.0
# id: (kind, settings). kinds: read = Madhav's reads (stop = the read's stop, exit after N days); h07 = RSI exit or N days;
# random = one random coin per daily close, exit after N days.
DAILY = {
    "H07": {"kind": "h07", "days": 10, "rsi_exit": 40},
    "M1a": {"kind": "read", "variant": "M1a", "days": 30},
    "M2a": {"kind": "read", "variant": "M2a", "days": 30},
    "M2a-G": {"kind": "read", "variant": "M2a", "days": 30, "market_gate": True},
    "M3a": {"kind": "read", "variant": "M3a", "days": 30},
    "M3b": {"kind": "read", "variant": "M3b", "days": 30},
    "RANDOM_10D": {"kind": "random", "days": 10},
    "RANDOM_20D": {"kind": "random", "days": 20},
    "RANDOM_30D": {"kind": "random", "days": 30},
}
EYE = {"ZONE_TOUCH": {"days": 20}}
COLS = ("id", "watch", "coin", "source", "signal_t", "signal_day", "entry_t", "entry_day", "entry", "stop", "exit_t", "exit_day",
        "exit", "net_usd", "status", "why", "exit_why", "regime", "detail")


def _table(j) -> None:
    j.db.execute("CREATE TABLE IF NOT EXISTS evidence_trades (id TEXT PRIMARY KEY, watch TEXT, coin TEXT, source TEXT, signal_t INTEGER, "
                 "signal_day TEXT, entry_t INTEGER, entry_day TEXT, entry REAL, stop REAL, exit_t INTEGER, exit_day TEXT, exit REAL, "
                 "net_usd REAL, status TEXT, why TEXT, exit_why TEXT, regime TEXT, detail TEXT)")
    j.db.execute("CREATE TABLE IF NOT EXISTS engine_state (k TEXT PRIMARY KEY, v TEXT)")


def _day(t: float) -> str:
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d")


def _cost(coin: str) -> float:
    from src.research import reads as R

    return R.cost(coin)


def net(coin: str, entry: float, exit_px: float) -> float:
    k = _cost(coin)
    return round(STAKE * (exit_px / entry * (1 - k) ** 2 - 1), 2)


def _daily(j, coin: str) -> list[tuple]:
    from jarvis.service.reads_watch import _daily as d

    return d(j, coin)


def regime_at(B, t: int) -> str | None:
    """ALLOWED when Bitcoin's last closed day at or before t is above its 50-day average (the M2a-G gate, V02), else RISK_OFF."""
    idx = None
    for k in range(len(B.t) - 1, -1, -1):
        if B.t[k] <= t:
            idx = k
            break
    if idx is None or B.ema50[idx] is None:
        return None
    return "ALLOWED" if B.c[idx] > B.ema50[idx] else "RISK_OFF"


def _random_pick(watch: str, day: str, coins: list[str]) -> str:
    h = int(hashlib.sha1(f"{watch}|{day}".encode()).hexdigest(), 16)
    return sorted(coins)[h % len(coins)]


def _fires(spec: dict, S, B, i: int, r10: list) -> tuple[bool, float | None, str]:
    """(fired, stop price or None, why) on closed day i."""
    from src.research import reads as R

    if spec["kind"] == "h07":
        up = S.sma200[i] is not None and S.c[i] > S.sma200[i]
        ok = bool(up and r10[i] is not None and r10[i] < 30)
        return ok, None, (f"RSI(10) {r10[i]:.0f}, above the 200-day" if ok else "")
    if spec["kind"] == "read":
        r = R.READERS[spec["variant"][:2]](S, i, B, spec["variant"])
        if not R.fired(r):
            return False, None, ""
        if spec.get("market_gate"):
            bi = B.at(S.t[i])
            if not (bi is not None and B.ema50[bi] is not None and B.c[bi] > B.ema50[bi]):
                return False, None, ""
        return True, float(r["stop"]) if r.get("stop") else None, "all conditions met"
    return False, None, ""


def _insert(j, row: dict) -> None:
    j.db.execute(f"INSERT INTO evidence_trades ({', '.join(COLS)}) VALUES ({', '.join('?' * len(COLS))})", tuple(row.get(c) for c in COLS))


def _busy(j, watch: str, coin: str, signal_t: int) -> bool:
    """One trade at a time per watch and coin; for reads also one episode per 20 days."""
    if j.db.execute("SELECT 1 FROM evidence_trades WHERE watch=? AND coin=? AND status IN ('WAITING','OPEN')", (watch, coin)).fetchone():
        return True
    if j.db.execute("SELECT 1 FROM evidence_trades WHERE watch=? AND coin=? AND signal_t=?", (watch, coin, signal_t)).fetchone():
        return True
    spec = DAILY.get(watch, {})
    if spec.get("kind") == "read":
        last = j.db.execute("SELECT MAX(signal_t) FROM evidence_trades WHERE watch=? AND coin=?", (watch, coin)).fetchone()[0]
        return bool(last and signal_t - last <= EPISODE_DAYS * DAY)
    return False


def _manage(j, coin: str, D: list[tuple], S, r10: list, rows: list[tuple]) -> list[dict]:
    """Fill WAITING trades at the next open and close OPEN ones by their rule, on closed daily candles."""
    out = []
    idx = {b[0]: k for k, b in enumerate(D)}
    for row in rows:
        r = dict(zip(COLS, row))
        spec = DAILY.get(r["watch"]) or EYE.get(r["watch"]) or {}
        if r["status"] == "WAITING":
            i = idx.get(r["signal_t"])
            if i is None or i + 1 >= len(D):
                continue                                      # the entry day has not closed yet
            k = i + 1
            r.update(entry_t=D[k][0], entry_day=_day(D[k][0]), entry=D[k][1], status="OPEN")
            j.db.execute("UPDATE evidence_trades SET entry_t=?, entry_day=?, entry=?, status='OPEN' WHERE id=?", (r["entry_t"], r["entry_day"], r["entry"], r["id"]))
            out.append({"watch": r["watch"], "coin": coin, "event": "filled"})
        if r["status"] != "OPEN":
            continue
        live = r["source"] in ("eye", "brain")
        det = json.loads(r.get("detail") or "{}") if live else {}
        if live:                                              # entered at a live price inside day k: daily checks start the next day
            k = next((m for m, b in enumerate(D) if b[0] > r["entry_t"]), None)
            if k is None:
                continue
            k0 = k - 1
        else:
            k = idx.get(r["entry_t"])
            if k is None:
                continue
            k0 = k
        days = int(det.get("days") or spec.get("days", 30))
        exit_px = exit_t = None
        why = ""
        for d in range(k, len(D)):
            if live and D[d][0] >= r["entry_t"] + days * DAY:
                exit_px, exit_t, why = D[d][1], D[d][0], f"{days} days"
                break
            if not live and d == k0 + days:
                exit_px, exit_t, why = D[d][1], D[d][0], f"{days} days"
                break
            if r["stop"]:
                if D[d][1] <= r["stop"]:
                    exit_px, exit_t, why = D[d][1], D[d][0], "opened under the stop"
                    break
                if D[d][3] <= r["stop"]:
                    exit_px, exit_t, why = r["stop"], D[d][0], "stop"
                    break
            if det.get("target") and D[d][2] >= det["target"]:      # the brain's target, if the eye missed it (daily high)
                exit_px, exit_t, why = (D[d][1] if D[d][1] >= det["target"] else det["target"]), D[d][0], "target"
                break
            if spec.get("rsi_exit") and r10[d] is not None and r10[d] > spec["rsi_exit"] and d + 1 < len(D):
                exit_px, exit_t, why = D[d + 1][1], D[d + 1][0], f"RSI(10) back over {spec['rsi_exit']} on {_day(D[d][0])}"
                break
        if exit_px is not None:
            n = net(coin, r["entry"], exit_px)
            j.db.execute("UPDATE evidence_trades SET exit_t=?, exit_day=?, exit=?, net_usd=?, status='CLOSED', exit_why=? WHERE id=?",
                         (exit_t, _day(exit_t), exit_px, n, why, r["id"]))
            out.append({"watch": r["watch"], "coin": coin, "event": "closed", "net_usd": n})
    return out


def run(j, watches: tuple | list | None = None, coins: list[str] | None = None) -> dict:
    """Catch up every closed daily candle not processed yet (at most the last 10 days), then manage open trades."""
    from src.research import reads as R

    _table(j)
    names = [w for w in (watches or DAILY) if w in DAILY]
    btc = _daily(j, "BTC")
    if len(btc) < 60:
        return {"opened": [], "filled": [], "closed": [], "note": "not enough daily candles"}
    B = R.Series(btc)
    base_key = "last_t:" + ",".join(sorted(names))
    opened, filled, closed = [], [], []
    universe = coins or list(R.COINS)
    data = {}
    for c in universe:
        D = btc if c == "BTC" else _daily(j, c)
        if len(D) < 60:
            continue
        S = B if c == "BTC" else R.Series(D)
        data[c] = (D, S, R.rsi(S.c, 10))
    for c, (D, S, r10) in data.items():
        key = f"{base_key}:{c}"                                # per coin: a coin whose candle comes late is not skipped
        row = j.db.execute("SELECT v FROM engine_state WHERE k=?", (key,)).fetchone()
        last_done = int(row[0]) if row else D[-1][0] - DAY       # first run: only the latest closed day (no backfilled 'trades')
        start = max(0, len(D) - 10)
        for i in range(start, len(D)):
            t = D[i][0]
            if t <= last_done:
                continue
            for w in names:
                spec = DAILY[w]
                if spec["kind"] == "random":
                    if _random_pick(w, _day(t), list(data)) != c:
                        continue
                    ok, stop, why = True, None, "random pick for the baseline"
                else:
                    if len(D) < 210 and spec["kind"] == "h07":
                        continue
                    ok, stop, why = _fires(spec, S, B, i, r10)
                if not ok or _busy(j, w, c, t):
                    continue
                _insert(j, {"id": uuid.uuid4().hex[:12], "watch": w, "coin": c, "source": "daily", "signal_t": t, "signal_day": _day(t),
                            "stop": stop, "status": "WAITING", "why": why, "regime": regime_at(B, t), "detail": json.dumps({"close": D[i][4]})})
                opened.append({"watch": w, "coin": c, "day": _day(t)})
        j.db.execute("INSERT OR REPLACE INTO engine_state VALUES (?,?)", (key, str(max(last_done, D[-1][0]))))
    for c, (D, S, r10) in data.items():
        rows = j.db.execute(f"SELECT {', '.join(COLS)} FROM evidence_trades WHERE coin=? AND status IN ('WAITING','OPEN') "
                            f"AND (watch IN ({','.join('?' * len(names))}) OR source IN ('eye','brain'))", (c, *names)).fetchall()
        for ev in _manage(j, c, D, S, r10, rows):
            (filled if ev["event"] == "filled" else closed).append(ev)
    j.db.commit()
    return {"opened": opened, "filled": filled, "closed": closed}


# ---------------------------------------------------------------------------
# the eye's trades (level-cross watches)
# ---------------------------------------------------------------------------
def open_eye_trade(j, watch: str, coin: str, price: float, stop: float | None, why: str, detail: dict, regime: str | None) -> dict | None:
    _table(j)
    if j.db.execute("SELECT 1 FROM evidence_trades WHERE watch=? AND coin=? AND status='OPEN'", (watch, coin)).fetchone():
        return None
    t = int(j.now())
    row = {"id": uuid.uuid4().hex[:12], "watch": watch, "coin": coin, "source": "eye", "signal_t": t, "signal_day": _day(t), "entry_t": t,
           "entry_day": _day(t), "entry": float(price), "stop": stop, "status": "OPEN", "why": why, "regime": regime, "detail": json.dumps(detail)}
    _insert(j, row)
    j.db.commit()
    return row


def close_at(j, trade_id: str, price: float, why: str) -> dict | None:
    _table(j)
    r = j.db.execute("SELECT coin, entry FROM evidence_trades WHERE id=? AND status='OPEN'", (trade_id,)).fetchone()
    if not r:
        return None
    t = int(j.now())
    n = net(r[0], r[1], float(price))
    j.db.execute("UPDATE evidence_trades SET exit_t=?, exit_day=?, exit=?, net_usd=?, status='CLOSED', exit_why=? WHERE id=?",
                 (t, _day(t), float(price), n, why, trade_id))
    j.db.commit()
    return {"id": trade_id, "coin": r[0], "net_usd": n}


def open_with_stops(j) -> list[dict]:
    _table(j)
    return [dict(zip(("id", "watch", "coin", "stop", "entry"), r)) for r in
            j.db.execute("SELECT id, watch, coin, stop, entry FROM evidence_trades WHERE status='OPEN' AND source='eye' AND stop IS NOT NULL")]


def trades(j, watch: str | None = None, limit: int = 500) -> list[dict]:
    _table(j)
    q = f"SELECT {', '.join(COLS)} FROM evidence_trades" + (" WHERE watch=?" if watch else "") + " ORDER BY signal_t DESC LIMIT ?"
    return [dict(zip(COLS, r)) for r in j.db.execute(q, ((watch, limit) if watch else (limit,)))]
