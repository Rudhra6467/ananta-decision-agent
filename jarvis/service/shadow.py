"""The blind shadow lane (OD-SHADOW-LANE, Madhav's yes on 2026-10-20 12:08 Toronto: "5. yes" to step 3 of the gate review).

What it is
- Each pre-registered review of the evidence window (docs/research/REVIEW_31.md to REVIEW_38.md, index PREREG_WINDOW_2026-10-20.md)
  has its rule's TRIGGER STATE evaluated here, as the pre-registration defines it: once a day after the daily close (run_daily) and,
  where a review needs intraday state, every 15 minutes (run_15m).
- What the rule would have done, with the exact inputs at that moment (price, zone, attention score and its parts, stop level, ...),
  is appended to an append-only, hash-chained log outside the repo: ~/ananta_runs/shadow/shadow_log.jsonl. Each row carries prev_hash
  and hash = sha256(prev_hash + canonical JSON of the row without its hash), as India's forecast ledger does (india/forecast.py).
  verify() recomputes the chain and names the first broken line.
- The universe's 5-minute bars (kept 14 days by the feed, feed.KEEP_5M_DAYS) are copied once a day to
  ~/ananta_runs/shadow/bars5m_YYYY-MM.sqlite (close, high and low per coin and bar) for an intraday version of review #32 after the
  window. Nothing reads that copy before day 60.

What it never does
- No outcome is computed and no result is shown. Rows hold inputs and would-do actions only; append() refuses any row carrying an
  outcome field (FORBIDDEN). The only function that hands rows back for scoring, results(), raises Sealed before 2026-12-15 00:00 UTC.
- It never wakes the brain, never touches a book, the gate, the account, strategy_status.json or any pinned file, and never places or
  changes a paper order. Every database of the agent folder is opened read-only (mode=ro, query_only); the only files it writes are
  under its own folder.

Rules and the reviews they shadow (W = the forward window 2026-10-21 00:00 UTC to 2026-12-14)
  R31  stop exits of the books brain.manage_live runs (and the zone-touch books beside): the touch, then the written close rule
       replayed day by day on universe daily candles (target first, time exit at the open, trail raised after each later day)
  R32  R38-D5 and R38-H20 at each daily close on point-in-time tiers A and B (away from support, market allowed, one trade per coin);
       every 15 minutes the first 5-minute cross of the same levels (recorder only: that version is not pre-registered)
  R33  each new TAKE pair of Jarvis's book and its twin, with both legs' plans
  R34  each brain decision and each wake the brain did not review (ranked out, monitoring only, dial closed), without any after_ column
  R35  the attention board every 15 minutes: score, level and the five parts, for each of the lab 10, queued or not
  R36  each Explorer ORDER and FILLED event with its room tags and group (real, NO_TYPE, RANDOM, ...)
  R37  each bold decision: whether its text cites T3 and T3's rating of the coin at that close
  R38  each missed-moves row with the frozen allowed books (REVIEW_38) that were in the move by missed.py's rule (no money)
  LANE one row per run (what was written, what failed) and the day's brain-wake states (the lost runs reviews #33-#35 name)

  run_daily(j) / run_15m(j)   one round (each rule isolated: one failing never stops the others)
  hook_daily(j, out) / hook_15m(j, out)   the guarded calls the daily close and the 15-minute jobs make; never raise
  verify()                    the chain
  results()                   sealed until 2026-12-15 00:00 UTC
  python -m jarvis.service.shadow verify | dry-run --agent DIR --out DIR [--since YYYY-MM-DD]
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import math
import os
import re
import sqlite3
import statistics
import sys
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

DAY = 86400
UTC = timezone.utc
WINDOW_START = int(datetime(2026, 10, 21, tzinfo=UTC).timestamp())
WINDOW_END = int(datetime(2026, 12, 15, tzinfo=UTC).timestamp()) - 1        # 2026-12-14 23:59:59 UTC
SEALED_UNTIL = int(datetime(2026, 12, 15, tzinfo=UTC).timestamp())          # CHECKPOINT-60 runs after the 2026-12-15 00:05 UTC close
LOG, RUN_LOG, ERR_LOG = "shadow_log.jsonl", "run.log", "errors.log"
CATCH_UP_DAYS = 7
SCHEMA = 1

# outcome fields: a row carrying any of these is refused (no outcome is computed or kept before day 60)
FORBIDDEN = frozenset({"net", "net_usd", "pnl", "pnl_usd", "caught_pnl_usd", "caught_books", "after_1d_pct", "after_5d_pct",
                       "after_1d_ex", "after_5d_ex", "ACTUAL_net", "ACTUAL_R", "ACTUAL_bell", "ACTUAL_exit_t", "mfe", "mae",
                       "excess", "win", "wins", "total", "totals", "profit", "vs_random_usd", "bell"})

# review #31
R31_DECIDES = ("JARVIS", "JARVIS_RANDOM", "JARVIS_BOLD", "RANDOM_BOLD")          # the books brain.manage_live runs
R31_BESIDE = ("ZONE_TOUCH", "ZONE_TOUCH-UA", "ZONE_TOUCH-UB", "ZONE_TOUCH-UC")
R31_STOP_WHY = ("stop", "stop (live price)", "trailing stop (live price)")
# review #32
TIER_A, TIER_B = 20e6, 1e6                                                       # registry.TIER_A / TIER_B at 448cb21
R32_HOLD = 5
# review #37: the T3 card's id and aliases (status_cards.json at 448cb21, as REVIEW_37 lists them)
T3_ALIASES = ("t3", "trend portfolio", "portfolio layer")
# review #38: allowed books frozen from strategy_status.json at 448cb21 (REVIEW_38); a watch's tier copy belongs to its base
R38_ALLOWED_WATCHES = frozenset({"H07", "H07-T30", "JARVIS", "JARVIS_BOLD", "M1a", "M2a", "M2a-G", "M3a", "M3b"})
R38_AFTER = 2 * 3600

_LOCK = threading.RLock()
_X5M: dict = {"day": None, "elig": None}


class Sealed(RuntimeError):
    """A result was asked for before CHECKPOINT-60."""


# ----------------------------------------------------------------------------------------------------------------------------- paths
def shadow_dir(root: str | Path | None = None) -> Path:
    if root:
        return Path(root).expanduser()
    if os.getenv("ANANTA_SHADOW_DIR"):
        return Path(os.environ["ANANTA_SHADOW_DIR"]).expanduser()
    return Path(os.getenv("ANANTA_RUNS_DIR", str(Path.home() / "ananta_runs"))).expanduser() / "shadow"


def _iso(t: float) -> str:
    return datetime.fromtimestamp(t, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _day(t: float) -> str:
    return datetime.fromtimestamp(t, UTC).strftime("%Y-%m-%d")


def _day_t(day: str) -> int:
    return int(datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=UTC).timestamp())


# ----------------------------------------------------------------------------------------------------------------------------- the log
def _clean(x: Any) -> Any:
    """JSON-safe and stable: tuples become lists, non-finite floats become None, so a row re-read hashes the same."""
    if isinstance(x, dict):
        return {str(k): _clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_clean(v) for v in x]
    if isinstance(x, float):
        return x if math.isfinite(x) else None
    if x is None or isinstance(x, (str, int, bool)):
        return x
    return str(x)


def _keys(x: Any) -> set[str]:
    if isinstance(x, dict):
        return set(x) | set().union(*(_keys(v) for v in x.values())) if x else set()
    if isinstance(x, list):
        return set().union(*(_keys(v) for v in x)) if x else set()
    return set()


def _canon(row: dict) -> str:
    return json.dumps({k: v for k, v in row.items() if k != "hash"}, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _tail_hash(p: Path) -> str:
    """The last row's hash, read from the end of the file (the log grows all window long)."""
    if not p.exists() or not p.stat().st_size:
        return "genesis"
    with p.open("rb") as fh:
        end = fh.seek(0, 2)
        buf, pos = b"", end
        while pos > 0:
            step = min(65536, pos)
            pos -= step
            fh.seek(pos)
            buf = fh.read(step) + buf
            lines = [x for x in buf.split(b"\n") if x.strip()]
            if len(lines) >= 2 or (pos == 0 and lines):
                return json.loads(lines[-1])["hash"]
    return "genesis"


@contextmanager
def _locked(d: Path):
    d.mkdir(parents=True, exist_ok=True)
    with _LOCK, open(d / ".lock", "a") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lk, fcntl.LOCK_UN)


def append(rows: list[dict], root: str | Path | None = None) -> int:
    """Append rows to the chain. Refuses (ValueError, nothing written) any row that carries an outcome field."""
    if not rows:
        return 0
    clean = [_clean(r) for r in rows]
    for r in clean:
        bad = _keys(r) & FORBIDDEN
        if bad:
            raise ValueError(f"the shadow lane keeps no outcomes: refused field(s) {sorted(bad)} in a {r.get('review')} row")
    d = shadow_dir(root)
    p = d / LOG
    with _locked(d):
        prev = _tail_hash(p)
        out = []
        for r in clean:
            r.pop("hash", None)
            r["prev_hash"] = prev
            r["hash"] = hashlib.sha256((prev + _canon(r)).encode()).hexdigest()
            prev = r["hash"]
            out.append(json.dumps(r, sort_keys=True, separators=(",", ":"), allow_nan=False))
        with p.open("a") as fh:
            fh.write("\n".join(out) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
    return len(out)


def _rows(root: str | Path | None = None) -> list[dict]:
    p = shadow_dir(root) / LOG
    if not p.exists():
        return []
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]


def verify(root: str | Path | None = None) -> dict:
    """Recomputes every hash: {ok, rows, broken_at_line, note}. Editing, deleting or reordering any row breaks every hash after it."""
    p = shadow_dir(root) / LOG
    if not p.exists():
        return {"ok": True, "rows": 0, "broken_at_line": None, "note": "no rows yet"}
    prev, n = "genesis", 0
    with p.open() as fh:
        for i, line in enumerate(fh, 1):
            if not line.strip():
                continue
            try:
                r = json.loads(line)
                good = r.get("prev_hash") == prev and hashlib.sha256((prev + _canon(r)).encode()).hexdigest() == r.get("hash")
            except (ValueError, TypeError):
                good = False
            if not good:
                return {"ok": False, "rows": n, "broken_at_line": i,
                        "note": f"hash chain broken at line {i}: an earlier row was edited, deleted or reordered"}
            prev, n = r["hash"], n + 1
    return {"ok": True, "rows": n, "broken_at_line": None, "note": "chain intact"}


def results(root: str | Path | None = None, now: float | None = None) -> dict:
    """The rows for the CHECKPOINT-60 scoring runs, grouped by review. Sealed before 2026-12-15 00:00 UTC: until then no function
    returns totals, wins or P&L (and the rows themselves hold none)."""
    now = time.time() if now is None else now
    if now < SEALED_UNTIL:
        raise Sealed(f"the shadow lane is blind until {_iso(SEALED_UNTIL)} (CHECKPOINT-60); nothing is shown before then")
    v = verify(root)
    if not v["ok"]:
        raise RuntimeError(v["note"])
    out: dict = {}
    for r in _rows(root):
        out.setdefault(r.get("review"), []).append(r)
    return {"verify": v, "by_review": out}


def _errlog(d: Path, where: str, exc: BaseException) -> str:
    """One timestamped line in errors.log; never raises."""
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())} UTC] {where}: {type(exc).__name__}: {str(exc)[:300]}"
    try:
        d.mkdir(parents=True, exist_ok=True)
        with (d / ERR_LOG).open("a") as fh:
            fh.write(line + "\n")
    except Exception:  # noqa: BLE001
        pass
    return line


# ----------------------------------------------------------------------------------------------------------------------------- read-only data
def _ro(path: Path) -> sqlite3.Connection:
    """The only way this module opens a database of the agent folder: it must exist, mode=ro never creates one, and query_only
    refuses every change."""
    if not Path(path).is_file():
        raise FileNotFoundError(f"no database at {path}")
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=10)
    con.execute("PRAGMA query_only = ON")
    return con


class _View:
    """What the zone and setup boards need from a Jarvis (dir, now, db), with a read-only database: anything they try to write
    fails and they fall back, exactly as on a database error."""

    def __init__(self, agent_dir: Path, now: Callable[[], float]):
        from jarvis.service.core import SafeDB

        self.dir, self.now = Path(agent_dir), now
        self.db = SafeDB(_ro(self.dir / "jarvis.sqlite"))

    def close(self) -> None:
        try:
            self.db.con.close()
        except Exception:  # noqa: BLE001
            pass


class Ctx:
    def __init__(self, j, root: str | Path | None, now: float | None, since: float | None):
        self.dir = Path(j.dir)
        self.now = float(now if now is not None else (j.now() if callable(getattr(j, "now", None)) else time.time()))
        self.since = int(WINDOW_START if since is None else since)
        self.root = shadow_dir(root)
        self._d1: dict | None = None
        self._log: list[dict] | None = None

    # the log as the rules' memory (which inputs were already recorded); never read for outcomes
    def logged(self) -> list[dict]:
        if self._log is None:
            self._log = _rows(self.root)
        return self._log

    def ids(self, review: str, kind: str | None = None) -> set:
        return {r.get("key") for r in self.logged() if r.get("review") == review and (kind is None or r.get("kind") == kind)}

    def db(self, name: str = "jarvis.sqlite") -> sqlite3.Connection:
        return _ro(self.dir / name)

    def d1(self) -> dict[str, list[tuple]]:
        """Every universe coin's closed daily candles (t, o, h, l, c, v, qv), one read."""
        if self._d1 is None:
            con = self.db("universe_bars.sqlite")
            try:
                out: dict[str, list[tuple]] = {}
                for row in con.execute("SELECT coin, t, o, h, l, c, v, qv FROM d1 ORDER BY coin, t"):
                    out.setdefault(row[0], []).append(tuple(row[1:]))
            finally:
                con.close()
            self._d1 = out
        return self._d1

    def lab_daily(self, coin: str) -> list[tuple]:
        from jarvis.service.reads_watch import _daily

        return _daily(self, coin)                                                # explorer_bars.sqlite, opened mode=ro by casebook


def _row(ctx: Ctx, review: str, kind: str, key: str, event_t: float | None, **f) -> dict:
    et = int(event_t) if event_t is not None else None
    return {"v": SCHEMA, "t": int(ctx.now), "at": _iso(ctx.now), "review": review, "kind": kind, "key": key, "event_t": et,
            "in_window": bool(et is not None and WINDOW_START <= et <= WINDOW_END), **f}


def _json(s: Any) -> Any:
    try:
        return json.loads(s) if isinstance(s, str) and s else (s or {})
    except ValueError:
        return {"raw": str(s)[:500]}


def _num(x: Any) -> float | None:
    try:
        v = float(x)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def _base(watch: str) -> str:
    return re.sub(r"-(UA|UB|UC|T30)$", "", watch or "")


# ----------------------------------------------------------------------------------------------------------------------------- R31: stops
def r31(ctx: Ctx) -> list[dict]:
    """Every stop exit (the touch) of the books run by brain.manage_live, and of the zone-touch books beside them, then the written
    close rule on each later daily close until it would have exited. Inputs only: the level in force, the candle, the would-do."""
    from jarvis.service import watch_engine

    books = R31_DECIDES + R31_BESIDE
    con = ctx.db()
    try:
        q = (f"SELECT id, watch, coin, source, entry_t, entry, stop, exit_t, exit, exit_why, detail FROM evidence_trades "
             f"WHERE watch IN ({','.join('?' * len(books))}) AND exit_why IN ({','.join('?' * len(R31_STOP_WHY))}) "
             f"AND exit_t IS NOT NULL AND exit_t >= ? ORDER BY exit_t")
        trades = con.execute(q, (*books, *R31_STOP_WHY, ctx.since)).fetchall()
    finally:
        con.close()
    # each track's state from its own earlier rows
    state: dict[str, dict] = {}
    for r in ctx.logged():
        if r.get("review") != "R31":
            continue
        tid = r.get("trade_id")
        if r["kind"] == "touch":
            state[tid] = {"level": r["level_at_touch"], "last_t": None, "done": False}
        elif r["kind"] == "close_rule" and tid in state:
            state[tid].update(level=r["level_next"], last_t=r["candle_t"], done=r["would"] != "HOLD")
    out = []
    D1 = ctx.d1()
    for tid, w, coin, src, entry_t, entry, stop, exit_t, exit_px, exit_why, dj in trades:
        d = _json(dj)
        days = int(d.get("days") or (watch_engine.EYE.get(w) or {}).get("days") or 30)
        plan = {"target": _num(d.get("target")), "days": days, "trail_atr": _num(d.get("trail_atr")), "atr": _num(d.get("atr")),
                "stop0": _num(d.get("stop0"))}
        if tid not in state:
            out.append(_row(ctx, "R31", "touch", f"touch:{tid}", exit_t, trade_id=tid, watch=w, coin=coin, source=src,
                            cell="A" if w in R31_DECIDES else "zone_touch_beside", entry_t=entry_t, entry=entry, level_at_touch=stop,
                            touch_t=exit_t, touch_price=exit_px, touch_why=exit_why,
                            has_minute=exit_why != "stop", stop_moves=(d.get("stop_moves") or [])[-5:], **plan,
                            would="SELL_ON_TOUCH (what the book did)"))
            state[tid] = {"level": stop, "last_t": None, "done": False}
        st = state[tid]
        if st["done"] or st["level"] is None:
            continue
        level = float(st["level"])
        for c in D1.get(coin, []):
            t, o, h, lo, cl = c[0], c[1], c[2], c[3], c[4]
            if t + DAY <= exit_t or (st["last_t"] is not None and t <= st["last_t"]) or t + DAY > ctx.now:
                continue
            touch_day = t <= exit_t < t + DAY
            due = (entry_t or exit_t) + days * DAY
            if t >= due:
                would, px = "TIME_EXIT_AT_OPEN", o
            elif plan["target"] and h >= plan["target"]:
                would, px = "TARGET", (o if o >= plan["target"] else plan["target"])
            elif cl <= level:
                would, px = "EXIT_AT_CLOSE", cl
            else:
                would, px = "HOLD", None
            nxt = level
            if would == "HOLD" and not touch_day and plan["trail_atr"] and plan["atr"]:
                nxt = max(level, h - plan["trail_atr"] * plan["atr"])              # the plan's own trail, raised after each later day
            out.append(_row(ctx, "R31", "close_rule", f"close:{tid}:{t}", exit_t, trade_id=tid, watch=w, coin=coin,
                            cell="A" if w in R31_DECIDES else "zone_touch_beside", candle_t=t, candle_day=_day(t),
                            o=o, h=h, l=lo, c=cl, level_in_force=level, level_next=nxt, time_exit_t=due, target=plan["target"],
                            touch_day=touch_day, catch_up=t + 2 * DAY <= ctx.now, would=would, would_price=px,
                            source_candles="universe_bars.d1"))
            level = nxt
            if would != "HOLD":
                break
    return out


# ----------------------------------------------------------------------------------------------------------------------------- R32: breakout
def _tier_pit(D: list[tuple], k: int) -> str | None:
    """Point-in-time tier at signal candle k: median traded value of the 30 candles before it, all 30 present (registry rule)."""
    qv = [x[6] for x in D[max(0, k - 30):k] if x[6] is not None]
    if len(qv) < 30:
        return None
    med = statistics.median(qv)
    return "A" if med >= TIER_A else "B" if med >= TIER_B else None


def _zone_hit(D: list[tuple], low: float, atr: float | None) -> str | None:
    from src.research import zones as Z

    if not atr or len(D) < 260:
        return None
    for z in Z.live_zones([x[:6] for x in D])["zones"]:
        if z["bot"] - 0.5 * atr <= low <= z["top"] + 0.5 * atr:
            return "+".join(z["kinds"]).lower() + f" [{z['bot']:.6g}, {z['top']:.6g}]"
    return None


def _atr(D: list[tuple]) -> float | None:
    from src.research import reads as R

    return _num(R.Series([x[:6] for x in D]).atr[-1]) if len(D) >= 15 else None


def _regime(btc: list[tuple], before_t: int) -> dict:
    """watch_engine.regime_at on Bitcoin's lab daily candles opened before `before_t`: the state, and the numbers behind it."""
    from jarvis.service import watch_engine
    from src.research import reads as R

    B = [x for x in btc if x[0] < before_t]
    if len(B) < 60:
        return {"regime": None, "btc_close": None, "btc_ema50": None, "btc_candle_t": None}
    S = R.Series(B)
    return {"regime": watch_engine.regime_at(S, B[-1][0]), "btc_close": S.c[-1], "btc_ema50": _num(S.ema50[-1]), "btc_candle_t": B[-1][0]}


def _breakouts(D: list[tuple], k: int) -> dict:
    c = D[k][4]
    hi5 = max(x[2] for x in D[k - 5:k])
    hi20 = max(x[2] for x in D[k - 20:k])
    prev_hi20 = max(x[2] for x in D[k - 21:k - 1])
    return {"hi5": hi5, "hi20": hi20, "prev_close": D[k - 1][4], "prev_hi20": prev_hi20,
            "R38-D5": c > hi5, "R38-H20": c > hi20 and D[k - 1][4] <= prev_hi20}


def r32(ctx: Ctx) -> list[dict]:
    """R38-D5 (decides) and R38-H20 (beside) at each daily close not yet evaluated: the breakout, the support and market filters
    under both readings of "to that day" (with the signal candle, and missed.context's candles before it), the point-in-time tier,
    the cost per side, and the would-do (BUY at the next open, exit at the open five candles later; one trade per coin)."""
    from jarvis.service import registry

    D1 = ctx.d1()
    btc = ctx.lab_daily("BTC")
    if "BTC" not in D1 or not btc:
        raise RuntimeError("no daily candles for BTC")
    done = {r["candle_t"] for r in ctx.logged() if r.get("review") == "R32" and r.get("kind") == "close_day"}
    open_until: dict[tuple, int] = {}
    for r in ctx.logged():
        if r.get("review") == "R32" and r.get("kind") == "signal" and str(r.get("would", "")).startswith("BUY"):
            key = (r["rule"], r["coin"])
            open_until[key] = max(open_until.get(key, 0), r["exit_open_t"])
    last = D1["BTC"][-1][0]
    todo = [t for t in range(last - (CATCH_UP_DAYS - 1) * DAY, last + DAY, DAY)
            if t + DAY >= ctx.since and t not in done and t + DAY <= ctx.now]
    try:
        reg = registry.load(ctx)
    except Exception:  # noqa: BLE001
        reg = {}
    out = []
    for T in todo:
        close_t = T + DAY
        reg_at_close, reg_prior = _regime(btc, close_t), _regime(btc, T)
        elig: dict[str, list[str]] = {"A": [], "B": []}
        sigs = []
        for coin, D in D1.items():
            k = next((i for i in range(len(D) - 1, -1, -1) if D[i][0] == T), None)
            if k is None or k < 260:
                continue
            tier = _tier_pit(D, k)
            if tier is None:
                continue
            elig[tier].append(coin)
            b = _breakouts(D, k)
            for rule in ("R38-D5", "R38-H20"):
                if not b[rule]:
                    continue
                atr_close, atr_prior = _atr(D[:k + 1]), _atr(D[:k])
                z_close, z_prior = _zone_hit(D[:k + 1], D[k][3], atr_close), _zone_hit(D[:k], D[k][3], atr_prior)
                away, allowed = z_close is None, reg_at_close["regime"] == "ALLOWED"
                held = open_until.get((rule, coin), 0) > close_t
                would = ("NO_TRADE: at a support zone" if not away else "NO_TRADE: market not allowed" if not allowed else
                         "IGNORED: this coin's trade is still open" if held else "BUY_NEXT_OPEN")
                entry_open, exit_open = close_t, close_t + R32_HOLD * DAY
                if would == "BUY_NEXT_OPEN":
                    open_until[(rule, coin)] = exit_open
                try:
                    cost = registry.cost(coin, reg)
                except Exception:  # noqa: BLE001
                    cost = None
                sigs.append(_row(ctx, "R32", "signal", f"{rule}:{coin}:{T}", close_t, rule=rule, decides=rule == "R38-D5", coin=coin,
                                 tier=tier, candle_t=T, close_t=close_t, o=D[k][1], h=D[k][2], l=D[k][3], c=D[k][4], qv=D[k][6],
                                 hi5=b["hi5"], hi20=b["hi20"], prev_close=b["prev_close"], prev_hi20=b["prev_hi20"],
                                 atr=atr_close, atr_prior=atr_prior, zone_hit=z_close, zone_hit_prior=z_prior,
                                 regime=reg_at_close["regime"], regime_prior=reg_prior["regime"],
                                 cost_side=cost, entry_open_t=entry_open, exit_open_t=exit_open, would=would,
                                 note="filters as read at the close (with the signal candle); *_prior = missed.context's candles before it"))
        out.append(_row(ctx, "R32", "close_day", f"day:{T}", close_t, candle_t=T, close_t=close_t, eligible_A=sorted(elig["A"]),
                        eligible_B=sorted(elig["B"]), btc=reg_at_close, btc_prior=reg_prior, catch_up=close_t + DAY <= ctx.now))
        out.extend(sigs)
    return out


def _x5m_eligible(ctx: Ctx, day0: int) -> dict:
    """Today's candidates for the intraday cross: point-in-time tier A or B on the closed candles, 260 of them, and the levels."""
    if _X5M["day"] == (str(ctx.dir), day0) and _X5M["elig"] is not None:
        return _X5M["elig"]
    out = {}
    for coin, D in ctx.d1().items():
        D = [x for x in D if x[0] < day0]
        k = len(D)
        if k < 261 or D[-1][0] != day0 - DAY:
            continue
        tier = _tier_pit(D, k)
        if tier is None:
            continue
        out[coin] = {"tier": tier, "hi5": max(x[2] for x in D[-5:]), "hi20": max(x[2] for x in D[-20:]),
                     "prev_close": D[-1][4], "prev_hi20": max(x[2] for x in D[-21:-1]), "D": D}
    _X5M.update(day=(str(ctx.dir), day0), elig=out)
    return out


def r32x(ctx: Ctx) -> list[dict]:
    """Recorder only (REVIEW_32: "needs a recorder"): the first 5-minute bar of the UTC day whose high crosses the D5 or H20 level,
    per coin and rule, with the support and market filters as they stood at that bar. Not a pre-registered rule."""
    day0 = int(ctx.now // DAY * DAY)
    elig = _x5m_eligible(ctx, day0)
    if not elig:
        return []
    seen = {r["key"] for r in ctx.logged() if r.get("review") == "R32" and r.get("kind") == "cross_5m" and r.get("day_t") == day0}
    con = ctx.db("universe_bars.sqlite")
    try:
        bars: dict[str, list[tuple]] = {}
        for coin, t, h, lo, c in con.execute("SELECT coin, t, h, l, c FROM m5 WHERE t >= ? ORDER BY coin, t", (day0,)):
            if coin in elig:
                bars.setdefault(coin, []).append((t, h, lo, c))
    finally:
        con.close()
    btc = ctx.lab_daily("BTC")
    reg = _regime(btc, day0)
    out = []
    for coin, B in bars.items():
        e = elig[coin]
        for rule, level, ok in (("R38-D5-X5M", e["hi5"], True), ("R38-H20-X5M", e["hi20"], e["prev_close"] <= e["prev_hi20"])):
            key = f"{rule}:{coin}:{day0}"
            if not ok or key in seen:
                continue
            i = next((n for n, b in enumerate(B) if b[1] is not None and b[1] > level), None)
            if i is None:
                continue
            low_so_far = min(b[2] for b in B[:i + 1])
            atr = _atr(e["D"])
            zone = _zone_hit(e["D"], low_so_far, atr)
            would = ("NO_TRADE: at a support zone" if zone else "NO_TRADE: market not allowed" if reg["regime"] != "ALLOWED"
                     else "BUY_AT_CROSS")
            out.append(_row(ctx, "R32", "cross_5m", key, B[i][0], rule=rule, prereg=False, coin=coin, tier=e["tier"], day_t=day0,
                            bar_t=B[i][0], bar_h=B[i][1], bar_c=B[i][3], level=level, low_so_far=low_so_far, atr=atr, zone_hit=zone,
                            regime=reg["regime"], btc_close=reg["btc_close"], btc_ema50=reg["btc_ema50"], seen_at=int(ctx.now),
                            would=would))
    return out


# ----------------------------------------------------------------------------------------------------------------------------- R33, R34
def r33(ctx: Ctx) -> list[dict]:
    """Each TAKE of Jarvis's book from the window on, with its twin: who, when, both legs' entries and plans (never their nets)."""
    seen = ctx.ids("R33")
    con = ctx.db()
    try:
        rows = con.execute("SELECT id, t, coin, triggers, confidence, size_pct, price, plan, trade_id, random_id FROM brain_decisions "
                           "WHERE action='TAKE' AND t >= ? ORDER BY t", (ctx.since,)).fetchall()
        out = []
        for did, t, coin, trig, conf, size, price, plan, tid, rid in rows:
            if f"take:{did}" in seen:
                continue
            legs = {}
            for name, x in (("pick", tid), ("twin", rid)):
                r = con.execute("SELECT watch, coin, entry_t, entry, stop, status, detail FROM evidence_trades WHERE id=?", (x,)).fetchone() if x else None
                if r:
                    d = _json(r[6])
                    legs[name] = {"id": x, "watch": r[0], "coin": r[1], "entry_t": r[2], "entry": r[3], "stop": r[4], "status_at_log": r[5],
                                  "target": d.get("target"), "days": d.get("days"), "trail_atr": d.get("trail_atr"), "atr": d.get("atr")}
                else:
                    legs[name] = {"id": x, "missing": True}
            out.append(_row(ctx, "R33", "take", f"take:{did}", t, decision_id=did, coin=coin, triggers=_json(trig), confidence=conf,
                            size_pct=size, price=price, plan=_json(plan), legs=legs, would="PAIR (the book's own TAKE and twin)"))
    finally:
        con.close()
    return out


def _unreviewed_group(reason: str) -> str:
    r = (reason or "").lower()
    if r.startswith("ranked too low") or r.startswith("waited 45 minutes"):
        return "ranked_out"
    if r.startswith("monitoring only"):
        return "monitoring_only"
    if "dial" in r:
        return "dial_closed"
    return "other"


def r34(ctx: Ctx) -> list[dict]:
    """Each brain decision (PASS and TAKE) and each wake it did not review, from the window on, with the inputs scoring needs
    (time, coin, price, trigger). The after_ columns are the live scoring and are never copied."""
    seen = ctx.ids("R34")
    con = ctx.db()
    out = []
    try:
        for did, t, coin, trig, act, conf, price, tid in con.execute(
                "SELECT id, t, coin, triggers, action, confidence, price, trade_id FROM brain_decisions WHERE t >= ? ORDER BY t", (ctx.since,)):
            if f"decision:{did}" in seen:
                continue
            tj = _json(trig)
            out.append(_row(ctx, "R34", "decision", f"decision:{did}", t, decision_id=did, coin=coin, action=act, confidence=conf,
                            price=price, trade_id=tid, triggers=sorted(k for k in tj if not k.startswith("_")) if isinstance(tj, dict) else tj,
                            rank=(tj.get("_rank") if isinstance(tj, dict) else None), cell="A" if act == "PASS" else "B_decided",
                            would=act))
        for uid, t, coin, trig, score, reason, price in con.execute(
                "SELECT id, t, coin, trigger, score, reason, price FROM brain_unreviewed WHERE t >= ? ORDER BY t", (ctx.since,)):
            if f"unreviewed:{uid}" in seen:
                continue
            g = _unreviewed_group(reason)
            out.append(_row(ctx, "R34", "unreviewed", f"unreviewed:{uid}", t, unreviewed_id=uid, coin=coin, trigger=trig, score=score,
                            reason=(reason or "")[:240], price=price, group=g, cell="B_ranked_out" if g == "ranked_out" else "beside",
                            would="NOT_REVIEWED"))
    finally:
        con.close()
    return out


def lane_wakes(ctx: Ctx) -> list[dict]:
    """The brain's wakes on each UTC day since the last one recorded, by state: the lost runs (failed or budget-dropped wakes) the
    results files of reviews #33 to #35 must name. Counts of wakes, not outcomes."""
    done = ctx.ids("LANE", "wakes_day")
    today0 = int(ctx.now // DAY * DAY)
    con = ctx.db()
    out = []
    try:
        for d0 in range(today0 - CATCH_UP_DAYS * DAY, today0, DAY):
            if d0 + DAY < ctx.since or f"wakes:{d0}" in done:
                continue
            states: dict[str, int] = {}
            n = 0
            for (st,) in con.execute("SELECT state FROM brain_queue WHERE t >= ? AND t < ?", (d0, d0 + DAY)):
                s = (st or "").split(":")[0].strip() or "NONE"
                if s.startswith("DROPPED") and "budget" in (st or "").lower():
                    s = "DROPPED_BUDGET"
                states[s] = states.get(s, 0) + 1
                n += 1
            out.append(_row(ctx, "LANE", "wakes_day", f"wakes:{d0}", d0, day=_day(d0), wakes=n, by_state=states,
                            attention_high_queued=con.execute("SELECT COUNT(*) FROM brain_queue WHERE t >= ? AND t < ? AND "
                                                              "trigger LIKE '%attention_high%'", (d0, d0 + DAY)).fetchone()[0]))
    finally:
        con.close()
    return out


# ----------------------------------------------------------------------------------------------------------------------------- R35: attention
def _attention_parts(row: dict, reads_row: dict | None) -> dict:
    """The five parts of zones_watch.attention, one by one (its weights at 448cb21)."""
    z = (row.get("inside") or [None])[0] or row.get("tested")
    parts = {"in_zone": 0, "supported_kind": 0, "came_down_5d": 0, "market_allowed": 0, "setup": 0}
    if z:
        parts["in_zone"] = 1
        if z.get("history") == "SUPPORTED":
            parts["supported_kind"] = 2
        rec = z.get("recent")
        if rec and row.get("day") and (datetime.strptime(row["day"], "%Y-%m-%d") - datetime.strptime(rec["entered"], "%Y-%m-%d")).days <= 5:
            parts["came_down_5d"] = 1
    f6 = next((x for x in row.get("reactions") or [] if x.get("id") == "F6"), None)
    if f6 and f6.get("present"):
        parts["market_allowed"] = 2
    for x in (reads_row or {}).get("reads", []):
        parts["setup"] += 2 if x.get("state") == "FIRED" else 1 if x.get("state") == "CLOSE" else 0
    return parts


def r35(ctx: Ctx) -> list[dict]:
    """The attention board as it stands now, for each lab coin: the score, its level (HIGH, WATCH, LOW), the five parts and their
    inputs, and whether an attention-HIGH wake was queued today. Recorded whatever the queue does (REVIEW_35's recorder gap)."""
    from jarvis.service import reads_watch, zones_watch

    v = _View(ctx.dir, lambda: ctx.now)
    try:
        board = zones_watch.board(v)
        try:
            rb = {r["coin"]: r for r in reads_watch.board(v).get("coins", [])}
        except Exception:  # noqa: BLE001
            rb = {}
        day0 = int(ctx.now // DAY * DAY)
        queued = {c for (c,) in v.db.execute("SELECT DISTINCT coin FROM brain_queue WHERE t >= ? AND trigger LIKE '%attention_high%'",
                                             (day0,)).fetchall()}
    finally:
        v.close()
    slot = int(ctx.now // 900 * 900)
    seen = ctx.ids("R35")
    out = []
    for r in board.get("coins", []):
        key = f"att:{r['coin']}:{slot}"
        if key in seen:
            continue
        a = r.get("attention") or zones_watch.attention(r, rb.get(r["coin"]))
        parts = _attention_parts(r, rb.get(r["coin"]))
        z = (r.get("inside") or [None])[0] or r.get("tested")
        out.append(_row(ctx, "R35", "board", key, ctx.now, coin=r["coin"], slot_t=slot, day=r.get("day"), price=r.get("price"),
                        atr=r.get("atr"), score=a.get("score"), level=a.get("level"), why=a.get("why"), parts=parts,
                        parts_sum_matches=sum(parts.values()) == a.get("score"),
                        zone=({k: z.get(k) for k in ("bot", "top", "kinds", "state", "history", "recent", "groups")} if z else None),
                        f6_present=parts["market_allowed"] == 2,
                        setups=[{k: x.get(k) for k in ("variant", "name", "state", "met", "of")} for x in (rb.get(r["coin"]) or {}).get("reads", [])],
                        queued_today=r["coin"] in queued, would=("WAKE (attention HIGH)" if a.get("level") == "HIGH" else a.get("level"))))
    return out


# ----------------------------------------------------------------------------------------------------------------------------- R36, R37, R38
R36_TAGS = ("room", "type_rule", "rules", "in_support", "entry_mode", "touch", "S1", "S2", "S2b", "S3", "trend_4h", "daily_above_ema50",
            "btc_S1", "btc_S2", "expensive", "hour_utc", "rsi15", "rsi1h", "roc_pct", "vol15", "vol1h", "contracted_now", "contracted_12h",
            "green_run_5m", "level")


def r36(ctx: Ctx) -> list[dict]:
    """Each Explorer ORDER (with the room check's tags and the group it fell in) and FILLED event from the window on. CLOSED events
    carry the result and are never read."""
    last = max((r.get("seq") or 0 for r in ctx.logged() if r.get("review") == "R36"), default=0)
    con = ctx.db("explorer_book.sqlite")
    out = []
    try:
        for seq, t, kind, coin, xid, js in con.execute("SELECT seq, t, kind, coin, id, json FROM events WHERE kind IN ('ORDER', 'FILLED') "
                                                       "AND t >= ? AND seq > ? ORDER BY seq", (ctx.since, last)):
            e = _json(js)
            if kind == "ORDER":
                sh = e.get("shadow") or ""
                tags = e.get("tags") or {}
                out.append(_row(ctx, "R36", "order", f"order:{seq}", t, seq=seq, trade_id=xid, coin=coin, setup=e.get("setup"),
                                type=e.get("type"), limit=e.get("limit"), shadow=sh,
                                group="real" if not sh else sh, tags={k: tags.get(k) for k in R36_TAGS if k in tags},
                                catch_up=e.get("catch_up"), rulebook=e.get("rulebook"),
                                would="TRADE" if not sh else f"SHADOW ({sh})"))
            else:
                out.append(_row(ctx, "R36", "fill", f"fill:{seq}", t, seq=seq, trade_id=xid, coin=coin, setup=e.get("setup"),
                                type=e.get("type"), entry=e.get("entry"), stop=e.get("stop"), target=e.get("target"),
                                catch_up=e.get("catch_up"), would="FILLED"))
    finally:
        con.close()
    return out


def _ema_hold(D: list[tuple], btc: list[tuple]) -> dict | None:
    """portfolio_layer.rate's IN/OUT (hold) from daily closes: close above EMA20 and EMA50, and Bitcoin above its EMA50."""
    from src.research import reads as R

    if len(D) < 50 or len(btc) < 50:
        return None
    c = [x[4] for x in D]
    e20, e50 = R.ema(c, 20)[-1], R.ema(c, 50)[-1]
    bc = [x[4] for x in btc]
    b50 = R.ema(bc, 50)[-1]
    on = c[-1] > e50 and c[-1] > e20 and bc[-1] > b50
    return {"hold": bool(on), "close": c[-1], "ema20": e20, "ema50": e50, "btc_close": bc[-1], "btc_ema50": b50, "candle_t": D[-1][0]}


def _t3_rating(ctx: Ctx, coin: str, t: int) -> dict:
    for name, src in (("portfolio_book.sqlite", "T3 lab 10"), ("portfolio_book_t30.sqlite", "T3 30-coin tier")):
        p = ctx.dir / name
        if not p.exists():
            continue
        con = _ro(p)
        try:
            r = con.execute("SELECT day_t, json FROM decisions WHERE day_t <= ? ORDER BY day_t DESC LIMIT 1", (t,)).fetchone()
        finally:
            con.close()
        if r:
            rt = (_json(r[1]).get("ratings") or {}).get(coin)
            if rt:
                return {"source": src, "day_t": r[0], "rating": rt.get("rating"), "hold": bool(rt.get("hold")), "why": rt.get("why")}
    D1 = ctx.d1()
    D = [x for x in D1.get(coin, []) if x[0] + DAY <= t]
    B = [x for x in D1.get("BTC", []) if x[0] + DAY <= t]
    h = _ema_hold(D, B)
    return {"source": "computed from universe daily candles", **(h or {"hold": None})}


def r37(ctx: Ctx) -> list[dict]:
    """Each bold decision from the window on: what it picked and its plan, whether its text cites T3 (the card id or an alias),
    and T3's rating of that coin at that close (IN = hold true)."""
    seen = ctx.ids("R37")
    con = ctx.db()
    out = []
    try:
        rows = con.execute("SELECT id, day, t, dial, action, coin, plan, price, stop, thesis, why, trade_id, random_id, note "
                           "FROM bold_decisions WHERE t >= ? ORDER BY t", (ctx.since,)).fetchall()
    finally:
        con.close()
    for bid, day, t, dial, act, coin, plan, price, stop, thesis, why, tid, rid, note in rows:
        if f"bold:{bid}" in seen:
            continue
        text = f"{thesis or ''} {why or ''}".lower()
        cites = [a for a in T3_ALIASES if a in text]
        rating = _t3_rating(ctx, coin, int(t)) if coin else None
        out.append(_row(ctx, "R37", "bold", f"bold:{bid}", t, bold_id=bid, day=day, dial=dial, action=act, coin=coin, plan=plan,
                        price=price, stop=stop, trade_id=tid, random_id=rid, has_twin=bool(rid), note=note,
                        thesis=(thesis or "")[:1200], why_text=(why or "")[:1200], cites_t3=bool(cites), cited_as=cites,
                        t3=rating, would=act))
    return out


def _units_at(fills: list[tuple], t: int) -> float:
    """fills: (t, side, units) -> units held at t."""
    return sum(u if s == "BUY" else -u for ft, s, u in fills if ft <= t)


def r38(ctx: Ctx) -> list[dict]:
    """Each missed-moves row from the window on, with the frozen allowed books (REVIEW_38) that were in the move: evidence trades
    entered by two hours after the low and not closed before it; the $500 book, the T3 books and Madhav's fills holding the coin at
    the low or buying it by two hours after. No money is read (caught_pnl_usd and caught_books are never copied)."""
    seen = ctx.ids("R38")
    con = ctx.db()
    out = []
    try:
        moves = con.execute("SELECT id, day, coin, low_t, high_t, low, high, move_pct, move_atr, label, saw, kind, at_zone, regime, "
                            "pattern, tier, miss_class, caught_allowed FROM missed_moves WHERE day >= ? ORDER BY day, id",
                            (_day(ctx.since),)).fetchall()
        b500 = [(t, c, s, q) for t, c, s, q in con.execute("SELECT t, coin, side, qty FROM book500_fills")]
        man = [(t, c, s, u) for t, c, s, u in con.execute("SELECT t, coin, side, units FROM manual_fills")]
        ev = con.execute("SELECT id, watch, coin, entry_t, exit_t FROM evidence_trades WHERE entry_t IS NOT NULL").fetchall()
    finally:
        con.close()
    t3: dict[str, list] = {}
    for name, book in (("portfolio_book.sqlite", "T3"), ("portfolio_book_t30.sqlite", "T3_T30")):
        p = ctx.dir / name
        if p.exists():
            c2 = _ro(p)
            try:
                t3[book] = [_json(x) for (x,) in c2.execute("SELECT json FROM fills ORDER BY t, seq")]
            finally:
                c2.close()
    for (mid, day, coin, low_t, high_t, low, high, pct, katr, label, saw, kind, zone, regime, pattern, tier, mclass,
         code_allowed) in moves:
        if f"move:{mid}" in seen or low_t is None:
            continue
        lt = int(low_t)
        ins = []
        for tid, w, c, et, xt in ev:
            if c == coin and _base(w) in R38_ALLOWED_WATCHES and et <= lt + R38_AFTER and (xt is None or xt >= lt):
                ins.append({"book": _base(w), "watch": w, "id": tid, "entry_t": et, "open_at_log": xt is None})
        for book, fills in (("BOOK500", [(t, s, q) for t, c, s, q in b500 if c == coin]),
                            ("MANUAL", [(t, s, u) for t, c, s, u in man if c == coin]),
                            *((b, [(f["t"], f["side"], (f["usd"] / f["px"]) if f.get("px") else 0.0) for f in fs
                                   if f.get("book") == "MAIN" and f.get("coin") == coin]) for b, fs in t3.items())):
            held = _units_at(fills, lt) > 1e-12
            bought = any(lt < ft <= lt + R38_AFTER and s == "BUY" for ft, s, _ in fills)
            if held or bought:
                ins.append({"book": book, "held_at_low": held, "bought_within_2h": bought})
        out.append(_row(ctx, "R38", "move", f"move:{mid}", _day_t(day), move_id=mid, day=day, coin=coin, tier=tier or "LIVE10",
                        low_t=lt, high_t=high_t, low=low, high=high, move_pct=pct, move_atr=katr, label=label, saw=_json(saw),
                        kind_of_move=kind, at_zone=zone, regime=regime, pattern=pattern, miss_class=mclass,
                        code_caught_allowed=code_allowed, allowed_in_it=ins,
                        would="CAUGHT_ALLOWED" if ins else "NOT_CAUGHT_ALLOWED"))
    return out


# ----------------------------------------------------------------------------------------------------------------------------- 5-minute bars
def archive_bars5m(ctx: Ctx) -> dict:
    """Copy each complete UTC day of the feed's 5-minute bars (close, high, low per coin) not yet copied into bars5m_YYYY-MM.sqlite.
    The feed keeps 14 days, so a lane that was down up to 13 days loses nothing. Nothing reads these files before day 60."""
    st_p = ctx.root / "bars5m_state.json"
    try:
        st = json.loads(st_p.read_text())
    except (OSError, ValueError):
        st = {}
    con = ctx.db("universe_bars.sqlite")
    try:
        lo, hi = con.execute("SELECT MIN(t), MAX(t) FROM m5").fetchone()
        if lo is None:
            return {"days": 0, "rows": 0}
        first = max(int(lo // DAY * DAY) + (DAY if lo % DAY else 0), _day_t(st["last_day"]) + DAY if st.get("last_day") else 0)
        days, rows = [], 0
        d0 = first
        while d0 + DAY <= int(hi) + 300 and d0 + DAY <= ctx.now:
            bars = con.execute("SELECT coin, t, h, l, c FROM m5 WHERE t >= ? AND t < ?", (d0, d0 + DAY)).fetchall()
            if bars:
                p = ctx.root / f"bars5m_{_day(d0)[:7]}.sqlite"
                ctx.root.mkdir(parents=True, exist_ok=True)
                out = sqlite3.connect(str(p))
                try:
                    out.execute("CREATE TABLE IF NOT EXISTS bars5m (coin TEXT, t INTEGER, h REAL, l REAL, c REAL, PRIMARY KEY (coin, t)) "
                                "WITHOUT ROWID")
                    out.executemany("INSERT OR IGNORE INTO bars5m VALUES (?,?,?,?,?)", bars)
                    out.commit()
                finally:
                    out.close()
                rows += len(bars)
            days.append(_day(d0))
            st["last_day"] = _day(d0)
            d0 += DAY
    finally:
        con.close()
    if days:
        st_p.write_text(json.dumps(st))
    return {"days": len(days), "rows": rows, "through": st.get("last_day")}


# ----------------------------------------------------------------------------------------------------------------------------- rounds
DAILY_RULES = (("R31", r31), ("R32", r32), ("R33", r33), ("R34", r34), ("R36", r36), ("R37", r37), ("R38", r38),
               ("LANE_wakes", lane_wakes))
INTRADAY_RULES = (("R35", r35), ("R32_x5m", r32x))


def _round(j, kind: str, rules, root, now, since, extra: Callable[[Ctx], dict] | None = None) -> dict:
    ctx = Ctx(j, root, now, since)
    rows, by, errors = [], {}, {}
    for name, fn in rules:
        try:
            got = fn(ctx)
            rows += got
            by[name] = len(got)
        except Exception as exc:  # noqa: BLE001  one rule failing never stops the others
            errors[name] = _errlog(ctx.root, f"{kind} {name}", exc)
            rows.append(_row(ctx, "LANE", "error", f"error:{kind}:{name}:{int(ctx.now)}", ctx.now, rule=name, error=errors[name]))
    bars = None
    if extra:
        try:
            bars = extra(ctx)
        except Exception as exc:  # noqa: BLE001
            errors["bars5m"] = _errlog(ctx.root, f"{kind} bars5m", exc)
    rows.append(_row(ctx, "LANE", "run", f"run:{kind}:{int(ctx.now)}", ctx.now, round=kind, rows_by_rule=by, errors=sorted(errors),
                     bars5m=bars, since=ctx.since))
    n = append(rows, ctx.root)
    v = verify(ctx.root)
    if kind == "daily":
        status = "ok" if v["ok"] and not errors else "; ".join(([] if v["ok"] else [v["note"]]) + [f"{k} failed" for k in sorted(errors)])
        try:
            with (ctx.root / RUN_LOG).open("a") as fh:
                fh.write(f"[{time.strftime('%Y-%m-%d %H:%M', time.gmtime(ctx.now))}] daily rows={n} status={status}\n")
        except OSError as exc:
            _errlog(ctx.root, "run.log", exc)
    return {"round": kind, "rows": n, "rows_by_rule": by, "errors": sorted(errors), "verify_ok": v["ok"], "chain_rows": v["rows"],
            "bars5m": bars}


def run_daily(j, root: str | Path | None = None, now: float | None = None, since: float | None = None) -> dict:
    """After the daily close: every daily rule, the day's brain wakes, and the 5-minute bar copy."""
    return _round(j, "daily", DAILY_RULES, root, now, since, archive_bars5m)


def run_15m(j, root: str | Path | None = None, now: float | None = None, since: float | None = None) -> dict:
    """Every 15 minutes: the attention board and the intraday breakout cross."""
    return _round(j, "15m", INTRADAY_RULES, root, now, since)


def guarded(kind: str, fn: Callable, *a, **kw) -> dict:
    """Never raises: an exception is written to errors.log with its time and returned as {"error": ...}."""
    try:
        return fn(*a, **kw)
    except Exception as exc:  # noqa: BLE001  the shadow lane never breaks the round that calls it
        return {"error": _errlog(shadow_dir(kw.get("root")), f"{kind} round", exc)}


def hook_daily(j, out: dict) -> None:
    """The one call the daily close makes (universe_watch.run_daily). Its result is not an *_error key, so a shadow failure never
    marks the round's own steps as failed; the run checker's shadow_lane part reports it instead."""
    out["shadow"] = guarded("daily", run_daily, j)


def hook_15m(j, out: dict) -> None:
    """The one call the 15-minute jobs make (app.background_jobs)."""
    out["shadow"] = guarded("15m", run_15m, j)


# ----------------------------------------------------------------------------------------------------------------------------- CLI
class _Agent:
    def __init__(self, d: str, now: float):
        self.dir, self._now = Path(d).expanduser(), now

    def now(self) -> float:
        return self._now


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m jarvis.service.shadow")
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("verify")
    v.add_argument("--root")
    d = sub.add_parser("dry-run", help="one daily and one 15-minute round on the live data, read-only, into a separate folder")
    d.add_argument("--agent", default=os.getenv("ANANTA_AGENT_DIR", str(Path.home() / "code" / "ananta-decision-agent")))
    d.add_argument("--out", required=True)
    d.add_argument("--since", help="UTC date; default today (rows before the window are flagged in_window=false)")
    a = ap.parse_args(argv)
    if a.cmd == "verify":
        r = verify(a.root)
        print(json.dumps(r))
        return 0 if r["ok"] else 1
    out = Path(a.out).expanduser()
    real = Path(os.getenv("ANANTA_RUNS_DIR", str(Path.home() / "ananta_runs"))).expanduser() / "shadow"
    if out.resolve() == real.resolve():
        print("refused: a dry run never writes the real log", file=sys.stderr)
        return 2
    now = time.time()
    since = _day_t(a.since) if a.since else int(now // DAY * DAY)
    ag = _Agent(a.agent, now)
    res = {"daily": run_daily(ag, out, now, since), "15m": run_15m(ag, out, now, since), "verify": verify(out)}
    print(json.dumps(res, indent=1, default=str))
    return 0 if res["verify"]["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
