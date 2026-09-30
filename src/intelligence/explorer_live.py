"""Live Explorer: Rulebook v0 in paper, every 15 minutes, on closed candles from Hands (Agent -> Hands HTTP only).

    .venv/bin/python -u -m src.intelligence.explorer_live run          # the loop (one instance only)
    .venv/bin/python -m src.intelligence.explorer_live status          # account, open trades, suggestions
    .venv/bin/python -m src.intelligence.explorer_live report          # write + push today's daily report now
    .venv/bin/python -m src.intelligence.explorer_live reconstruct     # R1: rebuild every decision from stored bars

Same engine as the history replay (explorer_engine). Paper only: no orders anywhere, never writes Hands' database.
Files (in the Agent folder): explorer_state.pkl, explorer_book.sqlite, explorer_bars.sqlite,
explorer_decisions.jsonl, explorer_daily/DATE.md, explorer.lock
"""
from __future__ import annotations

import json
import os
import pickle
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from src.intelligence import explorer_engine as xe

VERSION = "explorer.live.v0.1"
START_CAPITAL = 2000.0
MAX_OPEN, MAX_DAY = 20, 30            # N4
WARM_LIMITS = {"1d": 540, "4h": 300, "1h": 750, "30m": 719, "15m": 719, "5m": 719}
STEP_LIMITS = {"1d": 3, "4h": 4, "1h": 6, "30m": 8, "15m": 12, "5m": 36}
REPORT_HOUR_LOCAL = 21
LOCAL_TZ = "America/Toronto"
ORDER = ["BTC"] + [c for c in xe.COINS if c != "BTC"]   # BTC first: it is the others' context


def _utc(t: float) -> str:
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d %H:%M")


# ---------------------------------------------------------------------------
# Hands access (HTTP only)
# ---------------------------------------------------------------------------
class Hands:
    def __init__(self):
        self._tok, self._tok_t = None, 0.0

    def _headers(self):
        from src.tools import ananta_api

        if self._tok is None or time.time() - self._tok_t > 1800:
            from src.intelligence.paper_watch import _token

            self._tok, _ = _token()
            self._tok_t = time.time()
        return ananta_api.get_headers(self._tok)

    def candles(self, coin: str, tf: str, limit: int) -> list[tuple]:
        import requests

        from src.tools import ananta_api

        r = requests.get(f"{ananta_api.BASE_URL}/api/market/candles", params={"symbol": f"{coin}/USD", "timeframe": tf, "limit": limit},
                         headers=self._headers(), timeout=45)
        r.raise_for_status()
        j = r.json()
        if j.get("timeframe") != tf:
            raise RuntimeError(f"Hands served {j.get('timeframe')} for {tf}: update/restart Hands")
        return [(int(c["t"]) // 1000, float(c["open"]), float(c["high"]), float(c["low"]), float(c["close"]), float(c["volume"]))
                for c in j.get("candles") or []]

    def kill_switch_on(self) -> bool:
        import requests

        from src.tools import ananta_api

        r = requests.get(f"{ananta_api.BASE_URL}/api/risk/status", headers=self._headers(), timeout=30)
        r.raise_for_status()
        return bool((r.json().get("status") or {}).get("manual_kill"))


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------
class Store:
    def __init__(self, base: Path):
        self.base = base
        self.book = sqlite3.connect(str(base / "explorer_book.sqlite"))
        self.book.executescript("""
            CREATE TABLE IF NOT EXISTS events (seq INTEGER PRIMARY KEY AUTOINCREMENT, t INTEGER, kind TEXT, coin TEXT, id TEXT, json TEXT);
            CREATE TABLE IF NOT EXISTS trades (id TEXT PRIMARY KEY, coin TEXT, shadow TEXT, exit_t INTEGER, net REAL, json TEXT);
        """)
        self.bars = sqlite3.connect(str(base / "explorer_bars.sqlite"))
        self.bars.executescript("CREATE TABLE IF NOT EXISTS bars (coin TEXT, tf TEXT, t INTEGER, o REAL, h REAL, l REAL, c REAL, v REAL, PRIMARY KEY (coin, tf, t));")

    def event(self, e: dict) -> None:
        self.book.execute("INSERT INTO events (t, kind, coin, id, json) VALUES (?,?,?,?,?)",
                          (int(e.get("t") or 0), e["kind"], e.get("coin"), e.get("id"), json.dumps(e, default=str)))

    def trade(self, row: dict) -> None:
        self.book.execute("INSERT OR REPLACE INTO trades VALUES (?,?,?,?,?,?)",
                          (row["id"], row["coin"], row["shadow"], row.get("ACTUAL_exit_t"), row.get("ACTUAL_net"), json.dumps(row, default=str)))

    def save_bars(self, coin: str, tf: str, bars: list[tuple]) -> None:
        self.bars.executemany("INSERT OR IGNORE INTO bars VALUES (?,?,?,?,?,?,?,?)", [(coin, tf, *b) for b in bars])

    def load_bars(self, coin: str) -> dict[str, list[tuple]]:
        out = {tf: [] for tf in xe.TF_S}
        for tf, t, o, h, lo, c, v in self.bars.execute("SELECT tf, t, o, h, l, c, v FROM bars WHERE coin=? ORDER BY t", (coin,)):
            out[tf].append((t, o, h, lo, c, v))
        return out

    def commit(self) -> None:
        self.book.commit()
        self.bars.commit()


def events_of(bars_by_tf: dict[str, list[tuple]], after: dict[str, int] | None = None) -> list[tuple]:
    """(close_t, rank, tf, bar) in engine order; only bars opening after `after[tf]`."""
    ev = []
    for rank, tf in enumerate(xe.ORDER_TF):
        lo = (after or {}).get(tf, -1)
        ev.extend((b[0] + xe.TF_S[tf], rank, tf, b) for b in bars_by_tf.get(tf, []) if b[0] > lo)
    ev.sort(key=lambda e: (e[0], e[1]))
    return ev


# ---------------------------------------------------------------------------
# The Explorer
# ---------------------------------------------------------------------------
class Explorer:
    def __init__(self, base: Path | str = ".", hands: Any = None, now: Callable[[], float] = time.time,
                 alert: Callable[[str, str, str], None] | None = None):
        self.base = Path(base)
        self.hands = hands or Hands()
        self.now = now
        self.alert = alert or _phone
        self.store = Store(self.base)
        self.state_path = self.base / "explorer_state.pkl"
        self.decisions = self.base / "explorer_decisions.jsonl"
        self.st: dict[str, Any] = {}
        if self.state_path.exists():
            self.st = pickle.loads(self.state_path.read_bytes())
            for eng in self.st["engines"].values():
                self._attach(eng)

    # -- account and context --
    def _btc_ctx(self, T: int) -> dict:
        hist = self.st.get("btc_hist", [])
        best = None
        for t, v in reversed(hist):
            if t <= T:
                best = (t, v)
                break
        return best[1] if best and T - best[0] <= 2 * 3600 else {}

    def _slot_ok(self, coin: str, typ: str):
        if self.st.get("kill"):
            return "KILL_SWITCH"
        engines = self.st["engines"].values()
        open_n = sum(1 for e in engines for t in e.trades if t.shadow is None and not t.actual.done) + sum(
            1 for e in engines for o in e.orders if o.shadow is None)
        day = int(self.now() // 86400)
        if open_n >= MAX_OPEN or self.st["entries_by_day"].get(day, 0) >= MAX_DAY:
            return "CAP"
        return True

    def _on_event(self, e: dict) -> None:
        e = {**e, "rulebook": xe.RULEBOOK, "evidence": xe.EVIDENCE_CLASS, "catch_up": bool(self.now() - (e.get("t") or 0) > 1500)}
        self.store.event(e)
        if e.get("shadow"):
            return
        k = e["kind"]
        if k == "ORDER":
            d = int((e.get("t") or self.now()) // 86400)
            self.st["entries_by_day"][d] = self.st["entries_by_day"].get(d, 0) + 1
        elif k == "FILLED":
            self.alert("Ananta Explorer: paper buy", f"{e['coin']} {e['setup']} {e['type']} at {e['entry']:.6g}, stop {e['stop']:.6g}"
                       + (f", target {e['target']:.6g}" if e.get("target") else ""), "EVENT")
        elif k == "CLOSED":
            self.alert("Ananta Explorer: paper exit", f"{e['coin']} {e['setup']} {e['type']} {e['bell']} net ${e['net_usd']:+.2f}", "EVENT")
        elif k == "MISSED":
            self.alert("Ananta Explorer: missed entry", f"{e['coin']} {e['setup']} {e['type']} limit not filled; following it as a shadow", "INFO")

    def _attach(self, eng: xe.CoinEngine) -> None:
        eng.attach(btc_ctx=self._btc_ctx, slot_ok=self._slot_ok, on_event=self._on_event)

    # -- feeding --
    def _feed(self, coin: str, eng: xe.CoinEngine, ev: list[tuple], log: bool) -> int:
        scans, i, n = 0, 0, len(ev)
        while i < n:
            T = ev[i][0]
            while i < n and ev[i][0] == T:
                eng.on_bar(ev[i][2], ev[i][3])
                if coin == "BTC" and ev[i][2] == "1h":
                    v = eng.btc_view()
                    if v:
                        self.st["btc_hist"].append((v["btc_1h_close_t"], v))
                        self.st["btc_hist"] = self.st["btc_hist"][-800:]
                i += 1
            if T % 900 == 0:
                rec = eng.scan(T)
                scans += 1
                if log and T >= eng.trade_from_t:
                    rec["catch_up"] = bool(self.now() - T > 1500)
                    with self.decisions.open("a") as f:
                        f.write(json.dumps(rec, default=str) + "\n")
        for row in eng.trade_rows(eng.actual_closed):   # the real exit, as soon as it happens
            self.store.trade(row)
        eng.actual_closed = []
        for row in eng.trade_rows():                    # full rows once every shadow variant has finished
            self.store.trade(row)
        eng.closed = []
        return scans

    def start(self) -> dict:
        """Warm up from Hands' history (no trades before now), or resume the saved state."""
        if self.st:
            return {"resumed": True, "trade_from": _utc(self.st["trade_from_t"])}
        now = self.now()
        tfrom = int(now // 900) * 900 + 900
        self.st = {"version": VERSION, "rulebook": xe.RULEBOOK, "trade_from_t": tfrom, "engines": {}, "last_open": {},
                   "btc_hist": [], "entries_by_day": {}, "kill": False, "last_report_day": None, "started": now}
        for coin in ORDER:
            eng = xe.CoinEngine(coin, trade_from_t=tfrom)
            self._attach(eng)
            bars = {tf: [b for b in self.hands.candles(coin, tf, lim) if b[0] + xe.TF_S[tf] <= now] for tf, lim in WARM_LIMITS.items()}
            for tf, b in bars.items():
                self.store.save_bars(coin, tf, b)
            self._feed(coin, eng, events_of(bars), log=False)
            self.st["engines"][coin] = eng
            self.st["last_open"][coin] = {tf: (b[-1][0] if b else -1) for tf, b in bars.items()}
        self.store.commit()
        self._save()
        return {"resumed": False, "trade_from": _utc(tfrom), "ready": {c: e.ready() for c, e in self.st["engines"].items()}}

    def step(self) -> dict:
        now = self.now()
        out: dict[str, Any] = {"t": _utc(now), "errors": [], "scans": 0}
        try:
            kill = self.hands.kill_switch_on()
        except Exception as exc:  # noqa: BLE001
            kill = self.st.get("kill", False)
            out["errors"].append(f"kill-switch read failed: {str(exc)[:120]}")
        if kill and not self.st.get("kill"):
            n = sum(e.force_exit_all("X2_KILL_SWITCH") for e in self.st["engines"].values())
            self.alert("Ananta Explorer: KILL SWITCH", f"Hands kill switch is on. {n} paper exits at the next 5m open; no new entries.", "ERROR")
        self.st["kill"] = kill
        for coin in ORDER:
            eng = self.st["engines"][coin]
            try:
                bars = {}
                for tf, lim in STEP_LIMITS.items():
                    step = xe.TF_S[tf]
                    last = self.st["last_open"][coin].get(tf, -1)
                    if last + 2 * step <= now:                      # a new bar of this timeframe has closed
                        gap = int((now - last) // step) + 3 if last > 0 else lim   # catch up after a sleep
                        bars[tf] = [b for b in self.hands.candles(coin, tf, min(719, max(lim, gap))) if b[0] + step <= now]
                for tf, b in bars.items():
                    self.store.save_bars(coin, tf, b)
                ev = events_of(bars, self.st["last_open"][coin])
                out["scans"] += self._feed(coin, eng, ev, log=True)
                for tf, b in bars.items():
                    if b:
                        self.st["last_open"][coin][tf] = max(self.st["last_open"][coin].get(tf, -1), b[-1][0])
            except Exception as exc:  # noqa: BLE001  one coin failing never stops the others
                out["errors"].append(f"{coin}: {str(exc)[:160]}")
        self.store.commit()
        self._save()
        self._maybe_report()
        return out

    def _save(self) -> None:
        tmp = self.state_path.with_suffix(".tmp")
        tmp.write_bytes(pickle.dumps(self.st))
        tmp.replace(self.state_path)

    # -- reports (P2 / P3) --
    def status(self) -> dict:
        engines = self.st["engines"]
        rows, unreal = [], 0.0
        for coin, eng in engines.items():
            px = eng.tf["5m"].last[4] if eng.tf["5m"].last else None
            for tr in eng.trades:
                if tr.shadow is not None or px is None or tr.actual.done:
                    continue
                a = tr.actual
                pnl = xe.NOTIONAL * (px / tr.entry - 1)
                unreal += pnl
                why, sug = [], "HOLD"
                if a.stop is not None and px <= a.stop + 0.3 * a.R:
                    why.append("X1: price within 0.3R of the stop")
                    sug = "EXIT-SOON"
                if a.target is not None and px >= a.target - 0.3 * a.R:
                    why.append("X4: within 0.3R of the target")
                    sug = "TIGHTEN" if sug == "HOLD" else sug
                if a.typ == "LONG_TERM" and px >= tr.entry + a.R:
                    why.append("LONG_TERM above +1R: trail can start at +2R")
                    sug = "TIGHTEN" if sug == "HOLD" else sug
                if not why:
                    why.append("no bell close")
                rows.append({"coin": coin, "id": tr.id, "setup": tr.setup, "type": tr.typ, "entry": tr.entry, "price": px,
                             "stop": a.stop, "target": a.target, "pnl_usd": round(pnl, 2), "since": _utc(tr.entry_t),
                             "suggestion": sug, "why": "; ".join(why)})
        realized = self.store.book.execute("SELECT COALESCE(SUM(net),0), COUNT(*) FROM trades WHERE shadow=''").fetchone()
        return {"version": VERSION, "rulebook": xe.RULEBOOK, "trade_from": _utc(self.st["trade_from_t"]), "kill_switch": self.st.get("kill"),
                "equity": round(START_CAPITAL + realized[0] + unreal, 2), "realized_usd": round(realized[0], 2), "closed_trades": realized[1],
                "unrealized_usd": round(unreal, 2), "open": rows,
                "pending_orders": [{"coin": o.coin, "setup": o.setup, "type": o.typ, "limit": o.limit, "expires": _utc(o.expires_t)}
                                   for e in engines.values() for o in e.orders if o.shadow is None]}

    def report(self, day_local: str | None = None) -> Path:
        from zoneinfo import ZoneInfo

        tz = ZoneInfo(LOCAL_TZ)
        now_l = datetime.fromtimestamp(self.now(), tz)
        day = day_local or now_l.strftime("%Y-%m-%d")
        start = datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=tz).timestamp()
        s = self.status()
        closed = [json.loads(j) for (j,) in self.store.book.execute(
            "SELECT json FROM trades WHERE shadow='' AND exit_t >= ? AND exit_t < ?", (int(start), int(start + 86400)))]
        by: dict[str, list] = {}
        for r in closed:
            by.setdefault(f"{r['type']} / {r['setup']}", []).append(r["ACTUAL_net"])
        lines = [f"# Ananta Explorer daily report, {day}", "",
                 f"Rulebook {xe.RULEBOOK}, paper only. Account ${s['equity']:,.2f} (start ${START_CAPITAL:,.0f}); "
                 f"realized ${s['realized_usd']:+.2f}, open P&L ${s['unrealized_usd']:+.2f}. Kill switch: {'ON' if s['kill_switch'] else 'off'}.", "",
                 "## Open trades and suggestions", ""]
        if s["open"]:
            lines += ["| Coin | Setup | Type | Entry | Now | P&L | Suggestion | Why |", "|---|---|---|---|---|---|---|---|"]
            lines += [f"| {r['coin']} | {r['setup']} | {r['type']} | {r['entry']:.6g} | {r['price']:.6g} | ${r['pnl_usd']:+.2f} | {r['suggestion']} | {r['why']} |" for r in s["open"]]
        else:
            lines.append("None.")
        lines += ["", "## Closed today", ""]
        if closed:
            lines += ["| Type / setup | Trades | Net |", "|---|---|---|"]
            lines += [f"| {k} | {len(v)} | ${sum(v):+.2f} |" for k, v in sorted(by.items())]
        else:
            lines.append("None.")
        lines += ["", f"Pending limit orders: {len(s['pending_orders'])}."]
        d = self.base / "explorer_daily"
        d.mkdir(exist_ok=True)
        p = d / f"{day}.md"
        p.write_text("\n".join(lines) + "\n")
        sug = [f"{r['coin']} {r['suggestion']}" for r in s["open"] if r["suggestion"] != "HOLD"]
        self.alert("Ananta daily report", f"Account ${s['equity']:,.0f}; open {len(s['open'])}; closed today {len(closed)} "
                   f"(${sum(r['ACTUAL_net'] for r in closed):+.2f})" + (f"; {', '.join(sug)}" if sug else "; all HOLD"), "EVENT")
        return p

    def _maybe_report(self) -> None:
        from zoneinfo import ZoneInfo

        now_l = datetime.fromtimestamp(self.now(), ZoneInfo(LOCAL_TZ))
        day = now_l.strftime("%Y-%m-%d")
        if now_l.hour >= REPORT_HOUR_LOCAL and self.st.get("last_report_day") != day:
            self.report(day)
            self.st["last_report_day"] = day
            self._save()


# ---------------------------------------------------------------------------
# R1 reconstruction: rebuild every decision from the stored bars with a fresh engine
# ---------------------------------------------------------------------------
def reconstruct(base: Path | str = ".") -> dict:
    base = Path(base)
    store = Store(base)
    live = pickle.loads((base / "explorer_state.pkl").read_bytes())
    logged = [json.loads(j) for (j,) in store.book.execute("SELECT json FROM events WHERE kind IN ('ORDER','FILLED','CLOSED') ORDER BY seq")]
    key = lambda e: (e["kind"], e.get("coin"), int(e.get("t") or 0), e.get("setup"), e.get("type"), e.get("shadow") or "")  # noqa: E731
    rebuilt: list[dict] = []
    btc_hist: list = []

    def ctx(T):
        best = [v for t, v in btc_hist if t <= T]
        return best[-1] if best and T - [t for t, _ in btc_hist if t <= T][-1] <= 2 * 3600 else {}

    last_t = max((int(e.get("t") or 0) for e in logged), default=0)
    for coin in ORDER:
        eng = xe.CoinEngine(coin, trade_from_t=live["trade_from_t"])
        eng.attach(btc_ctx=ctx, on_event=lambda e: rebuilt.append(e))
        bars = store.load_bars(coin)
        ev = events_of(bars)
        i = 0
        while i < len(ev):
            T = ev[i][0]
            while i < len(ev) and ev[i][0] == T:
                eng.on_bar(ev[i][2], ev[i][3])
                if coin == "BTC" and ev[i][2] == "1h":
                    v = eng.btc_view()
                    if v:
                        btc_hist.append((v["btc_1h_close_t"], v))
                i += 1
            if T % 900 == 0:
                eng.scan(T)
    rebuilt = [e for e in rebuilt if e["kind"] in ("ORDER", "FILLED", "CLOSED") and int(e.get("t") or 0) <= last_t]
    a = sorted(map(key, [e for e in logged if not e.get("shadow")]))
    b = sorted(map(key, [e for e in rebuilt if not e.get("shadow")]))
    only_live = [x for x in a if x not in b]
    only_rebuilt = [x for x in b if x not in a]
    res = {"logged_real_events": len(a), "rebuilt_real_events": len(b), "match": not only_live and not only_rebuilt,
           "only_in_live": only_live[:20], "only_in_rebuilt": only_rebuilt[:20],
           "note": "Real (non-shadow) decisions only; the account caps are not re-applied in the rebuild."}
    (base / "explorer_reconstruct.json").write_text(json.dumps(res, indent=1, default=str))
    return res


# ---------------------------------------------------------------------------
def _phone(title: str, body: str, level: str) -> None:
    from src.intelligence.paper_watch import notify

    notify(title, body, level=level)


def run_forever() -> None:
    from src.intelligence.paper_watch import acquire_single_instance

    lock = acquire_single_instance(Path("explorer.lock"))
    if lock is None:
        raise SystemExit("Another Ananta Explorer is already running. Check with: pgrep -fl explorer_live")
    ex = Explorer()
    info = ex.start()
    _phone("Ananta Explorer started", f"{VERSION} {xe.RULEBOOK}: paper, every 15 min; trading from {info['trade_from']} UTC", "INFO")
    print(f"[{_utc(time.time())}] started {info}", flush=True)
    last_recon_day = None
    while True:
        wait = 900 - (time.time() % 900) + 60     # one minute after each 15m close
        time.sleep(wait)
        try:
            r = ex.step()
            s = ex.status()
            print(f"[{r['t']}] scans={r['scans']} open={len(s['open'])} pending={len(s['pending_orders'])} equity={s['equity']} "
                  f"errors={r['errors']}", flush=True)
            if r["errors"]:
                _phone("Ananta Explorer error", "; ".join(r["errors"])[:200], "WARN")
            day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            if day != last_recon_day and datetime.now(timezone.utc).hour == 0:
                rc = reconstruct()
                last_recon_day = day
                if not rc["match"]:
                    _phone("Ananta Explorer: reconstruction mismatch", f"{len(rc['only_in_live'])} live-only / {len(rc['only_in_rebuilt'])} rebuilt-only decisions; see explorer_reconstruct.json", "WARN")
        except Exception as exc:  # noqa: BLE001
            print(f"[{_utc(time.time())}] ERROR {exc}", flush=True)
            _phone("Ananta Explorer error", str(exc)[:200], "ERROR")


def main(argv=None) -> None:
    cmd = (argv or sys.argv[1:] or ["status"])[0]
    if cmd == "run":
        run_forever()
    elif cmd == "status":
        print(json.dumps(Explorer().status(), indent=1, default=str))
    elif cmd == "report":
        print(Explorer().report())
    elif cmd == "reconstruct":
        print(json.dumps(reconstruct(), indent=1, default=str))
    else:
        raise SystemExit(f"unknown command {cmd!r}: use run | status | report | reconstruct")


if __name__ == "__main__":
    main()
