"""SD6 — paper exit/risk manager attached to paper fills.

Granted 2026-09-29 by operator sentence: "attach SD6 to paper fills".

What this is
------------
A paper position book plus an exit manager for the Agent's paper TAKEs.
Before SD6 a paper TAKE recorded a $100 "position" with no entry price, no
stop and no exit, so nothing could ever close it. SD6 gives every paper fill:

  * a priced entry (close of the last closed 1h bar + 8bp haircut),
  * the Hands exit engine's modules, evaluated on closed 1h bars,
  * a shadow "Fixed % Target + Stop" exit on the same bars (never trades),
  * MFE / MAE / exit module / exit reason / P&L after haircut on close.

Parity
------
The exit modules are a port of Ananta ``backend/exit_engine.py`` (Hands is the
implementation of record — Law 11). Modules A, KILL, F, B, S, D, C, E, the
hunter/squeeze profiles, the RiskSettings defaults, the indicator math and the
single-pass priority arbitration are copied. Deviations, all deliberate:

  1. Bar-level, not tick-level. Hands watches every ~15s; SD6 sees closed 1h
     bars. Hard stops (A) and the ATR trail (C) are tested against the bar LOW
     using the state known BEFORE that bar (no lookahead) and fill at the stop
     level, or at the bar open when the bar gapped through it.
  2. Close-based modules (F, B, S, D, E, KILL) act at the bar close.
  3. A TIGHTEN from F takes effect from the next bar (Hands applies it on the
     next tick; within one bar we cannot know the order of high and low).
  4. Costs are the G8 8bp haircut on entry and exit, not Hands' taker fee.
  5. LONG only. Hands is spot; the App exit engine is long-only. A SHORT
     paper TAKE is refused and recorded, never silently flipped.

Known Hands behaviour kept on purpose (parity, not endorsement)
---------------------------------------------------------------
Module F rounds the floor to 8 dp. When that rounds DOWN, the stored floor is
below the desired floor, so F re-fires TIGHTEN on every later bar, and TIGHTEN
(P3) outranks B/S/D/C/E. In roughly half of trades that reach +1R, only A
(hard stop / floor) can then close the trade. Found 2026-09-29 by a
differential test against Hands; fixing it changes the live engine, so it is
an operator decision. SD6 matches Hands until Hands is fixed, so paper
evidence describes the engine that would go live.

Laws kept
---------
Never writes Mongo. Never calls /api/orders/manual. exec=False, live=False,
counts_for_m2=False (M2 credit needs its own operator sentence). One position,
$100 notional, $1,000 paper book. A fixture position is never written to the
live book. Missing bars are a DATA_STALE state, never an invented exit.
Live opening requires the fixture proof file (same rule as paper.path.v1).
"""
from __future__ import annotations

import json
import math
import sqlite3
import uuid
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

VERSION = "paper.exit.sd6.v1"
PORT_OF = "Ananta backend/exit_engine.py (A,KILL,F,B,S,D,C,E) @ 8cf4bcd"
BOOK_NAME = "paper_book.sqlite"
PROOF_NAME = "paper_exit_proof_v1.json"
HOUR_MS = 3_600_000

# Bar layout (same as Hands): [t_ms_open, open, high, low, close, volume]
_T, _O, _H, _L, _C, _V = 0, 1, 2, 3, 4, 5

ACT_NONE = "NONE"
ACT_EXIT_FULL = "EXIT_FULL"
ACT_EXIT_PARTIAL = "EXIT_PARTIAL"
ACT_TIGHTEN = "TIGHTEN"
PARTIAL_FRACTION = 0.5
PROFIT_FLOOR_PCT = 1.0


# ---------------------------------------------------------------------------
# Settings — Hands RiskSettings defaults (models.py) + G8 lab grant.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Sd6Settings:
    stop_loss_pct: float = 2.2
    trail_arm_pct: float = 1.6
    trail_distance_pct: float = 0.9
    profit_protection_enabled: bool = True
    structural_stop_enabled: bool = True
    ema_trend_loss_enabled: bool = True
    structure_failure_enabled: bool = True
    fixed_target_pct: float = 3.0  # shadow "Fixed % Target + Stop"
    haircut_bp: float = 8.0
    notional_usd: float = 100.0
    starting_cash: float = 1000.0
    max_open: int = 1
    stale_after_bars: int = 3  # no new closed bar for > N hours = DATA_STALE


SETTINGS = Sd6Settings()


@dataclass(frozen=True)
class StrategyProfile:
    name: str
    profit_arm_pct: float
    trail_atr_mult: float
    time_exit_hours: float | None
    ema_priority: bool = False
    ema_settle_hours: float = 6.0
    breakeven_r: float = 1.0
    trail_arm_r: float = 2.0
    structure_exit: bool = True
    structural_stop_enabled: bool = True
    ema_trend_loss_enabled: bool = True


PROFILES: dict[str, StrategyProfile] = {
    "hunter": StrategyProfile("hunter", 5.0, 2.0, 72.0),
    "squeeze": StrategyProfile("squeeze", 4.0, 2.5, None, ema_priority=True, ema_settle_hours=2.0),
}


def profile_for(core: str | None, settings: Sd6Settings = SETTINGS) -> StrategyProfile:
    prof = PROFILES.get((core or "hunter").lower(), PROFILES["hunter"])
    return replace(
        prof,
        structural_stop_enabled=settings.structural_stop_enabled,
        ema_trend_loss_enabled=settings.ema_trend_loss_enabled,
        structure_exit=settings.structure_failure_enabled,
    )


# ---------------------------------------------------------------------------
# Indicators — copied from Hands setup_classifier.py.
# ---------------------------------------------------------------------------
def ema(values: list[float], period: int) -> list[float]:
    if not values:
        return []
    alpha = 2.0 / (period + 1)
    out = [float(values[0])]
    for v in values[1:]:
        out.append(alpha * float(v) + (1 - alpha) * out[-1])
    return out


def rsi(closes: list[float], period: int = 14) -> list[float]:
    if len(closes) < period + 1:
        return []
    gains, losses = [], []
    for i in range(1, len(closes)):
        ch = closes[i] - closes[i - 1]
        gains.append(max(ch, 0.0))
        losses.append(max(-ch, 0.0))

    def _r(ag: float, al: float) -> float:
        if al == 0:
            return 100.0
        return 100.0 - 100.0 / (1.0 + ag / al)

    ag = sum(gains[:period]) / period
    al = sum(losses[:period]) / period
    out = [_r(ag, al)]
    for i in range(period, len(gains)):
        ag = (ag * (period - 1) + gains[i]) / period
        al = (al * (period - 1) + losses[i]) / period
        out.append(_r(ag, al))
    return out


def atr(highs: list[float], lows: list[float], closes: list[float], period: int = 14) -> list[float]:
    tr = []
    for i in range(len(highs)):
        if i == 0:
            tr.append(highs[i] - lows[i])
        else:
            pc = closes[i - 1]
            tr.append(max(highs[i] - lows[i], abs(highs[i] - pc), abs(lows[i] - pc)))
    if not tr:
        return []
    out = [tr[0]]
    for i in range(1, len(tr)):
        if i < period:
            out.append(sum(tr[: i + 1]) / (i + 1))
        else:
            out.append((out[-1] * (period - 1) + tr[i]) / period)
    return out


def indicators(bars: list[list[float]] | None) -> dict[str, Any]:
    n = len(bars or [])
    if n < 25:
        return {}
    closes = [b[_C] for b in bars]
    highs = [b[_H] for b in bars]
    lows = [b[_L] for b in bars]
    opens = [b[_O] for b in bars]
    vols = [b[_V] for b in bars]
    r = rsi(closes, 14)
    if not r:
        return {}
    ema20 = ema(closes, 20)[-1]
    ema50 = ema(closes, 50)[-1] if n >= 50 else ema20
    atr_last = atr(highs, lows, closes)[-1]
    vol_avg = sum(vols[-20:]) / 20.0
    o, h, l, c, v = opens[-1], highs[-1], lows[-1], closes[-1], vols[-1]
    rng = max(1e-12, h - l)
    upper_wick = h - max(o, c)
    close_pos = (c - l) / rng
    return {
        "rsi": round(r[-1], 2),
        "ema20": ema20,
        "ema50": ema50,
        "atr": atr_last,
        "vol_climax": bool(vol_avg > 0 and v >= 2.0 * vol_avg),
        "exhaustion_candle": bool(c < o or (upper_wick / rng >= 0.5 and close_pos <= 0.45)),
        "last_close": c,
    }


# ---------------------------------------------------------------------------
# Position helpers
# ---------------------------------------------------------------------------
def _risk_per_unit(pos: dict, s: Sd6Settings) -> float:
    ss = pos.get("structural_stop")
    if ss and ss < pos["entry_fill"]:
        return pos["entry_fill"] - ss
    return max(1e-9, pos["entry_fill"] * s.stop_loss_pct / 100.0)


def _hard_stop_levels(pos: dict, prof: StrategyProfile, s: Sd6Settings) -> list[tuple[float, str]]:
    levels = [(pos["entry_fill"] * (1.0 - s.stop_loss_pct / 100.0), "STOP_LOSS")]
    if pos.get("structural_stop") and prof.structural_stop_enabled:
        levels.append((float(pos["structural_stop"]), "STRUCTURAL_STOP"))
    if pos.get("locked_floor"):
        levels.append((float(pos["locked_floor"]), "PROFIT_FLOOR"))
    return levels


def _haircut(price: float, side: str, s: Sd6Settings) -> float:
    k = s.haircut_bp / 10_000.0
    return price * (1.0 + k) if side == "BUY" else price * (1.0 - k)


def _iso(ms: float) -> str:
    return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# One closed bar through the exit modules (ported arbitration).
# ---------------------------------------------------------------------------
def evaluate_bar(pos: dict, history: list[list[float]], bar: list[float], *, emergency: bool = False, s: Sd6Settings = SETTINGS) -> dict[str, Any]:
    """Evaluate one newly closed bar. ``history`` = closed bars BEFORE ``bar``.

    Returns {action, module, exit_reason, reason, price, fraction, new_floor, signals}.
    """
    prof = profile_for(pos.get("core"), s)
    entry = pos["entry_fill"]
    o, h, l, c = bar[_O], bar[_H], bar[_L], bar[_C]
    peak_before = max(pos.get("peak") or entry, entry)
    ind_before = indicators(history)
    ind_now = indicators(history + [bar])
    age_h = max(0.0, (bar[_T] + HOUR_MS - pos["entry_bar_close_ms"]) / HOUR_MS)
    R = _risk_per_unit(pos, s)
    signals: list[dict[str, Any]] = []

    # A — hard-stop bucket (intrabar, state known before this bar).
    breached = [(lvl, code) for lvl, code in _hard_stop_levels(pos, prof, s) if l <= lvl]
    if breached:
        lvl, code = max(breached, key=lambda x: x[0])
        signals.append({"priority": 1, "module": "A", "action": ACT_EXIT_FULL, "exit_reason": code,
                        "reason": f"{code}: low {l:.8g} <= {lvl:.8g}", "price": min(lvl, o)})
    # KILL — emergency stop at the close.
    if emergency:
        signals.append({"priority": 2, "module": "KILL", "action": ACT_EXIT_FULL, "exit_reason": "EMERGENCY_STOP",
                        "reason": "manual kill switch (Hands emergency rule)", "price": c})
    # F — profit protection (upgrade-only floor, effective next bar).
    if s.profit_protection_enabled:
        peak = max(peak_before, h)
        mfe_pct = (peak - entry) / entry * 100.0
        mfe_r = (peak - entry) / R if R > 0 else 0.0
        cands = []
        if mfe_r >= prof.breakeven_r:
            cands.append((entry, f"breakeven @ +{prof.breakeven_r:.2g}R"))
        if mfe_pct >= prof.profit_arm_pct:
            cands.append((entry * (1.0 + PROFIT_FLOOR_PCT / 100.0), f"+{PROFIT_FLOOR_PCT}% floor"))
        if cands:
            floor, why = max(cands, key=lambda x: x[0])
            cur = pos.get("locked_floor")
            if cur is None or cur < floor - 1e-12:
                signals.append({"priority": 3, "module": "F", "action": ACT_TIGHTEN, "exit_reason": "PROFIT_PROTECT",
                                "reason": f"MFE {mfe_pct:.2f}% ({mfe_r:.2f}R) lock {why}", "new_floor": round(floor, 8)})  # 8 dp = Hands
    # B — momentum exhaustion partial (once).
    if ind_now and not pos.get("momentum_partial_taken"):
        r = ind_now.get("rsi")
        climax, exh = ind_now.get("vol_climax"), ind_now.get("exhaustion_candle")
        if r is not None and ((r >= 80 and (climax or exh)) or (r >= 70 and climax and exh)):
            signals.append({"priority": 4, "module": "B", "action": ACT_EXIT_PARTIAL, "exit_reason": "MOMENTUM_EXHAUSTION",
                            "reason": f"RSI {r:.1f} climax={climax} exhaustion={exh}", "price": c, "fraction": PARTIAL_FRACTION})
    # S — structure failure.
    full = history + [bar]
    if prof.structure_exit and ind_now and age_h >= prof.ema_settle_hours and len(full) >= 12:
        lows = [b[_L] for b in full]
        dead = ind_now["rsi"] < 50.0 and ind_now["last_close"] < ind_now["ema20"]
        prior, recent = min(lows[-12:-3]), min(lows[-3:])
        pnl_pct = (c - entry) / entry * 100.0
        if recent < prior and dead and pnl_pct > -1.0:
            signals.append({"priority": 5, "module": "S", "action": ACT_EXIT_FULL, "exit_reason": "STRUCTURE_FAILURE",
                            "reason": f"lower-low {recent:.8g} < {prior:.8g}, momentum dead", "price": c})
    # D — EMA trend loss.
    if prof.ema_trend_loss_enabled and ind_now and age_h >= prof.ema_settle_hours:
        below = ind_now["last_close"] < ind_now["ema20"]
        dead_cross = ind_now["ema20"] < ind_now["ema50"]
        if (prof.ema_priority and below) or (not prof.ema_priority and below and dead_cross):
            signals.append({"priority": 5, "module": "D", "action": ACT_EXIT_FULL, "exit_reason": "EMA_TREND_LOSS",
                            "reason": f"close below 20-EMA{' + dead-cross' if dead_cross else ''}", "price": c})
    # C — ATR trail (armed from state before this bar, tested against the low).
    run_pct = (peak_before - entry) / entry * 100.0
    run_r = (peak_before - entry) / R if R > 0 else 0.0
    if run_r >= prof.trail_arm_r or run_pct >= s.trail_arm_pct:
        a = ind_before.get("atr") if ind_before else None
        trail = peak_before - prof.trail_atr_mult * a if a and a > 0 else peak_before * (1.0 - s.trail_distance_pct / 100.0)
        if l <= trail:
            signals.append({"priority": 6, "module": "C", "action": ACT_EXIT_FULL, "exit_reason": "ATR_TRAIL",
                            "reason": f"low {l:.8g} <= trail {trail:.8g}", "price": min(trail, o)})
    # E — time exit.
    pnl_pct = (c - entry) / entry * 100.0
    if age_h >= 48.0 and -0.4 <= pnl_pct <= 0.3:
        signals.append({"priority": 7, "module": "E", "action": ACT_EXIT_FULL, "exit_reason": "TIME_EXIT",
                        "reason": f"stagnant {age_h:.0f}h ({pnl_pct:+.2f}%)", "price": c})
    elif prof.time_exit_hours is not None and age_h >= prof.time_exit_hours:
        signals.append({"priority": 7, "module": "E", "action": ACT_EXIT_FULL, "exit_reason": "TIME_EXIT",
                        "reason": f"held {age_h:.0f}h >= {prof.time_exit_hours:.0f}h cap", "price": c})

    if not signals:
        return {"action": ACT_NONE, "signals": []}
    signals.sort(key=lambda x: x["priority"])
    win = dict(signals[0])
    win["signals"] = [{k: v for k, v in sg.items() if k in ("priority", "module", "action", "exit_reason")} for sg in signals]
    return win


# ---------------------------------------------------------------------------
# Shadow: Hands "Fixed % Target + Stop" on the same bars. Never trades.
# ---------------------------------------------------------------------------
def shadow_step(sh: dict, bar: list[float], s: Sd6Settings = SETTINGS) -> dict:
    if sh.get("status") != "OPEN":
        return sh
    sh = dict(sh)
    if bar[_L] <= sh["stop"]:
        px = min(sh["stop"], bar[_O])
        sh.update(status="CLOSED", exit_reason="STOP_LOSS", exit_ref=px)
    elif bar[_H] >= sh["target"]:
        px = max(sh["target"], bar[_O])
        sh.update(status="CLOSED", exit_reason="TARGET", exit_ref=px)
    if sh["status"] == "CLOSED":
        fill = _haircut(sh["exit_ref"], "SELL", s)
        sh["exit_fill"] = fill
        sh["exit_bar_open_ms"] = bar[_T]
        sh["pnl_usd"] = round(sh["qty"] * (fill - sh["entry_fill"]), 6)
    return sh


# ---------------------------------------------------------------------------
# Book (agent-side sqlite; never the Hands Mongo book).
# ---------------------------------------------------------------------------
class Book:
    def __init__(self, path: str | Path | None = None, *, fixture: bool = False):
        self.path = Path(path or BOOK_NAME)
        self.fixture = fixture
        self.con = sqlite3.connect(str(self.path))
        self.con.execute("CREATE TABLE IF NOT EXISTS positions (id TEXT PRIMARY KEY, status TEXT, asset TEXT, opened_at TEXT, payload_json TEXT)")
        self.con.execute("CREATE TABLE IF NOT EXISTS events (seq INTEGER PRIMARY KEY AUTOINCREMENT, pos_id TEXT, bar_open_ms REAL, kind TEXT, payload_json TEXT)")
        self.con.execute("CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT)")
        row = self.con.execute("SELECT v FROM meta WHERE k='kind'").fetchone()
        kind = "FIXTURE" if fixture else "LIVE_PAPER"
        if row is None:
            self.con.execute("INSERT INTO meta VALUES ('kind', ?)", (kind,))
            self.con.execute("INSERT INTO meta VALUES ('version', ?)", (VERSION,))
        elif row[0] != kind:
            self.con.close()
            raise ValueError(f"BOOK_KIND_MISMATCH:{row[0]}!={kind}")
        self.con.commit()

    def close(self) -> None:
        self.con.close()

    def save(self, pos: dict) -> None:
        self.con.execute("INSERT OR REPLACE INTO positions VALUES (?,?,?,?,?)",
                         (pos["id"], pos["status"], pos["asset"], pos["opened_at"], json.dumps(pos, default=str)))
        self.con.commit()

    def event(self, pos_id: str | None, bar_open_ms: float | None, kind: str, payload: dict) -> None:
        self.con.execute("INSERT INTO events (pos_id, bar_open_ms, kind, payload_json) VALUES (?,?,?,?)",
                         (pos_id, bar_open_ms, kind, json.dumps(payload, default=str)))
        self.con.commit()

    def open_positions(self) -> list[dict]:
        return [json.loads(r[0]) for r in self.con.execute("SELECT payload_json FROM positions WHERE status='OPEN' ORDER BY opened_at")]

    def all_positions(self) -> list[dict]:
        return [json.loads(r[0]) for r in self.con.execute("SELECT payload_json FROM positions ORDER BY opened_at")]

    def events(self, pos_id: str | None = None) -> list[dict]:
        q = "SELECT pos_id, bar_open_ms, kind, payload_json FROM events"
        rows = self.con.execute(q + (" WHERE pos_id=? ORDER BY seq" if pos_id else " ORDER BY seq"), ((pos_id,) if pos_id else ())).fetchall()
        return [{"pos_id": r[0], "bar_open_ms": r[1], "kind": r[2], **json.loads(r[3])} for r in rows]

    def ledger(self, s: Sd6Settings = SETTINGS) -> dict[str, Any]:
        pos = self.all_positions()
        closed = [p for p in pos if p["status"] == "CLOSED"]
        open_ = [p for p in pos if p["status"] == "OPEN"]
        realized = sum(p.get("realized_pnl_usd") or 0.0 for p in pos)
        reserved = sum(p["qty_open"] * p["entry_fill"] for p in open_)
        return {
            "id": "paper.ledger.sd6.v1",
            "version": VERSION,
            "book": "FIXTURE" if self.fixture else "LIVE_PAPER",
            "starting": s.starting_cash,
            "cash": round(s.starting_cash + realized - reserved, 6),
            "realized_pnl": round(realized, 6),
            "reserved_capital": round(reserved, 6),
            "open_positions": [{"id": p["id"], "asset": p["asset"], "core": p["core"], "entry_fill": p["entry_fill"],
                                "locked_floor": p.get("locked_floor"), "stale": p.get("stale")} for p in open_],
            "trade_count": len(closed),
            "wins": sum(1 for p in closed if (p.get("realized_pnl_usd") or 0) > 0),
            "losses": sum(1 for p in closed if (p.get("realized_pnl_usd") or 0) <= 0),
            "shadow_realized_pnl": round(sum((p.get("shadow") or {}).get("pnl_usd") or 0.0 for p in closed), 6),
            "exec": False, "live": False, "keep": False, "counts_for_m2": False,
        }


# ---------------------------------------------------------------------------
# Open / step / manage
# ---------------------------------------------------------------------------
def fixture_proven(proof_path: Path | None = None) -> bool:
    path = proof_path or Path(__file__).with_name(PROOF_NAME)
    try:
        proof = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return False
    return proof.get("status") == "FIXTURE_PASS" and proof.get("version") == VERSION


def open_from_take(book: Book, take: dict, bars: list[list[float]], *, s: Sd6Settings = SETTINGS, proof_path: Path | None = None) -> dict[str, Any]:
    """Open a priced paper position for a TAKE. ``bars`` = closed 1h bars, oldest first."""
    asset = take.get("asset")
    evidence = take.get("evidence_class") or ("FIXTURE" if book.fixture else "LIVE_PAPER")
    base = {"version": VERSION, "asset": asset, "core": take.get("core"), "decision_id": take.get("decision_id")}

    def refuse(reason: str) -> dict:
        out = {**base, "status": "REFUSED", "reason": reason}
        book.event(None, bars[-1][_T] if bars else None, "OPEN_REFUSED", out)
        return out

    if evidence == "FIXTURE" and not book.fixture:
        return refuse("FIXTURE_REFUSED_ON_LIVE_BOOK")
    if evidence != "FIXTURE" and book.fixture:
        return refuse("LIVE_REFUSED_ON_FIXTURE_BOOK")
    if not book.fixture and not fixture_proven(proof_path):
        return refuse("SD6_FIXTURE_NOT_PROVEN")
    if (take.get("core") or "") not in PROFILES:
        return refuse("CORE_NOT_PAPER_ELIGIBLE")
    direction = str(take.get("direction") or "NONE").upper()
    if direction == "SHORT":
        return refuse("SHORT_NOT_SUPPORTED_SPOT")
    if len(book.open_positions()) >= s.max_open:
        return refuse("SLOT_FULL")
    dbar = take.get("decision_bar_open_ms")
    if dbar is not None:
        try:
            dbar = float(dbar)
        except (TypeError, ValueError):
            return refuse("BAD_DECISION_BAR")
        bars = [b for b in bars if b[_T] <= dbar]
        if not bars or bars[-1][_T] != dbar:
            return refuse("DECISION_BAR_NOT_IN_CANDLES")
    if not bars:
        return refuse("NO_CLOSED_BARS")
    last = bars[-1]
    ref = float(last[_C])
    if not (ref > 0 and math.isfinite(ref)):
        return refuse("BAD_PRICE")
    fill = _haircut(ref, "BUY", s)
    qty = s.notional_usd / fill
    ss = take.get("structural_stop")
    ss = float(ss) if ss and 0 < float(ss) < fill else None
    stop_pct_level = fill * (1.0 - s.stop_loss_pct / 100.0)
    pos = {
        "id": f"sd6.{asset}.{int(last[_T])}.{uuid.uuid4().hex[:6]}",
        "version": VERSION,
        "status": "OPEN",
        "asset": asset,
        "core": take.get("core"),
        "card": take.get("card"),
        "direction": "LONG",
        "direction_in": direction,
        "cycle_id": take.get("cycle_id"),
        "decision_id": take.get("decision_id"),
        "evidence_class": evidence,
        "not_a_market_trade": evidence == "FIXTURE",
        "opened_at": _iso(last[_T] + HOUR_MS),
        "entry_bar_open_ms": last[_T],
        "entry_bar_close_ms": last[_T] + HOUR_MS,
        "entry_ref": ref,
        "entry_fill": fill,
        "qty": qty,
        "qty_open": qty,
        "notional_usd": s.notional_usd,
        "structural_stop": ss,
        "initial_stop": max(stop_pct_level, ss or 0.0),
        "risk_usd": round(qty * (fill - max(stop_pct_level, ss or 0.0)), 6),
        "peak": fill,
        "trough": fill,
        "locked_floor": None,
        "momentum_partial_taken": False,
        "last_bar_open_ms": last[_T],
        "bars_managed": 0,
        "realized_pnl_usd": 0.0,
        "stale": False,
        "profile": profile_for(take.get("core"), s).__dict__,
        "shadow": {"method": "FIXED_PCT_TARGET_STOP", "status": "OPEN", "entry_fill": fill, "qty": qty,
                   "stop": fill * (1.0 - s.stop_loss_pct / 100.0), "target": fill * (1.0 + s.fixed_target_pct / 100.0)},
        "exec": False, "live": False, "keep": False, "counts_for_m2": False, "authority_granted": False,
    }
    book.save(pos)
    book.event(pos["id"], last[_T], "OPENED", {"entry_ref": ref, "entry_fill": fill, "qty": qty, "initial_stop": pos["initial_stop"], "core": pos["core"]})
    return {**base, "status": "OPENED", "position_id": pos["id"], "entry_fill": fill, "initial_stop": pos["initial_stop"]}


def _close(book: Book, pos: dict, bar: list[float], win: dict, s: Sd6Settings) -> dict:
    fill = _haircut(float(win["price"]), "SELL", s)
    pnl = pos["qty_open"] * (fill - pos["entry_fill"])
    pos["realized_pnl_usd"] = round((pos.get("realized_pnl_usd") or 0.0) + pnl, 6)
    pos.update(status="CLOSED", qty_open=0.0, exit_fill=fill, exit_ref=float(win["price"]), exit_module=win["module"],
               exit_reason=win["exit_reason"], exit_detail=win.get("reason"), closed_at=_iso(bar[_T] + HOUR_MS),
               exit_bar_open_ms=bar[_T])
    pos["mfe_pct"] = round((pos["peak"] - pos["entry_fill"]) / pos["entry_fill"] * 100.0, 4)
    pos["mae_pct"] = round((pos["trough"] - pos["entry_fill"]) / pos["entry_fill"] * 100.0, 4)
    R = pos.get("risk_usd") or 0.0
    pos["r_multiple"] = round(pos["realized_pnl_usd"] / R, 4) if R > 0 else None
    pos["hold_hours"] = round((bar[_T] + HOUR_MS - pos["entry_bar_close_ms"]) / HOUR_MS, 2)
    pos["outcome"] = "WIN" if pos["realized_pnl_usd"] > 0 else "LOSS"
    book.event(pos["id"], bar[_T], "CLOSED", {k: pos.get(k) for k in ("exit_module", "exit_reason", "exit_fill", "realized_pnl_usd", "mfe_pct", "mae_pct", "r_multiple", "hold_hours", "outcome")})
    return pos


def step(book: Book, pos: dict, bars: list[list[float]], *, emergency: bool = False, now_ms: float | None = None, s: Sd6Settings = SETTINGS) -> dict[str, Any]:
    """Process every closed bar newer than the last one this position has seen."""
    events: list[dict] = []
    if pos["status"] != "OPEN":
        return {"id": pos["id"], "status": pos["status"], "events": events}
    new = [b for b in bars if b[_T] > pos["last_bar_open_ms"]]
    # Stale: no newer closed bar for too long. Never invent an exit.
    latest = max([b[_T] for b in bars] or [pos["last_bar_open_ms"]])
    if now_ms is not None:
        closed_age_bars = (now_ms - (latest + HOUR_MS)) / HOUR_MS
        stale = closed_age_bars > s.stale_after_bars
        if stale != bool(pos.get("stale")):
            pos["stale"] = stale
            book.event(pos["id"], latest, "DATA_STALE" if stale else "DATA_RESUMED", {"closed_age_bars": round(closed_age_bars, 2)})
            events.append({"kind": "DATA_STALE" if stale else "DATA_RESUMED"})
    for bar in new:
        history = [b for b in bars if b[_T] < bar[_T]]
        win = evaluate_bar(pos, history, bar, emergency=emergency, s=s)
        pos["peak"] = max(pos["peak"], bar[_H])
        pos["trough"] = min(pos["trough"], bar[_L])
        pos["last_bar_open_ms"] = bar[_T]
        pos["bars_managed"] = pos.get("bars_managed", 0) + 1
        pos["shadow"] = shadow_step(pos["shadow"], bar, s)
        act = win["action"]
        if act == ACT_TIGHTEN:
            pos["locked_floor"] = win["new_floor"]
            book.event(pos["id"], bar[_T], "TIGHTEN", {"new_floor": win["new_floor"], "reason": win.get("reason")})
            events.append({"kind": "TIGHTEN", "new_floor": win["new_floor"]})
        elif act == ACT_EXIT_PARTIAL:
            q = pos["qty_open"] * win.get("fraction", PARTIAL_FRACTION)
            fill = _haircut(float(win["price"]), "SELL", s)
            pos["realized_pnl_usd"] = round(pos["realized_pnl_usd"] + q * (fill - pos["entry_fill"]), 6)
            pos["qty_open"] -= q
            pos["momentum_partial_taken"] = True
            book.event(pos["id"], bar[_T], "PARTIAL", {"qty": q, "fill": fill, "reason": win.get("reason")})
            events.append({"kind": "PARTIAL", "fill": fill})
        elif act == ACT_EXIT_FULL:
            _close(book, pos, bar, win, s)
            events.append({"kind": "CLOSED", "module": win["module"], "exit_reason": win["exit_reason"], "pnl": pos["realized_pnl_usd"]})
            break
    book.save(pos)
    return {"id": pos["id"], "status": pos["status"], "events": events}


# ---------------------------------------------------------------------------
# Cycle integration
# ---------------------------------------------------------------------------
def _closed_only(bars: list[list[float]], now_ms: float) -> list[list[float]]:
    return [b for b in bars if b[_T] + HOUR_MS <= now_ms]


def fetch_bars_http(asset: str, limit: int = 120) -> list[list[float]]:
    """Closed-or-not 1h candles from Hands /api/market/candles (Agent -> Hands HTTP only)."""
    import requests

    from src.tools import ananta_api

    sym = asset if "/" in asset else f"{asset}/USD"
    tok = ananta_api.login()
    token = tok.get("token") if isinstance(tok, dict) else None
    r = requests.get(f"{ananta_api.BASE_URL}/api/market/candles", params={"symbol": sym, "timeframe": "1h", "limit": limit},
                     headers=ananta_api.get_headers(token), timeout=20)
    r.raise_for_status()
    return [[float(c["t"]), float(c["open"]), float(c["high"]), float(c["low"]), float(c["close"]), float(c["volume"])]
            for c in (r.json().get("candles") or [])]


def manage_cycle(takes: Iterable[dict], *, emergency_by_asset: dict[str, bool] | None = None,
                 fetch_bars: Callable[[str], list[list[float]]] = fetch_bars_http, now_ms: float | None = None,
                 book_path: str | Path | None = None, proof_path: Path | None = None, s: Sd6Settings = SETTINGS) -> dict[str, Any]:
    """Run once per cycle: manage the open position, then open any new TAKE if a slot is free.

    Managing first means a position closed on this bar frees its slot for a TAKE on the same bar.
    """
    now_ms = now_ms if now_ms is not None else datetime.now(timezone.utc).timestamp() * 1000.0
    emergency_by_asset = emergency_by_asset or {}
    book = Book(book_path)
    out: dict[str, Any] = {"version": VERSION, "managed": [], "opened": [], "refused": [], "errors": []}
    cache: dict[str, list[list[float]]] = {}

    def bars_for(asset: str) -> list[list[float]]:
        if asset not in cache:
            cache[asset] = _closed_only(sorted(fetch_bars(asset), key=lambda b: b[_T]), now_ms)
        return cache[asset]

    try:
        for pos in book.open_positions():
            try:
                res = step(book, pos, bars_for(pos["asset"]), emergency=bool(emergency_by_asset.get(pos["asset"])), now_ms=now_ms, s=s)
                out["managed"].append(res)
            except Exception as exc:  # never break the cycle; the gap is visible
                book.event(pos["id"], None, "MANAGE_ERROR", {"error": str(exc)[:300]})
                out["errors"].append({"id": pos["id"], "error": str(exc)[:300]})
        for take in takes:
            try:
                res = open_from_take(book, take, bars_for(take["asset"]), s=s, proof_path=proof_path)
            except Exception as exc:
                res = {"status": "REFUSED", "reason": f"FETCH_OR_OPEN_ERROR:{str(exc)[:200]}", "asset": take.get("asset")}
                book.event(None, None, "OPEN_REFUSED", res)
            (out["opened"] if res.get("status") == "OPENED" else out["refused"]).append(res)
        out["ledger"] = book.ledger(s)
    finally:
        book.close()
    return out


# ---------------------------------------------------------------------------
# Fixtures (synthetic bars; not market trades)
# ---------------------------------------------------------------------------
T0 = 1_790_000_000_000.0 - (1_790_000_000_000.0 % HOUR_MS)


def _flat(n: int, px: float = 100.0, start: float = T0, vol: float = 10.0) -> list[list[float]]:
    return [[start + i * HOUR_MS, px, px * 1.002, px * 0.998, px, vol] for i in range(n)]


def _bar(i: int, o: float, h: float, lo: float, c: float, v: float = 10.0) -> list[float]:
    return [T0 + i * HOUR_MS, o, h, lo, c, v]


def run_fixtures(workdir: Path, proof_path: Path | None = None) -> dict[str, Any]:
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    cases: dict[str, Any] = {}

    def fresh(name: str) -> Book:
        p = workdir / f"fx_{name}.sqlite"
        if p.exists():
            p.unlink()
        return Book(p, fixture=True)

    def take(asset="BTC", core="squeeze", direction="LONG", **kw):
        return {"asset": asset, "core": core, "card": f"card.{core}.r3.v1", "direction": direction, "evidence_class": "FIXTURE", **kw}

    hist = _flat(60)
    n = len(hist)

    # 1. entry opens with a priced fill and haircut
    b = fresh("entry")
    r = open_from_take(b, take(), hist)
    pos = b.open_positions()[0] if r["status"] == "OPENED" else {}
    cases["entry"] = {"status": r["status"], "entry_fill": round(pos.get("entry_fill", 0), 6),
                      "ok": r["status"] == "OPENED" and abs(pos["entry_fill"] - 100.08) < 1e-9 and pos["counts_for_m2"] is False and pos["exec"] is False}
    b.close()

    # 2. hard stop hit (-2.2%) fills at the stop level, shadow also stops
    b = fresh("stop")
    open_from_take(b, take(), hist)
    pos = b.open_positions()[0]
    bars = hist + [_bar(n, 100.0, 100.1, 97.0, 97.5)]
    step(b, pos, bars, s=SETTINGS)
    p = b.all_positions()[0]
    cases["stop"] = {"exit_reason": p.get("exit_reason"), "module": p.get("exit_module"), "pnl": p.get("realized_pnl_usd"),
                     "shadow": p["shadow"].get("exit_reason"),
                     "ok": p["status"] == "CLOSED" and p["exit_reason"] == "STOP_LOSS" and p["exit_module"] == "A"
                     and abs(p["exit_ref"] - 100.08 * 0.978) < 1e-9 and p["realized_pnl_usd"] < 0 and p["shadow"]["exit_reason"] == "STOP_LOSS"}
    b.close()

    # 3. gap through the stop fills at the open, not the stop (no free price)
    b = fresh("gap")
    open_from_take(b, take(), hist)
    pos = b.open_positions()[0]
    step(b, pos, hist + [_bar(n, 95.0, 95.5, 94.0, 94.5)])
    p = b.all_positions()[0]
    cases["gap"] = {"exit_ref": p.get("exit_ref"), "ok": p["exit_ref"] == 95.0}
    b.close()

    # 4. profit protection: +1R locks breakeven next bar, then floor exit (A/PROFIT_FLOOR), hunter
    b = fresh("protect")
    open_from_take(b, take(core="hunter"), hist)
    pos = b.open_positions()[0]
    e = pos["entry_fill"]
    bars = hist + [_bar(n, 100.1, e * 1.025, 100.05, e * 1.02), _bar(n + 1, e * 1.02, e * 1.021, e * 0.999, e * 1.0)]
    step(b, pos, bars)
    p = b.all_positions()[0]
    ev = [x["kind"] for x in b.events(p["id"])]
    cases["protect"] = {"events": ev, "exit_reason": p.get("exit_reason"),
                        "ok": "TIGHTEN" in ev and p["status"] == "CLOSED" and p["exit_reason"] == "PROFIT_FLOOR" and p["exit_module"] == "A"}
    b.close()

    # 5. ATR trail after a run-up; shadow hits its +3% target instead
    b = fresh("trail")
    open_from_take(b, take(core="hunter"), hist)
    pos = b.open_positions()[0]
    e = pos["entry_fill"]
    up = [_bar(n + i, e * (1 + 0.01 * i), e * (1 + 0.01 * (i + 1)), e * (1 + 0.01 * i) * 0.999, e * (1 + 0.01 * (i + 1))) for i in range(6)]
    drop = [_bar(n + 6, e * 1.06, e * 1.061, e * 1.02, e * 1.025)]
    step(b, pos, hist + up + drop)
    p = b.all_positions()[0]
    cases["trail"] = {"exit_reason": p.get("exit_reason"), "module": p.get("exit_module"), "shadow": p["shadow"].get("exit_reason"),
                      "pnl": p.get("realized_pnl_usd"), "shadow_pnl": p["shadow"].get("pnl_usd"),
                      "ok": p["status"] == "CLOSED" and p["exit_module"] in ("A", "C") and p["realized_pnl_usd"] > 0 and p["shadow"]["exit_reason"] == "TARGET"}
    b.close()

    # 6. time exit: hunter held 72h flat-ish above the stop
    b = fresh("time")
    open_from_take(b, take(core="hunter"), hist)
    pos = b.open_positions()[0]
    e = pos["entry_fill"]
    later = [[T0 + (n + i) * HOUR_MS, e * 1.004, e * 1.005, e * 1.003, e * 1.004, 10.0] for i in range(80)]
    step(b, pos, hist + later)
    p = b.all_positions()[0]
    cases["time"] = {"exit_reason": p.get("exit_reason"), "hold_hours": p.get("hold_hours"),
                     "ok": p["status"] == "CLOSED" and p["exit_reason"] == "TIME_EXIT" and p["exit_module"] == "E" and p["hold_hours"] <= 72.0 + 1e-9}
    b.close()

    # 7. stale data: no new bars for > 3h -> DATA_STALE, position stays OPEN, no invented exit
    b = fresh("stale")
    open_from_take(b, take(), hist)
    pos = b.open_positions()[0]
    now_ms = hist[-1][_T] + HOUR_MS * 6
    step(b, pos, hist, now_ms=now_ms)
    p = b.all_positions()[0]
    ev = [x["kind"] for x in b.events(p["id"])]
    cases["stale"] = {"status": p["status"], "events": ev, "ok": p["status"] == "OPEN" and p["stale"] is True and "DATA_STALE" in ev and "CLOSED" not in ev}
    b.close()

    # 8. kill switch exits at the close
    b = fresh("kill")
    open_from_take(b, take(), hist)
    pos = b.open_positions()[0]
    step(b, pos, hist + [_bar(n, 100.0, 100.3, 99.5, 100.2)], emergency=True)
    p = b.all_positions()[0]
    cases["kill"] = {"exit_reason": p.get("exit_reason"), "ok": p["exit_reason"] == "EMERGENCY_STOP" and p["exit_ref"] == 100.2}
    b.close()

    # 9. one position cap; SHORT refused; fixture never on the live book; live never before proof
    b = fresh("gates")
    first = open_from_take(b, take(), hist)
    second = open_from_take(b, take(asset="ETH"), hist)
    short = open_from_take(b, take(asset="SOL", core="hunter", direction="SHORT"), hist)
    b.close()
    live_path = workdir / "fx_livebook.sqlite"
    if live_path.exists():
        live_path.unlink()
    lb = Book(live_path)
    fx_on_live = open_from_take(lb, take(), hist)
    live_no_proof = open_from_take(lb, {**take(), "evidence_class": "LIVE_PAPER"}, hist, proof_path=workdir / "no_proof.json")
    lb.close()
    cases["gates"] = {"second": second.get("reason"), "short": short.get("reason"), "fixture_on_live": fx_on_live.get("reason"),
                      "live_no_proof": live_no_proof.get("reason"),
                      "ok": first["status"] == "OPENED" and second.get("reason") == "SLOT_FULL" and short.get("reason") == "SHORT_NOT_SUPPORTED_SPOT"
                      and fx_on_live.get("reason") == "FIXTURE_REFUSED_ON_LIVE_BOOK" and live_no_proof.get("reason") == "SD6_FIXTURE_NOT_PROVEN"}

    # 10. no lookahead: an entry-bar spike cannot move the stop or arm protection
    b = fresh("lookahead")
    spiky = hist[:-1] + [[hist[-1][_T], 100.0, 130.0, 99.0, 100.0, 10.0]]
    open_from_take(b, take(core="hunter"), spiky)
    pos = b.open_positions()[0]
    step(b, pos, spiky + [_bar(n, 100.0, 100.2, 99.9, 100.1)])
    p = b.all_positions()[0]
    cases["lookahead"] = {"locked_floor": p.get("locked_floor"), "ok": p["status"] == "OPEN" and p.get("locked_floor") is None}
    b.close()

    # 11. late cycle: entry is pinned to the decision bar, later bars are managed next cycle
    b = fresh("late")
    late = hist + [_bar(n, 100.0, 100.5, 99.9, 100.4), _bar(n + 1, 100.4, 100.6, 100.3, 100.5)]
    r = open_from_take(b, take(decision_bar_open_ms=hist[-1][_T]), late)
    pos = b.open_positions()[0] if r["status"] == "OPENED" else {}
    miss = open_from_take(fresh("late_miss"), take(decision_bar_open_ms=T0 - HOUR_MS * 500), late)
    cases["late"] = {"entry_ref": pos.get("entry_ref"), "miss": miss.get("reason"),
                     "ok": pos.get("entry_bar_open_ms") == hist[-1][_T] and pos.get("entry_ref") == 100.0 and miss.get("reason") == "DECISION_BAR_NOT_IN_CANDLES"}
    b.close()

    ok = all(c["ok"] for c in cases.values())
    proof = {"id": "paper.exit.proof.v1", "version": VERSION, "port_of": PORT_OF, "status": "FIXTURE_PASS" if ok else "FIXTURE_FAIL",
             "not_a_market_trade": True, "exec": False, "counts_for_m2": False, "cases": cases}
    if ok:
        (proof_path or Path(__file__).with_name(PROOF_NAME)).write_text(json.dumps(proof, indent=2, default=str))
    return proof


def print_status(book_path: str | Path | None = None) -> dict[str, Any]:
    book = Book(book_path)
    try:
        led = book.ledger()
        closed = [p for p in book.all_positions() if p["status"] == "CLOSED"]
    finally:
        book.close()
    print(f"\nSD6 PAPER BOOK  {VERSION}")
    print("=" * 64)
    print(f"  proof={'FIXTURE_PASS' if fixture_proven() else 'NOT_PROVEN'}  cash={led['cash']:.2f}  realized={led['realized_pnl']:+.4f}")
    print(f"  open={len(led['open_positions'])}  closed={led['trade_count']}  W/L={led['wins']}/{led['losses']}  shadow_realized={led['shadow_realized_pnl']:+.4f}")
    for p in led["open_positions"]:
        print(f"  OPEN   {p['asset']:<5} {p['core']:<8} entry={p['entry_fill']:.6g} floor={p['locked_floor']} stale={p['stale']}")
    for p in closed[-10:]:
        sh = p.get("shadow") or {}
        print(f"  CLOSED {p['asset']:<5} {p['core']:<8} {p['exit_module']}/{p['exit_reason']:<16} pnl={p['realized_pnl_usd']:+.4f} R={p.get('r_multiple')} "
              f"hold={p.get('hold_hours')}h | shadow {sh.get('exit_reason') or sh.get('status')} {sh.get('pnl_usd')}")
    print("  exec=False live=False m2=False  paper only; fixture fill is not a market trade")
    print("=" * 64)
    return led


if __name__ == "__main__":  # python -m src.intelligence.paper_exit [fixture|status]
    import sys
    import tempfile

    cmd = (sys.argv[1:] or ["status"])[0]
    if cmd == "fixture":
        res = run_fixtures(Path(tempfile.mkdtemp(prefix="sd6_fx_")))
        print(json.dumps({k: v["ok"] for k, v in res["cases"].items()}, indent=2))
        print(res["status"])
    else:
        print_status()
