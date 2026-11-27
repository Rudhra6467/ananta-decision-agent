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
    try:                                       # 21 Nov 2026 (the lock review, G-09): the exchange's known holidays past the calendar's end
        from india import dayplan
        hol = {dt.date.fromisoformat(str(h)[:10]) for h in dayplan.holidays(refresh=False)}
    except Exception:  # noqa: BLE001
        hol = set()
    d = last
    while len(days) < 10_000 and d < last + dt.timedelta(days=400):
        d += dt.timedelta(days=1)
        if d.weekday() < 5 and d > last and d not in hol:
            days.append(d)
    return days


def _finish(days, start: dt.date, done: int, need: int, through: dt.date | None = None) -> dt.date | None:
    """The session on which the trial reaches `need`. 21 Nov 2026 (the outside lock review, G-09): counting `need` sessions from `start`
    ignored the trial's own count, so a trial that skipped a session (the options line counts neither the Muhurat hour nor a lost day)
    was said to finish early: the options line at 18 of 20 on Fri 20 Nov was given 23 Nov, not Wed 25 Nov (24 Nov a holiday). With the
    count and the day it runs through, the finish is the (need - done)th session after that day; without them, as before."""
    if through is not None and 0 <= done < need:
        later = [d for d in days if d > through]
        k = need - done - 1
        return later[k] if k < len(later) else None
    after = [d for d in days if d >= start]
    if not after:
        return None
    idx = need - 1
    return after[idx] if idx < len(after) else None


def _done(days, start: dt.date, through: dt.date | None) -> int:
    through = through or dt.date.today()
    return sum(1 for d in days if start <= d <= through)


def practice_words(st: dict) -> str:
    """23 Nov 2026 (the audit re-check): this line said "every close so far has been a stop-loss; no trade has reached its hold yet" for
    good, written once on 29 Oct, while the book had 33 closes by time or target. It now reads the book (india/bookstats.py split)."""
    try:
        from india import bookstats
        s = bookstats.split(bookstats.trade_rows(st))
        c, o, k = s["total"]["closed"], s["total"]["open"], s["closes"]
    except Exception as exc:  # noqa: BLE001
        return f"the book's closes could not be read ({type(exc).__name__})"
    if not c["n"]:
        return "no trade has closed yet"
    avg = f"{100 * c['avg']:+.1f}%" if c["avg"] is not None else "n/a"
    return (f"{c['n']} closed so far ({k['stops']} by stop-loss, {k['time_or_target']} by time or target): {c['winners']} won, average {avg}; "
            f"{o['n']} still open, {o['winners']} of them up")


def managed_splits() -> list[tuple[str, str]]:
    """The managed book's rule versions and the day each split its record, from the pin history of its paper rules (india_lock.json):
    [('managed-v1', start), ('managed-v2', '2026-11-17'), ('managed-v3', '2026-11-21')]. Read-only."""
    import re
    from pathlib import Path
    lock = _load(Path(__file__).resolve().parent / "registrations" / "india_lock.json", {}) or {}
    out = []
    for h in (((lock.get("pins") or {}).get("paper_rules") or {}).get("history") or []):
        m = re.search(r"split at this day: (managed-v\d+)", str(h.get("note") or ""))
        if m and h.get("date"):
            out.append((m.group(1), str(h["date"])[:10]))
    return sorted(out, key=lambda x: x[1])


def managed_words(mb: dict, days: list, splits: list[tuple[str, str]] | None = None) -> str:
    """27 Nov 2026 (flag 231, the 23 Nov audit): the managed book's trial line leads with stocks and cash against the Nifty 500, then the
    options lot apart, and names the parts of its record split at each rule change (managed-v2 17 Nov, managed-v3 21 Nov). The 60-session
    clock itself is unchanged: it is the pinned judgement, counted from the first session."""
    sp = mb.get("split") or {}
    if not sp.get("words"):
        return str(mb.get("words") or "")
    splits = managed_splits() if splits is None else splits
    head = (f"Stocks and cash {sp['stocks_cash_pct']:+.1f}% (₹{sp['stocks_cash_inr']:+,.0f}) against the Nifty 500 {sp['market_pct']:+.1f}% over the same sessions; "
            f"the options lot apart, {'+' if (sp.get('options_inr') or 0) >= 0 else '−'}₹{abs(sp.get('options_inr') or 0):,.0f}; "
            f"together ₹{mb.get('value_inr') or 0:,.0f}, {mb.get('return_pct') or 0:+.2f}% since {_dw(mb.get('start_day'))}.")
    day = str(mb.get("day") or "")[:10]
    start = str(mb.get("start_day") or "")[:10]
    n = int((mb.get("clock") or {}).get("sessions") or 0)
    if splits and day and start:
        bounds = [("managed-v1", start)] + [s for s in splits if start < s[1] <= day]
        names = []
        for i, (name, frm) in enumerate(bounds):
            to = bounds[i + 1][1] if i + 1 < len(bounds) else None
            k = sum(1 for d in days if d.isoformat() > start and d.isoformat() >= frm and d.isoformat() <= day and (to is None or d.isoformat() < to))
            first = next((d.isoformat() for d in days if d.isoformat() >= frm and d.isoformat() > start), frm)   # the first session under it
            names.append((name, first, k))
        if len(names) > 1:
            if days and sum(k for _, _, k in names) == n:
                parts = "; ".join(f"{nm} {k} session{'s' if k != 1 else ''}" + ("" if j == 0 else f" from {_dw(frm)}") for j, (nm, frm, k) in enumerate(names))
            else:
                parts = "; ".join(nm + ("" if j == 0 else f" from {_dw(frm)}") for j, (nm, frm, _k) in enumerate(names))
            head += f" Its record is in {len(names)} parts, split at each rule change: {parts}."
    if mb.get("twins_words"):
        head += " " + str(mb["twins_words"])
    plan = mb.get("plan") or {}
    return (head + (f" {mb['clock']['words']}" if (mb.get("clock") or {}).get("words") else "")
            + (f" {plan['words']}" if isinstance(plan, dict) and plan.get("words") and not plan.get("error") else ""))


def sp1_words(rm_words: str | None, book: dict) -> str:
    """The options line's 'so far': the read model's day part, then the book part from the line's own book (flag 230), in the read model's words."""
    day = str(rm_words or "").split(" Book over ")[0].strip() if rm_words else ""
    if day.startswith("Book over "):
        day = ""
    parts = []
    for k, v in (book.get("by_index") or {}).items():
        late = int(v.get("scored_late") or 0)
        parts.append(f"{k}: {int(v.get('trades') or 0)} scored trade(s)" + (f" ({late} scored late)" if late else "")
                     + f", index {v.get('index_proxy_sum_bps') or 0:+.0f} bp, one option lot Rs {v.get('option_1lot_rs_realistic_fill') or 0:,.0f} with realistic fills")
    upd = str(book.get("updated") or "")[:10]
    tail = f"Book over {int(book.get('sessions') or 0)} scored session(s)" + (f", scored to {_dw(upd)}" if upd else "") + ": " + "; ".join(parts)
    return f"{day} {tail}" if day else tail


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
            fin = _finish(days, start_d, done, need, through) if start_d else None
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
            _done(days, f0, through), practice_words(st), judge="win rate and expectancy per family at 20 sessions")

    # 3. RX1 (avoid / exit stocks falling 2%+ under the 200-day)
    rx = _load(D / "paper" / "rx1_trial.json", {}) or {}
    if rx:
        add("the avoid-or-exit trial", "stocks falling 2% or more while below their 200-day average, the next session open to close against the 250 liquid stocks",
            rx.get("start"), int(rx.get("need") or 20), int(rx.get("scored") or 0), rx.get("words"), judge="the mean difference and its t across sessions; CONDITIONAL in history")

    # 3b. the relative-strength trial (Madhav's yes, 2 Nov 19:20): RS1's near miss recorded forward
    rs = _load(D / "paper" / "rs_trial.json", {}) or {}
    if rs:
        add("the relative-strength trial", "liquid stocks in the top tenth by 6-month strength against the Nifty, not stretched, each day's picks held 20 sessions, "
            "against the average liquid stock and random picks, after costs", rs.get("start"), int(rs.get("need") or 20), int(rs.get("scored") or 0), rs.get("words"),
            judge="the RS book's lead over the average stock and over random picks; INCONCLUSIVE in history (t 3.54 / 3.11 against a bar of 3.60)")

    # 4. the shadow trader
    sh = _load(D / "paper" / "shadow" / "summary.json", {}) or {}
    if sh:
        add("the shadow trader", "a second model plans each session blind to Ananta's plan, sealed before the open", "2026-10-30", int(sh.get("need") or 20),
            int(sh.get("sessions_sealed") or 0), sh.get("words"), judge="its odds beside the rule and the reviewer; its stance against the book's day; its watch names against the universe")

    # 5. your portfolio: the twin against the frozen holdings and the Nifty 500
    acc = (_load(D / "paper" / "account" / "view.json", {}) or {}).get("benchmark") or {}
    if acc.get("frozen_day"):
        # 31 Oct (outsider r5): the clock and the benchmark row must agree. Session 1 is the first session AFTER the frozen day (the snapshot
        # is taken after that day's close), so the trial starts the next day and 'done' is the benchmark's own count.
        start = next((d for d in days if d > dt.date.fromisoformat(acc["frozen_day"])), dt.date.fromisoformat(acc["frozen_day"]))
        add("your portfolio's twin against the frozen original", "the allocator's paper changes beside your holdings left as they were, and the Nifty 500", start, 60,
            int(acc.get("sessions") or _done(days, start, through)), acc.get("words"), judge="return and drawdown after costs; nothing read before 60 sessions")

    # 5b. the managed book (Madhav's yes, 30 Oct evening): the cuts replaced on paper
    mb = _load(D / "paper" / "managed" / "view.json", {}) or {}
    if mb.get("start_day"):
        try:                       # 27 Nov 2026 (flag 290, Madhav's yes of 26 Nov 22:22): the two twins, marked with the nightly trials run
            from india import managedtwins
            tw = managedtwins.build()
            if tw.get("status") == "ok":
                mb = {**mb, "twins_words": tw.get("words")}
        except Exception as e:  # noqa: BLE001  the twins never break the trials list
            print(f"managed twins not marked: {type(e).__name__}: {e}", file=sys.stderr)
        start = next((d for d in days if d > dt.date.fromisoformat(mb["start_day"])), dt.date.fromisoformat(mb["start_day"]))   # session 1 = the first plan's session
        add("the managed book (cuts replaced on paper)", "your holdings with each cut's money moved into a replacement chosen by the proved not-losing filters, beside the twin, the frozen original and the Nifty 500",
            start, 60, int((mb.get("clock") or {}).get("sessions") or 0), managed_words(mb, days), judge="return and drawdown after costs against the frozen original; the replacement ledger (cut right, replacement rose); nothing read before 60 sessions")

    # 6. the long-term tilt book
    fb = _load(D / "paper" / "factorbook" / "view.json", {}) or {}
    if fb:
        start = fb.get("started") or "2026-10-30"
        add("the long-term tilt book", "the 50 calmest stocks, and momentum-plus-calm, each beside an equal-weight book, Rs 10 lakh paper, monthly", start, 12,
            max(0, (dt.date.today().year - int(start[:4])) * 12 + dt.date.today().month - int(start[5:7])), fb.get("words"), unit="months", judge="drawdown as much as return over 12 months")

    # 7. the options line
    sp1 = ((rm.get("sp1") or {}).get("book") or {})
    own = _load(D / "paper" / "sp1" / "book.json", {}) or {}
    if own.get("sessions") is not None:
        # 27 Nov 2026 (flag 230, the 23 Nov audit): the read model can be older than the options line's own book (scored at 17:30 IST), so
        # this list said 18 sessions and Rs 43,431 while the brief said 19 and Rs 104,354. The count and the book's rupees come from the book.
        add("the options line", "one index option lot a session on paper at four decision points", "2026-10-24", 20, int(own.get("sessions") or 0),
            sp1_words((rm.get("sp1") or {}).get("words"), own), judge="net rupees with realistic fills against the index move, after 20 sessions")
    elif sp1.get("sessions") is not None:
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
