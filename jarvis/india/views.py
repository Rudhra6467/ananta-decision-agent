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
CAMPAIGN = {"BRK": "Breakout", "PULL": "Pullback", "REV": "Reversal", "CTL": "Random control"}
CAMPAIGN_WHY = {"BRK": "20-session breakout on volume", "PULL": "pullback in an uptrend", "REV": "oversold reversal (RSI under 30, P01)",
                "CTL": "random control: no edge claimed, the yardstick"}


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
                     "stamp": {"who": "ananta", "label": f"Stock book · {CAMPAIGN.get(parts[1], parts[1])}", "source": "stockbook"}, "link": None})
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

def _health(rm: dict) -> dict:
    j = rm.get("jobs") or {}
    jobs = j.get("jobs") or []
    down = [x["label"] for x in jobs if not x.get("ok")]
    age = None
    try:
        age = int((dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(rm["built_at"])).total_seconds())
    except (KeyError, ValueError):
        pass
    return {"all_ok": not down and bool(jobs), "down": down, "ok": len(jobs) - len(down), "of": len(jobs), "checked_s_ago": age}


def _account(rm: dict) -> dict:
    """The India account = the Rs 60,000 SP1 index line (paper). Positions: none until the first session books one.
    dial = the guardrail state (OPEN when no rule has fired); brakes = the 5%-day and 22%-pause rules."""
    s = rm.get("sp1") or {}
    g = rm.get("guardrails") or {}
    book = (s.get("book") or {}).get("by_index") or {}
    pnl = 0.0
    for v in book.values():
        pnl += float(v.get("option_1lot_rs_realistic_fill") or 0)
    sessions = (s.get("book") or {}).get("sessions") or 0
    m = rm.get("market") or {}
    trend = {"above_both": "uptrend: Nifty above both averages", "below_both": "downtrend: Nifty below both averages", "mixed": "no clear trend"}.get(m.get("trend_state"), "trend unknown")
    why = [f"Nifty {m.get('nifty_close'):,.0f} on {m.get('data_through')}: {trend}" if m.get("nifty_close") else "no market section",
           f"Daily call for {rm.get('next_session')}: {(rm.get('call') or {}).get('call') or 'none'}",
           f"Guardrails: stop the day at {g.get('daily_loss_limit_pct')}% loss; pause new entries {g.get('pause_drawdown_pct')}% below the high-water mark"]
    return {"started": ACCOUNT_SINCE, "value_cad": round(ACCOUNT_START + pnl, 2), "start_cad": ACCOUNT_START, "return_pct": round(100 * pnl / ACCOUNT_START, 2),
            "cash_cad": round(ACCOUNT_START + pnl, 2), "positions": {}, "currency": "INR",
            "brakes": {"paused": False, "block_until": None, "fired": {"day_loss": 0, "pause_22pct": 0}, "streak": 0},
            "dial": {"state": "OPEN: no guardrail has fired" if s.get("status") != "lost" else "OPEN: no guardrail has fired (last session lost to the sign-in)", "why": why},
            "last_step": (rm.get("built_at") or "")[:16].replace("T", " "), "execution_check": {"fills": 0, "inside_bid_ask": 0},
            "next": f"the next decisions come at the open of {rm.get('next_session')} (09:15 to 10:15 IST)", "sessions": sessions,
            "note": {"day": rm.get("data_through"), "t": _ts(rm.get("built_at")), "note": " ".join((rm.get("brief") or [])[:2]), "cost_usd": 0},
            "lab": _lab_list(rm), "pushed_rule": "A playbook action enters the Rs 60,000 line only after validation on 2018-2023, the selection checks, and Madhav's sentence (G02)."}


def _lab_list(rm: dict) -> list[dict]:
    r = rm.get("research") or {}
    out = [{"id": "SP1", "name": "Index intraday playbook (Nifty, Bank Nifty)", "status": "PAPER", "verdict": "paper since 21 Oct; sessions so far: " + str(((rm.get("sp1") or {}).get("book") or {}).get("sessions") or 0)},
           {"id": "SP3", "name": "Positional playbook (stocks and index)", "status": "FROZEN", "verdict": "run pending"},
           {"id": "SZ2", "name": "Sizing v2 (option structures)", "status": "FROZEN", "verdict": "study pending"}]
    for camp, name in CAMPAIGN.items():
        out.append({"id": camp, "name": f"Stock book · {name}", "status": "PAPER", "verdict": "recording since 16 Oct"})
    g = r.get("gate") or {}
    out.append({"id": "G02", "name": "The gate", "status": g.get("state") or "BLOCKED", "verdict": g.get("waiting_on") or ""})
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
                        "title": f"{mv.get('symbol')} {pct:+.1f}% on {day[5:]}",
                        "body": ("A family fired in the window: " + ", ".join(f"{f.get('campaign', '')} {f.get('date', '')}" for f in fired[:2])) if fired else "No rule covered it",
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
            rows.append({"t": t, "kind": "watch", "coin": None, "title": f"Decided {sum(v for k, v in by.items() if k != 'CTL')} paper entries for the next session",
                         "body": ", ".join(f"{v} {CAMPAIGN.get(k, k)}" for k, v in sorted(by.items())) + " · entry at the next open", "time": _when(d.get("decided_at"))})
        for x in d.get("signals", [])[:6]:
            if x.get("campaign") == "CTL":
                continue
            rows.append({"t": t - 1, "kind": "buy", "coin": x.get("symbol"), "title": f"{x.get('symbol')} · {CAMPAIGN.get(x.get('campaign'), '')} entry at the next open",
                         "body": CAMPAIGN_WHY.get(x.get("campaign"), "") + (f" · close {x.get('close')}" if x.get("close") else ""), "time": _when(d.get("decided_at"))})
    for e in _jsonl(DATA / "paper" / "events.jsonl")[-400:]:
        if e.get("event") == "close" and str(e.get("id", "")).endswith("|" + REF_POLICY):
            p = e["id"].split("|")
            net = e.get("net_inr") or 0
            rows.append({"t": _ts(e.get("at")), "kind": "sell", "coin": _names().get(p[2], p[2]), "good": net > 0, "trade_id": None,
                         "title": f"{_names().get(p[2], p[2])} closed ({e.get('reason')}) {net:+,.0f} INR", "body": f"{CAMPAIGN.get(p[1], p[1])} · exit {e.get('exit_date')}", "time": _when(e.get("at"))})
    for c in _jsonl(DATA / "paper" / "calls.jsonl")[-6:]:
        if c.get("kind") == "call":
            rows.append({"t": _ts(c.get("written_at")), "kind": "watch", "coin": "NIFTY", "title": f"Daily call for the next session: {c.get('call')}",
                         "body": f"Nifty {c.get('close'):,.0f}, {100 * (c.get('nifty_vs_sma50') or 0):+.1f}% from its 50-day", "time": _when(c.get("written_at"))})
        elif c.get("kind") == "score":
            rows.append({"t": _ts(c.get("scored_at")), "kind": "watch", "coin": "NIFTY", "title": f"Yesterday's call scored: {'right' if c.get('score') == 1 else 'wrong'}",
                         "body": f"Nifty moved {100 * (c.get('move') or 0):+.2f}%", "time": _when(c.get("scored_at"))})
    for day in _rm_days()[-3:]:
        o = _json(DATA / "manifests" / f"others_{day}.json", {}) or {}
        h1 = (o.get("by_h") or {}).get("1") or {}
        cov = h1.get("coverage") or {}
        if cov:
            rows.append({"t": _ts(o.get("made_at")), "kind": "watch", "coin": None, "title": f"League {day[5:]}: held {cov.get('TAKEN', 0)} of the top 20 trips, no rule for {cov.get('NOT_COVERED', 0)}",
                         "body": f"picks at the {round(100 * (h1.get('ananta_pct_vs_random') or 0))}th percentile of random · market {100 * (h1.get('market_mean') or 0):+.2f}%", "time": _when(o.get("made_at"))})
    lost = (rm.get("sp1") or {})
    if lost.get("status") == "lost":
        rows.append({"t": _day_t(rm.get("data_through", "2026-01-01"), 9, 10), "kind": "alert", "coin": "NIFTY", "title": "SP1 index session lost", "body": lost.get("words", "")[:140], "time": ""})
    rows.sort(key=lambda r: -r["t"])
    return rows[:limit]


def day_summary(rm: dict) -> dict:
    a = _account(rm)
    marks = exec_marks()
    lab_val = lab_start() + sum((m.get("realised_inr") or 0) + (m.get("open_unrealised_inr") or 0) for m in marks.values())
    pos = open_positions()
    d = rm.get("decisions_today") or {}
    chosen = [x for x in d.get("chosen", []) if x.get("campaign") != "CTL"]
    sentence = (" ".join((rm.get("brief") or [])[:1]) or "No read model yet.") + " Paper only: no real money is at risk."
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
    return {"id": p["id"], "coin": p["coin"], "book": "stockbook", "stamp": {"who": "ananta", "label": f"Stock book · {CAMPAIGN.get(p['campaign'], p['campaign'])}", "source": "stockbook"},
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
    account = {"book": {"name": "The Rs 60,000 India book (SP1 index line)", "value": a["value_cad"], "start": a["start_cad"], "currency": "INR", "execution_check": a["execution_check"],
                        "started": a["started"], "dial_open": True, "brakes": a["brakes"], "status": "ACTIVE",
                        "why": "The account: the index playbook's Rs 60,000 line on paper; sized by SZ2 once its study lands; guardrails 5% a day and a 22% pause."},
               "trades": [], "closed": [], "currency": "INR", "summary": acct_summary}
    lab_trades = [_trade_row(p) for p in pos]
    by_camp = []
    for camp, name in CAMPAIGN.items():
        m = marks.get(camp) or {}
        by_camp.append({"id": camp, "name": f"Stock book · {name}", "kind": "paper", "t": _ts(m.get("at")), "start": CAPS[camp] * NOTIONAL,
                        "value": round(CAPS[camp] * NOTIONAL + (m.get("realised_inr") or 0) + (m.get("open_unrealised_inr") or 0), 2), "status": "PAPER",
                        "verdict": f"{m.get('open') or 0} open · {m.get('closed') or 0} closed · win rate {m.get('win_rate') if m.get('win_rate') is not None else '–'}",
                        "events": m.get("closed") or 0, "result": None})
    return {"summary": {"value": round(lab_val + a["value_cad"], 2), "start": lab_start() + a["start_cad"], "open_pnl": round(open_pnl, 2), "closed_pnl_recent": round(closed_pnl, 2),
                        "open_count": len(pos), "retired_pnl": 0.0, "retired_count": 0, "evidence_open": len(pos)},
            "account": account, "lab": {"trades": lab_trades, "closed": closed, "books": by_camp, "decision": " ".join((rm.get("brief") or [])[:1])},
            "retired": [], "evidence_open_by": dict(Counter(p["campaign"] for p in pos)), "trades": lab_trades, "closed": closed, "books": by_camp,
            "stamps": {"stockbook": "the stock research book, Rs 50,000 a trade, every registered exit tracked"}, "random_open": sum(1 for p in pos if p["campaign"] == "CTL"),
            "initials": {}, "read": "Paper only. The Rs 60,000 line is the account; the stock book is the lab at research scale."}


def holdings() -> dict:
    rm = readmodel()
    a = _account(rm)
    d = rm.get("decisions_today") or {}
    not_held = [{"coin": x.get("symbol"), "rating": CAMPAIGN.get(x.get("campaign"), ""), "why": x.get("why", "")} for x in d.get("chosen", []) if x.get("campaign") != "CTL"][:10]
    return {"mode": "PAPER", "value": a["value_cad"], "start": a["start_cad"], "return_pct": a["return_pct"], "cash": a["cash_cad"], "invested": 0, "costs_paid": 0.0,
            "holdings": [], "not_held": not_held, "pending": [], "decided": rm.get("data_through"), "btc_gate": (rm.get("market") or {}).get("trend_state") == "above_both",
            "shadow": {"value": a["value_cad"], "return_pct": a["return_pct"]}, "rule_plain": "The Rs 60,000 line trades the index playbook on paper; stocks are the research book, not holdings."}


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
                    "daily": "above 200-day" if (r.get("dist_sma200") or 0) > 0 else "below 200-day",
                    "closest": {"setup": chosen.get(s, ""), "name": CAMPAIGN.get(chosen.get(s, ""), "no family fired"), "met": 1 if s in chosen else 0, "of": 1, "missing": "" if s in chosen else "not chosen this session"},
                    "liq_rank": r.get("liq_rank"), "vol_ratio20": r.get("vol_ratio20"), "rsi14": r.get("rsi14")})
    return {"coins": out, "data_through": rm.get("data_through"), "universe": (d.get("universe") or {})}


def chain() -> dict:
    rm = readmodel()
    gates = [{"gate": "LIQUIDITY", "question": "Is it in the liquid 250?"}, {"gate": "TREND", "question": "Where is the Nifty against its averages?"},
             {"gate": "FAMILY", "question": "Did a registered family fire (breakout, pullback, reversal)?"}, {"gate": "COSTS", "question": "Does it clear the Rs 50,000 cost model?"},
             {"gate": "GUARDRAIL", "question": "Has the 5% day or the 22% pause fired?"}]
    d = decision()
    rows = []
    for x in d.get("signals", [])[:12]:
        rows.append({"coin": x.get("symbol"), "price": x.get("close"), "verdict": "TAKEN" if x.get("campaign") != "CTL" else "CONTROL", "stops_at": "",
                     "summary": CAMPAIGN_WHY.get(x.get("campaign"), ""), "gates": [{**g, "status": "PASS", "why": "", "source": "decision file", "values": {}, "reached": True} for g in gates],
                     "observations": {"relative_strength": x.get("dist_sma200"), "volume": x.get("vol_ratio20"), "setup_family": CAMPAIGN.get(x.get("campaign")), "daily_atr_pct": round(100 * (x.get("atr14") or 0) / (x.get("close") or 1), 2) if x.get("close") else None, "your_setups": "", "zone": ""}})
    return {"framework": "India stock book v1.2: liquidity, Nifty trend, a registered family, the cost model, the guardrails", "gates": gates,
            "stops": {"GUARDRAIL": 0}, "coins": rows, "note": f"From the decision file for {rm.get('data_through')}; every registered exit is tracked on each entry."}


def exposure() -> dict:
    rm = readmodel()
    m = rm.get("market") or {}
    a = _account(rm)
    marks = exec_marks()
    books_ = []
    for camp, name in CAMPAIGN.items():
        mk = marks.get(camp) or {}
        start = CAPS[camp] * NOTIONAL
        books_.append({"book": f"Stock book · {name}", "role": "control" if camp == "CTL" else "family", "return_pct": round(100 * ((mk.get("realised_inr") or 0) + (mk.get("open_unrealised_inr") or 0)) / start, 2),
                       "worst_fall_pct": None, "trades": (mk.get("open") or 0) + (mk.get("closed") or 0), "days": len(_rm_days())})
    v50 = m.get("nifty_vs_sma50")
    trend_words = {"above_both": "uptrend: breakouts are in season", "below_both": "downtrend: reversals are watched, breakouts are rare", "mixed": "no clear trend"}.get(m.get("trend_state"), "trend unknown")
    return {"dial": {"dial": 1.0,                                                         # OPEN unless a guardrail has fired (the 5% day, the 22% pause): paper records, nothing has fired
                     "dial_words": f"No guardrail has fired. Nifty {trend_words}.", "why": a["dial"]["why"], "challenger_weight": None, "benchmark_in": True, "btc_vol_30d_pct": None,
                     "as_of_day": m.get("data_through"), "rule": "Stop the day at a 5% loss; pause new entries 22% below the high-water mark. The Nifty trend is the situation, not a switch."},
            "books": {"since": "2026-10-16", "books": books_, "how_to_read": "Each family is a paper book at research scale (Rs 50,000 a trade); the random control is the yardstick."},
            "measured_edges": [], "account": {"account_usd": a["value_cad"], "taken": 0, "closed": 0, "open": 0, "skipped": {"dial_closed": 0, "full": 0, "same_coin": 0, "same_day": 0, "risk_cap": 0},
                                              "net_usd": 0.0, "return_pct": a["return_pct"], "avg_R": None, "total_R": 0.0, "hurdle_pct": None, "beats_hurdle": False, "positive_expectancy": False,
                                              "rules": "the SP1 playbook; sizing v2 pending", "how_to_read": "0 sessions recorded until the sign-in holds"},
            "fidelity": {"cells": [], "min_trades": 20, "rule": "paper fills checked against live quotes once SP1 sessions record"}, "nifty_vs_sma50_pct": round(100 * v50, 2) if v50 is not None else None}


def watches_mine() -> dict:
    rm = readmodel()
    d = rm.get("decisions_today") or {}
    w = []
    by = {}
    for x in d.get("chosen", []):
        by.setdefault(x.get("campaign"), []).append(x.get("symbol"))
    for camp, syms in by.items():
        w.append({"id": f"family:{camp}", "t": _ts(d.get("decided_at")), "coins": syms, "group": None, "kind": camp, "kind_name": CAMPAIGN.get(camp, camp), "mode": "tell", "mode_words": "tells you (paper entry at the open)",
                  "state": "fired", "detail": {"coins": syms, "best": syms[0] if syms else None, "why": CAMPAIGN_WHY.get(camp, "")}, "checked_t": _ts(rm.get("built_at")), "fired_t": _ts(d.get("decided_at")), "by": "ananta"})
    return {"watches": w, "kinds": [{"kind": k, "name": v, "plain": CAMPAIGN_WHY.get(k, ""), "evidence": "stock book since 16 Oct", "default": k != "CTL"} for k, v in CAMPAIGN.items()],
            "modes": {"tell": "tells you", "ask": "asks first", "auto": "takes the paper trade"}, "groups": {"my_coins": "chosen today", "all": "the liquid 250", "large": "Nifty 50"}}


def evidence_live() -> dict:
    rm = readmodel()
    r = rm.get("research") or {}
    lg = (rm.get("learning") or {}).get("league") or {}
    h1 = lg.get("h1") or {}
    days = len(_rm_days())
    marks = exec_marks()
    items = [{"key": c, "label": f"Stock book · {CAMPAIGN[c]}", "closed": m.get("closed") or 0, "wins": None, "net_usd": round(m.get("realised_inr") or 0, 2),
              "avg_usd": round((m.get("realised_inr") or 0) / max(1, m.get("closed") or 0), 2), "events": days, "open": m.get("open") or 0, "events_own": days} for c, m in marks.items()]
    return {"as_of": rm.get("data_through"), "days": days, "rules": "India paper v1.2 · others-v1 · readmodel-v0", "since": "2026-10-16",
            "health": {**_health(rm), "summary": "", "outages_3d": []},
            "clocks": [{"cadence": "daily", "name": "paper", "scope": "stock book", "n": days, "unit": "sessions", "detail": "decisions at 22:30 Toronto"},
                       {"cadence": "daily", "name": "league", "scope": "reference traders", "n": days, "unit": "sessions", "detail": "H1/H5/H20 trips"},
                       {"cadence": "daily", "name": "sp1", "scope": "index line", "n": ((rm.get("sp1") or {}).get("book") or {}).get("sessions") or 0, "unit": "sessions", "detail": "needs the morning sign-in"},
                       {"cadence": "nightly", "name": "gate", "scope": "G02", "n": 0, "unit": "of 30", "detail": str(r.get("gate_counters"))}],
            "limits": [], "results": {"items": items, "random_avg_usd": round(NOTIONAL * (h1.get("market_mean") or 0), 2) if h1 else None, "events": days, "goal_events": 60,
                                      "books": [], "by_setup": [], "verdict": "too early", "read": "Sixty sessions on paper inside the expected range per book, then the gate."},
            "rebuild": _rebuild(rm, h1, days),
            "misses": [], "board": [], "in_use": {"verdicts": r.get("verdicts"), "studies": r.get("studies")}}


# ---------------------------------------------------------------------------------------------------------------- More: cockpit, evidence/collected, ladder

def cockpit() -> dict:
    rm = readmodel()
    j = rm.get("jobs") or {}
    systems = [{"label": f"India · {x['label']}", "ok": bool(x.get("ok"))} for x in j.get("jobs", [])]
    actions = []
    for day in reversed(_decision_days()[-5:]):
        d = _json(DATA / "paper" / "decisions" / f"{day}.json", {}) or {}
        actions.append({"time": _when(d.get("decided_at")), "who": "ananta", "action": "paper decisions", "detail": f"{len(d.get('signals', []))} signals from {len(d.get('journal', []))} candidates", "result": "recorded"})
    return {"switches": [{"key": "india_paper", "label": "India paper books", "on": True, "help": "The stock book and the SP1 line record every session on paper. Read-only here.", "confirm": False},
                         {"key": "india_orders", "label": "Order placing", "on": False, "help": "Forbidden until the G02 gate and Madhav's sentence; leakcheck enforces it.", "confirm": True}],
            "systems": systems, "circuit_breakers": {"india_book": {"status": "ARMED", "consecutive_losses": 0, "drawdown_usd": 0.0, "drawdown_pct_of_start": 0.0, "checked_at": rm.get("built_at"),
                                                                    "reason": "5% day / 22% pause: recorded, enforced at live", "tripped_at": None, "evidence": []}},
            "recent_actions": actions, "signin": j.get("signin")}


def _rx_cards() -> list[Path]:
    d = DATA / "paper" / "reconstruction"
    return sorted(d.glob("????-??-??.json")) if d.exists() else []


def _rebuild(rm: dict, h1: dict, days: int) -> dict:
    """The Reconstruction screen's block, from RX-IN (india/reconstruct.py): nightly cards, the league, the staircase as the chain."""
    rx = rm.get("reconstruction") or {}
    cards = _rx_cards()
    st = rx.get("staircase") or {}
    chain = []
    steps = ["NOTED", "DRAFT", "REGISTERED", "TESTED", "SHADOW", "ADMITTED", "LIVE_ELIGIBLE"]
    for k, r in (st.get("rules") or {}).items():
        chain.append({"id": k, "step": r.get("step"), "steps": steps, "words": f"{k}: {r.get('step')} · {r.get('shadow_sessions', 0)}/{r.get('shadow_bar', 20)} shadow sessions · beats RANDOM and MARKET on {r.get('beats', 0)}/{r.get('beats_bar', 10)} independent sessions"})
    f = rx.get("findings") or []
    return {"books": [{"book": "session card", "runs": len(cards), "mismatches": 0, "what": "A market · B people · C Ananta did · D did not do · E trade reviews · F findings · G forwarding"}],
            "nightly": {"runs": len(cards), "first": cards[0].stem if cards else "", "mismatches": 0, "every": "every night at 22:30 Toronto, after the paper engine, the missed movers and the league"},
            "asked": {"runs": 0, "mismatches": 0, "last": "", "how": "ask Ananta: what did you learn last night?"}, "total": len(cards), "mismatches": 0,
            "last": {"when": rx.get("built_at") or "", "match": True, "checked": len(f), "rebuilt": len(cards), "headline": rx.get("headline") or "no card yet"},
            "how": "every number names its file; a missing source says missing; findings fire only on fixed counts (3 of 7 sessions, 5 tags in 20, 20 shadow sessions)",
            "if_mismatch": "a SAFE finding goes to the repair board by itself; a DECISION finding waits in the queue for Madhav's read",
            "others": {"id": "league", "title": "Reference traders against Ananta", "date": rm.get("data_through"), "runs": str(days), "excluded_bots": 0, "accounts_trading_our_coins": 0,
                       "round_trips": 20, "long": 20, "short": 0, "period": "H1", "our_setups_silent_before_their_buys_pct": None, "their_timing_edge": "", "skill_persisted": False,
                       "what_we_did": rx.get("league_words") or f"held {(h1.get('coverage') or {}).get('TAKEN', 0)} of the top 20 trips; picks at the {round(100 * (h1.get('ananta_pct_vs_random') or 0))}th percentile of random"},
            "findings": [{"type": x.get("type"), "lane": x.get("lane"), "state": x.get("state"), "words": x.get("words")} for x in f],
            "reviews": rx.get("reviews") or {}, "staircase_words": st.get("words") or "", "chain": chain}


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
            "findings": c.get("findings") or [], "forwarding": c.get("forwarding") or {}, "staircase": rx.get("staircase") or {}, "cards": len(_rx_cards())}


def _queue_rows() -> list[dict]:
    q = REG / "reconstruction_queue.jsonl"
    rows = _jsonl(q)
    filed = {f.get("key"): f for f in _jsonl(DATA / "paper" / "reconstruction" / "forwarded.jsonl")}
    for r in rows:
        if r.get("key") in filed:
            r["state"] = "filed" if r.get("state") == "to_file" else r.get("state")
            r["request"] = filed[r["key"]].get("num")
    return rows


def evidence_collected() -> dict:
    rm = readmodel()
    marks = exec_marks()
    r = rm.get("research") or {}
    v = r.get("verdicts") or {}
    collected = [{"setup": c, "name": f"Stock book · {CAMPAIGN[c]}", "seen": None, "orders": (m.get("open") or 0) + (m.get("closed") or 0), "shadow_orders": 0, "bought": (m.get("open") or 0) + (m.get("closed") or 0),
                  "closed": m.get("closed") or 0, "net_usd": round(m.get("realised_inr") or 0, 2)} for c, m in marks.items()]
    tracker = [{"key": "sessions", "label": "Paper sessions recorded", "value": len(_rm_days()), "explain": "stock book decisions since 16 Oct"},
               {"key": "validated", "label": "Registry verdicts VALIDATED", "value": v.get("VALIDATED", 0), "explain": "of " + str(sum(v.values())) + " variants scored"},
               {"key": "ready", "label": "Studies ready to run", "value": (r.get("studies") or {}).get("ready", 0), "explain": "with every data item in hand"},
               {"key": "gate", "label": "Gate G02", "value": 0, "explain": str(r.get("gate_counters"))}]
    forwarded = []
    for k, p in (r.get("exit_book") or {}).get("chosen", {}).items():
        forwarded.append({"id": f"G01:{k}", "title": f"Exit book · {k}", "date": "2026-10-22", "verdict": "HELD" if p else "NOT_HELD", "why": p or "no dev leader held up", "question": "which exit held up out of sample?", "result": p or "none", "changed": ""})
    rx = rm.get("reconstruction") or {}
    st = rx.get("staircase") or {}
    rows = _queue_rows()
    for q in rows:
        if q.get("lane") == "SAFE":
            forwarded.append({"id": q.get("key"), "title": f"{q.get('type')} · {q.get('day')}", "date": q.get("day"), "verdict": q.get("state", "").upper(),
                              "why": (q.get("words") or "")[:220], "question": "filed on the repair board" + (f" as request #{q['request']}" if q.get("request") else " (filing tonight)"), "result": q.get("state"), "changed": ""})
    running = [{"id": k, "status": r.get("step"), "title": k, "waiting_for": f"{r.get('shadow_sessions', 0)}/{r.get('shadow_bar', 20)} shadow sessions; beats RANDOM and MARKET {r.get('beats', 0)}/{r.get('beats_bar', 10)}",
                "why": "the evidence staircase", "metric": "shadow sessions", "goal": r.get("shadow_bar", 20)} for k, r in (st.get("rules") or {}).items()]
    waiting = [{"id": q.get("key"), "status": q.get("state"), "title": f"{q.get('type')} ({q.get('day')})", "waiting_for": "Madhav's weekly read" if q.get("lane") == "DECISION" else "the repair board",
                "why": (q.get("words") or "")[:160], "metric": q.get("lane"), "goal": None} for q in rows if q.get("state") in ("DRAFT", "NOTE", "to_file", "filed")]
    done = [{"id": k, "status": "ADMITTED", "title": k, "waiting_for": "", "why": "Madhav's recorded yes", "metric": "", "goal": None} for k in (st.get("admitted") or [])]
    tracker.append({"key": "cards", "label": "Reconstruction cards", "value": len(_rx_cards()), "explain": "one per session since 22 Oct"})
    tracker.append({"key": "findings", "label": "Findings in the queue", "value": len([q for q in rows if q.get("state") in ("DRAFT", "NOTE", "to_file", "filed")]), "explain": "SAFE to the repair board, DECISION for Madhav"})
    shop = {"running": running, "waiting": waiting, "done": done, "summary": st.get("words") or "no staircase yet"}
    return {"collected": collected, "tracker": tracker, "forwarded": forwarded, "shop": shop}


def universe_ladder() -> dict:
    rm = readmodel()
    rows = [{"watch": f"Stock book · {n}", "rule": CAMPAIGN_WHY.get(c, ""), "tier": "research", "step": "PAPER", "meaning": "recording every session at research scale", "next_allowed": False,
             "why": "60 sessions and the gate first", "signed_by": None} for c, n in CAMPAIGN.items()]
    rows.append({"watch": "SP1 index playbook", "rule": "fade the session after 09:30 with the opening-range stop; hold longs overnight", "tier": "account", "step": "PAPER",
                 "meaning": "the Rs 60,000 line", "next_allowed": False, "why": "sessions so far: " + str(((rm.get("sp1") or {}).get("book") or {}).get("sessions") or 0), "signed_by": None})
    return {"rows": rows, "steps": ["RESEARCH", "PAPER", "GATE", "LIVE"], "rule": "Research → paper (60 sessions) → the G02 gate → Madhav's sentence → live."}


# ---------------------------------------------------------------------------------------------------------------- Ask-adjacent, alerts, needs, misc

def agent_state() -> dict:
    rm = readmodel()
    s = rm.get("sp1") or {}
    lines = [{"tone": "info", "text": x} for x in (rm.get("brief") or [])[:3]]
    if s.get("status") == "lost":
        lines.append({"tone": "warn", "text": "The index line's last session was lost to the Kite sign-in."})
    return {"lines": lines, "watches": watches_mine()["watches"], "positions": [{"coin": p["coin"], "pnl_pct": p["pnl_pct"], "since": p["since"]} for p in open_positions()[:20]],
            "needs_you": 0, "last_check": {"accounts": 1, "fired": 0, "warned": 1 if s.get("status") == "lost" else 0, "ms": 0}}


def ask_suggestions() -> dict:
    rm = readmodel()
    d = rm.get("decisions_today") or {}
    first = next((x["symbol"] for x in d.get("chosen", []) if x.get("campaign") != "CTL"), None)
    q = ["What did you decide for the next session?", "Why is the daily call " + str((rm.get("call") or {}).get("call") or "what it is") + "?", "How is the stock paper book doing?",
         "What did you learn last night?", "What is on the evidence staircase?", "What held up in the exit book?", "Where do we stand against the reference traders?", "Is every job running?", "What is the Nifty trend?", "What are the guardrails?"]
    if first:
        q.insert(1, f"Why {first}?")
    return {"questions": q, "portfolio": ["How many positions are open?", "What was closed recently?", "What is the Rs 60,000 line doing?", "How did the random control do?"],
            "market": ["What is the Nifty trend?", "How wide is breadth?", "Where is the VIX?", "What were the biggest moves?"]}


def ask_threads() -> dict:
    return {"threads": _jsonl(DATA / "ask" / "threads.jsonl")[-20:]}


def ask_last() -> dict:
    t = _jsonl(DATA / "ask" / "threads.jsonl")
    last = t[-1] if t else None
    return {"last": last, "continue_minutes": 30}


def alerts() -> dict:
    rm = readmodel()
    out = []
    s = rm.get("sp1") or {}
    if s.get("status") == "lost":
        out.append({"id": "sp1-lost", "t": _ts(rm.get("built_at")), "kind": "system", "coin": "NIFTY", "value": None, "setup": "SP1", "note": s.get("words", "")[:120], "status": "open",
                    "fired_t": _ts(rm.get("built_at")), "message": "Index session lost: no Kite sign-in", "what": "sign in before 09:10 IST"})
    for x in (rm.get("missing") or []):
        out.append({"id": f"missing-{x}", "t": _ts(rm.get("built_at")), "kind": "system", "coin": None, "value": None, "setup": x, "note": "section missing from the read model", "status": "open",
                    "fired_t": _ts(rm.get("built_at")), "message": f"Read model: {x} missing", "what": "check the evening jobs"})
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
            moves.append({"day": day, "coin": mv.get("symbol"), "move_pct": round(100 * (mv.get("cc") or 0), 1), "move_atr": None, "label": mv.get("side"), "why": ", ".join(f"{f.get('campaign')} {f.get('date')}" for f in fired[:2]) or "no rule covered it",
                          "kind": kind, "at_zone": "", "regime": (rm.get("market") or {}).get("trend_state"), "low_t": _day_t(day), "tier": "liquid 250", "miss_class": None, "trade_ok": bool(fired), "class_why": ""})
    drafts = _jsonl(REG / "missed_drafts.jsonl")
    patterns = [{"pattern": d.get("pattern") or d.get("situation_key") or d.get("key", ""), "times": d.get("sessions") or d.get("count") or 0, "rows": 0, "avg_move_pct": None, "coins": ", ".join(d.get("symbols", [])[:5]) if isinstance(d.get("symbols"), list) else "",
                 "said": d.get("text") or d.get("draft") or "", "status": d.get("status", "DRAFT")} for d in drafts[-10:]]
    return {"days": len(days), "counts": dict(counts), "classes": {}, "class_meaning": {}, "moves": moves[:40], "patterns": patterns,
            "catches": {"all_tiers": {"CAUGHT_TRADE_OK": counts.get("CAUGHT", 0), "CAUGHT_MONITOR_ONLY": 0, "CAUGHT_UNSCORED": 0}, "meaning": "a mover a family fired on in the window", "money": ""},
            "tier30": {"counts": dict(counts)}, "universe": "the liquid 250", "how_to_read": "Every session's top movers against what fired in the 7-session window; 3 sessions in 7 files a DRAFT, never a rule."}


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
    return {"day": rm.get("data_through"), "coins": rows, "fired": [], "close": [], "recent": [], "history": {k: CAMPAIGN_WHY[k] for k in CAMPAIGN}, "note": d.get("rules", "")}


ROUTES = {"home": home, "books": books, "holdings": holdings, "coins": coins, "chain": chain, "exposure": exposure, "watches/mine": watches_mine, "evidence/live": evidence_live,
          "cockpit": cockpit, "evidence/collected": evidence_collected, "universe/ladder": universe_ladder, "agent/state": agent_state, "ask/suggestions": ask_suggestions,
          "ask/threads": ask_threads, "ask/last": ask_last, "alerts": alerts, "needs": needs, "onboard/demo": onboard_demo, "missed": missed, "brain": brain, "reads": reads}


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
            if camp == "BRK":
                reason = f"it broke its 20-session high on {bits[0]}" if bits else why
            elif camp == "PULL":
                reason = f"it pulled back {100 * (x.get('dist_sma20') or 0):+.1f}% to its 20-day average inside an uptrend ({100 * (x.get('dist_sma200') or 0):+.1f}% above the 200-day)"
            elif camp == "REV":
                reason = f"it is oversold (RSI under 30), {100 * (x.get('dist_sma20') or 0):+.1f}% below its 20-day average, and reversals have paid here before"
            else:
                reason = why
            out.append({"id": f"{day}|{camp}|{x.get('sid')}", "t": t, "time": _when(d.get("decided_at")), "coin": x.get("symbol"), "action": "TAKE", "price": px,
                        "headline": f"Chose {x.get('symbol')} at ₹{px:,.2f} ({CAMPAIGN.get(camp, camp).lower()}) because {reason}" if px else f"Chose {x.get('symbol')}: {why}",
                        "message": (f"What: a paper entry in {x.get('symbol')} at the next session's open ({rm.get('next_session') if day == rm.get('data_through') else 'the session after ' + day}), Rs 50,000 notional, every registered exit tracked.\n"
                                    f"Why: {why}; {', '.join(bits)}; liquidity rank {x.get('liq_rank')}.\n"
                                    + (f"Wrong if: the signal bar's low (₹{stop[0]:,.2f}) gives way; that is the first stop, {100 * (stop[1] / stop[0] - 1):.1f}% below the entry.\n" if stop else "Wrong if: the signal bar's low gives way (the first stop).\n")
                                    + f"Decided {_when(d.get('decided_at'))} by rules {d.get('rules')} on data through {day}."),
                        "confidence": None, "link": "/jarvis"})
        cands = d.get("candidates") or {}
        passed = sum((v.get("candidates") or 0) - (v.get("chosen") or 0) for k, v in cands.items() if k != "CTL")
        if passed:
            out.append({"id": f"{day}|pass", "t": t - 1, "time": _when(d.get("decided_at")), "coin": None, "action": "PASS", "price": None,
                        "headline": f"Passed on {passed} other candidates on {day[5:]}: outside the liquid 250 or beaten on the family's own ranking",
                        "message": f"What: {passed} candidates fired a family rule but were not taken.\nWhy: the book takes at most {', '.join(f'{v} {k}' for k, v in CAPS.items())} a session from the liquid 250, ranked by each family's own score; the rest are recorded in the journal, never traded.\nThey are scored anyway: the missed-movers review checks every session whether a pass was a miss.",
                        "confidence": None, "link": "/missed"})
    for c in reversed(_jsonl(DATA / "paper" / "calls.jsonl")[-6:]):
        if c.get("kind") == "call":
            out.append({"id": f"call|{c.get('data_through')}", "t": _ts(c.get("written_at")), "time": _when(c.get("written_at")), "coin": "NIFTY", "action": "CALL", "price": c.get("close"),
                        "headline": f"Called the next session {c.get('call')} with Nifty at {c.get('close'):,.0f}",
                        "message": f"What: the mechanical daily call ({c.get('rule')}) for the session after {c.get('data_through')}: {c.get('call')}.\nWhy: Nifty {100 * (c.get('nifty_vs_sma50') or 0):+.1f}% from its 50-day average, last session {100 * (c.get('nifty_ret1') or 0):+.2f}%.\nScored the next evening against a coin flip; so far {(rm.get('call') or {}).get('hits')} of {(rm.get('call') or {}).get('scored')} right.",
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
    words = (f"{sessions} sessions recorded on the index line" if sessions else "0 sessions recorded on the index line") + (f"; the last session was lost: {s.get('words', '')[:90]}" if s.get("status") == "lost" else "")
    return {"capital_inr": ACCOUNT_START, "value_inr": round(ACCOUNT_START + line_pnl, 2), "pnl_inr": round(line_pnl, 2), "sessions": sessions, "status": s.get("status"), "words": words,
            "plan": {"session": plan.get("session"), "bull": fc.get("bull"), "bear": fc.get("bear"), "neutral": fc.get("neutral"), "scenarios": sc, "limits": plan.get("limits") or [],
                     "vix": ((plan.get("overnight") or {}).get("INDIA VIX") or {}).get("close")},
            "decisions_today": s.get("decisions") or [], "errors": (s.get("errors") or [])[:1], "by_index": by_idx,
            "recorder": {"trades": len(rec), "net_inr": round(rec_net, 2), "last": [{"strategy": r.get("strategy"), "index": r.get("index"), "day": r.get("day"), "net_inr": round(r.get("net_inr") or 0), "exit": r.get("exit_reason")} for r in rec[-3:]],
                         "what": "O-03/O-04 expiry-day paper book on the recorder's real option minutes (Rs 50,000 scale)"},
            "suitability": "an option entry needs the required move to clear the premium, the spread and theta before it is taken (the SZ2 check)",
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


ROUTES.update({"decisions/recent": decisions_recent, "options": options, "allocation": _allocation, "reconstruction": reconstruction})
