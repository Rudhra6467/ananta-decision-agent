"""The $500 NDAX book (plan D9, D12, D13, Oct 11): the rules, shared by the backtest here and the live paper book
(jarvis/service/ndax_book.py), so what is tested is what runs.

Sleeves, as shares of the book's value in CAD:
  CORE      up to 60%: BTC 40% + ETH 20% while the exposure dial is open (Bitcoin's close above its 50-day and 200-day averages,
            review #25); cash when it is closed. Moves only when the dial changes.
  EDGES     up to 30%: measured edges only. Review #26 found one: H07 on tier-A coins while the dial is CLOSED. H07 = a close above
            the 200-day average with RSI(10) under 30; buy the next open; sell the next open after RSI(10) closes over 40, else the
            open 10 days after entry; no stop (review #27). Sized so the distance to the invalidation level (2 x ATR(14) under the
            entry) is 0.5% of the book; at most 10% of the book in one trade; at most 6% of the book at risk across open setup trades;
            at most 2 open in coins whose 90-day correlation with each other is over 0.8.
  JUDGMENT  up to 10%: the brain's buys on NDAX coins, the same sizing. Live paper only; not in the backtest (it cannot be replayed).
Brakes (D12; code, outside the AI). They stop new buys only; exits always run:
  a day's loss of 2% -> no buys the next day | a week's loss of 4% -> none until Monday | 4 losing setup trades in a row -> none for
  7 days | a 15% fall from the peak -> PAUSED (live: until Madhav resumes it; the backtest stands in 30 days).
NDAX: CAD pairs only; each instrument's minimum quantity and quantity step; 0.20% fee a side plus the spread.

    python -m src.research.book500 run --out ~/ananta_runs/book500
"""
from __future__ import annotations

import json
import math
import os
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

DAY = 86400
START_CAD = 500.0
CORE = {"BTC": 0.40, "ETH": 0.20}
EDGE_SLEEVE, JUDGMENT_SLEEVE = 0.30, 0.10
RISK_PER_TRADE, MAX_OPEN_RISK, MAX_PER_TRADE = 0.005, 0.06, 0.10
CORR_LIMIT, CORR_MAX_OPEN, CORR_DAYS = 0.8, 2, 90
INV_ATR = 2.0
NDAX_STOP_ATR = 6.0                     # D12: a resting stop on NDAX, outage insurance only (never touched 2018-2026)
H07_DAYS, H07_RSI_IN, H07_RSI_OUT = 10, 30, 40
BRAKES = {"day_loss": 0.02, "week_loss": 0.04, "losing_streak": 4, "streak_pause_days": 7, "fall_from_peak": 0.15, "backtest_pause_days": 30}
SPLITS = {"DISCOVERY": ("2018-01-01", "2023-12-31"), "CONFIRM": ("2024-01-01", "2099-01-01")}
NDAX_FEE = 0.002


def _t(s: str) -> int:
    return int(datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())


def _day(t: int) -> str:
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d")


# ---------- indicators (plain lists, aligned to the bars) ----------
def ema(x: list[float], n: int) -> list[float | None]:
    out: list[float | None] = []
    k, e = 2 / (n + 1), None
    for i, v in enumerate(x):
        if i + 1 < n:
            out.append(None)
            continue
        e = sum(x[i + 1 - n:i + 1]) / n if e is None else v * k + e * (1 - k)
        out.append(e)
    return out


def sma(x: list[float], n: int) -> list[float | None]:
    out: list[float | None] = []
    s = 0.0
    for i, v in enumerate(x):
        s += v
        if i >= n:
            s -= x[i - n]
        out.append(s / n if i + 1 >= n else None)
    return out


def rsi(x: list[float], n: int) -> list[float | None]:
    out: list[float | None] = [None] * len(x)
    if len(x) <= n:
        return out
    g = [max(0.0, x[i] - x[i - 1]) for i in range(1, len(x))]
    l = [max(0.0, x[i - 1] - x[i]) for i in range(1, len(x))]
    ag, al = sum(g[:n]) / n, sum(l[:n]) / n
    for i in range(n, len(x)):
        if i > n:
            ag = (ag * (n - 1) + g[i - 1]) / n
            al = (al * (n - 1) + l[i - 1]) / n
        out[i] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    return out


def atr(bars: list[tuple], n: int = 14) -> list[float | None]:
    tr = [bars[0][2] - bars[0][3]] + [max(b[2] - b[3], abs(b[2] - p[4]), abs(b[3] - p[4])) for p, b in zip(bars, bars[1:])]
    return sma(tr, n)


class Coin:
    """One coin's daily bars (t, o, h, l, c) in CAD with the indicators the rules use."""

    def __init__(self, bars: list[tuple]):
        self.t = [int(b[0]) for b in bars]
        self.o = [b[1] for b in bars]
        self.c = [b[4] for b in bars]
        self.l = [b[3] for b in bars]
        self.ema50, self.sma200 = ema(self.c, 50), sma(self.c, 200)
        self.rsi10, self.atr14 = rsi(self.c, 10), atr(bars)
        self.ix = {t: i for i, t in enumerate(self.t)}
        self.ret = {self.t[i]: self.c[i] / self.c[i - 1] - 1 for i in range(1, len(self.c))}


# ---------- the rules (used live and in the backtest) ----------
def dial_open(btc: Coin, i: int) -> bool | None:
    if i < 0 or btc.sma200[i] is None:
        return None
    return btc.c[i] > btc.ema50[i] and btc.c[i] > btc.sma200[i]


def h07(s: Coin, i: int) -> bool:
    return bool(s.sma200[i] is not None and s.rsi10[i] is not None and s.c[i] > s.sma200[i] and s.rsi10[i] < H07_RSI_IN)


def h07_exit(s: Coin, i: int) -> bool:
    return s.rsi10[i] is not None and s.rsi10[i] > H07_RSI_OUT


def corr(a: Coin, b: Coin, t_end: int, days: int = CORR_DAYS) -> float | None:
    ts = [t for t in a.ret if t_end - days * DAY < t <= t_end and t in b.ret]
    if len(ts) < 30:
        return None
    x, y = [a.ret[t] for t in ts], [b.ret[t] for t in ts]
    try:
        return statistics.correlation(x, y)
    except statistics.StatisticsError:
        return None


def round_qty(value: float, price: float, inst: dict | None) -> float:
    """NDAX: quantity rounded down to the instrument's step; 0 when under its minimum."""
    if price <= 0 or value <= 0:
        return 0.0
    q = value / price
    if inst:
        step = inst.get("qty_inc") or 0
        if step:
            q = math.floor(q / step + 1e-9) * step
        if q < (inst.get("min_qty") or 0):
            return 0.0
    return q


def size_setup(equity: float, entry: float, atr_v: float | None, sleeve_used: float, sleeve_cap: float, open_risk: float) -> tuple[float, float, float]:
    """(value to buy, risk in CAD, invalidation price) under D9; value 0 when a limit says no."""
    if not atr_v or entry <= 0:
        return 0.0, 0.0, 0.0
    inv = entry - INV_ATR * atr_v
    if inv <= 0:
        return 0.0, 0.0, 0.0
    dist = (entry - inv) / entry
    risk = RISK_PER_TRADE * equity
    value = min(risk / dist, MAX_PER_TRADE * equity, sleeve_cap * equity - sleeve_used)
    risk = value * dist
    if value <= 0 or open_risk + risk > MAX_OPEN_RISK * equity + 1e-9:
        return 0.0, 0.0, inv
    return value, risk, inv


class Brakes:
    """D12. Fed once a day with the book's closing value and the setup trades that closed; says whether new buys may happen."""

    def __init__(self, backtest: bool = True):
        self.backtest = backtest
        self.prev = self.peak = self.week_start = None
        self.week = None
        self.block_until = 0
        self.paused = False
        self.streak = 0
        self.fired: dict[str, int] = {"day_loss": 0, "week_loss": 0, "losing_streak": 0, "fall_from_peak": 0}
        self.log: list[dict] = []

    def _fire(self, kind: str, t: int, until: int, value: float) -> None:
        self.fired[kind] += 1
        self.block_until = max(self.block_until, until)
        self.log.append({"day": _day(t), "brake": kind, "value": round(value, 2), "until": _day(until)})

    def close(self, t: int, value: float, closed_pnls: list[float]) -> None:
        wk = datetime.fromtimestamp(t, timezone.utc).isocalendar()[:2]
        if self.week != wk:
            self.week, self.week_start = wk, (self.prev if self.prev is not None else value)
        if self.prev and value / self.prev - 1 <= -BRAKES["day_loss"]:
            self._fire("day_loss", t, t + 2 * DAY, value)
        if self.week_start and value / self.week_start - 1 <= -BRAKES["week_loss"]:
            nxt = t - t % DAY + (7 - datetime.fromtimestamp(t, timezone.utc).weekday()) * DAY
            if self.block_until < nxt:
                self._fire("week_loss", t, nxt, value)
        for p in closed_pnls:
            self.streak = self.streak + 1 if p < 0 else 0
            if self.streak >= BRAKES["losing_streak"]:
                self._fire("losing_streak", t, t + (BRAKES["streak_pause_days"] + 1) * DAY, value)
                self.streak = 0
        self.peak = max(self.peak or value, value)
        if value / self.peak - 1 <= -BRAKES["fall_from_peak"]:
            if self.backtest:
                self._fire("fall_from_peak", t, t + (BRAKES["backtest_pause_days"] + 1) * DAY, value)
                self.peak = value
            elif not self.paused:
                self.paused = True
                self.fired["fall_from_peak"] += 1
                self.log.append({"day": _day(t), "brake": "fall_from_peak", "value": round(value, 2), "until": "Madhav resumes"})
        self.prev = value

    def may_buy(self, t: int) -> bool:
        return not self.paused and t >= self.block_until


# ---------- the backtest ----------
def simulate(C: dict[str, Coin], tier_a: list[str], inst: dict, cost: dict, t0: int, t1: int, disaster_stop: bool = False, stop_atr: float = INV_ATR) -> dict:
    """disaster_stop: a resting stop on the exchange at each setup's invalidation level (2 x ATR under entry); filled at that level, or
    at the open when the day opens under it. Off by default (review #27); the question D12 raises for live money."""
    btc = C["BTC"]
    cash, pos, trades, curve, sizes = START_CAD, {}, [], [], []
    brakes = Brakes(backtest=True)
    days = [t for t in btc.t if t0 <= t <= t1]
    exit_flag: set[str] = set()
    pending: list[str] = []
    dial_prev = None

    def px(coin: str, t: int, kind: str = "c") -> float | None:
        s = C.get(coin)
        i = s.ix.get(t) if s else None
        return None if i is None else (s.o[i] if kind == "o" else s.c[i])

    def value(t: int) -> float:
        return cash + sum(p["qty"] * (px(c, t) or p["last"]) for c, p in pos.items())

    eq_prev = START_CAD
    core_days = 0
    for t in days:
        closed_today: list[float] = []
        # 1. exits at the open
        for c in list(pos):
            p = pos[c]
            if p["sleeve"] != "EDGE":
                continue
            o = px(c, t, "o")
            if o is None:
                continue
            if c in exit_flag or t - p["entry_t"] >= H07_DAYS * DAY:
                cash += p["qty"] * o * (1 - cost[c])
                pnl = p["qty"] * o * (1 - cost[c]) - p["paid"]
                trades.append({"coin": c, "in": _day(p["entry_t"]), "out": _day(t), "pnl_cad": round(pnl, 2), "pct": round(100 * pnl / p["paid"], 2)})
                closed_today.append(pnl)
                exit_flag.discard(c)
                del pos[c]
        # 2. core follows yesterday's dial
        core_held = any(p["sleeve"] == "CORE" for p in pos.values())
        if dial_prev is False and core_held:
            for c in [c for c, p in pos.items() if p["sleeve"] == "CORE"]:
                o = px(c, t, "o") or pos[c]["last"]
                cash += pos[c]["qty"] * o * (1 - cost[c])
                del pos[c]
        elif dial_prev and not core_held and brakes.may_buy(t):
            for c, w in CORE.items():
                o = px(c, t, "o")
                q = round_qty(w * eq_prev, o or 0, inst.get(c))
                if q:
                    pos[c] = {"sleeve": "CORE", "qty": q, "paid": q * o * (1 + cost[c]), "entry_t": t, "last": o}
                    cash -= q * o * (1 + cost[c])
        # 3. setup entries signalled at yesterday's close (H07 counts only while the dial was closed)
        if pending and brakes.may_buy(t):
            for c in pending:
                if c in pos:
                    continue
                o, s = px(c, t, "o"), C[c]
                i = s.ix.get(t)
                if o is None or i is None or i < 1:
                    continue
                used = sum(p["paid"] for p in pos.values() if p["sleeve"] == "EDGE")
                risk_open = sum(p.get("risk", 0) for p in pos.values() if p["sleeve"] == "EDGE")
                v, risk, inv = size_setup(eq_prev, o, s.atr14[i - 1], used, EDGE_SLEEVE, risk_open)
                if not v:
                    continue
                twins = sum(1 for d, p in pos.items() if p["sleeve"] == "EDGE" and (corr(s, C[d], t - DAY) or 0) > CORR_LIMIT)
                if twins >= CORR_MAX_OPEN:
                    continue
                q = round_qty(min(v, cash / (1 + cost[c])), o, inst.get(c))
                if not q:
                    continue
                paid = q * o * (1 + cost[c])
                cash -= paid
                pos[c] = {"sleeve": "EDGE", "qty": q, "paid": paid, "entry_t": t, "risk": risk, "inv": inv, "last": o, "entry": o, "atr": s.atr14[i - 1]}
                sizes.append({"coin": c, "day": _day(t), "risk_pct": round(100 * risk / eq_prev, 3), "value_pct": round(100 * paid / eq_prev, 2)})
        # 3b. a resting stop on the exchange (the D12 question), checked on the day's low
        if disaster_stop:
            for c in list(pos):
                p = pos[c]
                s_, i_ = C.get(c), (C[c].ix.get(t) if c in C else None)
                if p["sleeve"] != "EDGE" or i_ is None:
                    continue
                lvl = p["entry"] - stop_atr * p["atr"]
                if s_.l[i_] > lvl:
                    continue
                fill = min(s_.o[i_], lvl)
                cash += p["qty"] * fill * (1 - cost[c])
                pnl = p["qty"] * fill * (1 - cost[c]) - p["paid"]
                trades.append({"coin": c, "in": _day(p["entry_t"]), "out": _day(t), "pnl_cad": round(pnl, 2), "pct": round(100 * pnl / p["paid"], 2),
                               "why": "stop"})
                closed_today.append(pnl)
                exit_flag.discard(c)
                del pos[c]
        # 4. the close
        for c, p in pos.items():
            p["last"] = px(c, t) or p["last"]
        eq = value(t)
        curve.append((t, eq))
        core_days += any(p["sleeve"] == "CORE" for p in pos.values())
        brakes.close(t, eq, closed_today)
        bi = btc.ix[t]
        dial_prev = dial_open(btc, bi)
        exit_flag = {c for c, p in pos.items() if p["sleeve"] == "EDGE" and C[c].ix.get(t) is not None and h07_exit(C[c], C[c].ix[t])}
        pending = []
        if dial_prev is False:
            cands = [(C[c].rsi10[C[c].ix[t]], c) for c in tier_a if c in C and C[c].ix.get(t) is not None and h07(C[c], C[c].ix[t])]
            pending = [c for _, c in sorted(cands)]
        eq_prev = eq
    peak, dd = START_CAD, 0.0
    for _, v in curve:
        peak = max(peak, v)
        dd = min(dd, v / peak - 1)
    pn = [x["pct"] for x in trades]
    return {"from": _day(days[0]) if days else None, "to": _day(days[-1]) if days else None, "start_cad": START_CAD,
            "end_cad": round(curve[-1][1], 2) if curve else START_CAD, "return_pct": round(100 * (curve[-1][1] / START_CAD - 1), 2) if curve else 0,
            "max_fall_pct": round(100 * dd, 2), "setup_trades": len(trades), "setup_win_rate": round(sum(p > 0 for p in pn) / len(pn), 3) if pn else None,
            "setup_avg_pct": round(statistics.mean(pn), 2) if pn else None, "brakes_fired": brakes.fired, "brake_log": brakes.log[:40],
            "sizes_ok": all(s["risk_pct"] <= 100 * RISK_PER_TRADE + 1e-6 and s["value_pct"] <= 100 * MAX_PER_TRADE + 0.5 for s in sizes),
            "max_risk_pct_seen": max((s["risk_pct"] for s in sizes), default=0), "trades": trades[-30:], "days": len(curve), "core_days_pct": round(100 * core_days / len(curve), 1) if curve else 0,
            "curve_month_end": [(_day(t), round(v, 2)) for k, (t, v) in enumerate(curve) if k + 1 == len(curve) or _day(curve[k + 1][0])[:7] != _day(t)[:7]]}


def bench(btc: Coin, cost: float, t0: int, t1: int) -> dict:
    """HOLD Bitcoin and GATE50 (Bitcoin above its 50-day, the hurdle every book must beat) in CAD over the same days."""
    out = {}
    for name in ("HOLD", "GATE50"):
        eq, held, peak, dd = START_CAD, False, START_CAD, 0.0
        qty = 0.0
        for i, t in enumerate(btc.t):
            if not (t0 <= t <= t1) or i == 0:
                continue
            want = True if name == "HOLD" else (btc.ema50[i - 1] is not None and btc.c[i - 1] > btc.ema50[i - 1])
            if want and not held:
                qty, held = eq * (1 - cost) / btc.o[i], True
            elif not want and held:
                eq, held = qty * btc.o[i] * (1 - cost), False
            v = qty * btc.c[i] if held else eq
            peak = max(peak, v)
            dd = min(dd, v / peak - 1)
            last = v
        out[name] = {"end_cad": round(last, 2), "return_pct": round(100 * (last / START_CAD - 1), 2), "max_fall_pct": round(100 * dd, 2)}
    return out


def load(coins: list[str], fx_path: Path) -> dict[str, Coin]:
    from src.research import review25 as R25

    obs = json.loads(fx_path.read_text())["observations"]
    fx = {o["d"]: float(o["FXUSDCAD"]["v"]) for o in obs if o.get("FXUSDCAD")}
    days = sorted(fx)
    out = {}
    for c in coins:
        bars = R25.daily(c)
        if len(bars) < 260:
            continue
        cad, last, j = [], None, 0
        for b in bars:
            d = _day(int(b[0]))
            while j < len(days) and days[j] <= d:
                last = fx[days[j]]
                j += 1
            r = last or fx[days[0]]
            cad.append((int(b[0]), b[1] * r, b[2] * r, b[3] * r, b[4] * r))
        out[c] = Coin(cad)
    return out


def instruments(get=None) -> dict:
    """NDAX's CAD instruments: {coin: {id, min_qty, qty_inc, price_inc}}."""
    import requests

    get = get or (lambda u: requests.get(u, timeout=20).json())
    ins = get("https://api.ndax.io:8443/AP/GetInstruments?OMSId=1")
    return {i["Product1Symbol"]: {"id": i["InstrumentId"], "min_qty": i.get("MinimumQuantity"), "qty_inc": i.get("QuantityIncrement"),
                                  "price_inc": i.get("PriceIncrement")}
            for i in ins if i.get("Product2Symbol") == "CAD" and not i.get("IsDisable")}


def run(out: Path) -> dict:
    from jarvis.service import core, registry

    j = core.from_env()
    reg = registry.load(j)
    nd = {c for c, k in reg["coins"].items() if k.get("ndax")}
    tier_a = sorted(c for c in nd if reg["coins"][c].get("tier") == "A")
    inst = instruments()
    C = load(sorted(set(tier_a) | set(CORE)), out / "usdcad.json")
    cost = {c: registry.cost(c, reg) for c in C}
    rep = {"written": time.strftime("%Y-%m-%d %H:%M"), "rules": {"core": CORE, "edge_sleeve": EDGE_SLEEVE, "risk_per_trade": RISK_PER_TRADE,
           "max_open_risk": MAX_OPEN_RISK, "max_per_trade": MAX_PER_TRADE, "corr": [CORR_LIMIT, CORR_MAX_OPEN], "brakes": BRAKES},
           "coins": {"tier_a_ndax": tier_a, "with_history": sorted(C)}, "periods": {}}
    for name, (a, b) in SPLITS.items():
        t0, t1 = _t(a), _t(b)
        rep["periods"][name] = {"book": simulate(C, tier_a, inst, cost, t0, t1), "benchmarks": bench(C["BTC"], cost["BTC"], t0, t1)}
    out.mkdir(parents=True, exist_ok=True)
    (out / "book500_backtest.json").write_text(json.dumps(rep, indent=1))
    return rep


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "run":
        o = Path(os.path.expanduser(sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else "~/ananta_runs/book500"))
        r = run(o)
        for k, v in r["periods"].items():
            b = v["book"]
            print(k, {x: b[x] for x in ("from", "to", "end_cad", "return_pct", "max_fall_pct", "setup_trades", "setup_win_rate", "setup_avg_pct",
                                       "brakes_fired", "sizes_ok", "max_risk_pct_seen")}, v["benchmarks"])
