"""Explorer engine: Rulebook v0 (docs/RULEBOOK_V0.md) as one streaming engine for history replay AND live paper.

Pure Python (the Agent venv has no numpy). Feed it CLOSED candles in time order via `CoinEngine.on_bar`,
then call `CoinEngine.scan(T)` at every 15-minute close. Execution (fills, stops, targets, market exits)
happens on 5m bars. Every order, trade and exit carries the rule IDs and state values that produced it.

Laws: paper only; no orders anywhere; evidence class PAPER_EXPLORER.
"""
from __future__ import annotations

import hashlib
import math
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable

RULEBOOK = "rulebook.v0"
ENGINE_VERSION = "explorer.engine.v0.1"
EVIDENCE_CLASS = "PAPER_EXPLORER"
TF_S = {"5m": 300, "15m": 900, "30m": 1800, "1h": 3600, "4h": 14400, "1d": 86400}
ORDER_TF = ("5m", "15m", "30m", "1h", "4h", "1d")  # same close time: execute 5m first, then higher states
COINS = ["BTC", "ETH", "SOL", "ADA", "DOGE", "AVAX", "BCH", "LINK", "LTC", "XRP"]
NDAX_FEE = 0.0020
HALF_SPREAD = {"BTC": 0.00178, "ETH": 0.00084, "SOL": 0.00289, "ADA": 0.00273, "DOGE": 0.00307,
               "AVAX": 0.00370, "BCH": 0.00400, "LINK": 0.00341, "LTC": 0.00334, "XRP": 0.00251}
DEFAULT_HS = 0.0040
EXPENSIVE_HS = 0.0030
NOTIONAL = 100.0
TYPES = ("LONG_TERM", "SHORT_TERM", "INTRADAY")
TIME_CAP = {"LONG_TERM": 60 * 86400, "SHORT_TERM": 5 * 86400, "INTRADAY": 8 * 3600}
ORDER_LIFE = {"LONG_TERM": 7200, "SHORT_TERM": 7200, "INTRADAY": 3600}   # N2
RANDOM_RATE = 0.02          # share of scans that create a random-entry shadow (baseline)
WARM = {"15m": 60, "30m": 40, "1h": 60, "4h": 55, "1d": 55}


# ---------------------------------------------------------------------------
# Incremental indicators (match pandas ewm(adjust=False))
# ---------------------------------------------------------------------------
class Ema:
    __slots__ = ("a", "v")

    def __init__(self, n: int):
        self.a, self.v = 2.0 / (n + 1), None

    def up(self, x: float) -> float:
        self.v = x if self.v is None else self.v + self.a * (x - self.v)
        return self.v


class Wilder:
    __slots__ = ("a", "v")

    def __init__(self, n: int = 14):
        self.a, self.v = 1.0 / n, None

    def up(self, x: float) -> float:
        self.v = x if self.v is None else self.v + self.a * (x - self.v)
        return self.v


def pct_rank(values, x) -> float:
    """Share of values <= x (0..1)."""
    if not values:
        return float("nan")
    return sum(1 for v in values if v <= x) / len(values)


class TfState:
    """Bars and indicators of one timeframe for one coin."""

    def __init__(self, tf: str):
        self.tf, self.step = tf, TF_S[tf]
        self.bars: deque = deque(maxlen=260)           # (t_open, o, h, l, c, v)
        self.n = 0
        self.ema20, self.ema50, self.ema25, self.ema30 = Ema(20), Ema(50), Ema(25), Ema(30)
        self.e20h: deque = deque(maxlen=8)
        self.e50h: deque = deque(maxlen=8)
        self.e25h: deque = deque(maxlen=8)
        self.e30h: deque = deque(maxlen=8)
        self.atr, self._pc = Wilder(14), None
        self.atrh: deque = deque(maxlen=50)
        self.rsi_up, self.rsi_dn, self.rsi = Wilder(14), Wilder(14), None
        self.rsih: deque = deque(maxlen=4)
        self.bbw: deque = deque(maxlen=100)            # 1h Bollinger width history (I3)
        self.bb_upper = None
        self.contracted: deque = deque(maxlen=13)      # I3 flag per bar
        self.roc: deque = deque(maxlen=200)            # I2
        self.volh: deque = deque(maxlen=21)

    def add(self, t, o, h, lo, c, v):
        self.bars.append((t, o, h, lo, c, v))
        self.n += 1
        self.e20h.append(self.ema20.up(c))
        self.e50h.append(self.ema50.up(c))
        self.e25h.append(self.ema25.up(c))
        self.e30h.append(self.ema30.up(c))
        pc = self._pc if self._pc is not None else c
        tr = max(h - lo, abs(h - pc), abs(lo - pc))
        self.atrh.append(self.atr.up(tr))
        d = c - pc
        u, dn = self.rsi_up.up(max(d, 0.0)), self.rsi_dn.up(max(-d, 0.0))
        self.rsi = 100.0 if dn <= 0 else 100.0 - 100.0 / (1.0 + u / dn)
        self.rsih.append(self.rsi)
        self._pc = c
        self.volh.append(v)
        if self.tf == "1h":
            closes = [b[4] for b in list(self.bars)[-20:]]
            if len(closes) == 20:
                m = sum(closes) / 20
                sd = math.sqrt(sum((x - m) ** 2 for x in closes) / 20)
                self.bb_upper = m + 2 * sd
                w = 4 * sd / m if m else 0.0
                self.bbw.append(w)
                a_now = self.atrh[-1]
                a_mean = sum(self.atrh) / len(self.atrh)
                con = (len(self.bbw) >= 50 and pct_rank(list(self.bbw), w) <= 0.20) or (len(self.atrh) >= 50 and a_now < 0.8 * a_mean)
                self.contracted.append(bool(con))
            if len(self.bars) > 12:
                self.roc.append(c / self.bars[-13][4] - 1.0)

    # helpers
    @property
    def last(self):
        return self.bars[-1] if self.bars else None

    @property
    def close_t(self) -> int:
        return self.bars[-1][0] + self.step if self.bars else -1

    def ema_ago(self, which: str, k: int):
        h = {"20": self.e20h, "50": self.e50h, "25": self.e25h, "30": self.e30h}[which]
        return h[-1 - k] if len(h) > k else None

    def vol_ratio(self) -> float | None:
        if len(self.volh) < 21:
            return None
        prev = list(self.volh)[:-1]
        m = sum(prev) / len(prev)
        return self.volh[-1] / m if m > 0 else None


# ---------------------------------------------------------------------------
# Orders, trades, exit variants
# ---------------------------------------------------------------------------
@dataclass
class Variant:
    name: str
    typ: str
    stop: float | None
    target: float | None
    R: float
    trail: bool = False
    bells: bool = True                 # HOLD variant: no stop / warning / profit, time cap only
    exit_px: float | None = None
    exit_t: int | None = None
    exit_bell: str | None = None
    exit_kind: str | None = None       # LIMIT | MARKET
    pending_market: str | None = None  # bell id to execute at the next 5m open
    hi_close: float = 0.0
    mfe: float = 0.0
    mae: float = 0.0

    @property
    def done(self) -> bool:
        return self.exit_px is not None


@dataclass
class Order:
    id: str
    coin: str
    setup: str
    typ: str
    limit: float
    placed_t: int
    expires_t: int
    tags: dict
    atr15: float
    atr1h: float
    atr4h: float
    support_low: float | None
    resistance_low: float | None
    shadow: str | None = None          # None = real; else RANDOM / NO_TYPE / REJECTED_SLOT / REJECTED_DUP / CAP
    chase: "Trade | None" = None       # MISSED shadow: bought at market at placement


@dataclass
class Trade:
    id: str
    coin: str
    setup: str
    typ: str
    entry: float
    entry_t: int
    entry_kind: str                    # LIMIT | MARKET
    fill_intrabar: bool
    fill_bar_t: int
    tags: dict
    variants: dict = field(default_factory=dict)
    shadow: str | None = None
    order_id: str | None = None

    @property
    def actual(self) -> Variant:
        return self.variants["ACTUAL"]


def cost_side(coin: str, kind: str) -> float:
    return NDAX_FEE if kind == "LIMIT" else NDAX_FEE + HALF_SPREAD.get(coin, DEFAULT_HS)


def net_usd(tr: Trade, v: Variant) -> float:
    g = v.exit_px / tr.entry - 1.0
    return NOTIONAL * (g - cost_side(tr.coin, tr.entry_kind) - (1 + g) * cost_side(tr.coin, v.exit_kind))


def make_variants(typ: str, entry: float, o: Order, full: bool = True) -> dict[str, Variant]:
    """ACTUAL (assigned type); for real trades also AS_<type> for all three types (the other types' exits)
    and HOLD (time cap only, no bells: what the bells saved). Shadows carry ACTUAL only."""
    out = {}
    for name, t in [("ACTUAL", typ)] + ([(f"AS_{x}", x) for x in TYPES] if full else []):
        if t == "LONG_TERM":
            st = entry - 3.0 * o.atr1h
            if o.support_low is not None:
                st = min(st, o.support_low)
            R = entry - st
            v = Variant(name, t, st, None, R, trail=True)
        elif t == "SHORT_TERM":
            st = entry - 2.0 * o.atr1h
            R = entry - st
            tg = entry + 2 * R
            if o.resistance_low is not None and o.resistance_low > entry:
                tg = min(tg, o.resistance_low)
            v = Variant(name, t, st, tg, R)
        else:
            dist = max(1.2 * o.atr15, 0.006 * entry)
            st = entry - dist
            R = dist
            tg = entry + 1.5 * R
            if o.resistance_low is not None and o.resistance_low > entry:
                tg = min(tg, o.resistance_low)
            tg = max(tg, entry * 1.012)
            v = Variant(name, t, st, tg, R)
        v.hi_close = entry
        out[name] = v
    if full:
        out["HOLD"] = Variant("HOLD", typ, None, None, out["ACTUAL"].R, bells=False, hi_close=entry)
    return out


# ---------------------------------------------------------------------------
# Coin engine
# ---------------------------------------------------------------------------
class CoinEngine:
    def __init__(self, coin: str, *, trade_from_t: int = 0, btc_ctx: Callable[[int], dict] | None = None,
                 slot_ok: Callable[[str, str], bool] | None = None, on_event: Callable[[dict], None] | None = None,
                 random_rate: float = RANDOM_RATE):
        self.coin = coin
        self.tf = {k: TfState(k) for k in TF_S}
        self.trade_from_t = trade_from_t
        self.btc_ctx = btc_ctx or (lambda t: {})
        self.slot_ok = slot_ok or (lambda coin, typ: True)   # portfolio caps (N4); live passes the account check
        self.on_event = on_event or (lambda e: None)
        self.random_rate = random_rate
        self.orders: list[Order] = []
        self.trades: list[Trade] = []          # open (real + shadow)
        self.closed: list[Trade] = []
        self.missed: list[Order] = []
        self.pivots: deque = deque()           # (t_close, price, kind) confirmed 1h swings
        self.day_open: float | None = None
        self.green_run = 0
        self.last_scan = None
        self._seq = 0

    # ---- data in ----
    def on_bar(self, tf: str, bar) -> None:
        t, o, h, lo, c, v = bar
        s = self.tf[tf]
        if s.bars and t <= s.bars[-1][0]:
            return  # duplicate / out of order: ignore
        if tf == "5m":
            self._execute(bar)
            self.green_run = self.green_run + 1 if c > o else 0
        s.add(t, o, h, lo, c, v)
        if tf == "1h":
            if t % 86400 == 0:
                self.day_open = o
            self._update_pivots()

    def _update_pivots(self) -> None:
        b = list(self.tf["1h"].bars)
        if len(b) >= 7:
            k = len(b) - 4
            mid = b[k]
            left, right = b[k - 3:k], b[k + 1:k + 4]
            if all(x[3] > mid[3] for x in left + right):
                self.pivots.append((mid[0] + 3600, mid[3], "LOW"))
            if all(x[2] < mid[2] for x in left + right):
                self.pivots.append((mid[0] + 3600, mid[2], "HIGH"))
        horizon = self.tf["1h"].close_t - 10 * 86400
        while self.pivots and self.pivots[0][0] < horizon:
            self.pivots.popleft()

    # ---- levels ----
    def levels(self) -> tuple[list[float], list[float]]:
        sup = [p for _, p, k in self.pivots if k == "LOW"]
        res = [p for _, p, k in self.pivots if k == "HIGH"]
        d = self.tf["1d"].last
        if d:
            sup.append(d[3])
            res.append(d[2])
        if self.day_open:
            sup.append(self.day_open)
            res.append(self.day_open)
        return sup, res

    def zones(self, price: float):
        a = self.tf["1h"].atrh[-1] if self.tf["1h"].atrh else 0.0
        w = 0.25 * a
        sup, res = self.levels()
        below = [x for x in sup if x - w <= price]
        sup_z = max(below) if below else None                    # nearest support level at/below price (+zone)
        above = [x for x in res if x - w > price]
        res_z = min(above) if above else None                    # nearest resistance level above price
        in_sup = [x for x in sup if x - w <= price <= x + w]
        return {"w": w, "support": sup_z, "support_low": (sup_z - w) if sup_z is not None else None,
                "resistance": res_z, "resistance_low": (res_z - w) if res_z is not None else None,
                "in_support": bool(in_sup), "res_levels": res}

    # ---- state ----
    def ready(self) -> bool:
        return all(self.tf[k].n >= n for k, n in WARM.items())

    def stale(self, T: int) -> list[str]:
        return [k for k in ("15m", "30m", "1h", "4h", "1d") if T - self.tf[k].close_t > 2 * TF_S[k]]

    def state(self, T: int) -> dict:
        h1, m15, m30, h4, d1 = (self.tf[k] for k in ("1h", "15m", "30m", "4h", "1d"))
        c1 = h1.last[4]
        e50, e50_5 = h1.e50h[-1], h1.ema_ago("50", 5)
        e20, e20_3 = h1.e20h[-1], h1.ema_ago("20", 3)
        e25, e25_3 = h1.e25h[-1], h1.ema_ago("25", 3)
        S1 = "BULL" if c1 > e50 and e50 > e50_5 else "BEAR" if c1 < e50 and e50 < e50_5 else "NEUTRAL"
        S2 = "UP" if c1 > e20 and e20 > e20_3 else "DOWN" if c1 < e20 and e20 < e20_3 else "FLAT"
        S2b = "UP" if c1 > e25 and e25 > e25_3 else "DOWN" if c1 < e25 and e25 < e25_3 else "FLAT"
        # S3 / S4 on 15m, confirmation on 30m
        b15 = m15.bars
        c15, pc15 = b15[-1][4], b15[-2][4]
        e15, pe15, e15_3 = m15.e20h[-1], m15.ema_ago("20", 1), m15.ema_ago("20", 3)
        cross_up = pc15 <= pe15 and c15 > e15 and e15 > e15_3
        cross_dn = pc15 >= pe15 and c15 < e15 and e15 < e15_3
        b30 = list(m30.bars)[-5:]
        e30s = list(m30.e30h)[-5:]
        above30 = b30[-1][4] > e30s[-1]
        crossed30 = any(b30[i - 1][4] <= e30s[i - 1] and b30[i][4] > e30s[i] for i in range(1, len(b30)))
        below30 = b30[-1][4] < e30s[-1]
        crossed30d = any(b30[i - 1][4] >= e30s[i - 1] and b30[i][4] < e30s[i] for i in range(1, len(b30)))
        S3 = ("S3_CONFIRMED" if (above30 or crossed30) else "S3_EARLY") if cross_up else None
        S4 = ("S4_CONFIRMED" if (below30 or crossed30d) else "S4_EARLY") if cross_dn else None
        # S4 on 30m for SHORT_TERM warning
        c30, pc30 = b30[-1][4], b30[-2][4]
        s4_30 = pc30 >= e30s[-2] and c30 < e30s[-1] and m30.e30h[-1] < (m30.ema_ago("30", 3) or m30.e30h[-1])
        c4 = h4.last[4]
        tr4 = "UP" if c4 > h4.e50h[-1] and h4.e20h[-1] > h4.e50h[-1] else "DOWN" if c4 < h4.e50h[-1] and h4.e20h[-1] < h4.e50h[-1] else "FLAT"
        d_above50 = d1.last[4] > d1.e50h[-1]
        roc_pct = pct_rank(list(h1.roc), h1.roc[-1]) if len(h1.roc) >= 50 else None
        z = self.zones(c15)
        hs = HALF_SPREAD.get(self.coin, DEFAULT_HS)
        btc = self.btc_ctx(T) if self.coin != "BTC" else {"btc_S1": S1, "btc_S2": S2, "btc_1h_ret": h1.last[4] / h1.last[1] - 1}
        return {
            "S1": S1, "S2": S2, "S2b": S2b, "S3": S3, "S4_15m": S4, "S4_30m": bool(s4_30),
            "trend_4h": tr4, "daily_above_ema50": d_above50,
            "btc_S1": btc.get("btc_S1"), "btc_S2": btc.get("btc_S2"), "btc_1h_ret": btc.get("btc_1h_ret"),
            "rsi15": m15.rsi, "rsi15_prev": m15.rsih[-2] if len(m15.rsih) > 1 else None,
            "rsi15_min3": min(list(m15.rsih)[-3:]), "rsi1h": h1.rsi,
            "roc_pct": roc_pct, "contracted_now": h1.contracted[-1] if h1.contracted else False,
            "contracted_12h": any(list(h1.contracted)[-13:-1]) if len(h1.contracted) > 1 else False,
            "contracted_prev": h1.contracted[-2] if len(h1.contracted) > 1 else False,
            "vol1h": h1.vol_ratio(), "vol15": m15.vol_ratio(),
            "green_run_5m": self.green_run, "hour_utc": (T % 86400) // 3600,
            "c15": c15, "c1h": c1, "ema20_1h": e20, "ema50_1h": e50, "ema20_15": e15, "ema20_d": d1.e20h[-1],
            "atr15": m15.atrh[-1], "atr1h": h1.atrh[-1], "atr4h": h4.atrh[-1],
            "bb_upper_1h": h1.bb_upper, "zones": z, "expensive": hs > EXPENSIVE_HS,
            "h1_closed_now": T % 3600 == 0, "d1_closed_now": T % 86400 == 0,
        }

    # ---- setups (E rules) ----
    def setups(self, st: dict) -> list[tuple[str, float, dict]]:
        out = []
        m15 = self.tf["15m"]
        last4 = list(m15.bars)[-4:]
        low4 = min(b[3] for b in last4)
        z = st["zones"]
        touched_ema = low4 <= st["ema20_1h"]
        touched_sup = z["support"] is not None and low4 <= z["support"] + z["w"]
        lim_rev = st["c15"] - 0.25 * st["atr15"]
        if st["S1"] == "BULL" and (touched_ema or touched_sup) and 35 <= st["rsi1h"] <= 55 and st["S3"]:
            out.append(("E1", lim_rev, {"touch": "EMA20_1h" if touched_ema else "SUPPORT"}))
        if st["h1_closed_now"] and st["vol1h"] is not None and st["vol1h"] >= 1.5 and st["contracted_12h"]:
            h1 = self.tf["1h"]
            c1, pc1 = h1.bars[-1][4], h1.bars[-2][4]
            broke = [x for x in z["res_levels"] if pc1 <= x + z["w"] < c1]
            if broke:
                lvl = max(broke)
                out.append(("E2", lvl + z["w"], {"level": lvl}))
        in_sup = z["in_support"] or touched_sup
        if in_sup and st["rsi15_min3"] < 35 and st["rsi15_prev"] is not None and st["rsi15"] > st["rsi15_prev"] and st["S3"]:
            out.append(("E3", lim_rev, {}))
        prev15 = m15.bars[-2]
        if (st["S1"] == "BULL" and st["S2"] == "UP" and st["roc_pct"] is not None and st["roc_pct"] >= 0.70
                and 55 <= st["rsi1h"] <= 70 and prev15[3] <= m15.ema_ago("20", 1) and st["c15"] > st["ema20_15"]):
            out.append(("E4", st["ema20_15"], {}))
        if (st["h1_closed_now"] and st["contracted_prev"] and st["bb_upper_1h"] is not None
                and st["c1h"] > st["bb_upper_1h"] and st["S2"] != "DOWN"):
            out.append(("E5", st["c1h"] - 0.25 * st["atr1h"], {}))
        return out

    # ---- trade type (G rules) ----
    @staticmethod
    def room(st: dict, entry: float) -> float:
        r = st["zones"]["resistance_low"]
        return (r - entry) / entry if (r is not None and r > entry) else 0.05  # no level above: "open sky" = 5%

    def trade_type(self, setup: str, st: dict, entry: float) -> tuple[str | None, str]:
        room = self.room(st, entry)
        if st["S1"] == "BULL" and st["trend_4h"] == "UP" and st["daily_above_ema50"] and setup in ("E1", "E4", "E5", "RND"):
            return "LONG_TERM", "G1"
        if st["S1"] in ("BULL", "NEUTRAL") and room >= 0.03:
            return "SHORT_TERM", "G2"
        if 0.012 <= room < 0.03 or (setup == "E3" and st["S1"] == "BEAR"):
            return "INTRADAY", "G3"
        return None, "NO_TYPE"

    def _busy(self, typ: str) -> bool:
        return any(o.typ == typ and o.shadow is None for o in self.orders) or any(
            t.typ == typ and t.shadow is None for t in self.trades)

    def _id(self, T: int, tag: str) -> str:
        self._seq += 1
        return f"{self.coin}-{T}-{tag}-{self._seq}"

    def _tags(self, st: dict) -> dict:
        keep = ("S1", "S2", "S2b", "S3", "trend_4h", "daily_above_ema50", "btc_S1", "btc_S2", "rsi15", "rsi1h", "roc_pct",
                "contracted_now", "contracted_12h", "vol1h", "vol15", "green_run_5m", "hour_utc", "expensive")
        t = {k: (round(v, 4) if isinstance(v, float) else v) for k, v in st.items() if k in keep}
        t["in_support"] = st["zones"]["in_support"]
        return t

    def _place(self, T, setup, typ, limit, st, extra, shadow=None) -> Order:
        z = st["zones"]
        tags = self._tags(st) | extra | {"room": round(self.room(st, limit), 4), "type_rule": extra.get("type_rule")}
        o = Order(self._id(T, setup), self.coin, setup, typ, limit, T, T + ORDER_LIFE[typ], tags, st["atr15"], st["atr1h"],
                  st["atr4h"], z["support_low"] if (setup in ("E1", "E3") and z["support"] is not None) else None,
                  z["resistance_low"], shadow)
        # MISSED shadow (real orders only): the same trade bought at market at the next 5m open
        o.chase = "PENDING" if shadow is None else None
        self.orders.append(o)
        self.on_event({"kind": "ORDER", "t": T, "coin": self.coin, "id": o.id, "setup": setup, "type": typ,
                       "limit": limit, "shadow": shadow, "tags": tags})
        return o

    # ---- the scan ----
    def scan(self, T: int) -> dict:
        """Run at every 15m close T, after all bars closing at T were fed. Returns the decision record."""
        rec: dict[str, Any] = {"t": T, "coin": self.coin, "rulebook": RULEBOOK, "engine": ENGINE_VERSION}
        if not self.ready():
            rec["skip"] = "WARMING_UP"
            return rec
        stale = self.stale(T)
        st = self.state(T)
        rec["state"] = self._tags(st)
        # bells for open trades (X2 -> X3 -> X4 trail -> X5)
        self._bells(T, st)
        if T < self.trade_from_t:
            rec["skip"] = "BEFORE_TRADE_FROM"
            return rec
        if stale:
            rec["skip"] = f"STALE:{','.join(stale)}"   # U4: no new entries, trades still managed
            return rec
        fired = self.setups(st)
        rec["setups"] = [f[0] for f in fired]
        cands = []
        for setup, limit, extra in fired:
            typ, grule = self.trade_type(setup, st, limit)
            cands.append((setup, limit, extra | {"type_rule": grule}, typ))
        taken = None
        real = [c for c in cands if c[3] is not None and not self._busy(c[3])]
        if real:
            taken = max(real, key=lambda c: self.room(st, c[1]))
            if self.slot_ok(self.coin, taken[3]):
                self._place(T, taken[0], taken[3], taken[1], st, taken[2])
            else:
                self._place(T, taken[0], taken[3], taken[1], st, taken[2], shadow="CAP")
        for c in cands:
            if taken is not None and c is taken:
                continue
            why = "NO_TYPE" if c[3] is None else ("REJECTED_SLOT" if self._busy(c[3]) else "REJECTED_DUP")
            self._place(T, c[0], c[3] or "SHORT_TERM", c[1], st, c[2], shadow=why)
        rec["candidates"] = [{"setup": c[0], "type": c[3], "rule": c[2].get("type_rule")} for c in cands]
        # random-entry baseline (shadow, deterministic)
        h = int(hashlib.sha1(f"{self.coin}:{T}".encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
        if h < self.random_rate:
            lim = st["c15"] - 0.25 * st["atr15"]
            typ, grule = self.trade_type("RND", st, lim)
            self._place(T, "RND", typ or "SHORT_TERM", lim, st, {"type_rule": grule}, shadow="RANDOM")
        self.last_scan = T
        return rec

    def _bells(self, T: int, st: dict) -> None:
        m15 = self.tf["15m"].bars[-1]
        drop15 = (m15[1] - m15[4]) >= 3.0 * st["atr1h"]
        btc_crash = st["h1_closed_now"] and st.get("btc_1h_ret") is not None and st["btc_1h_ret"] <= -0.04
        for tr in self.trades:
            for v in tr.variants.values():
                if v.done or v.pending_market:
                    continue
                v.hi_close = max(v.hi_close, st["c15"])
                if T - tr.entry_t >= TIME_CAP[v.typ]:
                    v.pending_market = "X5_TIME"
                    continue
                if not v.bells:
                    continue
                if drop15 or btc_crash:
                    v.pending_market = "X2_BTC_CRASH" if btc_crash else "X2_COIN_CRASH"
                    continue
                if v.typ == "LONG_TERM":
                    if st["d1_closed_now"] and self.tf["1d"].last[4] < st["ema20_d"]:
                        v.pending_market = "X3_DAILY_EMA20"
                        continue
                    if v.hi_close >= tr.entry + 2 * v.R:
                        v.stop = max(v.stop, v.hi_close - 2.5 * st["atr4h"])
                elif v.typ == "SHORT_TERM":
                    if st["h1_closed_now"] and st["c1h"] < st["ema50_1h"]:
                        v.pending_market = "X3_1H_EMA50"
                        continue
                    if st["S4_30m"] and T % 1800 == 0 and st["c15"] < tr.entry + v.R:
                        v.pending_market = "X3_S4_30M"
                        continue
                else:
                    if st["S4_15m"]:
                        v.pending_market = "X3_S4_15M"
                        continue
                    if T - tr.entry_t >= 4 * 3600 and v.hi_close < tr.entry + 0.3 * v.R:
                        v.pending_market = "X3_NO_PROGRESS"
                        continue

    # ---- execution on 5m bars ----
    def _execute(self, bar) -> None:
        t, o, h, lo, c, v = bar
        # 1) exits of open trades (orders placed at T only act on bars opening at/after T)
        still = []
        for tr in self.trades:
            for var in tr.variants.values():
                if var.done or t < tr.fill_bar_t:
                    continue
                fill_bar = t == tr.fill_bar_t
                if var.pending_market:
                    self._exit(tr, var, o, t, var.pending_market, "MARKET")
                    continue
                if not fill_bar:
                    if var.stop is not None and o <= var.stop:
                        self._exit(tr, var, o, t, "X1_STOP_GAP", "MARKET")
                        continue
                    if var.target is not None and o >= var.target:
                        self._exit(tr, var, o, t, "X4_TARGET_GAP", "LIMIT")
                        continue
                if var.stop is not None and lo <= var.stop:
                    self._exit(tr, var, var.stop, t, "X1_STOP" if not var.trail or var.stop < tr.entry else "X4_TRAIL", "MARKET")
                    continue
                if var.target is not None and h >= var.target and not (fill_bar and tr.fill_intrabar):
                    self._exit(tr, var, var.target, t, "X4_TARGET", "LIMIT")
                    continue
                var.mfe = max(var.mfe, h / tr.entry - 1)
                var.mae = min(var.mae, lo / tr.entry - 1)
            if all(x.done for x in tr.variants.values()):
                self.closed.append(tr)
                if tr.shadow is None:
                    a = tr.actual
                    self.on_event({"kind": "CLOSED", "t": a.exit_t, "coin": self.coin, "id": tr.id, "setup": tr.setup,
                                   "type": tr.typ, "bell": a.exit_bell, "net_usd": round(net_usd(tr, a), 4)})
            else:
                still.append(tr)
        self.trades = still
        # 2) fills of resting limits; MISSED chase shadows start at the first bar after placement
        keep = []
        for od in self.orders:
            if t < od.placed_t:
                keep.append(od)
                continue
            if od.chase == "PENDING":
                od.chase = self._open(od, o, t, "MARKET", False, shadow="MISSED_CHASE", register=False)
            filled = None
            if o <= od.limit:
                filled = (o, False)
            elif lo <= od.limit:
                filled = (od.limit, True)
            if filled:
                tr = self._open(od, filled[0], t, "LIMIT", filled[1], shadow=od.shadow)
                self._execute_fill_bar(tr, bar)
                continue
            if t + 300 >= od.expires_t:
                self.missed.append(od)
                if od.chase is not None and od.chase != "PENDING":
                    self.trades.append(od.chase)      # follow what chasing would have done
                if od.shadow is None:
                    self.on_event({"kind": "MISSED", "t": od.expires_t, "coin": self.coin, "id": od.id, "setup": od.setup, "type": od.typ})
                continue
            keep.append(od)
        self.orders = keep
        # chase shadows advance with the market while their order is still resting
        for od in self.orders:
            if isinstance(od.chase, Trade):
                self._advance_detached(od.chase, bar)

    def _advance_detached(self, tr: Trade, bar) -> None:
        """Move a not-yet-registered chase shadow through one bar (stops/targets only)."""
        t, o, h, lo, c, v = bar
        for var in tr.variants.values():
            if var.done or t < tr.fill_bar_t:
                continue
            fill_bar = t == tr.fill_bar_t   # bought at this bar's open: the stop can hit, the target cannot
            if var.stop is not None and (lo <= var.stop):
                self._exit(tr, var, o if (o <= var.stop and not fill_bar) else var.stop, t, "X1_STOP", "MARKET")
            elif var.target is not None and h >= var.target and not fill_bar:
                self._exit(tr, var, max(o, var.target), t, "X4_TARGET", "LIMIT")

    def _execute_fill_bar(self, tr: Trade, bar) -> None:
        t, o, h, lo, c, v = bar
        for var in tr.variants.values():
            if var.stop is not None and lo <= var.stop:
                self._exit(tr, var, var.stop, t, "X1_STOP", "MARKET")
            elif var.target is not None and h >= var.target and not tr.fill_intrabar:
                self._exit(tr, var, var.target, t, "X4_TARGET", "LIMIT")

    def _open(self, od: Order, px: float, t: int, kind: str, intrabar: bool, shadow=None, register=True) -> Trade:
        tr = Trade(od.id if register else od.id + "-chase", self.coin, od.setup, od.typ, px, t, kind, intrabar, t,
                   dict(od.tags), shadow=shadow or None, order_id=od.id)
        tr.variants = make_variants(od.typ, px, od, full=(shadow is None and register))
        if register:
            self.trades.append(tr)
            if shadow is None:
                self.on_event({"kind": "FILLED", "t": t, "coin": self.coin, "id": tr.id, "setup": tr.setup, "type": tr.typ,
                               "entry": px, "stop": tr.actual.stop, "target": tr.actual.target})
        return tr

    def _exit(self, tr: Trade, v: Variant, px: float, t: int, bell: str, kind: str) -> None:
        v.exit_px, v.exit_t, v.exit_bell, v.exit_kind = px, t, bell, kind
        v.pending_market = None

    # ---- output ----
    def trade_rows(self) -> list[dict]:
        rows = []
        for tr in self.closed:
            row = {"id": tr.id, "coin": tr.coin, "setup": tr.setup, "type": tr.typ, "shadow": tr.shadow or "",
                   "entry": tr.entry, "entry_t": tr.entry_t, "entry_kind": tr.entry_kind, **{f"tag_{k}": v for k, v in tr.tags.items()}}
            for name, v in tr.variants.items():
                row[f"{name}_net"] = round(net_usd(tr, v), 4)
                row[f"{name}_bell"] = v.exit_bell
                row[f"{name}_exit_t"] = v.exit_t
                row[f"{name}_R"] = round((v.exit_px - tr.entry) / v.R, 3) if v.R > 0 else None
            a = tr.actual
            row["mfe"], row["mae"] = round(a.mfe, 5), round(a.mae, 5)
            rows.append(row)
        return rows
