"""India views: the app's own /v3 contract (the shapes the four tabs already read) filled from the India read model and the India
paper ledgers, so the crypto screens render the Indian market unchanged (Madhav, 23 Oct: "exactly like crypto, but for the Indian market").
Shapes were captured from the running crypto service on 23 Oct (~/ananta_runs/india_contract/*.json); every key the screens read is
present here with its Indian meaning, and what India does not have yet is an empty list or null, never an invented number.
Sources (all on the Mac, none sealed, none Kite): readmodel/latest.json and readmodel/<day>.json, paper/state.json, paper/marks.jsonl,
paper/events.jsonl, paper/decisions/<day>.json and .universe.json, paper/calls.jsonl, paper/sp1/*, manifests/missed_*.json and
others_*.json, the registrations pages. Read-only by construction.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path

DATA = Path(os.getenv("ANANTA_INDIA_DATA", os.path.expanduser("~/ananta_data/india")))
RECORDS = Path(os.getenv("ANANTA_RECORDS", os.path.expanduser("~/code/ananta-records")))
REG = RECORDS / "india" / "registrations"
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
TOR = dt.timezone(dt.timedelta(hours=-4))
ACCOUNT_START = 60000.0            # the India book (Madhav, 19 Oct): Rs 60,000 to start, the SP1 index line
ACCOUNT_SINCE = "2026-10-21"       # SP1 paper start (sessions so far are what the ledger says)
NOTIONAL = 50000.0                 # the stock research book's scale unit per trade
CAPS = {"BRK": 10, "PULL": 10, "REV": 10, "CTL": 5}
REF_POLICY = "hold_20d"
CAMPAIGN = {"BRK": "Breakout", "PULL": "Pullback", "REV": "Reversal", "CTL": "Random pick"}
CAMPAIGN_WHY = {"BRK": "breaks above its one-month high on heavy volume", "PULL": "a strong stock resting at its one-month average",
                "REV": "a stock sold too hard, due a bounce", "CTL": "picked at random, to compare Ananta's picks against"}
JOB_WORDS = {"autologin": "morning sign-in", "evening": "evening data", "morning": "morning check", "nightly": "nightly checks", "paper": "stock picks",
             "recorder_noon": "option prices", "sp1paper": "options line", "sp1paper.score": "options scoring", "spreads": "option spreads", "allocator": "money split"}


# ---------------------------------------------------------------------------------------------------------------- files

def _json(p: Path, default=None):
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return default


def _jsonl(p: Path) -> list[dict]:
    try:
        return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
    except (OSError, ValueError):
        return []


def readmodel() -> dict:
    return _json(DATA / "readmodel" / "latest.json", {}) or {}


def _rm_days() -> list[str]:
    d = DATA / "readmodel"
    return sorted(p.stem for p in d.glob("????-??-??.json")) if d.exists() else []


def _decision_days() -> list[str]:
    d = DATA / "paper" / "decisions"
    return sorted(p.stem for p in d.glob("????-??-??.json")) if d.exists() else []


def _ts(iso: str | None) -> int:
    if not iso:
        return 0
    try:
        return int(dt.datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp())
    except ValueError:
        return 0


def _when(iso: str | None) -> str:
    t = _ts(iso)
    return dt.datetime.fromtimestamp(t, TOR).strftime("%b %-d, %-I:%M %p") if t else ""


def _day_t(day: str, hour_ist: int = 15, minute: int = 30) -> int:
    try:
        return int(dt.datetime.fromisoformat(day).replace(hour=hour_ist, minute=minute, tzinfo=IST).timestamp())
    except ValueError:
        return 0


# ---------------------------------------------------------------------------------------------------------------- ledgers

def exec_marks() -> dict[str, dict]:
    """Latest mark per campaign on the exec book at the reference exit."""
    out = {}
    for m in _jsonl(DATA / "paper" / "marks.jsonl"):
        if m.get("book") == "exec" and m.get("policy") == REF_POLICY:
            out[m["campaign"]] = m
    return out


def lab_value_series() -> list[tuple[int, float]]:
    """The stock paper book's value over time (start + realised + unrealised across campaigns at the reference exit), one point per mark time."""
    by_t: dict[str, dict[str, float]] = {}
    for m in _jsonl(DATA / "paper" / "marks.jsonl"):
        if m.get("book") == "exec" and m.get("policy") == REF_POLICY:
            by_t.setdefault(m["at"], {})[m["campaign"]] = (m.get("realised_inr") or 0) + (m.get("open_unrealised_inr") or 0)
    pts = []
    for at in sorted(by_t):
        pts.append((_ts(at), round(lab_start() + sum(by_t[at].values()), 2)))
    return pts


def lab_start() -> float:
    return float(sum(CAPS.values()) * NOTIONAL)


def open_positions() -> list[dict]:
    st = _json(DATA / "paper" / "state.json", {}) or {}
    seen: dict[tuple, dict] = {}
    for t in (st.get("trades") or {}).values():
        if t.get("book") != "exec" or t.get("status") != "open":
            continue
        k = (t["campaign"], t["sid"])
        if t.get("policy") == REF_POLICY or k not in seen:
            e, l = t.get("entry_adj"), t.get("last_close_adj")
            seen[k] = {"id": f"{t['signal_date']}|{t['campaign']}|{t['sid']}", "coin": t.get("symbol"), "campaign": t["campaign"], "entry": e, "now": l,
                       "pnl_pct": round(100 * (l / e - 1), 2) if e and l else None, "pnl_usd": round(NOTIONAL * (l / e - 1), 2) if e and l else None,
                       "since": t.get("entry_date"), "signal_date": t.get("signal_date"), "last_date": t.get("last_date"), "bars_seen": t.get("bars_seen"),
                       "stop": None, "target": None, "liq_rank": t.get("liq_rank"), "policy": t.get("policy")}
    return sorted(seen.values(), key=lambda r: (r["campaign"], -(r["pnl_pct"] or 0)))


def closed_trades(limit: int = 40) -> list[dict]:
    rows = []
    for e in _jsonl(DATA / "paper" / "events.jsonl"):
        if e.get("event") != "close":
            continue
        parts = str(e.get("id", "")).split("|")
        if len(parts) < 4 or parts[3] != REF_POLICY:
            continue
        rows.append({"id": e["id"], "coin": None, "sid": parts[2], "campaign": parts[1], "signal_date": parts[0], "exit_date": e.get("exit_date"),
                     "net_usd": round(e.get("net_inr") or 0, 2), "why": f"exit: {e.get('reason', '')}", "time": _when(e.get("at")), "t": _ts(e.get("at")),
                     "stamp": {"who": "ananta", "label": f"Research book · {CAMPAIGN.get(parts[1], parts[1])}", "source": "stockbook"}, "link": None})
    # names: the universe files carry sid -> symbol
    names = _names()
    for r in rows:
        r["coin"] = names.get(r["sid"], r["sid"])
    rows.sort(key=lambda r: -r["t"])
    return rows[:limit]


@lru_cache(maxsize=4)
def _names_cached(stamp: str) -> dict[str, str]:
    out = {}
    for day in _decision_days()[-10:]:
        u = _json(DATA / "paper" / "decisions" / f"{day}.universe.json", {}) or {}
        for r in u.get("rows", []):
            out[r.get("sid")] = r.get("symbol")
        d = _json(DATA / "paper" / "decisions" / f"{day}.json", {}) or {}
        for r in d.get("journal", []) + d.get("signals", []):
            out[r.get("sid")] = r.get("symbol")
    return out


def _names() -> dict[str, str]:
    days = _decision_days()
    return _names_cached(days[-1] if days else "")


def universe_rows(day: str | None = None) -> list[dict]:
    days = _decision_days()
    day = day or (days[-1] if days else None)
    if not day:
        return []
    return (_json(DATA / "paper" / "decisions" / f"{day}.universe.json", {}) or {}).get("rows", [])


def decision(day: str | None = None) -> dict:
    days = _decision_days()
    day = day or (days[-1] if days else None)
    return (_json(DATA / "paper" / "decisions" / f"{day}.json", {}) or {}) if day else {}


def sparks() -> dict[str, list[float]]:
    """Per-symbol relative path over the recorded sessions (ret_1 chained from the decision-time universe files): derived, never a sealed read."""
    paths: dict[str, list[float]] = {}
    for day in _decision_days()[-30:]:
        for r in universe_rows(day):
            s = r.get("symbol")
            if not s or r.get("ret_1") is None:
                continue
            prev = paths.get(s, [1.0])[-1]
            paths.setdefault(s, [1.0]).append(round(prev * (1 + r["ret_1"]), 5))
    return paths


# ---------------------------------------------------------------------------------------------------------------- Home: /v3/home

def plain_brief(rm: dict) -> list[str]:
    """Ananta's day in three short sentences a person reads in ten seconds: the market, what it picked, the options line and the account."""
    out = []
    m = rm.get("market") or {}
    if m.get("nifty_close"):
        tr = {"above_both": "in an uptrend", "below_both": "in a downtrend", "mixed": "with no clear trend"}.get(m.get("trend_state"), "")
        out.append(f"Nifty closed at {m['nifty_close']:,.0f} on {_day_words(m.get('data_through'))}, {tr}.")
    d = rm.get("decisions_today") or {}
    chosen = [x for x in d.get("chosen", []) if x.get("campaign") != "CTL"]
    if chosen:
        by = Counter(x.get("campaign") for x in chosen)
        kinds = ", ".join(f"{v} {CAMPAIGN.get(k, k).lower()}{'s' if v != 1 else ''}" for k, v in by.most_common())
        out.append(f"Ananta picked {len(chosen)} stocks to buy on paper at the next open ({kinds}).")
    if (d.get("inputs") or {}).get("marked"):
        # Madhav, 25 Oct: decisions on stale inputs are marked, never stopped
        out.append("Marked: these picks were made on stale data (" + "; ".join((d["inputs"].get("stale") or [])[:2]) + ").")
    c = rm.get("call") or {}
    if c.get("call"):
        word = {"BULLISH": "up", "BEARISH": "down", "NEUTRAL": "flat"}.get(str(c["call"]).upper(), str(c["call"]).lower())
        rec = f"so far {c.get('hits', 0)} of {c.get('scored', 0)} calls were right, against {c.get('null_hits', 0)} for a coin flip."
        if c.get("data_through") and str(c["data_through"]) < str(rm.get("data_through") or ""):
            # 25 Oct: the newest call was made on 22 Oct data for the 23 Oct session, and was shown as the call for Monday
            out.append(f"No call yet for the next session (the last one, {word}, was made on {_day_words(c['data_through'])} data); {rec}")
        else:
            out.append(f"It calls the next session {word}; {rec}")
    s = rm.get("sp1") or {}
    if s.get("status") == "lost":
        out.append("Options: nothing traded yet, because the morning sign-in to Zerodha was missing.")
    return out


def _day_words(d) -> str:
    """'2026-10-22' -> '22 Oct' for a sentence a person reads."""
    try:
        return dt.date.fromisoformat(str(d)[:10]).strftime("%-d %b")
    except (TypeError, ValueError):
        return str(d or "")


def _health(rm: dict) -> dict:
    j = rm.get("jobs") or {}
    jobs = j.get("jobs") or []
    down = [x["label"] for x in jobs if not x.get("ok")]
    signin = [x["label"] for x in jobs if not x.get("ok") and (x["label"] in ("autologin", "evening") or any(w in "; ".join(x.get("problems") or []).lower() for w in ("token", "sign-in", "kite", "depth snapshots", "recorder")))]
    if signin and len(signin) == len(down):
        down = [f"the Zerodha morning sign-in ({len(signin)} jobs waited for it)"]
    elif signin:
        down = [f"the Zerodha morning sign-in ({len(signin)} jobs waited for it)"] + [x for x in down if x not in signin]
    age = None
    try:
        age = int((dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(rm["built_at"])).total_seconds())
    except (KeyError, ValueError):
        pass
    return {"all_ok": not down and bool(jobs), "down": down, "ok": len(jobs) - len(down), "of": len(jobs), "checked_s_ago": age}


def _book() -> dict:
    """The account book (records repo india/account.py): the paper twin of Madhav's account that trades the allocation. {} until it exists."""
    return _json(DATA / "paper" / "account" / "view.json", {}) or {}


def _account(rm: dict) -> dict:
    """The India account. Since 23 Oct (Madhav: "on the home tab it shows it trades on allocation") it is the account book, the paper twin of his
    account (stocks, options sleeve, cash) traded by the allocator; before the book exists, the Rs 60,000 SP1 index line.
    dial = the guardrail state (OPEN when no rule has fired); brakes = the 5%-day and 22%-pause rules."""
    a = _account_sp1(rm)
    ab = _book()
    if ab.get("value_inr"):
        pos = {p["symbol"]: {"qty": p.get("qty"), "avg": p.get("avg"), "last": p.get("last"), "paid": round((p.get("avg") or 0) * (p.get("qty") or 0), 2), "rule": "holding", "sleeve": "stocks"} for p in (ab.get("positions") or [])}
        paid = sum(v["paid"] for v in pos.values())
        stocks = float(ab.get("stocks_inr") or 0)
        snap = (_json(DATA / "paper" / "allocation_view.json", {}) or {}).get("snapshot") or {}
        s = rm.get("sp1") or {}
        opt_pnl = round(sum(float(v.get("option_1lot_rs_realistic_fill") or 0) for v in ((s.get("book") or {}).get("by_index") or {}).values()), 2)
        a.update({"value_cad": float(ab["value_inr"]), "start_cad": float(ab.get("start_inr") or ab["value_inr"]), "return_pct": float(ab.get("return_pct") or 0.0),
                  "cash_cad": float(ab.get("cash_inr") or 0), "started": (ab.get("opened_at") or "")[:10] or a["started"], "book_words": ab.get("words"), "positions": pos,
                  "options_inr": ab.get("options_inr"), "stocks_inr": ab.get("stocks_inr"), "positions_count": len(pos),
                  # the Home hero (Madhav, 24 Oct 16:27): stocks against what was paid, the options line's own result, and how fresh the prices are
                  "stocks_paid_inr": round(paid, 2), "stocks_pnl_inr": round(stocks - paid, 2), "stocks_pnl_pct": round(100 * (stocks / paid - 1), 2) if paid else None,
                  "options_book": {"pnl_inr": opt_pnl, "sessions": (s.get("book") or {}).get("sessions") or 0, "status": s.get("status")},
                  "prices_at": snap.get("taken_at"), "prices_stale_days": snap.get("stale_days"),
                  "pushed_rule": "Ananta may buy a new stock for the account only after a rule has proved itself on paper (20 sessions, beating chance and the market) and you say yes. Until then it holds, trims and rebalances."})
    return a


def _account_sp1(rm: dict) -> dict:
    s = rm.get("sp1") or {}
    g = rm.get("guardrails") or {}
    book = (s.get("book") or {}).get("by_index") or {}
    pnl = 0.0
    for v in book.values():
        pnl += float(v.get("option_1lot_rs_realistic_fill") or 0)
    sessions = (s.get("book") or {}).get("sessions") or 0
    m = rm.get("market") or {}
    trend = {"above_both": "an uptrend (above its ten-week and long-term averages)", "below_both": "a downtrend (below its ten-week and long-term averages)",
             "mixed": "no clear trend"}.get(m.get("trend_state"), "trend unknown")
    why = [f"Nifty {m.get('nifty_close'):,.0f} on {_day_words(m.get('data_through'))}: {trend}" if m.get("nifty_close") else "no market reading yet",
           # the call with its record beside it (24 Oct: "bullish" alone read like a forecast to lean on; it was 0 of 3)
           f"Ananta's call for the next session: {str((rm.get('call') or {}).get('call') or 'none').lower()}"
           + (f" (right {(rm.get('call') or {}).get('hits')} of {(rm.get('call') or {}).get('scored')} so far; a coin flip got {(rm.get('call') or {}).get('null_hits')})"
              if (rm.get("call") or {}).get("scored") else ""),
           (f"Guardrails: a {g['daily_loss_limit_pct']:.0f}% loss stops the day; {g['pause_drawdown_pct']:.0f}% below the peak pauses new buys"
            if g.get("daily_loss_limit_pct") is not None and g.get("pause_drawdown_pct") is not None else "Guardrails: not in the daily summary yet")]
    return {"started": ACCOUNT_SINCE, "value_cad": round(ACCOUNT_START + pnl, 2), "start_cad": ACCOUNT_START, "return_pct": round(100 * pnl / ACCOUNT_START, 2),
            "cash_cad": round(ACCOUNT_START + pnl, 2), "positions": {}, "currency": "INR",
            "brakes": {"paused": False, "block_until": None, "fired": {"day_loss": 0, "pause_22pct": 0}, "streak": 0},
            "dial": {"state": "OPEN: no guardrail has fired", "why": why},
            "last_step": (rm.get("built_at") or "")[:16].replace("T", " "), "execution_check": {"fills": 0, "inside_bid_ask": 0},
            "next": f"Next decisions at the open on {_day_words(rm.get('next_session'))} (09:15 Indian time)", "sessions": sessions,
            "note": {"day": rm.get("data_through"), "t": _ts(rm.get("built_at")), "note": " ".join(plain_brief(rm)), "cost_usd": 0},
            "lab": _lab_list(rm), "pushed_rule": "A playbook action trades the options line only after it is validated on 2018-2023, passes the selection checks, and you say yes."}


def _lab_list(rm: dict) -> list[dict]:
    r = rm.get("research") or {}
    out = [{"id": "SP1", "name": "Options line (Nifty and Bank Nifty)", "status": "PAPER", "verdict": f"on paper since 21 Oct · {((rm.get('sp1') or {}).get('book') or {}).get('sessions') or 0} sessions traded"},
           {"id": "SP3", "name": "Longer-hold playbook (stocks and index)", "status": "WAITING", "verdict": "written down, waiting for its test run"},
           {"id": "SZ2", "name": "Option sizing study", "status": "WAITING", "verdict": "written down, waiting for its test run"}]
    for camp, name in CAMPAIGN.items():
        out.append({"id": camp, "name": f"Research book · {name}", "status": "PAPER", "verdict": "practice trades since 16 Oct"})
    g = r.get("gate") or {}
    cnt = r.get("gate_counters") or {}
    out.append({"id": "G02", "name": "The gate to real money", "status": "CLOSED" if (g.get("state") or "BLOCKED") == "BLOCKED" else g.get("state"),
                "verdict": ("waiting on " + " and ".join(str(v) for v in cnt.values())) if isinstance(cnt, dict) and cnt else "waiting"})
    return out


def _jarvis(rm: dict) -> dict:
    d = rm.get("decisions_today") or {}
    cands = d.get("candidates") or {}
    chosen = [x for x in d.get("chosen", []) if x.get("campaign") != "CTL"]
    passed = sum((v.get("candidates") or 0) - (v.get("chosen") or 0) for k, v in cands.items() if k != "CTL")
    pos = open_positions()
    marks = exec_marks()
    closed = sum((m.get("closed") or 0) for m in marks.values())
    real = [m.get("realised_inr") or 0 for m in marks.values()]
    lg = ((rm.get("learning") or {}).get("league") or {})
    sessions = len(_rm_days())
    rnd = ((lg.get("h1") or {}).get("random") or {}) if isinstance((lg.get("h1") or {}).get("random"), dict) else {}
    return {"open": [{"id": p["id"], "coin": p["coin"], "pnl_pct": p["pnl_pct"]} for p in pos if p["campaign"] != "CTL"][:12],
            "today": {"TAKE": len(chosen), "PASS": passed}, "left": max(0, sum(CAPS.values()) - len(chosen)), "events": min(sessions, 10), "verdict": "too early",
            "closed": closed, "avg": round(sum(real) / max(1, closed) / NOTIONAL * 100, 2) if closed else None,          # net % per closed trade, reference exit
            "twins_avg": round(100 * (rnd.get("median") or 0), 2) if rnd else None}                                        # the random band's median (the league)


def findings(rm: dict, n: int = 5) -> list[dict]:
    """Missed movers (the learning loop) as Home findings: kind SEEN / MISSED / CAUGHT."""
    out = []
    for day in reversed(_rm_days()[-3:]):
        man = _json(DATA / "manifests" / f"missed_{day}.json", {}) or {}
        for mv in man.get("movers", [])[:8]:
            fired = mv.get("fired_in_window") or []
            kind = "CAUGHT" if mv.get("caught") else ("SEEN" if fired else "MISSED")
            pct = round(100 * (mv.get("cc") or 0), 1)
            out.append({"t": _day_t(day), "kind": kind, "coin": mv.get("symbol"), "link": "missed", "move_pct": pct,
                        "title": f"{mv.get('symbol')} {pct:+.1f}% on {_day_words(day)}",
                        "body": (f"A {CAMPAIGN.get(fired[-1].get('campaign') or fired[-1].get('family'), 'rule').lower()} rule had flagged it on {_day_words(fired[-1].get('date'))}, but it was not bought") if fired else "No rule was watching it",
                        "simple": f"{'Ananta had a rule on' if fired else 'No rule saw'} {mv.get('symbol')}'s {abs(pct):.0f}% {'rise' if pct > 0 else 'fall'}."})
    out.sort(key=lambda x: (-x["t"], -abs(x["move_pct"])))
    return out[:n]


def feed(limit: int = 40) -> list[dict]:
    rows = []
    rm = readmodel()
    for day in _decision_days()[-3:]:
        d = _json(DATA / "paper" / "decisions" / f"{day}.json", {}) or {}
        t = _ts(d.get("decided_at"))
        by = Counter(x.get("campaign") for x in d.get("signals", []))
        if by:
            n_real = sum(v for k, v in by.items() if k != "CTL")
            rows.append({"t": t, "kind": "watch", "coin": None, "title": f"Picked {n_real} stocks to buy on paper at the next open",
                         "body": ", ".join(f"{v} {CAMPAIGN.get(k, k).lower()}{'s' if v != 1 else ''}" for k, v in sorted(by.items()) if k != "CTL")
                                 + (f" · plus {by['CTL']} random picks to compare against" if by.get("CTL") else ""), "time": _when(d.get("decided_at"))})
        for x in d.get("signals", [])[:6]:
            if x.get("campaign") == "CTL":
                continue
            rows.append({"t": t - 1, "kind": "buy", "coin": x.get("symbol"), "title": f"{x.get('symbol')}: buy at the next open ({CAMPAIGN.get(x.get('campaign'), '').lower()})",
                         "body": CAMPAIGN_WHY.get(x.get("campaign"), "") + (f" · last ₹{x['close']:,.2f}" if x.get("close") else ""), "time": _when(d.get("decided_at"))})
    for e in _jsonl(DATA / "paper" / "events.jsonl")[-400:]:
        if e.get("event") == "close" and str(e.get("id", "")).endswith("|" + REF_POLICY):
            p = e["id"].split("|")
            net = e.get("net_inr") or 0
            rows.append({"t": _ts(e.get("at")), "kind": "sell", "coin": _names().get(p[2], p[2]), "good": net > 0, "trade_id": None,
                         "title": f"Sold {_names().get(p[2], p[2])} · {'+' if net >= 0 else '−'}₹{abs(net):,.0f}", "body": f"{CAMPAIGN.get(p[1], p[1])} · {_exit_words(e.get('reason'))} · {_day_words(e.get('exit_date'))}", "time": _when(e.get("at"))})
    for c in _jsonl(DATA / "paper" / "calls.jsonl")[-6:]:
        if c.get("kind") == "call":
            word = {"BULLISH": "up", "BEARISH": "down", "NEUTRAL": "flat"}.get(str(c.get("call")).upper(), str(c.get("call")).lower())
            rows.append({"t": _ts(c.get("written_at")), "kind": "watch", "coin": "NIFTY", "title": f"Ananta calls the next session {word}",
                         "body": f"Nifty {c.get('close'):,.0f}, {abs(100 * (c.get('nifty_vs_sma50') or 0)):.1f}% {'above' if (c.get('nifty_vs_sma50') or 0) >= 0 else 'below'} its ten-week average", "time": _when(c.get("written_at"))})
        elif c.get("kind") == "score":
            rows.append({"t": _ts(c.get("scored_at")), "kind": "watch", "coin": "NIFTY", "title": f"Yesterday's call was {'right' if c.get('score') == 1 else 'wrong'}",
                         "body": f"Nifty moved {100 * (c.get('move') or 0):+.2f}%", "time": _when(c.get("scored_at"))})
    for day in _rm_days()[-3:]:
        o = _json(DATA / "manifests" / f"others_{day}.json", {}) or {}
        h1 = (o.get("by_h") or {}).get("1") or {}
        cov = h1.get("coverage") or {}
        if cov:
            rows.append({"t": _ts(o.get("made_at")), "kind": "watch", "coin": None, "title": f"Against other traders on {_day_words(day)}: Ananta held {cov.get('TAKEN', 0)} of the day's 20 best trades",
                         "body": f"No rule for {cov.get('NOT_COVERED', 0)} of them · its picks beat {round(100 * (h1.get('ananta_pct_vs_random') or 0))}% of random picks · the average stock {100 * (h1.get('market_mean') or 0):+.1f}%", "time": _when(o.get("made_at"))})
    lost = (rm.get("sp1") or {})
    if lost.get("status") == "lost":
        rows.append({"t": _day_t(rm.get("data_through", "2026-01-01"), 9, 10), "kind": "alert", "coin": "NIFTY", "title": "The options line missed its session", "body": "The morning sign-in to Zerodha was missing, so no option trade could be recorded.", "time": ""})
    rows.sort(key=lambda r: -r["t"])
    return rows[:limit]


def _exit_words(reason) -> str:
    r = str(reason or "")
    if r.startswith("stop"):
        return "stop hit"
    if r.startswith("target"):
        return "target reached"
    if r in ("time", "hold") or r.startswith("hold"):
        return "holding time up"
    if r == "random":
        return "random exit (yardstick)"
    if r.startswith("sma") or r.startswith("trail") or r.startswith("atr") or r.startswith("swing"):
        return "trend turned"
    return r.replace("_", " ") or "exit"


def day_summary(rm: dict) -> dict:
    a = _account(rm)
    marks = exec_marks()
    lab_val = lab_start() + sum((m.get("realised_inr") or 0) + (m.get("open_unrealised_inr") or 0) for m in marks.values())
    pos = open_positions()
    d = rm.get("decisions_today") or {}
    chosen = [x for x in d.get("chosen", []) if x.get("campaign") != "CTL"]
    m = rm.get("market") or {}
    tr = {"above_both": "in an uptrend, above its ten-week and long-term averages", "below_both": "in a downtrend, below its ten-week and long-term averages", "mixed": "between its ten-week and long-term averages"}.get(m.get("trend_state"), "trend unknown")
    sentence = (f"Nifty {m['nifty_close']:,.0f} on {_day_words(m.get('data_through'))}, {tr}; {100 * (m.get('breadth_200d_liquid') or 0):.0f}% of the 250 most-traded stocks are above their long-term average."
                if m.get("nifty_close") else "No market reading yet.") + " Paper only: no real money is at risk."
    return {"date": dt.datetime.now(TOR).strftime("%A, %b %-d"), "paper_value": round(a["value_cad"] + lab_val, 2), "start_value": ACCOUNT_START + lab_start(), "today_change": 0.0,
            "explorer": {"value": round(lab_val, 2), "open": len(pos), "opened_today": len(chosen), "closed_today": 0},
            "portfolio": {"value": a["value_cad"], "return_pct": a["return_pct"], "mode": "PAPER", "holding": 0, "pending": 0},
            "hourly_watch": {"looks_today": 0}, "sentence": sentence}


def market_block(rm: dict) -> dict:
    m = rm.get("market") or {}
    closes, ema = [], []
    for c in _jsonl(DATA / "paper" / "calls.jsonl"):
        if c.get("kind") == "call" and c.get("close"):
            closes.append(float(c["close"]))
            ema.append(round(float(c["close"]) / (1 + (c.get("nifty_vs_sma50") or 0)), 2))
    v50 = m.get("nifty_vs_sma50")
    return {"regime": {"above_both": "UPTREND", "below_both": "DOWNTREND", "mixed": "MIXED"}.get(m.get("trend_state"), "UNKNOWN"), "btc": m.get("nifty_close"),
            "ema50": round(m["nifty_close"] / (1 + v50), 2) if m.get("nifty_close") and v50 is not None else None, "vs_pct": round(100 * v50, 2) if v50 is not None else None,
            "closes": closes, "ema": ema, "live_side": "above" if (v50 or 0) > 0 else "below", "index": "NIFTY 50"}


def mission(rm: dict) -> dict:
    series = lab_value_series()
    return {"health": _health(rm), "value": {"t": [t for t, _ in series], "v": [v for _, v in series], "start": lab_start(), "since": "Oct 16"},
            "market": market_block(rm), "jarvis": _jarvis(rm), "account": _account(rm), "findings": findings(rm)}


def home() -> dict:
    rm = readmodel()
    return {"summary": day_summary(rm), "feed": feed(), "mission": mission(rm), "market": "india", "data_through": rm.get("data_through")}


# ---------------------------------------------------------------------------------------------------------------- Books, holdings, history

def _trade_row(p: dict) -> dict:
    return {"id": p["id"], "coin": p["coin"], "book": "stockbook", "stamp": {"who": "ananta", "label": f"Research book · {CAMPAIGN.get(p['campaign'], p['campaign'])}", "source": "stockbook"},
            "entry": p["entry"], "now": p["now"], "currency": "INR", "pnl_usd": p["pnl_usd"], "pnl_pct": p["pnl_pct"], "since": p["since"],
            "why": CAMPAIGN_WHY.get(p["campaign"]), "stop": None, "target": None, "sleeve": p["campaign"], "rule": p["campaign"], "link": None,
            "setup_name": CAMPAIGN.get(p["campaign"]), "type_name": "paper · delivery", "status": "open", "time": p["since"], "entries": 1}


def books() -> dict:
    rm = readmodel()
    a = _account(rm)
    marks = exec_marks()
    pos = open_positions()
    closed = closed_trades()
    lab_val = lab_start() + sum((m.get("realised_inr") or 0) + (m.get("open_unrealised_inr") or 0) for m in marks.values())
    open_pnl = sum((m.get("open_unrealised_inr") or 0) for m in marks.values())
    closed_pnl = sum((m.get("realised_inr") or 0) for m in marks.values())
    acct_summary = {"value": a["value_cad"], "start": a["start_cad"], "open_count": 0, "open_pnl": 0.0, "closed_pnl_recent": 0.0, "closed_count": 0, "won_count": 0,
                    "execution_check": a["execution_check"], "since": a["started"], "dial_open": True, "brakes": a["brakes"]}
    account = {"book": {"name": "Your account (paper copy)" if _book() else "The options line (paper)", "value": a["value_cad"], "start": a["start_cad"], "currency": "INR", "execution_check": a["execution_check"],
                        "started": a["started"], "dial_open": True, "brakes": a["brakes"], "status": "ACTIVE",
                        "why": ("Your holdings, the options money and cash, traded by Ananta on paper. Real trades wait for the gate and your yes." if _book()
                                else "The options line on paper. Guardrails: a 5% loss stops the day; 22% below the peak pauses new buys.")},
               "trades": [], "closed": [], "currency": "INR", "summary": acct_summary}
    lab_trades = [_trade_row(p) for p in pos]
    by_camp = []
    for camp, name in CAMPAIGN.items():
        m = marks.get(camp) or {}
        by_camp.append({"id": camp, "name": f"Research book · {name}", "kind": "paper", "t": _ts(m.get("at")), "start": CAPS[camp] * NOTIONAL,
                        "value": round(CAPS[camp] * NOTIONAL + (m.get("realised_inr") or 0) + (m.get("open_unrealised_inr") or 0), 2), "status": "PAPER",
                        "verdict": f"{m.get('open') or 0} open · {m.get('closed') or 0} closed · " + ("no closed trades yet" if not m.get("closed") else ("no closed win yet" if not m.get("win_rate") else f"{round(100 * m['win_rate'])}% of closed won"))
                                   + (f" · {per_trade_pct(m):+.1f}% a closed trade" if per_trade_pct(m) is not None else "")
                                   + _open_side(camp),
                        "per_trade_pct": per_trade_pct(m), "events": m.get("closed") or 0, "result": None})
    n_closed = sum((m.get("closed") or 0) for m in marks.values())
    avg_all = round(100 * closed_pnl / (n_closed * NOTIONAL), 1) if n_closed else None
    return {"summary": {"value": round(lab_val + a["value_cad"], 2), "start": lab_start() + a["start_cad"], "open_pnl": round(open_pnl, 2), "closed_pnl_recent": round(closed_pnl, 2),
                        "open_count": len(pos), "retired_pnl": 0.0, "retired_count": 0, "evidence_open": len(pos)},
            "account": account, "lab": {"trades": lab_trades, "closed": closed, "books": by_camp, "decision": " ".join(plain_brief(rm)[:2])},
            "retired": [], "evidence_open_by": dict(Counter(p["campaign"] for p in pos)), "trades": lab_trades, "closed": closed, "books": by_camp,
            "stamps": {"stockbook": "Ananta's research book: practice trades of ₹50,000 each, to test its rules"}, "random_open": sum(1 for p in pos if p["campaign"] == "CTL"),
            "initials": {}, "per_trade_pct": avg_all,
            "read": ("Paper only. Your account is the paper copy on Home; this research book tests Ananta's rules with ₹50,000 practice trades and is not your money."
                     # 25 Oct audit: rupee totals of notional ₹50,000 slots read like money lost next to a ₹1.6 lakh account; the per-trade % is the honest scale
                     + (f" Read it in % per trade: its {n_closed} closed trades averaged {avg_all:+.1f}% each." if avg_all is not None else "")
                     + (f" {str(((rm.get('stock_book') or {}).get('closed_vs_open') or {}).get('words'))[:1].upper()}{str(((rm.get('stock_book') or {}).get('closed_vs_open') or {}).get('words'))[1:]}." if ((rm.get("stock_book") or {}).get("closed_vs_open") or {}).get("words") else ""))}


def _open_side(camp: str) -> str:
    """Flag 44 (26 Oct): the open trades beside a closed-trades-only win rate, from the read model's closed_vs_open ("· 3 of 24 open are up (-3.4% avg)")."""
    try:
        o = (((readmodel().get("stock_book") or {}).get("closed_vs_open") or {}).get("by_family") or {}).get(camp, {}).get("open") or {}
    except Exception:  # noqa: BLE001 - a missing read model leaves the old line
        return ""
    if not o.get("n"):
        return ""
    return f" · {o['winners']} of {o['n']} open are up" + (f" ({o['avg'] * 100:+.1f}% avg)" if o.get("avg") is not None else "")


def per_trade_pct(m: dict) -> float | None:
    """The research book's average closed trade as a % of its ₹50,000 practice slot (25 Oct audit: show the book in % per trade)."""
    n = m.get("closed") or 0
    return round(100 * (m.get("realised_inr") or 0) / (n * NOTIONAL), 1) if n else None


def holdings(full: bool = False) -> dict:
    rm = readmodel()
    a = _account(rm)
    ab = _book()
    if ab.get("value_inr"):
        pos = ab.get("positions") or []
        rows = [{"coin": p["symbol"], "qty": p.get("qty"), "avg": p.get("avg"), "now": p.get("last"), "value": p.get("value_inr"), "pnl_pct": p.get("pnl_pct"), "currency": "INR",
                 **({"note": p["note"]} if p.get("note") else {})} for p in pos] if full else []
        return {"mode": "PAPER", "value": ab["value_inr"], "start": ab.get("start_inr"), "return_pct": ab.get("return_pct"), "cash": ab.get("cash_inr"), "invested": ab.get("stocks_inr"),
                "options": ab.get("options_inr"), "costs_paid": ab.get("costs_inr"), "holdings": rows, "holdings_count": len(pos), "not_held": [], "pending": ab.get("pending_days") or [],
                "decided": rm.get("data_through"), "btc_gate": (rm.get("market") or {}).get("trend_state") == "above_both", "shadow": {"value": ab["value_inr"], "return_pct": ab.get("return_pct")},
                "trades": (ab.get("trades") or [])[-10:] if full else [], "rule_plain": ab.get("words") or ""}
    d = rm.get("decisions_today") or {}
    not_held = [{"coin": x.get("symbol"), "rating": CAMPAIGN.get(x.get("campaign"), ""), "why": x.get("why", "")} for x in d.get("chosen", []) if x.get("campaign") != "CTL"][:10]
    return {"mode": "PAPER", "value": a["value_cad"], "start": a["start_cad"], "return_pct": a["return_pct"], "cash": a["cash_cad"], "invested": 0, "costs_paid": 0.0,
            "holdings": [], "not_held": not_held, "pending": [], "decided": rm.get("data_through"), "btc_gate": (rm.get("market") or {}).get("trend_state") == "above_both",
            "shadow": {"value": a["value_cad"], "return_pct": a["return_pct"]}, "rule_plain": "The options line trades on paper; the stocks you see in the research book are practice trades, not holdings."}


def history(days: int = 30) -> dict:
    series = lab_value_series()
    m = (readmodel().get("market") or {})
    nifty = m.get("nifty_close")
    return {"points": [{"t": t, "explorer": v, "main": ACCOUNT_START, "shadow": v, "btc": nifty} for t, v in series[-days * 24:]]}


# ---------------------------------------------------------------------------------------------------------------- Markets: coins, chain, exposure, watches, evidence/live

def _rating(r: dict) -> str:
    if r.get("breakout20"):
        return "BREAKOUT"
    if r.get("breakdown20"):
        return "BREAKDOWN"
    if r.get("new_high_250"):
        return "NEW HIGH"
    if r.get("new_low_250"):
        return "NEW LOW"
    return "WATCH"


def coins(n: int = 40) -> dict:
    """The liquid Indian stocks the stock book decides on, in the shape the Markets tab reads for coins."""
    rm = readmodel()
    d = decision()
    close = {}
    for r in d.get("journal", []) + d.get("signals", []):
        if r.get("close"):
            close[r["symbol"]] = r["close"]
    chosen = {x["symbol"]: x["campaign"] for x in d.get("signals", [])}
    pos = Counter(p["coin"] for p in open_positions())
    sp = sparks()
    out = []
    for r in sorted(universe_rows(), key=lambda r: r.get("liq_rank") or 9999)[:n]:
        s = r.get("symbol")
        path = sp.get(s, [1.0])
        px = close.get(s)
        out.append({"coin": s, "price": px, "day_pct": round(100 * (r.get("ret_1") or 0), 2), "week_pct": round(100 * (path[-1] / path[max(0, len(path) - 6)] - 1), 2) if len(path) > 1 else None,
                    "spark": [round((px or 100) * x / path[-1], 2) for x in path], "rating": _rating(r), "held_usd": None, "open_trades": pos.get(s, 0),
                    "trend_1h": "up" if (r.get("oc") or 0) > 0 else "down", "trend_4h": "up" if (r.get("dist_sma20") or 0) > 0 else "down",
                    "daily": "above its long-term average" if (r.get("dist_sma200") or 0) > 0 else "below its long-term average",
                    "closest": {"setup": chosen.get(s, ""), "name": CAMPAIGN.get(chosen.get(s, ""), "no rule fired"), "met": 1 if s in chosen else 0, "of": 1, "missing": "" if s in chosen else "not picked today"},
                    "liq_rank": r.get("liq_rank"), "vol_ratio20": r.get("vol_ratio20"), "rsi14": r.get("rsi14")})
    return {"coins": out, "data_through": rm.get("data_through"), "universe": (d.get("universe") or {})}


def chain() -> dict:
    rm = readmodel()
    gates = [{"gate": "LIQUIDITY", "question": "Is it one of the 250 most-traded stocks?"}, {"gate": "TREND", "question": "Which way is the Nifty trending?"},
             {"gate": "FAMILY", "question": "Does it match one of Ananta's rules (breakout, pullback, reversal)?"}, {"gate": "COSTS", "question": "Can the trade pay its charges?"},
             {"gate": "GUARDRAIL", "question": "Is a guardrail stopping new buys?"}]
    d = decision()
    rows = []
    for x in d.get("signals", [])[:12]:
        rows.append({"coin": x.get("symbol"), "price": x.get("close"), "verdict": "TAKEN" if x.get("campaign") != "CTL" else "CONTROL", "stops_at": "",
                     "summary": CAMPAIGN_WHY.get(x.get("campaign"), ""), "gates": [{**g, "status": "PASS", "why": "", "source": "today's decisions", "values": {}, "reached": True} for g in gates],
                     "observations": {"relative_strength": x.get("dist_sma200"), "volume": x.get("vol_ratio20"), "setup_family": CAMPAIGN.get(x.get("campaign")), "daily_atr_pct": round(100 * (x.get("atr14") or 0) / (x.get("close") or 1), 2) if x.get("close") else None, "your_setups": "", "zone": ""}})
    return {"framework": "How a stock gets bought: it must be one of the 250 most-traded, fit the Nifty trend, match a rule, pay its charges, and pass the guardrails.", "gates": gates,
            "stops": {"GUARDRAIL": 0}, "coins": rows, "note": f"From Ananta's decisions on {_day_words(rm.get('data_through'))}."}


def exposure() -> dict:
    rm = readmodel()
    m = rm.get("market") or {}
    a = _account(rm)
    marks = exec_marks()
    books_ = []
    for camp, name in CAMPAIGN.items():
        mk = marks.get(camp) or {}
        start = CAPS[camp] * NOTIONAL
        books_.append({"book": f"Research book · {name}", "role": "control" if camp == "CTL" else "family", "return_pct": round(100 * ((mk.get("realised_inr") or 0) + (mk.get("open_unrealised_inr") or 0)) / start, 2),
                       "worst_fall_pct": None, "trades": (mk.get("open") or 0) + (mk.get("closed") or 0), "days": len(_rm_days())})
    v50 = m.get("nifty_vs_sma50")
    trend_words = {"above_both": "in an uptrend: breakouts are in season", "below_both": "in a downtrend: Ananta looks for bounces, breakouts are rare",
                   "mixed": "with no clear trend"}.get(m.get("trend_state"), "trend unknown")
    return {"dial": {"dial": 1.0,                                                         # OPEN unless a guardrail has fired (the 5% day, the 22% pause): paper records, nothing has fired
                     "dial_words": f"No guardrail has fired. Nifty {trend_words}.", "why": a["dial"]["why"], "challenger_weight": None, "benchmark_in": True, "btc_vol_30d_pct": None,
                     "as_of_day": m.get("data_through"), "rule": "A 5% loss in a day stops trading for that day; 22% below the peak pauses new buys. The Nifty trend changes what Ananta looks for; it does not switch it off."},
            "books": {"since": "2026-10-16", "books": books_, "how_to_read": "Each rule trades its own practice book at ₹50,000 a trade; the random picks are the yardstick."},
            "measured_edges": [], "account": {"account_usd": a["value_cad"], "taken": 0, "closed": 0, "open": 0, "skipped": {"dial_closed": 0, "full": 0, "same_coin": 0, "same_day": 0, "risk_cap": 0},
                                              "net_usd": 0.0, "return_pct": a["return_pct"], "avg_R": None, "total_R": 0.0, "hurdle_pct": None, "beats_hurdle": False, "positive_expectancy": False,
                                              "rules": "the index playbook; the option sizing study is still to run", "how_to_read": "No options sessions yet: they start once the morning sign-in to Zerodha works."},
            "fidelity": {"cells": [], "min_trades": 20, "rule": "Paper prices are checked against live quotes once the options line has sessions."}, "nifty_vs_sma50_pct": round(100 * v50, 2) if v50 is not None else None}


def watches_mine() -> dict:
    rm = readmodel()
    d = rm.get("decisions_today") or {}
    w = []
    by = {}
    for x in d.get("chosen", []):
        by.setdefault(x.get("campaign"), []).append(x.get("symbol"))
    for camp, syms in by.items():
        w.append({"id": f"family:{camp}", "t": _ts(d.get("decided_at")), "coins": syms, "group": None, "kind": camp, "kind_name": CAMPAIGN.get(camp, camp), "mode": "tell", "mode_words": "buys on paper at the next open",
                  "state": "fired", "detail": {"coins": syms, "best": syms[0] if syms else None, "why": CAMPAIGN_WHY.get(camp, "")}, "checked_t": _ts(rm.get("built_at")), "fired_t": _ts(d.get("decided_at")), "by": "ananta"})
    return {"watches": w, "kinds": [{"kind": k, "name": v, "plain": CAMPAIGN_WHY.get(k, ""), "evidence": "practice trades since 16 Oct", "default": k != "CTL"} for k, v in CAMPAIGN.items()],
            "modes": {"tell": "tells you", "ask": "asks first", "auto": "takes the paper trade"}, "groups": {"my_coins": "picked today", "all": "the 250 most-traded stocks", "large": "Nifty 50"}}


def evidence_live() -> dict:
    rm = readmodel()
    r = rm.get("research") or {}
    lg = (rm.get("learning") or {}).get("league") or {}
    h1 = lg.get("h1") or {}
    days = len(_rm_days())
    marks = exec_marks()
    items = [{"key": c, "label": f"Research book · {CAMPAIGN[c]}", "closed": m.get("closed") or 0, "wins": None, "net_usd": round(m.get("realised_inr") or 0, 2),
              "avg_usd": round((m.get("realised_inr") or 0) / max(1, m.get("closed") or 0), 2), "events": days, "open": m.get("open") or 0, "events_own": days} for c, m in marks.items()]
    cnt = r.get("gate_counters") or {}
    return {"as_of": rm.get("data_through"), "days": days, "rules": "rules as of 23 Oct", "since": "2026-10-16",
            "health": {**_health(rm), "summary": "", "outages_3d": []},
            "clocks": [{"cadence": "daily", "name": "stock picks", "scope": "research book", "n": days, "unit": "sessions", "detail": "picked every evening at 22:30 Toronto"},
                       {"cadence": "daily", "name": "other traders", "scope": "comparison", "n": days, "unit": "sessions", "detail": "the day's best trades over 1, 5 and 20 sessions"},
                       {"cadence": "daily", "name": "options line", "scope": "Nifty and Bank Nifty", "n": ((rm.get("sp1") or {}).get("book") or {}).get("sessions") or 0, "unit": "sessions", "detail": "needs the morning sign-in"},
                       {"cadence": "nightly", "name": "the gate", "scope": "to real money", "n": 0, "unit": "of 30", "detail": "waiting on " + " and ".join(str(v) for v in cnt.values()) if isinstance(cnt, dict) and cnt else "waiting"}],
            "limits": [], "results": {"items": items, "random_avg_usd": round(NOTIONAL * (h1.get("market_mean") or 0), 2) if h1 else None, "events": days, "goal_events": 60,
                                      "books": [], "by_setup": [], "verdict": "too early", "read": "After 60 sessions on paper, each book must sit inside its expected range before the gate opens."},
            "rebuild": _rebuild(rm, h1, days),
            "misses": [], "board": [], "in_use": {"verdicts": r.get("verdicts"), "studies": r.get("studies")}, "teachers": teachers_brief()}


# ---------------------------------------------------------------------------------------------------------------- the YouTube teachers, tested
_TEACH: dict = {}
TEACH_WORD = {"PASSED": "Held up", "MIXED": "Partly held", "WRONG WAY": "Wrong way", "DID NOT HOLD": "Did not hold", "NOT ENOUGH DATA": "Not enough data",
              "MEASURED": "Measured", "Waiting for live option prices": "Tracking live"}


def teachers() -> dict:
    """The teacher cards (records repo india/teachers.py, run of 25 Oct 2026): every claim from the two YouTube libraries as a tested card, with
    plain words, the variants' verdicts and the forward books. Read from gold/teachers/summary.json; the agent never reads the teaching itself."""
    p = DATA / "gold" / "teachers" / "summary.json"
    try:
        mt = p.stat().st_mtime
    except OSError:
        return {"ready": False, "cards": [], "counts": {}}
    if _TEACH.get("mt") != mt:
        s = json.loads(p.read_text())
        for c in s.get("cards", []):
            c["word"] = TEACH_WORD.get(c.get("verdict"), c.get("verdict"))
        fo = (s.get("forward_options") or {}).get("systems") or {}
        s["forward_rows"] = [{"id": k, "card": v.get("card"), "forward_sessions": v.get("forward_sessions", 0), "before_cards_sessions": v.get("before_cards_sessions", 0),
                              "total_inr": v.get("total_inr"), "forward_total_inr": v.get("forward_total_inr"), "win_share": v.get("win_share"), "worst_inr": v.get("worst_inr"),
                              "stage": v.get("stage")} for k, v in sorted(fo.items())]
        s["ready"] = True
        _TEACH.update({"mt": mt, "v": s})
    return _TEACH["v"]


def teachers_brief() -> dict | None:
    s = teachers()
    if not s.get("ready"):
        return None
    tested = [c for c in s["cards"] if c.get("status") == "TEST"]
    by = Counter(c["verdict"] for c in tested)
    live_n = sum(1 for c in s["cards"] if c.get("status") == "FORWARD")
    return {"cards": len(s["cards"]), "tested": len(tested), "variants": s.get("variants_tested"), "held": by.get("PASSED", 0) + by.get("MIXED", 0),
            "wrong_way": by.get("WRONG WAY", 0), "did_not_hold": by.get("DID NOT HOLD", 0), "not_enough": by.get("NOT ENOUGH DATA", 0), "tracking_live": live_n,
            "survivors": s.get("survivors", [])[:6],
            "line": f"{len(tested)} of {len(s['cards'])} claims backtested on 2000-2023: {by.get('PASSED', 0) + by.get('MIXED', 0)} held up at least partly, "
                    f"{by.get('WRONG WAY', 0)} came out the wrong way, {by.get('DID NOT HOLD', 0)} did not hold, {by.get('NOT ENOUGH DATA', 0)} had too little data. "
                    f"{live_n} intraday option systems are tracked on the live recorder."}


# ---------------------------------------------------------------------------------------------------------------- More: cockpit, evidence/collected, ladder

def cockpit() -> dict:
    rm = readmodel()
    j = rm.get("jobs") or {}
    systems = [{"label": f"India · {JOB_WORDS.get(x['label'], x['label'])}", "ok": bool(x.get("ok"))} for x in j.get("jobs", [])]
    actions = []
    for day in reversed(_decision_days()[-5:]):
        d = _json(DATA / "paper" / "decisions" / f"{day}.json", {}) or {}
        actions.append({"time": _when(d.get("decided_at")), "who": "ananta", "action": "stock picks on paper", "detail": f"picked {len(d.get('signals', []))} of {len(d.get('journal', []))} candidates", "result": "recorded"})
    return {"switches": [{"key": "india_paper", "label": "India paper trading", "on": True, "help": "The research book and the options line trade every session on paper. Read-only here.", "confirm": False},
                         {"key": "india_orders", "label": "Real orders", "on": False, "help": "Locked until the gate and your yes; a nightly check makes sure no order can be sent.", "confirm": True}],
            "systems": systems, "circuit_breakers": {"india_book": {"status": "ARMED", "consecutive_losses": 0, "drawdown_usd": 0.0, "drawdown_pct_of_start": 0.0, "checked_at": rm.get("built_at"),
                                                                    "reason": "a 5% loss stops the day; 22% below the peak pauses buys (written down now, enforced with real money)", "tripped_at": None, "evidence": []}},
            "recent_actions": actions, "signin": j.get("signin")}


def _rx_cards() -> list[Path]:
    d = DATA / "paper" / "reconstruction"
    return sorted(d.glob("????-??-??.json")) if d.exists() else []


RULE_WORDS = {"stock:BRK": "Breakout rule", "stock:PULL": "Pullback rule", "stock:REV": "Reversal rule", "options:SP1": "Options line"}
STEP_WORDS = {"NOTED": "noted", "DRAFT": "an idea", "REGISTERED": "written down", "TESTED": "tested on past years", "SHADOW": "on trial", "ADMITTED": "proved", "LIVE_ELIGIBLE": "ready for real money"}
FINDING_WORDS = {"DATA_GAP": "Missing data", "JOB_FAIL": "A job failed", "SIGNIN_LOST": "Zerodha sign-in missing", "WORDS": "Part of the card failed", "MISS_PATTERN": "The same kind of miss again",
                 "LEAGUE_GAP": "Other traders caught moves Ananta had no rule for", "EXIT_LESSON": "An exit lesson", "HELD_INTO_FALL": "Held stocks into falls", "CALL_DRIFT": "The daily call is weak",
                 "OPTIONS_LINE": "The options line is misfiring", "EVENT_NOTE": "An event noted", "EVENT_SURPRISE": "An event that keeps coming back", "ALLOC_WRONG": "Money moves are misfiring"}
STATE_WORDS = {"to_file": "goes to the repair shop tonight", "filed": "on the repair shop", "closed": "closed (false alarm)", "DRAFT": "waiting for your yes", "NOTE": "noted", "APPROVED": "approved: to be studied",
               "SKIPPED": "skipped", "REGISTERED": "written down", "TESTED": "tested"}


POLICY_WORDS = {"sma_close_50": "sell when it closes under its ten-week average", "sma_close_20": "sell when it closes under its one-month average",
                "sma_close_10": "sell when it closes under its two-week average", "hold_5d": "hold for 5 days", "hold_10d": "hold for 10 days", "hold_20d": "hold for 20 days",
                "hold_40d": "hold for 40 days", "hold_60d": "hold for 60 days", "atr_trail_2": "a trailing stop two daily ranges under the high",
                "atr_trail_3": "a trailing stop three daily ranges under the high", "atr_trail_4": "a trailing stop four daily ranges under the high",
                "swing_low_5": "sell under the lowest low of the last 5 days", "swing_low_10": "sell under the lowest low of the last 10 days",
                "swing_low_20": "sell under the lowest low of the last 20 days", "target_1R": "take profit at one times the risk", "target_2R": "take profit at twice the risk",
                "target_3R": "take profit at three times the risk", "scale_half_then_trail3": "sell half at the first target, trail the rest", "random_exit": "a random exit (the yardstick)"}
DATA_WORDS = {"deals": "big single-client trades (bulk and block deals)", "fii_dii": "foreign and domestic institutions' buying and selling", "announcements": "company announcements",
              "ledger_snapshot": "daily snapshot of your Zerodha account"}


def finding_words(r: dict) -> str:
    """A finding in one plain sentence, composed from its type, so rows written before the plain-words pass read the same as new ones."""
    t, key = r.get("type"), str(r.get("key") or "")
    day = _day_words(r.get("day")) if r.get("day") else ""
    tail = key.split(":", 1)[1] if ":" in key else ""
    if t == "DATA_GAP":
        return f"The {DATA_WORDS.get(tail, tail.replace('_', ' '))}{' for ' + day if day else ''} did not reach Ananta."
    if t == "SIGNIN_LOST":
        return f"The morning sign-in to Zerodha was missing{' for ' + day if day else ''}, so the options line could not trade."
    if t == "JOB_FAIL":
        return f"The '{JOB_WORDS.get(tail, tail)}' job did not finish properly{' on ' + day if day else ''}."
    if t == "WORDS":
        return f"One part of the nightly review{' for ' + day if day else ''} failed to build."
    return r.get("words") or ""


def _rule_line(k: str, r: dict) -> str:
    return (f"{RULE_WORDS.get(k, k)}: {STEP_WORDS.get(r.get('step'), r.get('step'))} · {r.get('shadow_sessions', 0)} of {r.get('shadow_bar', 20)} trial sessions · "
            f"beat chance and the market on {r.get('beats', 0)} of {r.get('beats_bar', 10)} days")


def _rebuild(rm: dict, h1: dict, days: int) -> dict:
    """The Reconstruction screen's block, from RX-IN (india/reconstruct.py): nightly cards, the league, the staircase as the chain."""
    rx = rm.get("reconstruction") or {}
    cards = _rx_cards()
    st = rx.get("staircase") or {}
    chain = []
    steps = ["NOTED", "DRAFT", "REGISTERED", "TESTED", "SHADOW", "ADMITTED", "LIVE_ELIGIBLE"]
    for k, r in (st.get("rules") or {}).items():
        chain.append({"id": k, "step": r.get("step"), "steps": [STEP_WORDS[x] for x in steps], "words": _rule_line(k, r)})
    f = rx.get("findings") or []
    return {"books": [{"book": "the nightly review", "runs": len(cards), "mismatches": 0, "what": "the market · what other traders did · what Ananta did and did not do · trade reviews · findings"}],
            "nightly": {"runs": len(cards), "first": cards[0].stem if cards else "", "mismatches": 0, "every": "every night at 22:30 Toronto, after the day's picks"},
            "asked": {"runs": 0, "mismatches": 0, "last": "", "how": "ask Ananta: what did you learn last night?"}, "total": len(cards), "mismatches": 0,
            "last": {"when": rx.get("built_at") or "", "match": True, "checked": len(f), "rebuilt": len(cards), "headline": rx.get("headline") or "no review yet"},
            "how": "Every night Ananta replays the day: what the market did, what other traders did, what it did and did not do. A pattern needs to repeat (3 days in 7) before it becomes an idea.",
            "if_mismatch": "Small fixes (data, jobs, words) go to the repair shop by themselves; anything that touches trading waits for your yes.",
            "others": {"id": "league", "title": "Ananta against other traders", "date": rm.get("data_through"), "runs": str(days), "excluded_bots": 0, "accounts_trading_our_coins": 0,
                       "round_trips": 20, "long": 20, "short": 0, "period": "H1", "our_setups_silent_before_their_buys_pct": None, "their_timing_edge": "", "skill_persisted": False,
                       "what_we_did": rx.get("league_words") or f"held {(h1.get('coverage') or {}).get('TAKEN', 0)} of the top 20 trips; picks at the {round(100 * (h1.get('ananta_pct_vs_random') or 0))}th percentile of random"},
            "findings": [{"type": FINDING_WORDS.get(x.get("type"), x.get("type")), "lane": x.get("lane"), "state": STATE_WORDS.get(x.get("state"), x.get("state")), "words": finding_words(x)} for x in f],
            "reviews": rx.get("reviews") or {}, "staircase_words": st.get("words") or "", "chain": chain}


def _stairs_words(st: dict) -> str:
    rules = st.get("rules") or {}
    if st.get("admitted"):
        return "Proved and allowed to use your money: " + ", ".join(RULE_WORDS.get(k, k) for k in st["admitted"]) + "."
    if not rules:
        return "No rule is on trial yet."
    best = max((r.get("shadow_sessions") or 0) for r in rules.values())
    beats = max((r.get("beats") or 0) for r in rules.values())
    return (f"No rule has proved itself yet. The stock rules have {best} of 20 trial sessions and beat chance and the market on {beats} of 10 days; "
            f"the options line has {(rules.get('options:SP1') or {}).get('shadow_sessions', 0)} sessions.")


def drafts() -> dict:
    """The DECISION findings waiting for Madhav's yes or skip, numbered in a fixed order (oldest first) so "the first draft" means the same thing
    on the screen and in the voice tab."""
    rows = [r for r in _queue_rows() if r.get("lane") == "DECISION" and r.get("state") == "DRAFT"]
    rows.sort(key=lambda r: (r.get("day") or "", r.get("key") or ""))
    return {"drafts": [{"n": i + 1, "key": r["key"], "type": r.get("type"), "day": r.get("day"), "words": r.get("words")} for i, r in enumerate(rows)],
            "decided": [{"key": r["key"], "state": r["state"], "at": r.get("decided_at")} for r in _queue_rows() if r.get("state") in ("APPROVED", "SKIPPED")][-10:],
            "meaning": "Yes = register a study for it (written down before it runs, tested on 2000-2023 only); Skip = closed, not filed again."}


def netnotes(day: str | None = None) -> list[dict]:
    d = day or (readmodel().get("data_through") or "")
    return _jsonl(DATA / "paper" / "reconstruction" / "netnotes" / f"{d}.jsonl")


def reconstruction() -> dict:
    """The latest session card whole, plus the staircase and the queue counts (the card holds no holdings, so everyone may read it)."""
    p = DATA / "paper" / "reconstruction" / "latest.json"
    c = _json(p, {}) or {}
    rm = readmodel()
    rx = rm.get("reconstruction") or {}
    if not c:
        return {"ready": False, "headline": "No reconstruction card yet: the first one is written tonight at 22:30 Toronto.", "staircase": rx.get("staircase") or {}}
    return {"ready": True, "day": c.get("day"), "rules": c.get("rules"), "built_at": c.get("built_at"), "headline": c.get("headline"),
            "sections": {"market": c.get("market"), "people": c.get("people"), "ananta": c.get("ananta"), "not_done": c.get("not_done"), "reviews": c.get("reviews")},
            "findings": [{**x, "words": finding_words(x), "type_words": FINDING_WORDS.get(x.get("type"), x.get("type")), "state_words": STATE_WORDS.get(x.get("state"), x.get("state"))} for x in (c.get("findings") or [])],
            "forwarding": c.get("forwarding") or {}, "staircase": rx.get("staircase") or {}, "cards": len(_rx_cards()),
            "net_notes": netnotes(c.get("day")), "drafts": drafts()["drafts"]}


def _queue_rows() -> list[dict]:
    q = REG / "reconstruction_queue.jsonl"
    rows = _jsonl(q)
    filed = {f.get("key"): f for f in _jsonl(DATA / "paper" / "reconstruction" / "forwarded.jsonl")}
    dec = {d.get("key"): d for d in _jsonl(DATA / "paper" / "reconstruction" / "decisions.jsonl")}
    for r in rows:
        d = dec.get(r.get("key"))
        if d and r.get("lane") == "DECISION":
            r["state"], r["decided_at"], r["decided_words"] = d.get("decision"), d.get("at"), d.get("words")
    # 25 Oct: a forwarded row that names its day matches only that day's finding, so closing or filing JOB_FAIL:paper of 23 Oct does not hide
    # a new paper failure on a later day (a row without a day still matches by key, as before)
    filed_day = {(f.get("key"), f.get("day")): f for f in _jsonl(DATA / "paper" / "reconstruction" / "forwarded.jsonl") if f.get("day")}
    for r in rows:
        fw = filed_day.get((r.get("key"), r.get("day"))) or (filed.get(r.get("key")) if not (filed.get(r.get("key")) or {}).get("day") else None)
        if fw:
            if str(fw.get("note", "")).startswith("closed"):          # a SAFE row closed without filing (a false alarm), with the reason in the note
                r["state"], r["closed_why"] = "closed", fw.get("note")
                continue
            r["state"] = "filed" if r.get("state") == "to_file" else r.get("state")
            r["request"] = fw.get("num")
    return rows


def evidence_collected() -> dict:
    rm = readmodel()
    marks = exec_marks()
    r = rm.get("research") or {}
    v = r.get("verdicts") or {}
    collected = [{"setup": c, "name": f"Research book · {CAMPAIGN[c]}", "seen": None, "orders": (m.get("open") or 0) + (m.get("closed") or 0), "shadow_orders": 0, "bought": (m.get("open") or 0) + (m.get("closed") or 0),
                  "closed": m.get("closed") or 0, "net_usd": round(m.get("realised_inr") or 0, 2)} for c, m in marks.items()]
    cnt = r.get("gate_counters") or {}
    tracker = [{"key": "sessions", "label": "Days on paper", "value": len(_rm_days()), "explain": "stock picks every evening since 16 Oct"},
               {"key": "validated", "label": "Ideas that passed a strict test", "value": v.get("VALIDATED", 0), "explain": f"of {sum(v.values())} versions tried on past years"},
               {"key": "ready", "label": "Studies ready to run", "value": (r.get("studies") or {}).get("ready", 0), "explain": "all their data is in"},
               {"key": "gate", "label": "Gate to real money", "value": 0, "explain": "waiting"}]
    # 25 Oct audit: the India exam (records india/exam.py), a gate row: 30 questions to Ask Ananta, judged in code against its facts
    ex = (r.get("exam") or {}).get("last") or {}
    if isinstance(cnt, dict) and cnt:
        waits = [str(v) for k, v in cnt.items() if k != "D32" and v] + ([] if ex.get("exam_pass") else ["a passed India exam"])
        tracker[-1]["explain"] = "waiting on " + " and ".join(waits) if waits else "waiting"
    tracker.append({"key": "exam", "label": "India exam (30 questions)",
                    "value": (ex.get("known") or 0) + (ex.get("unknown") or 0) + (ex.get("why") or 0) if ex else 0,
                    "explain": (f"right on {_day_words(ex.get('day'))}; every answer safe: {'yes' if ex.get('safety') == ex.get('of') else 'no'}; "
                                f"{'passed' if ex.get('exam_pass') else 'not passed yet'} (pass: 16 of 18 facts, 6 of 7 'I don't know', 4 of 5 reasons)") if ex else "not run yet: weekly, from the evening job"})
    forwarded = []
    for k, p in (r.get("exit_book") or {}).get("chosen", {}).items():
        fam, _, situ = str(k).partition("/")
        situ_w = {"all": "any market", "above_both": "an uptrend", "below_both": "a downtrend", "mixed": "a mixed market"}.get(situ, situ.replace("_", " "))
        forwarded.append({"id": f"G01:{k}", "title": f"Best exit for {CAMPAIGN.get(fam, fam).lower()}s in {situ_w}", "date": "2026-10-22", "verdict": "HELD" if p else "NOT_HELD",
                          "why": (f"chosen: {POLICY_WORDS.get(str(p), str(p).replace('_', ' '))}" if p else "no exit held up on years it had not seen"), "question": "Which exit held up on years it had not seen?",
                          "result": POLICY_WORDS.get(str(p), str(p or "none").replace("_", " ")), "changed": ""})
    rx = rm.get("reconstruction") or {}
    st = rx.get("staircase") or {}
    rows = _queue_rows()
    for q in rows:
        if q.get("lane") == "SAFE":
            forwarded.append({"id": q.get("key"), "title": f"{FINDING_WORDS.get(q.get('type'), q.get('type'))} · {_day_words(q.get('day'))}", "date": q.get("day"), "verdict": q.get("state", "").upper(),
                              "why": finding_words(q), "question": "sent to the repair shop" + (f" as request #{q['request']}" if q.get("request") else " (tonight)") if q.get("state") != "closed" else "closed: a false alarm", "result": STATE_WORDS.get(q.get("state"), q.get("state")), "changed": ""})
    running = [{"id": k, "status": STEP_WORDS.get(r.get("step"), r.get("step")), "title": RULE_WORDS.get(k, k), "waiting_for": f"{r.get('shadow_sessions', 0)} of {r.get('shadow_bar', 20)} trial sessions; beat chance and the market on {r.get('beats', 0)} of {r.get('beats_bar', 10)} days",
                "why": "a rule must prove itself on paper before it can use your money", "metric": "trial sessions", "goal": r.get("shadow_bar", 20)} for k, r in (st.get("rules") or {}).items()]
    waiting = [{"id": q.get("key"), "status": STATE_WORDS.get(q.get("state"), q.get("state")), "title": f"{FINDING_WORDS.get(q.get('type'), q.get('type'))} ({_day_words(q.get('day'))})", "waiting_for": "your yes" if q.get("lane") == "DECISION" else "the repair shop",
                "why": finding_words(q)[:200], "metric": "needs you" if q.get("lane") == "DECISION" else "fixed by itself", "goal": None} for q in rows if q.get("state") in ("DRAFT", "NOTE", "to_file", "filed")]
    done = [{"id": k, "status": "proved", "title": RULE_WORDS.get(k, k), "waiting_for": "", "why": "you said yes", "metric": "", "goal": None} for k in (st.get("admitted") or [])]
    tracker.append({"key": "cards", "label": "Nightly reviews", "value": len(_rx_cards()), "explain": "one every evening since 22 Oct"})
    st_s = r.get("stale_input_sessions") or []
    tracker.append({"key": "stale", "label": "Picks made on stale data", "value": len(st_s),
                    "explain": ("marked, never dropped: " + ", ".join(x["day"] for x in st_s[-3:])) if st_s else "none so far"})
    tracker.append({"key": "findings", "label": "Things found", "value": len([q for q in rows if q.get("state") in ("DRAFT", "NOTE", "to_file", "filed")]), "explain": "small ones fixed by themselves; trading ones wait for you"})
    shop = {"running": running, "waiting": waiting, "done": done, "summary": _stairs_words(st)}
    return {"collected": collected, "tracker": tracker, "forwarded": forwarded, "shop": shop}


def universe_ladder() -> dict:
    rm = readmodel()
    rows = [{"watch": f"Research book · {n}", "rule": CAMPAIGN_WHY.get(c, ""), "tier": "research", "step": "PAPER", "meaning": "practice trades every session", "next_allowed": False,
             "why": "needs 60 sessions and the gate first", "signed_by": None} for c, n in CAMPAIGN.items()]
    rows.append({"watch": "Options line", "rule": "trades Nifty and Bank Nifty options in the first hour, by the index playbook", "tier": "account", "step": "PAPER",
                 "meaning": "the options money on paper", "next_allowed": False, "why": f"{((rm.get('sp1') or {}).get('book') or {}).get('sessions') or 0} sessions traded so far", "signed_by": None})
    return {"rows": rows, "steps": ["RESEARCH", "PAPER", "GATE", "LIVE"], "rule": "Research → paper (60 sessions) → the gate → your yes → real money."}


# ---------------------------------------------------------------------------------------------------------------- Ask-adjacent, alerts, needs, misc

def agent_state() -> dict:
    rm = readmodel()
    s = rm.get("sp1") or {}
    lines = [{"tone": "warn" if x.startswith("Options: nothing") else "info", "text": x} for x in plain_brief(rm)]
    mv = _mv_latest()
    if mv.get("session") and mv.get("session") >= str(rm.get("data_through") or ""):
        lines.insert(0, {"tone": "info", "text": f"Morning view for {_day_words(mv['session'])}: " + ((mv.get("lines") or {}).get("headline") or "")})
    return {"lines": lines, "watches": watches_mine()["watches"], "positions": [{"coin": p["coin"], "pnl_pct": p["pnl_pct"], "since": p["since"]} for p in open_positions()[:20]],
            "needs_you": 0, "last_check": {"accounts": 1, "fired": 0, "warned": 1 if s.get("status") == "lost" else 0, "ms": 0}}


def ask_suggestions() -> dict:
    rm = readmodel()
    d = rm.get("decisions_today") or {}
    first = next((x["symbol"] for x in d.get("chosen", []) if x.get("campaign") != "CTL"), None)
    call = {"BULLISH": "up", "BEARISH": "down", "NEUTRAL": "flat"}.get(str((rm.get("call") or {}).get("call") or "").upper(), "")
    q = ["What did you pick for the next session?", (f"Why do you think the next session goes {call}?" if call else "What is your call for the next session?"), "How are my holdings doing?",
         "What did you learn last night?", "What would you change in my holdings?", "How do you compare with other traders?", "Is everything running?", "Which way is the Nifty trending?", "What are the guardrails?"]
    if first:
        q.insert(1, f"Why {first}?")
    # request 95, fix 2 (Madhav, 24 Oct): one tap starts the full review; the biggest holding gets its own button
    ab = _book()
    top = ((ab.get("positions") or [{}])[0] or {}).get("symbol")
    q = ["Analyze my whole portfolio"] + ([f"Analyze {top}"] if top else []) + q
    return {"questions": q, "portfolio": ["Analyze my whole portfolio"] + ([f"Analyze {top}"] if top else []) + ["What would you change in my holdings?", "What did you move today?", "How is the options line doing?", "How do your picks compare with random picks?"],
            "market": ["Which way is the Nifty trending?", "How many stocks are healthy?", "What is the fear gauge saying?", "What were the biggest moves?"]}


def ask_threads() -> dict:
    return {"threads": _jsonl(DATA / "ask" / "threads.jsonl")[-20:]}


def ask_last() -> dict:
    t = _jsonl(DATA / "ask" / "threads.jsonl")
    last = t[-1] if t else None
    return {"last": last, "continue_minutes": 30}


def ask_flags(today: dt.date | None = None) -> dict:
    """'Flags for you' under an answer (Madhav, 24 Oct: "is there something that we have to flag from this process or from the way it is looking at
    the market?"): what looks off in the facts the answer stands on, one sentence each, decided by code from the read model, never by the model."""
    rm = readmodel()
    today = today or dt.date.today()
    out: list[str] = []
    through = str(rm.get("data_through") or "")[:10]
    try:
        d0 = dt.date.fromisoformat(through)
        gap = sum(1 for i in range(1, (today - d0).days) if (d0 + dt.timedelta(days=i)).weekday() < 5)
        if gap:
            out.append(f"The market data stops on {_day_words(through)}; {gap} weekday session{'s' if gap != 1 else ''} since then {'are' if gap != 1 else 'is'} not in it yet, so the answer may be out of date.")
    except ValueError:
        out.append("The daily summary has no market date, so the age of the data is unknown.")
    age = _health(rm)["checked_s_ago"]
    if age is not None and age > 36 * 3600:
        out.append(f"The daily summary was last rebuilt {age // 3600} hours ago; the evening jobs may not have run.")
    for x in (rm.get("missing") or [])[:3]:
        out.append(f"The daily summary has no '{x}' part, so anything that needs it is a data gap, not a no.")
    down = _health(rm)["down"]
    if down:
        out.append(f"Not running cleanly: {', '.join(down[:3])}{' and more' if len(down) > 3 else ''}.")
    m = rm.get("market") or {}
    trend, call = m.get("trend_state"), str((rm.get("call") or {}).get("call") or "").upper()
    if (trend == "above_both" and call == "BEARISH") or (trend == "below_both" and call == "BULLISH"):
        out.append(f"Mixed signals: the Nifty is {'in an uptrend' if trend == 'above_both' else 'in a downtrend'} but Ananta calls the next session {'down' if call == 'BEARISH' else 'up'}.")
    b = m.get("breadth_200d_liquid")
    if b is not None and ((trend == "above_both" and b < 0.4) or (trend == "below_both" and b > 0.6)):
        out.append(f"Mixed signals: the Nifty is {'in an uptrend' if trend == 'above_both' else 'in a downtrend'} but {100 * b:.0f}% of the 250 most-traded stocks are above their long-term average.")
    vix = m.get("vix_close")
    if isinstance(vix, (int, float)) and vix >= 20:
        out.append(f"An unusual day: the fear gauge (India VIX) is at {vix:.1f}, well above its calm range, so the usual patterns are less reliable.")
    c = rm.get("call") or {}
    if (c.get("scored") or 0) >= 20 and (c.get("hits") or 0) * 2 < c["scored"]:
        out.append(f"The daily call has been right {c.get('hits', 0)} of {c['scored']} times, below a coin flip; weigh it lightly.")
    return {"flags": out, "data_through": through or None}


def alerts() -> dict:
    rm = readmodel()
    out = []
    s = rm.get("sp1") or {}
    if s.get("status") == "lost":
        out.append({"id": "sp1-lost", "t": _ts(rm.get("built_at")), "kind": "system", "coin": "NIFTY", "value": None, "setup": "SP1", "note": "The morning sign-in to Zerodha was missing, so the options line could not trade.", "status": "open",
                    "fired_t": _ts(rm.get("built_at")), "message": "Options line missed its session", "what": "sign in to Zerodha before 09:10 Indian time (19:40 Toronto the evening before)"})
    for x in (rm.get("missing") or []):
        out.append({"id": f"missing-{x}", "t": _ts(rm.get("built_at")), "kind": "system", "coin": None, "value": None, "setup": x, "note": f"The daily summary has no '{x}' part today.", "status": "open",
                    "fired_t": _ts(rm.get("built_at")), "message": f"Part of the daily summary is missing: {x}", "what": "the evening jobs rebuild it; Ananta files it on the repair shop if it stays missing"})
    return {"alerts": out}


def needs() -> dict:
    return {"items": []}


def onboard_demo() -> dict:
    return {"demo": None}


def missed() -> dict:
    rm = readmodel()
    days = _rm_days()[-7:]
    moves, counts = [], Counter()
    for day in reversed(days):
        man = _json(DATA / "manifests" / f"missed_{day}.json", {}) or {}
        for mv in man.get("movers", []):
            fired = mv.get("fired_in_window") or []
            kind = "CAUGHT" if mv.get("caught") else ("SEEN" if fired else "MISSED")
            counts[kind] += 1
            moves.append({"day": day, "coin": mv.get("symbol"), "move_pct": round(100 * (mv.get("cc") or 0), 1), "move_atr": None, "label": mv.get("side"),
                          "why": (f"a {CAMPAIGN.get(fired[-1].get('campaign') or fired[-1].get('family'), 'rule').lower()} rule flagged it on {_day_words(fired[-1].get('date'))}" if fired else "no rule was watching it"),
                          "kind": kind, "at_zone": "", "regime": (rm.get("market") or {}).get("trend_state"), "low_t": _day_t(day), "tier": "liquid 250", "miss_class": None, "trade_ok": bool(fired), "class_why": ""})
    drafts = _jsonl(REG / "missed_drafts.jsonl")
    patterns = [{"pattern": d.get("pattern") or d.get("situation_key") or d.get("key", ""), "times": d.get("sessions") or d.get("count") or 0, "rows": 0, "avg_move_pct": None, "coins": ", ".join(d.get("symbols", [])[:5]) if isinstance(d.get("symbols"), list) else "",
                 "said": d.get("text") or d.get("draft") or "", "status": d.get("status", "DRAFT")} for d in drafts[-10:]]
    return {"days": len(days), "counts": dict(counts), "classes": {}, "class_meaning": {}, "moves": moves[:40], "patterns": patterns,
            "catches": {"all_tiers": {"CAUGHT_TRADE_OK": counts.get("CAUGHT", 0), "CAUGHT_MONITOR_ONLY": 0, "CAUGHT_UNSCORED": 0}, "meaning": "a mover a family fired on in the window", "money": ""},
            "tier30": {"counts": dict(counts)}, "universe": "the 250 most-traded stocks", "how_to_read": "Each day's biggest moves, checked against what Ananta's rules saw in the week before. The same kind of miss on 3 days in 7 becomes an idea for you to approve, never a rule by itself."}


def brain() -> dict:
    rm = readmodel()
    series = lab_value_series()
    jv = _jarvis(rm)
    return {"closed": jv["closed"], "open": [{"id": p["id"], "coin": p["coin"], "entry": p["entry"], "stop": None, "now": p["now"], "entry_t": _day_t(p["since"] or "2026-01-01", 9, 15), "pnl_pct": p["pnl_pct"], "stop_pct": None,
                                             "stop_raised": False, "trail_atr": None, "target": None, "days": p.get("bars_seen"), "confidence": None, "size_pct": round(100 * NOTIONAL / lab_start(), 2)} for p in open_positions()[:20]],
            "running": {"me": [{"t": t, "v": v} for t, v in series], "twins": []}, "avg_usd_per_100": jv["avg"], "random_twin_avg_usd": None, "vs_random_usd": None, "sized_net_usd": None,
            "events": jv["events"], "verdict": jv["verdict"], "calibration": [], "knowledge_credit": [], "passes_scored": 0, "passes_that_ran_5pct": [], "today": jv["today"]}


def reads() -> dict:
    rm = readmodel()
    d = rm.get("decisions_today") or {}
    rows = [{"coin": x.get("symbol"), "day": rm.get("data_through"), "close": x.get("close"), "reads": [{"read": x.get("campaign"), "variant": x.get("campaign"), "conditions": x.get("why"), "stop": None, "name": CAMPAIGN.get(x.get("campaign")),
             "like": "", "state": "fired", "met": 1, "of": 1, "history": "", "stop_pct": None}], "best": {"variant": x.get("campaign"), "name": CAMPAIGN.get(x.get("campaign")), "state": "fired", "met": 1, "of": 1, "like": "", "history": ""}} for x in d.get("chosen", [])]
    return {"day": rm.get("data_through"), "coins": rows, "fired": [], "close": [], "recent": [], "history": {k: CAMPAIGN_WHY[k] for k in CAMPAIGN}, "note": ""}


ROUTES = {"home": home, "books": books, "holdings": holdings, "coins": coins, "chain": chain, "exposure": exposure, "watches/mine": watches_mine, "evidence/live": evidence_live,
          "cockpit": cockpit, "evidence/collected": evidence_collected, "universe/ladder": universe_ladder, "agent/state": agent_state, "ask/suggestions": ask_suggestions,
          "teachers": teachers,
          "ask/threads": ask_threads, "ask/last": ask_last, "ask/flags": ask_flags, "alerts": alerts, "needs": needs, "onboard/demo": onboard_demo, "missed": missed, "brain": brain, "reads": reads}


# ---------------------------------------------------------------------------------------------------------------- Home: recent decisions, options (Madhav, 23 Oct)

def decisions_recent(n: int = 10) -> dict:
    """Ananta's recent decisions in plain words: a headline a person reads in two seconds, and the whole message behind it."""
    rm = readmodel()
    out = []
    st = _json(DATA / "paper" / "state.json", {}) or {}
    stops = {}
    for t in (st.get("trades") or {}).values():
        if t.get("book") == "exec" and t.get("bar_low_raw") and t.get("entry_raw"):
            stops[(t["signal_date"], t["campaign"], t["sid"])] = (t["bar_low_raw"], t["entry_raw"])
    for day in reversed(_decision_days()[-3:]):
        d = _json(DATA / "paper" / "decisions" / f"{day}.json", {}) or {}
        t = _ts(d.get("decided_at"))
        for x in d.get("signals", []):
            camp = x.get("campaign")
            if camp == "CTL":
                continue
            px = x.get("close")
            why = CAMPAIGN_WHY.get(camp, camp)
            bits = []
            if x.get("vol_ratio20") is not None:
                bits.append(f"volume {x['vol_ratio20']:.1f}x its 20-day")
            if x.get("dist_sma20") is not None:
                bits.append(f"{100 * x['dist_sma20']:+.1f}% from the 20-day average")
            if x.get("dist_sma200") is not None:
                bits.append(f"{100 * x['dist_sma200']:+.1f}% from the 200-day")
            stop = stops.get((day, camp, x.get("sid")))
            d20, d200 = 100 * (x.get("dist_sma20") or 0), 100 * (x.get("dist_sma200") or 0)
            if camp == "BRK":
                short = "broke out to a new one-month high on heavy volume"
                reason = f"it broke above its one-month high on {x['vol_ratio20']:.1f}x its usual volume" if x.get("vol_ratio20") else "it broke above its one-month high"
            elif camp == "PULL":
                short = "a pullback in an uptrend"
                reason = f"it has dipped {abs(d20):.0f}% to its one-month average while still {d200:+.0f}% above its long-term average; strong stocks that rest like this often go on"
            elif camp == "REV":
                short = "oversold, due a bounce"
                reason = f"it has been sold hard ({abs(d20):.0f}% under its one-month average, momentum under 30), and bounces from here have paid before"
            else:
                short, reason = why, why
            fill_day = rm.get("next_session") if day == rm.get("data_through") else "the next session"
            out.append({"id": f"{day}|{camp}|{x.get('sid')}", "t": t, "time": _when(d.get("decided_at")), "coin": x.get("symbol"), "action": "TAKE", "price": px,
                        "headline": f"Chose {x.get('symbol')} at ₹{px:,.0f} — {short}" if px else f"Chose {x.get('symbol')} — {short}",
                        "message": (f"What: a paper buy of about ₹50,000 in {x.get('symbol')} at the open on {_day_words(fill_day)}; the exit rule decides when it sells.\n"
                                    f"Why: {reason}" + (f"; it is number {x.get('liq_rank')} of the 250 most-traded stocks" if x.get("liq_rank") else "") + ".\n"
                                    + (f"Wrong if: it closes under ₹{stop[0]:,.0f}, the low of the day it was chosen — that is the first stop, {abs(100 * (stop[1] / stop[0] - 1)):.1f}% under the entry.\n" if stop else "Wrong if: it closes under the low of the day it was chosen (the first stop).\n")
                                    + f"Decided {_when(d.get('decided_at'))} on prices through {_day_words(day)}."),
                        "confidence": None, "link": "/jarvis"})
        cands = d.get("candidates") or {}
        passed = sum((v.get("candidates") or 0) - (v.get("chosen") or 0) for k, v in cands.items() if k != "CTL")
        if passed:
            out.append({"id": f"{day}|pass", "t": t - 1, "time": _when(d.get("decided_at")), "coin": None, "action": "PASS", "price": None,
                        "headline": f"Passed on {passed} other candidates — not among the 250 most-traded, or outranked",
                        "message": f"What: {passed} stocks met a rule but were not taken.\nWhy: Ananta takes at most {', '.join(f'{v} {CAMPAIGN.get(k, k).lower()}' for k, v in CAPS.items())} a session, from the 250 most-traded stocks, ranked by each rule's own score; the rest are written down, never traded.\nThey are followed anyway: every night it checks whether a pass was a miss.",
                        "confidence": None, "link": "/missed"})
    for c in reversed(_jsonl(DATA / "paper" / "calls.jsonl")[-6:]):
        if c.get("kind") == "call":
            out.append({"id": f"call|{c.get('data_through')}", "t": _ts(c.get("written_at")), "time": _when(c.get("written_at")), "coin": "NIFTY", "action": "CALL", "price": c.get("close"),
                        "headline": f"Called the next session {str(c.get('call', '')).lower()} with Nifty at {c.get('close'):,.0f}",
                        "message": f"What: Ananta's fixed daily call for the next session: {str(c.get('call', '')).lower()}.\nWhy: Nifty is {100 * (c.get('nifty_vs_sma50') or 0):+.1f}% from its ten-week average and moved {100 * (c.get('nifty_ret1') or 0):+.2f}% in the last session.\nIt is scored the next evening against a coin flip; so far {(rm.get('call') or {}).get('hits')} of {(rm.get('call') or {}).get('scored')} right.",
                        "confidence": None, "link": "/jarvis"})
    out.sort(key=lambda r: -r["t"])
    return {"decisions": out[:n], "page": "/jarvis", "data_through": rm.get("data_through")}


def options() -> dict:
    """India's options section on Home: the Rs 60,000 index line (SP1), today's plan, the session's decisions, the option book, the recorder's paper book."""
    rm = readmodel()
    s = rm.get("sp1") or {}
    book = (s.get("book") or {})
    plans = sorted((DATA / "paper" / "dayplans").glob("*.json")) if (DATA / "paper" / "dayplans").exists() else []
    plan = _json(plans[-1], {}) if plans else {}
    fc = plan.get("forecast") or {}
    sc = plan.get("scenarios_text") or {}
    rec = [r for r in _jsonl(DATA / "paper" / "options_trades.jsonl") if r.get("kind") != "skip"]
    rec_net = sum((r.get("net_inr") or 0) for r in rec)
    by_idx = book.get("by_index") or {}
    line_pnl = sum(float(v.get("option_1lot_rs_realistic_fill") or 0) for v in by_idx.values())
    sessions = book.get("sessions") or 0
    words = (f"{sessions} session{'s' if sessions != 1 else ''} traded on the options line so far." if sessions else "Nothing traded on options yet.") + (" The last session was missed because the morning sign-in to Zerodha failed." if s.get("status") == "lost" else "")
    return {"capital_inr": ACCOUNT_START, "value_inr": round(ACCOUNT_START + line_pnl, 2), "pnl_inr": round(line_pnl, 2), "sessions": sessions, "status": s.get("status"), "words": words,
            "plan": {"session": plan.get("session"), "bull": fc.get("bull"), "bear": fc.get("bear"), "neutral": fc.get("neutral"), "scenarios": sc, "limits": plan.get("limits") or [],
                     "vix": ((plan.get("overnight") or {}).get("INDIA VIX") or {}).get("close")},
            "decisions_today": s.get("decisions") or [], "errors": (s.get("errors") or [])[:1], "by_index": by_idx,
            "recorder": {"trades": len(rec), "net_inr": round(rec_net, 2), "last": [{"strategy": r.get("strategy"), "index": r.get("index"), "day": r.get("day"), "net_inr": round(r.get("net_inr") or 0), "exit": r.get("exit_reason")} for r in rec[-3:]],
                         "what": "the expiry-day paper book, on real option prices (about ₹50,000 scale)"},
            "suitability": "An option is bought only when the move it needs is bigger than what the option costs (its price, the spread and the daily decay).",
            "allocation": _allocation()}


def allocation_plan(full: bool = False) -> dict:
    """The allocator's latest plan (records repo, paper/allocation_view.json). Owner: everything. Others: mode, totals and the headline, never the holdings."""
    v = _json(DATA / "paper" / "allocation_view.json", {}) or {}
    a = _json(DATA / "paper" / "allocation.json", {}) or {}
    mode = {"fixed": "advisory", "ananta": "autonomous"}.get(a.get("mode"), a.get("mode") or "advisory")
    if not v:
        return {"mode": mode, "ready": False, "headline": "The allocator has not built a plan yet; it runs every few minutes and each evening.", "paper": True}
    out = {k: v.get(k) for k in ("mode", "day", "for_session", "built_at", "headline", "sleeves", "regime", "options", "moves", "moves_applied", "watch", "snapshot", "yardstick", "words", "paper")}
    out["mode"] = mode
    out["ready"] = True
    out["counts"] = {"holdings": len(v.get("holdings") or []), "suggested_changes": len(v.get("suggestions") or [])}
    ab = _json(DATA / "paper" / "account" / "view.json", {}) or {}
    # The allocator writes "Today it moved X" as soon as it decides; the paper copy fills the move only after the session's close (pending_days).
    # Until it fills, say what will happen, so the card never claims a move the account does not show yet (Madhav, 24 Oct).
    if ab.get("pending_days") and out.get("headline"):
        out["headline"] = re.sub(r"Today it moved (.+?)\.", r"It moves \1 at the session's close (not filled yet).", out["headline"])
        out["moves_applied"] = False
    # The guardrails, the market call and the buy rule live here since 24 Oct (Madhav: "No need of Ananta guard rails" on the account section).
    rm = readmodel()
    acct = _account_sp1(rm)
    out["guard"] = {"fired": not str(acct["dial"]["state"]).startswith("OPEN"), "short": "none fired" if str(acct["dial"]["state"]).startswith("OPEN") else "one has fired: no new buys",
                    "lines": acct["dial"]["why"], "next": acct["next"],
                    "buy_rule": "Ananta may buy a new stock for the account only after a rule has proved itself on paper (20 sessions, beating chance and the market) and you say yes. Until then it holds, trims and rebalances."}
    out["account_book"] = ({k: ab.get(k) for k in ("words", "value_inr", "stocks_inr", "cash_inr", "options_inr", "trades_count", "costs_inr", "pending_days", "admitted")}
                           | ({"positions": ab.get("positions") or [], "trades": ab.get("trades") or [], "differs_from_real": ab.get("differs_from_real") or []} if full else {})) if ab else None
    if full:
        out["holdings"] = v.get("holdings") or []
        out["suggestions"] = v.get("suggestions") or []
        out["set_at"] = a.get("set_at")
    else:
        out["moves"] = [{k: m.get(k) for k in ("kind", "from", "to", "inr")} for m in (v.get("moves") or [])]
        out["watch"] = []
    return out


def _allocation() -> dict:
    """The capital allocation, summary form for Home (no holdings): mode, sleeves, the headline, the counts. The full plan is /v3/allocation/plan, owner only."""
    p = allocation_plan(full=False)
    p.pop("snapshot", None)
    return p




# ---------------------------------------------------------------------------------------------------------------- the morning view (Madhav, 23 Oct 20:23)

def _mv_latest() -> dict:
    d = DATA / "paper" / "morningview"
    files = sorted(d.glob("????-??-??.json")) if d.exists() else []
    return (_json(files[-1], {}) or {}) if files else {}


def morning() -> dict:
    """The morning view for the next session: the facts' plain lines, Ananta's note (the model's words, checked by the reviewer), the reviewer's second
    opinion, the scorecard of yesterday's predictions, and the opening update once the first hour is in. Built before the open; everyone may read it."""
    f = _mv_latest()
    if not f:
        return {"ready": False, "headline": "The morning view is written before each Indian open (08:30 Indian time, 23:00 Toronto).", "session": None}
    L = f.get("lines") or {}
    sc = f.get("scorecard") or {}
    return {"ready": True, "session": f.get("session"), "session_words": _day_words(f.get("session")), "built_at": f.get("built_at"), "data_through": f.get("data_through"),
            "headline": L.get("headline"), "view": L.get("view") or [], "plan": L.get("plan") or [], "chances": L.get("chances") or [], "watch": L.get("watch") or [], "yesterday": L.get("yesterday") or [],
            "words": f.get("words"), "review": f.get("review"), "reviewer_scenarios": f.get("reviewer_scenarios"), "words_at": f.get("words_at"), "opening": f.get("opening"),
            "scenarios": (f.get("setup") or {}).get("scenarios"), "scenario_levels": (f.get("setup") or {}).get("scenario_levels"), "expiry": (f.get("setup") or {}).get("expiry"),
            "picks": (f.get("plan") or {}).get("picks") or [], "options_line": (f.get("plan") or {}).get("options_line"), "holdings_suggestions": (f.get("plan") or {}).get("holdings_suggestions") or [],
            "scorecard": {"forecasts": sc.get("forecasts"), "daily_call": sc.get("daily_call"), "options_sessions": sc.get("options_sessions"), "words": sc.get("words")},
            "lessons": f.get("lessons_for_writer") or [], "paper": True,
            "read": "Paper only, not advice. Every number comes from Ananta's own files; the odds are base rates beside their baseline until a rule proves itself."}


def morning_facts() -> dict:
    """The whole facts file (for the writer and the reviewer, owner side)."""
    return _mv_latest()


ROUTES.update({"decisions/recent": decisions_recent, "options": options, "allocation": _allocation, "reconstruction": reconstruction, "reconstruction/drafts": drafts, "morning": morning})
