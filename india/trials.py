"""The clocks (Madhav, 30 Oct 2026: "it can talk to me what it is doing on them currently and tell me how much more time needed and what has
happened till now"): every running trial in one place, each with what it is, when it started, sessions done of needed, the expected finish
date, and what has happened so far. Read by the read model, the voice's facts and Home.

  python -m india.trials             -> manifests/trials.json (and prints the words)

Nothing here decides anything; it reads the trials' own files. Dates count NSE sessions on the trading calendar.
"""
from __future__ import annotations

import datetime as dt
import json
import sys

from india import paths


def _load(p, default=None):
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return default


def _sessions():
    """Trading days from the calendar plus a weekday extension (holidays after the calendar's end are not known; said as 'about')."""
    import pandas as pd
    try:
        c = pd.read_parquet(paths.data_dir() / "silver/calendar/calendar.parquet")
        days = sorted(pd.to_datetime(c[c["is_trading_day"]]["date"]).dt.date)
    except Exception:  # noqa: BLE001
        days = []
    last = days[-1] if days else dt.date.today()
    d = last
    while len(days) < 10_000 and d < last + dt.timedelta(days=400):
        d += dt.timedelta(days=1)
        if d.weekday() < 5 and d > last:
            days.append(d)
    return days


def _finish(days, start: dt.date, done: int, need: int) -> dt.date | None:
    """The session on which the trial reaches `need`, counting from `start` (session 1 = the first session on or after start)."""
    after = [d for d in days if d >= start]
    if not after:
        return None
    idx = need - 1
    return after[idx] if idx < len(after) else None


def _done(days, start: dt.date, through: dt.date | None) -> int:
    through = through or dt.date.today()
    return sum(1 for d in days if start <= d <= through)


def build() -> dict:
    D = paths.data_dir()
    days = _sessions()
    rm = _load(D / "readmodel" / "latest.json", {}) or {}
    through = dt.date.fromisoformat(rm["data_through"]) if rm.get("data_through") else None
    rows = []

    def add(name, what, start, need, done, so_far, unit="sessions", judge=None):
        start_d = dt.date.fromisoformat(start) if isinstance(start, str) else start
        if unit == "months" and start_d:
            y, m = start_d.year + (start_d.month - 1 + need) // 12, (start_d.month - 1 + need) % 12 + 1
            fin = dt.date(y, m, min(start_d.day, 28))
        else:
            fin = _finish(days, start_d, done, need) if start_d else None
        left = max(need - done, 0)
        rows.append({"name": name, "what": what, "started": start_d.isoformat() if start_d else None, "done": done, "need": need, "left": left,
                     "unit": unit, "expected_finish": fin.isoformat() if fin else None, "complete": done >= need, "so_far": so_far, "judged_on": judge})

    # 1. the no-chase filter in the paper rules (Madhav's yes, 30 Oct)
    st = _load(D / "paper" / "state.json", {}) or {}
    nc_start = dt.date(2026, 10, 30)
    nc_days = [d for d in sorted(st.get("decisions", {})) if d >= nc_start.isoformat()]
    rejected = 0
    for d in nc_days:
        dec = _load(D / "paper" / "decisions" / f"{d}.json", {}) or {}
        rejected += sum(1 for r in dec.get("journal", []) if r.get("reason") == "no_chase")
    add("the no-chase filter", "breakout, pullback and reversal buys are refused when the stock is extended or overbought (E04, RSI over 70)", nc_start, 20,
        _done(days, nc_start, through) if nc_days else 0,
        f"{len(nc_days)} decision day{'s' if len(nc_days) != 1 else ''} under the filter; {rejected} candidate{'s' if rejected != 1 else ''} refused for chasing" if nc_days else "starts with tonight's decision",
        judge="the filtered books against their own record before the filter and against the random control, after 20 sessions")

    # 2. the practice book's first 20-day exits
    first = min(st.get("decisions", {}), default=None)
    if first:
        f0 = dt.date.fromisoformat(first)
        add("the practice book's first 20-day holds", "the first trades reach their 20-session hold, so the book's win rate starts to mean something", f0, 21,
            _done(days, f0, through), "every close so far has been a stop-loss; no trade has reached its hold yet", judge="win rate and expectancy per family at 20 sessions")

    # 3. RX1 (avoid / exit stocks falling 2%+ under the 200-day)
    rx = _load(D / "paper" / "rx1_trial.json", {}) or {}
    if rx:
        add("the avoid-or-exit trial", "stocks falling 2% or more while below their 200-day average, the next session open to close against the 250 liquid stocks",
            rx.get("start"), int(rx.get("need") or 20), int(rx.get("scored") or 0), rx.get("words"), judge="the mean difference and its t across sessions; CONDITIONAL in history")

    # 4. the shadow trader
    sh = _load(D / "paper" / "shadow" / "summary.json", {}) or {}
    if sh:
        add("the shadow trader", "a second model plans each session blind to Ananta's plan, sealed before the open", "2026-10-30", int(sh.get("need") or 20),
            int(sh.get("sessions_sealed") or 0), sh.get("words"), judge="its odds beside the rule and the reviewer; its stance against the book's day; its watch names against the universe")

    # 5. your portfolio: the twin against the frozen holdings and the Nifty 500
    acc = (_load(D / "paper" / "account" / "view.json", {}) or {}).get("benchmark") or {}
    if acc.get("frozen_day"):
        add("your portfolio's twin against the frozen original", "the allocator's paper changes beside your holdings left as they were, and the Nifty 500", acc["frozen_day"], 60,
            _done(days, dt.date.fromisoformat(acc["frozen_day"]), through), acc.get("words"), judge="return and drawdown after costs; nothing read before 60 sessions")

    # 6. the long-term tilt book
    fb = _load(D / "paper" / "factorbook" / "view.json", {}) or {}
    if fb:
        start = fb.get("started") or "2026-10-30"
        add("the long-term tilt book", "the 50 calmest stocks, and momentum-plus-calm, each beside an equal-weight book, Rs 10 lakh paper, monthly", start, 12,
            max(0, (dt.date.today().year - int(start[:4])) * 12 + dt.date.today().month - int(start[5:7])), fb.get("words"), unit="months", judge="drawdown as much as return over 12 months")

    # 7. the options line
    sp1 = ((rm.get("sp1") or {}).get("book") or {})
    if sp1.get("sessions") is not None:
        add("the options line", "one index option lot a session on paper at four decision points", "2026-10-24", 20, int(sp1.get("sessions") or 0),
            (rm.get("sp1") or {}).get("words"), judge="net rupees with realistic fills against the index move, after 20 sessions")

    out = {"built_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "data_through": rm.get("data_through"), "trials": rows,
           "note": "sessions are NSE trading days; an expected finish after the calendar's end counts weekdays, so a holiday can move it a day or two"}
    out["words"] = words(out)
    (paths.manifest_dir() / "trials.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    return out


def _dw(s: str | None) -> str:
    if not s:
        return "unknown"
    d = dt.date.fromisoformat(s)
    return d.strftime("%a %-d %b")


def words(out: dict) -> str:
    bits = []
    for r in out["trials"]:
        if r["complete"]:
            bits.append(f"{r['name']}: complete ({r['done']} of {r['need']} {r['unit']}).")
        else:
            bits.append(f"{r['name']}: {r['done']} of {r['need']} {r['unit']} done, {r['left']} to go, expected to finish about {_dw(r['expected_finish'])}; so far: {r['so_far']}")
    return " ".join(bits) if bits else "no trial is running"


if __name__ == "__main__":
    o = build()
    for r in o["trials"]:
        print(f"- {r['name']}: {r['done']}/{r['need']} {r['unit']}, finish ~{r['expected_finish']}; {str(r['so_far'])[:110]}")
