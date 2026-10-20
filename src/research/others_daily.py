"""Other traders, every day, held against Ananta (Madhav, 2026-10-20: "why are we not doing it on daily basis, that's how we learn.
Why wait?"; decision OD-HL-FILLS (a) for the capture itself: worker/hl_capture.py).

Reference only (docs/LOCK.md, D8): other traders are reference and event generators, never teachers or copy signals. This file
reads the worker's day files of other traders' fills and Ananta's own logs and databases, read-only, and writes three things: a page
in plain words, one row of history and, when a situation repeats, one repair-board request worded as a DRAFT finding through the
repair board's own function (jarvis.service.requests_log.add). It makes no network call and has no code that places, changes or
cancels an order, a setting or a rule (tests/test_hl_daily.py checks it).

THE FIXED RULES (written 2026-10-20, before any captured day was read; they change only with Madhav's yes)
 1. Input: the pulled day files (~/ananta_worker_data/hl_YYYY-MM-DD.sqlite) for the day and up to 13 days before it, per account only
    the unbroken run of days that ends on the day (a missing file, an account that GAVE_UP or was truncated on a day breaks the run:
    a trip cannot be rebuilt honestly across a hole). Round trips are rebuilt per account with hl_bench.round_trips (flat to flat; a
    position already open at the start of the run is not scored). The day's cases are the trips that CLOSED on that UTC day.
 2. Dropped and counted: market makers and HFT by review #2's trip rule (hl_bench.is_hft: median hold under 10 minutes or more than
    200 trips a week) on the account's trips in its run. The 6 accounts review #2 itself dropped by that rule are not even captured
    (they are left out of hl_accounts.json; an older list's r2_hft flag is still honoured).
 3. Coins: Hyperliquid's name mapped to ours (kPEPE -> PEPE; renames as tier30.RENAMED; spot "@n", pairs and builder markets left out).
    Groups, in this order: LAB10 (the 10 live coins), T30 (the rest of the 30-coin tier), UNIV-A / UNIV-B / UNIV-C (the rest of the
    watched universe by registry tier). Anything else is OUTSIDE: counted, not classed.
 4. The result after OUR costs: the trip as a $100 paper trade at Ananta's cost per side (registry.cost):
    100 x (sign x (exit_vwap / entry_vwap - 1) - 2 x cost). Their own dollars are shown beside it, never used.
 5. Ananta at their entry moment T (the trip's first fill), read-only:
    - the Explorer's scan of the coin: the last 15-minute scan at or before T (a later one would know the future), within 30 minutes;
      saved for the 10 only (explorer_decisions.jsonl). Other coins: the universe Explorer's tags when it placed an order in the window.
    - the dial on T's UTC day (exposure.dial_by_day: decided on the previous close): OPEN, CLOSED or UNKNOWN.
    - what fired on the coin from T - 2 h to T + 1 h: the Explorer (orders, blocked orders, unfilled limits, and setups its scans saw
      that are not in the active rules), the universe Explorer (its orders are shadows), Hunter, the eye's zone entries, the brain's
      wakes (brain_queue, with what became of each) and decisions (brain_decisions); the daily watches from T - 24 h (they decide once
      a day, at the close).
    - what we held: a paper position of ours in the coin open at T or opened by T + 1 h: the Explorer's real trades, every evidence
      book except the random baselines (the daily watches, the eye's zone trades, the brain's own books), Hunter's takes, the trend
      books (T3 on the 10, T3 on the 30), the $500 book.
 6. The class (the first that fits):
    (d) LOST     their trip lost after our costs (rule 4 <= 0): nothing to miss.
    (c) COVERED BY NOTHING, part 1: a winning SHORT trip, labelled "short (we only buy)": Ananta is spot, long only. Kept on the
        page and in the history as reference; never counted by the pattern rule (rule 8).
    (a) TAKEN    a winning long trip and we held the coin (rule 5).
    (b) PASSED   a winning long trip, something of ours fired, no position: said by what (the blocked reasons).
    (c) NOT COVERED a winning long trip and nothing of ours fired.
 7. The situation of a (c) case: group (rule 3), kind = LONG or SHORT with the hold (scalp under 1 h, intraday 1-24 h, swing 1-7 days,
    position over 7 days), and the dial on T's day.
 8. The pattern rule: the same situation on 3 or more separate report days within the 7 days ending on the day -> one repair-board
    request (kind idea, by ananta-auto) worded as a DRAFT finding, never a rule or a signal. Short situations never count (we only
    buy). The same situation is not filed again within 30 days (the history file records each filing).
 9. Output: docs/repair_shop/daily/others_YYYY-MM-DD.md (plain words, counts, the top 10 winning cases after our costs) and one row
    in docs/repair_shop/daily/others_history.jsonl; every case in ~/ananta_runs/others_daily/cases_YYYY-MM-DD.json. Accounts appear
    only by their sample label (LB_WINNER-03), never by address (the repo is public; review #2: results are never published per person).

    python -m src.research.others_daily run                 every day of the last 7 with a day file and no report yet (oldest first)
    python -m src.research.others_daily run --day 2026-10-19 [--force] [--no-requests] [--data DIR] [--agent DIR] [--out DOCS]
    python -m src.research.others_daily accounts --hl ~/ananta_runs/hl_bench/hl_bench.sqlite --out ~/ananta_runs/hl_daily/hl_accounts.json
"""
from __future__ import annotations

import argparse
import bisect
import calendar
import json
import os
import sqlite3
import statistics
import time
import types
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from src.research import hl_bench as hb

VERSION = "others.daily.v1 (2026-10-20)"
DAY = 86400
LOOKBACK_DAYS = 14                     # the day and the 13 before it
BEFORE_S, AFTER_S, DAILY_BEFORE_S = 2 * 3600, 3600, 24 * 3600
SCAN_MAX_AGE_S = 1800
REPEAT_N, REPEAT_DAYS, REFILE_DAYS = 3, 7, 30
TOP_N = 10
GROUPS = ("LAB10", "T30", "UNIV-A", "UNIV-B", "UNIV-C")
CLASS_WORDS = {"a": "a rule of ours fired and we took it", "b": "a rule of ours fired but we passed or it was blocked",
               "c": "no rule of ours covers it", "d": "they lost after our costs: nothing to miss"}
GROUP_WORDS = {"LAB10": "the 10 lab coins", "T30": "the 30-coin tier", "UNIV-A": "tier A of the universe", "UNIV-B": "tier B of the universe",
               "UNIV-C": "tier C of the universe"}
SHADOW_WORDS = {"CAP": "the account's caps (20 open or 60 a day)", "KILL_SWITCH": "the kill switch", "KILL_SWITCH_UNREAD": "the kill switch could not be read",
                "NO_TYPE": "no trade type had room to a target", "REJECTED_SLOT": "a trade of the same type was already open",
                "REJECTED_DUP": "another setup on the same scan was chosen", "UNIVERSE": "the universe Explorer only shadows (review #9: its setups lost after costs)"}
NOT_OURS = {"RANDOM", "JARVIS_RANDOM", "RANDOM_BOLD"}
NO_POSITION = "it fired, but no position of ours was open by an hour after their entry"
AGENT_DIR = Path(os.environ.get("JARVIS_AGENT_DIR", str(Path.home() / "code" / "ananta-decision-agent")))
DATA_DIR = Path.home() / "ananta_worker_data"
ACCOUNTS_FILE = Path.home() / "ananta_runs" / "hl_daily" / "hl_accounts.json"
CASES_DIR = Path.home() / "ananta_runs" / "others_daily"
DOCS_DIR = Path(__file__).resolve().parents[2] / "docs"


def _day(t: float) -> str:
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d")


def _day_t(day: str) -> int:
    return calendar.timegm(time.strptime(day, "%Y-%m-%d"))


def _hm(t: float) -> str:
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d %H:%M")


def _ro(p: Path) -> sqlite3.Connection | None:
    return sqlite3.connect(f"file:{p}?mode=ro", uri=True, timeout=30) if Path(p).exists() else None


# ---------------------------------------------------------------------------
# the account list (built once, from review #2's collection)
# ---------------------------------------------------------------------------
def build_accounts(hl: Path, out: Path) -> dict:
    """The fixed sample of review #2: every account of the Sep 29 hl_bench collection whose fills were fetched (DONE / DONE_TRUNCATED),
    labelled by source, with review #2's HFT verdict on its whole history. Never overwrites an existing list."""
    out = Path(out)
    if out.exists():
        raise FileExistsError(f"{out} exists: the list is fixed and is never rebuilt")
    con = _ro(Path(hl))
    if con is None:
        raise FileNotFoundError(hl)
    try:
        sampling = json.loads((con.execute("SELECT v FROM meta WHERE k='sampling'").fetchone() or ["{}"])[0])
        rows = con.execute("SELECT address, source, status FROM accounts WHERE status LIKE 'DONE%' ORDER BY source, address").fetchall()
        accts, n_by = [], {}
        for a, src, status in rows:
            n_by[src] = n_by.get(src, 0) + 1
            f = con.execute("SELECT time, coin, side, px, sz, start_pos, closed_pnl, fee FROM fills WHERE address=? ORDER BY time, tid", (a,)).fetchall()
            beh = hb.behaviour(hb.round_trips(f))
            accts.append({"account": a.lower(), "label": f"{src}-{n_by[src]:02d}", "source": src, "r2_status": status, "r2_hft": hb.is_hft(beh)})
        skipped = dict(con.execute("SELECT status, COUNT(*) FROM accounts WHERE status NOT LIKE 'DONE%' GROUP BY status").fetchall())
    finally:
        con.close()
    hft = [a for a in accts if a["r2_hft"]]                  # coordinator, Oct 20: market makers / HFT are not captured at all
    accts = [a for a in accts if not a["r2_hft"]]
    how = (f"Review #2's fixed sample, unchanged: every account of the hl_bench collection of 2026-09-29 (src/research/hl_bench.py, seed "
           f"{sampling.get('seed', hb.SEED)}; analysed in review #2 on 2026-09-30) whose fills were fetched. Chosen at random within strata from "
           "three public sources: the Hyperliquid leaderboard's active accounts (30-day volume above 0, account value at least $1,000, monthly "
           "volume under 300 times account value) split into thirds by all-time PnL, 10 from each (LB_LOSER, LB_MIDDLE, LB_WINNER); wallets "
           "seen in recent trades on the 10 lab coins, taken in random order until 20 complete histories were fetched (TAPE; a truncated "
           "one is kept too); public vaults open, with at least $10,000 and over "
           "a year old, 5 from each third by APR (VAULT). " + ", ".join(f"{k} {v}" for k, v in sorted(n_by.items())) + f" = {len(accts) + len(hft)} accounts"
           + (f"; left out: " + ", ".join(f"{v} {k}" for k, v in sorted(skipped.items())) if skipped else "") + ". The "
           f"{len(hft)} that review #2 dropped as market makers or HFT ({', '.join(a['label'] for a in hft) or 'none'}) are not captured, so "
           f"{len(accts)} accounts are. Labels are by source and address order (kept from the whole sample); the addresses stay on Madhav's "
           "Macs (the repo is public).")
    d = {"version": "hl.accounts.v1 (2026-10-20)", "made": _day(time.time()), "how_chosen": how, "sampling": sampling, "accounts": accts,
         "left_out_hft": [{"label": a["label"], "source": a["source"]} for a in hft]}
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, indent=1))
    tmp.replace(out)
    return {"accounts": len(accts), "by_source": n_by, "left_out_hft": [a["label"] for a in hft], "out": str(out)}


def load_accounts(path: Path) -> dict[str, dict]:
    d = json.loads(Path(path).read_text())
    return {a["account"].lower(): a for a in d.get("accounts") or []}


# ---------------------------------------------------------------------------
# the fills and the round trips
# ---------------------------------------------------------------------------
def day_files(data: Path, day: str) -> list[tuple[str, Path]]:
    """(day, file) for the day and up to LOOKBACK_DAYS - 1 days before it, while the files run unbroken back from the day."""
    out, t = [], _day_t(day)
    for k in range(LOOKBACK_DAYS):
        d = _day(t - k * DAY)
        p = Path(data) / f"hl_{d}.sqlite"
        if not p.exists():
            break
        out.append((d, p))
    return out[::-1]


def load_fills(files: list[tuple[str, Path]]) -> tuple[dict[str, list[tuple]], dict[str, str]]:
    """Per account, its fills in its unbroken run of good days ending on the last day: (time, coin, side, px, sz, start_pos,
    closed_pnl, fee) sorted by time. Also each account's status on the last day."""
    per: dict[str, dict[str, list]] = {}
    good: dict[str, set] = {}
    last_status: dict[str, str] = {}
    days = [d for d, _ in files]
    for d, p in files:
        con = _ro(p)
        try:
            st = {a: (s, tr) for a, s, tr in con.execute("SELECT account, status, truncated FROM accounts")}
            for a, (s, tr) in st.items():
                if s == "OK" and not tr:
                    good.setdefault(a, set()).add(d)
                if d == days[-1]:
                    last_status[a] = s if not tr else "TRUNCATED"
            for row in con.execute("SELECT account, time, coin, side, px, sz, start_position, closed_pnl, fee, tid FROM fills ORDER BY time, tid"):
                per.setdefault(row[0], {}).setdefault(d, []).append(row[1:])
        finally:
            con.close()
    out = {}
    for a, ok in good.items():
        if days[-1] not in ok:
            continue
        run = []
        for d in reversed(days):
            if d not in ok:
                break
            run.append(d)
        rows = [r for d in sorted(run) for r in per.get(a, {}).get(d, [])]
        rows.sort(key=lambda r: (r[0], r[-1] or 0))
        out[a] = [(t, coin, side, px or 0.0, sz or 0.0, sp or 0.0, cp or 0.0, fee or 0.0) for t, coin, side, px, sz, sp, cp, fee, _ in rows]
    return out, last_status


def our_coin(hl: str | None) -> str | None:
    """Hyperliquid's perp name -> ours; None for spot ("@107"), pairs ("PURR/USDC") and builder markets ("xyz:TSLA")."""
    from jarvis.service import tier30

    if not hl or hl.startswith("@") or "/" in hl or ":" in hl:
        return None
    c = hl[1:] if hl.startswith("k") and hl[1:].isupper() else hl.upper()
    return tier30.RENAMED.get(c, c) if c in tier30.RENAMED else c


def hold_kind(hold_h: float) -> str:
    return "scalp" if hold_h < 1 else "intraday" if hold_h < 24 else "swing" if hold_h < 24 * 7 else "position"


# ---------------------------------------------------------------------------
# Ananta's side, read-only, loaded once for the whole time range
# ---------------------------------------------------------------------------
class Ananta:
    """Everything of ours that the classes need, from the agent folder (read-only connections only)."""

    def __init__(self, agent: Path, t0: int, t1: int):
        from jarvis.service import registry, tier30

        self.dir = Path(agent)
        self.lo, self.hi = t0 - DAILY_BEFORE_S, t1 + AFTER_S
        self.lab10 = list(registry.lab10())
        self.t30 = [c for c in tier30.COINS if c not in self.lab10]
        self.reg = registry.load(types.SimpleNamespace(dir=self.dir))
        self.notes: list[str] = []
        self.scans: dict[str, list[tuple[int, dict]]] = {}
        self.fired: dict[str, list[dict]] = {}
        self.held: dict[str, list[dict]] = {}
        self.brain: dict[str, list[dict]] = {}
        self.uni_tags: dict[str, list[tuple[int, dict]]] = {}
        self.trend: dict[str, list[tuple[int, set]]] = {}
        self.dial: dict[str, float] = {}
        for name, fn in (("explorer scans", self._scans), ("explorer book", self._explorer), ("universe explorer", self._universe),
                         ("jarvis.sqlite", self._jarvis), ("hunter", self._hunter), ("trend books", self._trend), ("dial", self._dial)):
            try:
                fn()
            except Exception as exc:  # noqa: BLE001  a source that cannot be read is said, never guessed
                self.notes.append(f"{name}: {type(exc).__name__}: {str(exc)[:120]}")

    # -- the coin's group and cost
    def group(self, coin: str) -> str:
        if coin in self.lab10:
            return "LAB10"
        if coin in self.t30:
            return "T30"
        k = (self.reg.get("coins") or {}).get(coin)
        if k and k.get("status") == "LISTED":
            return f"UNIV-{k.get('tier') or 'C'}"
        return "OUTSIDE"

    def cost(self, coin: str) -> float:
        from jarvis.service import registry

        return registry.cost(coin, self.reg)

    def _add(self, d: dict, coin: str, item: dict) -> None:
        d.setdefault(coin, []).append(item)

    # -- loaders
    def _scans(self) -> None:
        p = self.dir / "explorer_decisions.jsonl"
        if not p.exists():
            self.notes.append("explorer scans: no explorer_decisions.jsonl")
            return
        lo = self.lo - SCAN_MAX_AGE_S
        with open(p, "r", errors="ignore") as f:
            for ln in f:
                if not ln.startswith('{"t": '):
                    continue
                try:
                    t = int(ln[6:ln.index(",", 6)])
                except ValueError:
                    continue
                if t < lo or t > self.hi:
                    continue
                try:
                    r = json.loads(ln)
                except ValueError:
                    continue
                self.scans.setdefault(r.get("coin"), []).append((t, r))
        for v in self.scans.values():
            v.sort(key=lambda x: x[0])

    def _explorer(self) -> None:
        con = _ro(self.dir / "explorer_book.sqlite")
        if con is None:
            self.notes.append("explorer book: not found")
            return
        try:
            opened: dict[str, tuple] = {}
            for t, kind, coin, js in con.execute("SELECT t, kind, coin, json FROM events WHERE kind IN ('ORDER','MISSED','FILLED','CLOSED') "
                                                 "AND t >= ? ORDER BY seq", (self.lo - 60 * DAY,)):
                e = json.loads(js)
                if e.get("shadow") == "RANDOM":
                    continue
                if kind == "FILLED":
                    opened[e.get("id")] = (t, coin, e.get("setup"))
                elif kind == "CLOSED" and e.get("id") in opened:
                    t0, c, s = opened.pop(e.get("id"))
                    self._add(self.held, c, {"src": "Explorer", "what": f"Explorer {s} trade", "t0": t0, "t1": t})
                if t < self.lo or t > self.hi or kind in ("FILLED", "CLOSED"):
                    continue
                sh = e.get("shadow")
                if kind == "ORDER":
                    self._add(self.fired, coin, {"src": "Explorer", "what": f"Explorer {e.get('setup')} order", "t": t,
                                                 "blocked": SHADOW_WORDS.get(sh, sh) if sh else None})
                else:                                            # MISSED (sightings come from the scans: setups seen but not in the rules)
                    self._add(self.fired, coin, {"src": "Explorer", "what": f"Explorer {e.get('setup')} order", "t": t, "blocked": "the limit order did not fill"})
            for _id, (t0, c, s) in opened.items():
                self._add(self.held, c, {"src": "Explorer", "what": f"Explorer {s} trade", "t0": t0, "t1": None})
        finally:
            con.close()

    def _universe(self) -> None:
        con = _ro(self.dir / "universe_explorer.sqlite")
        if con is None:
            self.notes.append("universe explorer: not found")
            return
        try:
            for t, coin, js in con.execute("SELECT t, coin, json FROM events WHERE kind='ORDER' AND t >= ? AND t <= ?", (self.lo, self.hi)):
                if coin in self.lab10:
                    continue                                     # the live Explorer decides on the 10
                e = json.loads(js)
                sh = e.get("shadow")
                if sh == "RANDOM":
                    continue
                self._add(self.fired, coin, {"src": "universe Explorer", "what": f"universe Explorer {e.get('setup')} order", "t": t,
                                             "blocked": SHADOW_WORDS.get(sh, sh or "shadow")})
                if e.get("tags"):
                    self.uni_tags.setdefault(coin, []).append((t, e["tags"]))
        finally:
            con.close()

    def _jarvis(self) -> None:
        con = _ro(self.dir / "jarvis.sqlite")
        if con is None:
            self.notes.append("jarvis.sqlite: not found")
            return
        try:
            for w, coin, st, et, xt, status in con.execute("SELECT watch, coin, signal_t, entry_t, exit_t, status FROM evidence_trades "
                                                           "WHERE (signal_t >= ? AND signal_t <= ?) OR (entry_t IS NOT NULL AND entry_t <= ? AND (exit_t IS NULL OR exit_t >= ?))",
                                                           (self.lo, self.hi, self.hi, self.lo)):
                if w in NOT_OURS or (w or "").startswith("RANDOM"):
                    continue
                name = {"JARVIS": "the brain's book", "JARVIS_BOLD": "the brain's bold book"}.get(w, f"{w} evidence trade")
                if et:
                    self._add(self.held, coin, {"src": "evidence", "what": name, "t0": et, "t1": xt})
                if st and self.lo <= st <= self.hi:
                    daily = not str(w or "").startswith(("ZONE", "JARVIS"))
                    self._add(self.fired, coin, {"src": "daily" if daily else "evidence", "what": f"{w} signal", "t": st, "daily": daily,
                                                 "blocked": None if et else ("waiting for its entry price" if status == "WAITING" else f"not entered ({status})")})
            for t, coin, title in con.execute("SELECT t, coin, title FROM eye_events WHERE kind IN ('ZONE_ENTRY','ZONE_TOUCH') AND t >= ? AND t <= ?", (self.lo, self.hi)):
                self._add(self.fired, coin, {"src": "eye", "what": f"eye: {title}"[:90], "t": t, "blocked": "a zone entry the eye saw (no trade by itself)"})
            for t, coin, trig, state in con.execute("SELECT t, coin, trigger, state FROM brain_queue WHERE t >= ? AND t <= ?", (self.lo, self.hi)):
                s = str(state or "")
                self._add(self.brain, coin, {"t": t, "wake": trig, "state": s})
                self._add(self.fired, coin, {"src": "brain", "what": f"the brain woke ({trig})", "t": t,
                                             "blocked": None if s.startswith("DONE") else "the brain did not decide: " + (s.split(":", 1)[1].strip() if ":" in s else s or "queued")})
            for t, coin, act, conf, thesis in con.execute("SELECT t, coin, action, confidence, thesis FROM brain_decisions WHERE t >= ? AND t <= ?", (self.lo, self.hi)):
                self._add(self.brain, coin, {"t": t, "decision": act, "confidence": conf, "thesis": (thesis or "")[:160]})
                if act != "TAKE":
                    self._add(self.fired, coin, {"src": "brain", "what": f"the brain decided {act}", "t": t,
                                                 "blocked": f"the brain passed ({conf:.0f}% confident)" if act == "PASS" and conf is not None else f"the brain: {act}"})
            try:
                pos: dict[str, list] = {}
                for t, coin, side, qty in con.execute("SELECT t, coin, side, qty FROM book500_fills WHERE t <= ? ORDER BY t", (self.hi,)):
                    pos.setdefault(coin, []).append((t, qty if side == "BUY" else -qty))
                for coin, xs in pos.items():
                    q, t0 = 0.0, None
                    for t, dq in xs:
                        before, q = q, q + dq
                        if before <= 1e-12 < q:
                            t0 = t
                        elif q <= 1e-12 < before and t0 is not None:
                            self._add(self.held, coin, {"src": "$500", "what": "the $500 book", "t0": t0, "t1": t})
                            t0 = None
                    if t0 is not None:
                        self._add(self.held, coin, {"src": "$500", "what": "the $500 book", "t0": t0, "t1": None})
            except sqlite3.Error:
                pass
        finally:
            con.close()

    def _hunter(self) -> None:
        con = _ro(self.dir / "agent_decisions.sqlite")
        if con is None:
            return
        try:
            a, b = datetime.fromtimestamp(self.lo, timezone.utc).isoformat(), datetime.fromtimestamp(self.hi, timezone.utc).isoformat()
            for ts, coin, dec, setup in con.execute("SELECT ts_utc, instrument, decision, setup FROM decisions WHERE ts_utc >= ? AND ts_utc <= ? "
                                                    "AND decision IN ('TAKE','SHADOW_PAPER')", (a, b)):
                t = int(datetime.fromisoformat(str(ts).replace("Z", "+00:00")).timestamp())
                c = str(coin).split("-")[0].upper()
                if dec == "TAKE":                                # the moment it took (its exit is in Hunter's own book, not read here)
                    self._add(self.held, c, {"src": "Hunter", "what": "Hunter's book", "t0": t, "t1": t})
                self._add(self.fired, c, {"src": "Hunter", "what": f"Hunter {str(setup or '').split('.')[-1]}", "t": t,
                                          "blocked": None if dec == "TAKE" else "Hunter's book was full (a shadow)"})
        finally:
            con.close()

    def _trend(self) -> None:
        for book, fname in (("T3", "portfolio_book.sqlite"), ("T3 on the 30", "portfolio_book_t30.sqlite")):
            con = _ro(self.dir / fname)
            if con is None:
                continue
            try:
                for day_t, js in con.execute("SELECT day_t, json FROM decisions WHERE day_t >= ? AND day_t <= ? ORDER BY day_t", (self.lo - 3 * DAY, self.hi)):
                    held = {c for c, r in (json.loads(js).get("ratings") or {}).items() if r.get("hold")}
                    self.trend.setdefault(book, []).append((int(day_t), held))
            finally:
                con.close()

    def _dial(self) -> None:
        if not (self.dir / "universe_bars.sqlite").exists():           # feed would create it; we only read
            self.notes.append("dial: no universe_bars.sqlite")
            return
        from jarvis.service import exposure

        self.dial = exposure.dial_by_day(types.SimpleNamespace(dir=self.dir))

    # -- the state at one moment
    def at(self, coin: str, T: int) -> dict:
        a, b = T - BEFORE_S, T + AFTER_S
        out: dict[str, Any] = {"dial": {1.0: "OPEN", 0.0: "CLOSED"}.get(self.dial.get(_day(T)), "UNKNOWN") if self.dial else "UNKNOWN"}
        sc = self.scans.get(coin) or []
        ts = [x[0] for x in sc]
        i = bisect.bisect_right(ts, T) - 1
        seen_now = []
        for t, r in sc[bisect.bisect_left(ts, a): bisect.bisect_right(ts, b)]:      # setups its scans saw in the window, not in the rules
            for st in r.get("sightings") or []:
                if st not in (r.get("setups") or []):
                    seen_now.append({"src": "Explorer", "what": f"Explorer {st} sighting", "t": t, "blocked": "seen, not in the active rulebook"})
        if i >= 0 and T - sc[i][0] <= SCAN_MAX_AGE_S:
            r = sc[i][1]
            s = r.get("state") or {}
            out["scan"] = {"t": sc[i][0], "skip": r.get("skip"), "setups": r.get("setups") or [], "sightings": r.get("sightings") or [],
                           **{k: s.get(k) for k in ("S1", "S2", "trend_4h", "daily_above_ema50", "rsi15", "rsi1h", "vol1h", "in_support", "expensive", "btc_S1")}}
        elif coin in self.lab10:
            out["scan"] = None
            out["scan_note"] = "no Explorer scan saved within 30 minutes before the entry"
        else:
            ut = [x for x in self.uni_tags.get(coin, []) if a <= x[0] <= b]
            if ut:
                out["tags"] = {k: ut[0][1].get(k) for k in ("S1", "S2", "trend_4h", "daily_above_ema50", "rsi15", "rsi1h", "in_support")}
        fired = []
        for f in self.fired.get(coin, []) + seen_now:
            lo = T - DAILY_BEFORE_S if f.get("daily") else a
            if lo <= f["t"] <= b:
                fired.append(f)
        seen, uniq = set(), []
        for f in sorted(fired, key=lambda f: f["t"]):
            k = (f["what"], f.get("blocked"))
            if k not in seen:
                seen.add(k)
                uniq.append(f)
        out["fired"] = uniq
        held = [h["what"] for h in self.held.get(coin, []) if h["t0"] <= b and (h["t1"] is None or h["t1"] >= T)]
        for book, days in self.trend.items():
            k = bisect.bisect_right([d for d, _ in days], T) - 1
            if k >= 0 and T - days[k][0] <= 2 * DAY and coin in days[k][1]:
                held.append(f"the trend book ({book})")
        out["held"] = sorted(set(held))
        out["brain"] = [x for x in self.brain.get(coin, []) if a <= x["t"] <= b]
        return out


# ---------------------------------------------------------------------------
# one day
# ---------------------------------------------------------------------------
def classify(net_pct: float, direction: str, state: dict) -> str:
    if net_pct <= 0:
        return "d"
    if direction == "SHORT":
        return "c"
    if state.get("held"):
        return "a"
    if state.get("fired"):
        return "b"
    return "c"


def situation(group: str, direction: str, hold_h: float, dial: str) -> str:
    return f"{group}|{direction} {hold_kind(hold_h)}|{dial}"


def rebuild(day: str, data: Path, accounts: dict[str, dict], agent: Path) -> dict:
    """Every round trip that closed on the day, with Ananta's state at its entry and its class."""
    files = day_files(data, day)
    if not files or files[-1][0] != day:
        return {"day": day, "missing": True}
    fills, last_status = load_fills(files)
    d0 = _day_t(day)
    acc_n = {"in_sample": len(accounts), "in_file": len(last_status), "captured": sum(1 for s in last_status.values() if s == "OK"),
             "hft_dropped": 0, "closed_a_trip": 0}
    trips, hft = [], []
    for a, f in fills.items():
        meta = accounts.get(a) or {"label": "UNLISTED", "source": "?"}
        tr = hb.round_trips(f)
        if meta.get("r2_hft") or hb.is_hft(hb.behaviour(tr)):
            hft.append(meta.get("label"))
            continue
        mine = [t for t in tr if d0 * 1000 <= t["close_ms"] < (d0 + DAY) * 1000]
        if mine:
            acc_n["closed_a_trip"] += 1
        for t in mine:
            trips.append({**t, "label": meta.get("label"), "source": meta.get("source")})
    acc_n["hft_dropped"] = len(hft)
    t_lo = min([int(t["open_ms"] // 1000) for t in trips], default=d0)
    ana = Ananta(agent, t_lo, d0 + DAY)
    cases, outside, unmapped = [], 0, 0
    for t in trips:
        coin = our_coin(t["coin"])
        if coin is None:
            unmapped += 1
            continue
        g = ana.group(coin)
        if g == "OUTSIDE":
            outside += 1
            continue
        T = int(t["open_ms"] // 1000)
        sign = 1.0 if t["dir"] == "LONG" else -1.0
        cost = ana.cost(coin)
        net_pct = 100 * (sign * (t["exit_vwap"] / t["entry_vwap"] - 1) - 2 * cost) if t["entry_vwap"] else 0.0
        st = ana.at(coin, T)
        cls = classify(net_pct, t["dir"], st)
        cases.append({"coin": coin, "hl_coin": t["coin"], "group": g, "label": t["label"], "source": t["source"], "dir": t["dir"],
                      "entry_t": T, "exit_t": int(t["close_ms"] // 1000), "hold_h": round(t["hold_h"], 2), "entry_vwap": t["entry_vwap"],
                      "exit_vwap": t["exit_vwap"], "cost_per_side_pct": round(100 * cost, 3), "after_our_costs_pct": round(net_pct, 3),
                      "their_net_usd": round(t["net"], 2), "class": cls, "state": st,
                      "blocked_by": (sorted({f["blocked"] for f in st["fired"] if f.get("blocked")}) or [NO_POSITION]) if cls == "b" else [],
                      "situation": situation(g, t["dir"], t["hold_h"], st["dial"]) if cls == "c" else None})
    rank = {g: i for i, g in enumerate(GROUPS)}
    cases.sort(key=lambda c: (rank.get(c["group"], 9), -c["after_our_costs_pct"]))
    return {"day": day, "version": VERSION, "files": [d for d, _ in files], "accounts": acc_n, "hft_labels": sorted(hft),
            "trips_closed": len(trips), "unmapped": unmapped, "outside": outside, "cases": cases, "notes": ana.notes,
            "dial": ana.dial and {1.0: "OPEN", 0.0: "CLOSED"}.get(ana.dial.get(day), "UNKNOWN") or "UNKNOWN"}


def summary(r: dict) -> dict:
    cs = r["cases"]
    cls = {k: sum(1 for c in cs if c["class"] == k) for k in "abcd"}
    by_group = {}
    for g in GROUPS:
        x = [c for c in cs if c["group"] == g]
        if x:
            by_group[g] = {"trips": len(x), **{k: sum(1 for c in x if c["class"] == k) for k in "abcd"},
                           "median_after_our_costs_pct": round(statistics.median(c["after_our_costs_pct"] for c in x), 3)}
    blocked: dict[str, int] = {}
    for c in cs:
        for b in c["blocked_by"]:
            blocked[b] = blocked.get(b, 0) + 1
    sit: dict[str, dict] = {}
    for c in cs:
        if c["class"] == "c":
            s = sit.setdefault(c["situation"], {"n": 0, "pcts": [], "coins": set()})
            s["n"] += 1
            s["pcts"].append(c["after_our_costs_pct"])
            s["coins"].add(c["coin"])
    return {"classes": cls, "by_group": by_group, "blocked_by": dict(sorted(blocked.items(), key=lambda kv: -kv[1])),
            "situations_c": {k: {"n": v["n"], "median_pct": round(statistics.median(v["pcts"]), 3), "coins": sorted(v["coins"])} for k, v in sorted(sit.items())}}


# ---------------------------------------------------------------------------
# history and the pattern rule
# ---------------------------------------------------------------------------
def read_history(path: Path) -> list[dict]:
    if not Path(path).exists():
        return []
    out = []
    for ln in Path(path).read_text().splitlines():
        try:
            out.append(json.loads(ln))
        except ValueError:
            continue
    return out


def write_history(path: Path, rows: list[dict]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in sorted(rows, key=lambda r: r["day"])))
    tmp.replace(path)


SHORT_LABEL = "short (we only buy)"


def is_short(key: str) -> bool:
    """A situation key of a short trip (group|SHORT hold|dial)."""
    parts = str(key).split("|")
    return len(parts) == 3 and parts[1].startswith("SHORT")


def repeats(rows: list[dict], day: str) -> list[dict]:
    """Rule 8: long situations of class (c) seen on REPEAT_N or more separate report days in the REPEAT_DAYS days ending on `day`, and not
    filed in the REFILE_DAYS days before it."""
    t = _day_t(day)
    lo, refile_lo = _day(t - (REPEAT_DAYS - 1) * DAY), _day(t - REFILE_DAYS * DAY)
    seen: dict[str, dict] = {}
    for r in rows:
        if lo <= r["day"] <= day:
            for k, v in (r.get("situations_c") or {}).items():
                if is_short(k):                                  # short (we only buy): reference only, never a request
                    continue
                s = seen.setdefault(k, {"days": [], "n": 0, "pcts": [], "coins": set()})
                s["days"].append(r["day"])
                s["n"] += v.get("n", 0)
                s["pcts"].append(v.get("median_pct", 0.0))
                s["coins"].update(v.get("coins") or [])
    filed = {f["key"] for r in rows if refile_lo < r["day"] <= day for f in r.get("filed") or []}
    out = []
    for k, s in sorted(seen.items()):
        if len(set(s["days"])) >= REPEAT_N and k not in filed:
            out.append({"key": k, "days": sorted(set(s["days"])), "trips": s["n"], "median_pct": round(statistics.median(s["pcts"]), 3),
                        "coins": sorted(s["coins"])})
    return out


def draft_text(p: dict, day: str) -> str:
    group, kind, dial = p["key"].split("|")
    direction, hold = kind.split(" ")
    kind_words = f"{'long' if direction == 'LONG' else 'short'} {hold}"
    return (f"DRAFT finding (other traders, reference only, D8; the daily rebuild's 3-in-7 rule): on {len(p['days'])} separate days in the 7 "
            f"days to {day} ({', '.join(p['days'])}), traders in the fixed Hyperliquid sample closed {p['trips']} winning {kind_words} trips "
            f"on {GROUP_WORDS.get(group, group)} while the dial was {dial.lower()}, and no rule of ours covered that situation (daily medians "
            f"around {p['median_pct']:+.2f}% after our costs; coins {', '.join(p['coins'][:8])}{', ...' if len(p['coins']) > 8 else ''}). "
            f"Something to look at, not a rule or a signal: nobody is copied, and Rule B (no new strategies in the evidence window) holds. "
            f"The cases: docs/repair_shop/daily/others_{day}.md.")


def _file_request(agent: Path) -> Callable[[str], dict]:
    """The repair board's own function (requests_log.add) on its own short-lived connection: the only write this file makes to a
    database of ours."""
    def add(text: str) -> dict:
        from jarvis.service import requests_log

        con = sqlite3.connect(str(Path(agent) / "jarvis.sqlite"), timeout=30)
        try:
            return requests_log.add(types.SimpleNamespace(db=con, now=time.time), "idea", text, about="other traders (daily)", by="ananta-auto")
        finally:
            con.close()
    return add


# ---------------------------------------------------------------------------
# the page
# ---------------------------------------------------------------------------
def _pct(x: float) -> str:
    return f"{x:+.2f}%"


def _state_words(c: dict) -> str:
    st = c["state"]
    bits = []
    sc = st.get("scan")
    if sc:
        bits.append(f"Explorer scan {_hm(sc['t'])[11:]} UTC: trend {sc.get('S1')}/{sc.get('S2')}, 4-hour {sc.get('trend_4h')}, "
                    f"{'above' if sc.get('daily_above_ema50') else 'below'} the 50-day, RSI 15m {round(sc['rsi15']) if sc.get('rsi15') is not None else '?'}"
                    + (", in support" if sc.get("in_support") else "") + (f", skipped ({sc['skip']})" if sc.get("skip") else ""))
    elif st.get("scan_note"):
        bits.append(st["scan_note"])
    elif st.get("tags"):
        bits.append(f"universe Explorer tags: trend {st['tags'].get('S1')}/{st['tags'].get('S2')}, 4-hour {st['tags'].get('trend_4h')}")
    bits.append(f"dial {st['dial'].lower()}")
    if st.get("held"):
        bits.append("held: " + ", ".join(st["held"]))
    fired = [f["what"] + (f" (blocked: {f['blocked']})" if f.get("blocked") else "") for f in st.get("fired") or []]
    if fired:
        bits.append("fired: " + "; ".join(fired[:4]) + (f"; and {len(fired) - 4} more" if len(fired) > 4 else ""))
    dec = [b for b in st.get("brain") or [] if b.get("decision")]
    if dec:
        bits.append(f"the brain decided {dec[0]['decision']}" + (f" ({dec[0]['confidence']:.0f}%)" if dec[0].get("confidence") is not None else ""))
    elif not any(b.get("wake") for b in st.get("brain") or []):
        bits.append("the brain did not wake")
    return "; ".join(bits)


def page(r: dict, s: dict, filed: list[dict], pending: list[dict]) -> str:
    a, cs = r["accounts"], r["cases"]
    n_g = {g: sum(1 for c in cs if c["group"] == g) for g in GROUPS}
    lines = [f"# Other traders against Ananta, {r['day']}", "",
             "Reference only (D8): what traders in a fixed public sample did on this UTC day, held against what Ananta saw and did at the "
             "same moment. Nobody is copied, and nothing here is a rule or a signal. Every result is shown after OUR costs: their trip as a "
             "$100 paper trade at Ananta's cost per side. The fixed rules are at the top of `src/research/others_daily.py`.", "",
             "## The day in numbers", "",
             f"- Accounts: {a['in_sample']} in the sample, {a['captured']} captured whole, {a['hft_dropped']} dropped as market makers or HFT, "
             f"{a['closed_a_trip']} closed at least one round trip.",
             f"- Round trips closed: {r['trips_closed']}. On coins we watch: {len(cs)} (the 10 lab coins {n_g['LAB10']}, the 30-coin tier {n_g['T30']}, "
             f"the rest of the universe {n_g['UNIV-A'] + n_g['UNIV-B'] + n_g['UNIV-C']}); outside our list {r['outside']}; spot or other markets {r['unmapped']}.",
             f"- The dial that day: {r['dial'].lower()}.", "", "On the coins we watch:", ""]
    for k in "abcd":
        lines.append(f"- ({k}) {CLASS_WORDS[k]}: {s['classes'][k]}")
    if s["blocked_by"]:
        lines += ["", "What stopped us in (b): " + "; ".join(f"{k} ({v})" for k, v in list(s["blocked_by"].items())[:8]) + "."]
    if s["by_group"]:
        lines += ["", "## By group", "", "| group | trips | (a) | (b) | (c) | (d) | median after our costs |", "|---|---|---|---|---|---|---|"]
        lines += [f"| {GROUP_WORDS[g]} | {v['trips']} | {v['a']} | {v['b']} | {v['c']} | {v['d']} | {_pct(v['median_after_our_costs_pct'])} |"
                  for g, v in s["by_group"].items()]
    win = sorted([c for c in cs if c["class"] != "d"], key=lambda c: -c["after_our_costs_pct"])[:TOP_N]
    lines += ["", f"## The top {TOP_N} cases (winners after our costs)", ""]
    if not win:
        lines.append("None: no trip on a coin we watch made money after our costs.")
    for i, c in enumerate(win, 1):
        why = {"a": "we were in it", "b": "something of ours fired but we did not trade: " + "; ".join(c["blocked_by"][:3]),
               "c": "nothing of ours covers it" + (f": a {SHORT_LABEL}, reference only" if c["dir"] == "SHORT" else "")}[c["class"]]
        lines.append(f"{i}. **{c['coin']}** ({GROUP_WORDS[c['group']]}), {c['label']}, {SHORT_LABEL if c['dir'] == 'SHORT' else 'long'} from {_hm(c['entry_t'])} UTC, "
                     f"held {c['hold_h']:.1f} h, {_pct(c['after_our_costs_pct'])} after our costs (their own net ${c['their_net_usd']:,.2f}). "
                     f"Class ({c['class']}): {why}. Ananta then: {_state_words(c)}.")
    lines += ["", "## Repeated situations (3 days in 7)", ""]
    if s["situations_c"]:
        lines.append("Class (c) today, by situation (group | kind | dial): " + "; ".join(
            f"{k} ({v['n']}{', ' + SHORT_LABEL + ': reference, never filed' if is_short(k) else ''})" for k, v in s["situations_c"].items()) + ".")
    else:
        lines.append("No class (c) case today.")
    for f in filed:
        lines.append(f"- {f['key']}: {len(f['days'])} days ({', '.join(f['days'])}): sent to the repair board as a DRAFT finding"
                     + (f", request {f['num']}" if f.get("num") else "") + ".")
    for p in pending:
        lines.append(f"- {p['key']}: {len(p['days'])} days ({', '.join(p['days'])}): would be a DRAFT finding (requests off for this run).")
    if not filed and not pending:
        lines.append("No situation reached 3 separate days in the last 7 (or it was filed in the last 30 days).")
    lines += ["", "## How this was read", "",
              f"- Day files used: {r['files'][0]} to {r['files'][-1]} ({len(r['files'])}); a trip is rebuilt only inside an account's unbroken run of days.",
              "- Ananta's side was read from its own logs and databases, read-only: " + ("everything answered." if not r["notes"] else "; ".join(r["notes"]) + "."),
              f"- {VERSION}.", ""]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# the run
# ---------------------------------------------------------------------------
def run_day(day: str, data: Path = DATA_DIR, accounts: Path = ACCOUNTS_FILE, agent: Path = AGENT_DIR, out: Path = DOCS_DIR,
            cases_dir: Path | None = CASES_DIR, file_request: Callable[[str], dict] | None = None, requests: bool = True) -> dict:
    """Rebuild one day, write the page and the history row, apply the pattern rule. Returns what was done."""
    accts = load_accounts(accounts)
    r = rebuild(day, Path(data), accts, Path(agent))
    if r.get("missing"):
        return {"day": day, "missing": f"no hl_{day}.sqlite in {data}"}
    s = summary(r)
    hist_p = Path(out) / "repair_shop" / "daily" / "others_history.jsonl"
    rows = read_history(hist_p)
    old = next((x for x in rows if x["day"] == day), None)
    rows = [x for x in rows if x["day"] != day]
    row = {"day": day, "made_t": int(time.time()), "version": VERSION, "files": len(r["files"]), "accounts": r["accounts"],
           "trips_closed": r["trips_closed"], "watched": len(r["cases"]), "outside": r["outside"], "unmapped": r["unmapped"], "dial": r["dial"],
           **s, "filed": (old or {}).get("filed") or [], "notes": r["notes"], "dry_run": not requests}
    rows.append(row)
    filed, pending = [], []
    for p in repeats(rows, day):
        if requests:
            res = (file_request or _file_request(Path(agent)))(draft_text(p, day))
            f = {**p, "num": res.get("num") if isinstance(res, dict) else None, "duplicate": bool(isinstance(res, dict) and res.get("duplicate"))}
            filed.append(f)
            row["filed"].append({"key": p["key"], "num": f["num"], "day": day})
        else:
            pending.append(p)
    write_history(hist_p, rows)
    pg = Path(out) / "repair_shop" / "daily" / f"others_{day}.md"
    pg.parent.mkdir(parents=True, exist_ok=True)
    pg.write_text(page(r, s, filed, pending))
    if cases_dir:
        Path(cases_dir).mkdir(parents=True, exist_ok=True)
        (Path(cases_dir) / f"cases_{day}.json").write_text(json.dumps(r, indent=1, default=str))
    return {"day": day, "page": str(pg), "watched": len(r["cases"]), "classes": s["classes"], "filed": [{"key": f["key"], "num": f["num"]} for f in filed],
            "would_file": [p["key"] for p in pending], "notes": r["notes"]}


def run(days: int = 7, now: float | None = None, data: Path = DATA_DIR, out: Path = DOCS_DIR, force: bool = False, **kw) -> list[dict]:
    """Every day of the last `days` finished UTC days that has a day file and no history row yet (oldest first). A row written by a
    dry run (--no-requests) does not count as done, so the pattern rule still runs on that day."""
    now = now or time.time()
    today = int(now) - int(now) % DAY
    done = {r["day"] for r in read_history(Path(out) / "repair_shop" / "daily" / "others_history.jsonl") if not r.get("dry_run")}
    res = []
    for k in range(days, 0, -1):
        d = _day(today - k * DAY)
        if (Path(data) / f"hl_{d}.sqlite").exists() and (force or d not in done):
            res.append(run_day(d, data=data, out=out, **kw))
    return res


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "accounts"])
    ap.add_argument("--day")
    ap.add_argument("--data", default=str(DATA_DIR))
    ap.add_argument("--accounts", default=str(ACCOUNTS_FILE))
    ap.add_argument("--agent", default=str(AGENT_DIR))
    ap.add_argument("--out", default=str(DOCS_DIR), help="the docs folder (the page goes to OUT/repair_shop/daily)")
    ap.add_argument("--cases", default=str(CASES_DIR))
    ap.add_argument("--no-requests", action="store_true", help="say what the pattern rule would file, file nothing")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--hl", help="accounts: the hl_bench collection")
    ap.add_argument("--file", help="accounts: where to write the list (default --accounts)")
    a = ap.parse_args(argv)
    ex = lambda p: Path(os.path.expanduser(p))  # noqa: E731
    if a.cmd == "accounts":
        print(json.dumps(build_accounts(ex(a.hl or "~/ananta_runs/hl_bench/hl_bench.sqlite"), ex(a.file or a.accounts)), indent=1))
        return
    kw = dict(data=ex(a.data), accounts=ex(a.accounts), agent=ex(a.agent), out=ex(a.out), cases_dir=ex(a.cases), requests=not a.no_requests)
    if a.day:
        print(json.dumps(run_day(a.day, **kw), indent=1, default=str))
    else:
        print(json.dumps(run(force=a.force, **kw), indent=1, default=str))


if __name__ == "__main__":
    main()
