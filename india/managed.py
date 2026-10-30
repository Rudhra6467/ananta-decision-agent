"""The managed paper book (Madhav, 30 Oct 2026: "Your duty is to do paper ... pick the replacements and you have to trade the replacements in
paper so you know how your reasoning was"; "yes, sounds reasonable. lets do it" to the plan in
claude/review-2026-10-30-outsider-conversation-and-managed-book-plan.md).

A fourth paper book that starts from the account twin's holdings and ACTS on the evening cut list: each cut frees rupees, and those rupees buy a
replacement chosen by the rules that proved themselves (not losing), on paper, tracked against the twin, the frozen portfolio and the Nifty 500.

  python -m india.managed run [day]      evening: fill the plan written for the session that just closed, mark, apply exits, write tomorrow's plan
  python -m india.managed score          +5 / +20 sessions after each plan: was the cut right, did the replacement rise (the replacement ledger)
  python -m india.managed show

The daily cycle (all paper; nothing is placed, india/leakcheck.py holds)
  evening (Toronto; before the next Indian open)
    1. fill: the plan written yesterday evening for today's session fills at today's OFFICIAL OPEN from the exchange's own bhavcopy, plus 0.1%
       slippage and india/costs.py delivery costs. A buy whose open gapped more than max_gap_pct above the previous close is skipped and said so
       (the no-chase rule, E04/P01). Sells fill at the open less 0.1%.
    2. mark: every position at today's close.
    3. exits for replacements: a close at or under the fixed stop (stop_pct below entry) -> sold at the next open; after min_hold_sessions, a close
       under its 200-day average -> sold at the next open. The twin's original holdings leave only through the cut list.
    4. plan for the next session: the cuts (the allocator's REDUCE / TRIM / TIDY suggestions on names this book holds, plus the exits above; a
       name is not cut twice inside reentry_sessions), the rupees they free, and for each cut a replacement from the Nifty 500 passing every
       filter (above its 50- and 200-day averages, not stretched: RSI under 70 and under max_dist_sma50 above the 50-day, not up more than
       max_ret_20 in 20 sessions, not a 40%-down name, calm: its 60-day volatility in the lower half of the survivors, liquid, a sector not over
       max_sector_pct of the stock book after the buy), ranked by calm then by strength against the Nifty 500; at most max_new_per_week new
       names a week. "No change" is a valid plan. The plan is written to paper/managed/plans.jsonl with a sha chain (each row carries the sha of
       the row before it) and is refused on or after 09:15 IST of the session it is for, so it is a forecast, never hindsight.
  nightly: score() grades every plan at +5 and +20 sessions (did the cut name fall, did the replacement rise, replacement minus cut).
  benchmark: india/account.py adds this book to paper/account/benchmark.jsonl (managed_ret_pct); nothing is read into any gap before 60 sessions.
Every row records the sha of india/paper_config.json (pinned; the books.managed section was added on Madhav's yes of 30 Oct 2026).
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
import sys
from pathlib import Path

import pandas as pd

from india import allocator, costs, paths

IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
CFG_FILE = Path(__file__).with_name("paper_config.json")


def _dir() -> Path:
    d = paths.data_dir() / "paper" / "managed"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def _load(p: Path, default=None):
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return default


def _jsonl(p: Path) -> list[dict]:
    try:
        return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
    except OSError:
        return []


def _write_jsonl(p: Path, rows: list[dict]) -> None:
    p.write_text("".join(json.dumps(r) + "\n" for r in rows))


def cfg() -> dict:
    c = json.loads(CFG_FILE.read_text())
    m = dict(c["books"]["managed"])
    m["config_sha"] = hashlib.sha256(CFG_FILE.read_bytes()).hexdigest()[:16]
    return m


# ------------------------------------------------------------------------------------------------------------------------ calendar

def holidays() -> set:
    try:
        from india import dayplan
        return dayplan.holidays(refresh=False)
    except Exception:  # noqa: BLE001
        return set()


def next_session(after: dt.date) -> dt.date:
    hol = holidays()
    d = after + dt.timedelta(days=1)
    while d.weekday() >= 5 or d in hol:
        d += dt.timedelta(days=1)
    return d


def sessions_between(a: str, b: str) -> int:
    """Trading sessions after day a up to and including day b (a < b)."""
    hol = holidays()
    da, db = dt.date.fromisoformat(a), dt.date.fromisoformat(b)
    n, d = 0, da
    while d < db:
        d += dt.timedelta(days=1)
        if d.weekday() < 5 and d not in hol:
            n += 1
    return n


# ------------------------------------------------------------------------------------------------------------------------ bars and features

def bars() -> pd.DataFrame:
    """Adjusted daily bars for the lookback (the paper book's own reader; live data, the research is untouched)."""
    from india import paper
    df = paper.load_adjusted()
    keep = ["symbol", "date", "adj_open", "adj_high", "adj_low", "adj_close", "volume"]
    if "turnover" in df:
        keep.append("turnover")
    df = df[keep].rename(columns={"adj_open": "open", "adj_high": "high", "adj_low": "low", "adj_close": "close"})
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values(["symbol", "date"]).reset_index(drop=True)


def nifty500() -> dict:
    """symbol -> industry from the newest Nifty 500 constituent list NSE published (bronze/indices/nifty500_<date>.csv)."""
    fs = sorted((paths.data_dir() / "bronze" / "indices").glob("nifty500_*.csv"))
    if not fs:
        return {}
    df = pd.read_csv(fs[-1])
    cols = {c.strip().lower(): c for c in df.columns}
    sym, ind = cols.get("symbol"), cols.get("industry")
    return {str(r[sym]).strip(): str(r[ind]).strip() if ind else "unknown" for _, r in df.iterrows() if sym}


def features(df: pd.DataFrame, day: str) -> pd.DataFrame:
    """One row per symbol as of `day`: close, sma50, sma200, rsi14, ret_20, ret_120, dist from the 250-day high, 60-day volatility, median turnover."""
    d = df[df["date"] <= pd.Timestamp(day)]
    out = []
    for sym, g in d.groupby("symbol"):
        c = g["close"].astype(float).reset_index(drop=True)
        if len(c) < 210:
            continue
        delta = c.diff()
        up, dn = delta.clip(lower=0), -delta.clip(upper=0)
        au, ad = up.ewm(alpha=1 / 14, adjust=False).mean(), dn.ewm(alpha=1 / 14, adjust=False).mean()
        rsi = float((100 - 100 / (1 + (au.iloc[-1] / ad.iloc[-1]))) if ad.iloc[-1] > 0 else 100.0)
        rets = c.pct_change().dropna()
        turn = float(g["turnover"].tail(60).median()) if "turnover" in g else None
        out.append({"symbol": sym, "date": str(g["date"].iloc[-1].date()), "close": float(c.iloc[-1]), "sma50": float(c.tail(50).mean()), "sma200": float(c.tail(200).mean()),
                    "rsi14": rsi, "ret_20": float(c.iloc[-1] / c.iloc[-21] - 1), "ret_120": float(c.iloc[-1] / c.iloc[-121] - 1) if len(c) > 121 else None,
                    "off_high_250": float(c.iloc[-1] / c.tail(250).max() - 1), "vol60": float(rets.tail(60).std() * math.sqrt(250)), "turnover_med60": turn,
                    "prev_close": float(c.iloc[-2])})
    return pd.DataFrame(out)


# ------------------------------------------------------------------------------------------------------------------------ the book

def open_book(day: str) -> dict | None:
    """Starts from the account twin as it stands: the same positions, cash and options sleeve, so the four books are comparable from one start."""
    twin = _load(paths.data_dir() / "paper" / "account" / "state.json")
    if not twin:
        return None
    pos = {s: {"qty": int(v["qty"]), "avg": float(v["avg"]), "last": float(v["last"]), "source": "twin", "entered": twin.get("snapshot_day")} for s, v in twin["positions"].items() if v["qty"] > 0}
    value = sum(v["qty"] * v["last"] for v in pos.values()) + float(twin["cash_inr"]) + float(twin["options_inr"])
    return {"opened_at": _now(), "opened_from": "paper/account/state.json (the account twin)", "start_day": day, "start_inr": round(value, 2),
            "positions": pos, "cash_inr": round(float(twin["cash_inr"]), 2), "options_inr": float(twin["options_inr"]), "trades": [], "costs_inr": 0.0,
            "filled_plans": [], "cut_days": {}, "sessions": []}


def value_of(book: dict) -> float:
    return sum(v["qty"] * v["last"] for v in book["positions"].values()) + book["cash_inr"] + book["options_inr"]


def _plans() -> list[dict]:
    return _jsonl(_dir() / "plans.jsonl")


def _sha(row: dict) -> str:
    return hashlib.sha256(json.dumps({k: v for k, v in row.items() if k != "sha"}, sort_keys=True).encode()).hexdigest()


def chain_ok() -> tuple[bool, str]:
    prev = ""
    for i, r in enumerate(_plans()):
        if r.get("prev_sha", "") != prev or _sha(r) != r.get("sha"):
            return False, f"plan {i} ({r.get('for_session')}) breaks the chain"
        prev = r["sha"]
    return True, "chain intact"


# ------------------------------------------------------------------------------------------------------------------------ fill, mark, exits

def fill(book: dict, day: str, df: pd.DataFrame, c: dict) -> list[dict]:
    """Fill the plan written for `day` at the day's official open (bhavcopy), with slippage and costs; the no-chase check on every buy."""
    plan = next((p for p in _plans() if p.get("for_session") == day), None)
    if not plan or plan["id"] in book["filled_plans"]:
        return []
    today = df[df["date"] == pd.Timestamp(day)].set_index("symbol")
    prev = df[df["date"] < pd.Timestamp(day)].groupby("symbol").tail(1).set_index("symbol")
    slip = c["slippage_pct"] / 100
    done = []
    for cut in plan.get("cuts") or []:
        sym, p = cut["symbol"], book["positions"].get(cut["symbol"])
        t = {"plan": plan["id"], "day": day, "side": "SELL", "symbol": sym, "why": cut.get("why"), "kind": cut.get("kind")}
        if not p or sym not in today.index:
            t["skipped"] = "not held" if not p else "no bar for the day (not traded or suspended): tried again tomorrow"
            done.append(t)
            continue
        price = float(today.loc[sym, "open"]) * (1 - slip)
        qty = p["qty"] if cut.get("all") else min(p["qty"], max(1, math.floor(float(cut["inr"]) / price)))
        value = qty * price
        k = costs.cost("delivery", "sell", value)
        p["qty"] -= qty
        book["cash_inr"] += value - k
        book["costs_inr"] += k
        book["cut_days"][sym] = day
        t.update({"qty": qty, "price": round(price, 2), "value_inr": round(value, 2), "cost_inr": round(k, 2), "pnl_inr": round(qty * (price - p["avg"]) - k, 2), "filled": True})
        if p["qty"] <= 0:
            del book["positions"][sym]
        done.append(t)
    for buy in plan.get("buys") or []:
        sym = buy["symbol"]
        t = {"plan": plan["id"], "day": day, "side": "BUY", "symbol": sym, "for_cut": buy.get("for_cut"), "why": buy.get("why")}
        if sym not in today.index:
            t["skipped"] = "no bar for the day"
            done.append(t)
            continue
        o, pc = float(today.loc[sym, "open"]), float(prev.loc[sym, "close"]) if sym in prev.index else None
        gap = (o / pc - 1) if pc else 0.0
        if gap > c["max_gap_pct"] / 100:
            t.update({"skipped": f"opened {100 * gap:+.1f}% above the previous close: more than {c['max_gap_pct']}%, so not chased", "gap_pct": round(100 * gap, 2)})
            done.append(t)
            continue
        price = o * (1 + slip)
        inr = min(float(buy["inr"]), book["cash_inr"])
        qty = math.floor(inr / price)
        if qty < 1:
            t["skipped"] = "not enough cash for one share"
            done.append(t)
            continue
        value = qty * price
        k = costs.cost("delivery", "buy", value)
        p = book["positions"].setdefault(sym, {"qty": 0, "avg": price, "last": price, "source": "replacement", "entered": day})
        p["avg"] = (p["avg"] * p["qty"] + value) / (p["qty"] + qty)
        p["qty"] += qty
        p.update({"stop": round(p["avg"] * (1 - c["stop_pct"] / 100), 2), "min_exit_after": c["min_hold_sessions"], "plan": plan["id"], "for_cut": buy.get("for_cut")})
        book["cash_inr"] -= value + k
        book["costs_inr"] += k
        t.update({"qty": qty, "price": round(price, 2), "value_inr": round(value, 2), "cost_inr": round(k, 2), "gap_pct": round(100 * gap, 2), "stop": p["stop"], "filled": True})
        done.append(t)
    book["filled_plans"].append(plan["id"])
    book["trades"] += done
    led = _jsonl(_dir() / "ledger.jsonl")
    for t in done:
        led.append({"plan": plan["id"], "for_session": day, "written_at": plan.get("written_at"), **{k: v for k, v in t.items() if k not in ("plan", "day")}, "scored": {}})
    _write_jsonl(_dir() / "ledger.jsonl", led)
    return done


def mark(book: dict, day: str, df: pd.DataFrame) -> None:
    today = df[df["date"] == pd.Timestamp(day)].set_index("symbol")["close"]
    for sym, p in book["positions"].items():
        if sym in today.index and float(today[sym]) > 0:
            p["last"] = float(today[sym])
    if day not in book["sessions"]:
        book["sessions"].append(day)


def exits(book: dict, day: str, feats: pd.DataFrame, c: dict) -> list[dict]:
    """Replacements only: the fixed stop on the close; after the minimum hold, a close under the 200-day average."""
    f = feats.set_index("symbol")
    out = []
    for sym, p in book["positions"].items():
        if p.get("source") != "replacement":
            continue
        held = sessions_between(p["entered"], day) if p.get("entered") and p["entered"] < day else 0
        if p["last"] <= p.get("stop", 0):
            out.append({"symbol": sym, "kind": "stop", "all": True, "inr": round(p["qty"] * p["last"]), "why": f"closed at ₹{p['last']:,.2f}, at or under its {c['stop_pct']}% stop of ₹{p['stop']:,.2f}"})
        elif held >= c["min_hold_sessions"] and sym in f.index and p["last"] < float(f.loc[sym, "sma200"]):
            out.append({"symbol": sym, "kind": "weak", "all": True, "inr": round(p["qty"] * p["last"]), "why": f"after {held} sessions it closed under its 200-day average (₹{float(f.loc[sym, 'sma200']):,.0f})"})
    return out


# ------------------------------------------------------------------------------------------------------------------------ the plan

def cut_list(book: dict, day: str, c: dict) -> list[dict]:
    """The allocator's REDUCE / TRIM / TIDY suggestions on names this book holds, not cut again inside reentry_sessions."""
    v = _load(paths.data_dir() / "paper" / "allocation_view.json", {}) or {}
    out = []
    for s in v.get("suggestions") or []:
        sym, act = s.get("symbol"), s.get("action")
        p = book["positions"].get(sym)
        if not p or act not in ("REDUCE", "TRIM", "TIDY") or p.get("source") == "replacement":
            continue
        last_cut = book["cut_days"].get(sym)
        if last_cut and sessions_between(last_cut, day) < c["reentry_sessions"]:
            continue
        inr = p["qty"] * p["last"] if act == "TIDY" else min(float(s.get("suggest_inr") or 0), p["qty"] * p["last"])
        if inr < 1 or (act != "TIDY" and inr < c["min_cut_inr"]):          # a ₹500 trim is noise, not a decision
            continue
        out.append({"symbol": sym, "kind": act, "all": act == "TIDY", "inr": round(inr), "grade": s.get("grade"), "why": s.get("why"), "wrong_if": s.get("wrong_if")})
    return out


def candidates(book: dict, feats: pd.DataFrame, sectors: dict, n500_ret120: float | None, exclude: set, day: str, c: dict) -> pd.DataFrame:
    f = feats[feats["symbol"].isin(sectors)].copy()
    f = f[~f["symbol"].isin(exclude)]
    f["industry"] = f["symbol"].map(sectors)
    f["why_out"] = ""
    rules = [
        ("under its 50-day average", f["close"] <= f["sma50"]),
        ("under its 200-day average", f["close"] <= f["sma200"]),
        (f"stretched: RSI {c['max_rsi14']} or more", f["rsi14"] >= c["max_rsi14"]),
        (f"stretched: more than {c['max_dist_sma50_pct']}% above its 50-day", f["close"] / f["sma50"] - 1 > c["max_dist_sma50_pct"] / 100),
        (f"up more than {c['max_ret_20_pct']}% in 20 sessions", f["ret_20"] > c["max_ret_20_pct"] / 100),
        ("40% or more under its one-year high", f["off_high_250"] <= -0.40),
        (f"under ₹{c['min_price_inr']}", f["close"] < c["min_price_inr"]),
    ]
    if "turnover_med60" in f and f["turnover_med60"].notna().any():
        rules.append((f"thin: under ₹{c['min_turnover_cr']} crore a day", f["turnover_med60"].fillna(0) < c["min_turnover_cr"] * 1e7))
    for why, bad in rules:
        f.loc[bad & (f["why_out"] == ""), "why_out"] = why
    ok = f[f["why_out"] == ""].copy()
    if len(ok) >= 4:
        med = ok["vol60"].median()
        f.loc[(f["why_out"] == "") & (f["vol60"] > med), "why_out"] = f"not calm: swings more than the median survivor ({100 * med:.0f}% a year)"
        ok = f[f["why_out"] == ""].copy()
    stock_val = sum(v["qty"] * v["last"] for v in book["positions"].values())
    by_sector = {}
    for s, p in book["positions"].items():
        by_sector[sectors.get(s, "unknown")] = by_sector.get(sectors.get(s, "unknown"), 0) + p["qty"] * p["last"]
    ok["sector_pct_now"] = ok["industry"].map(lambda i: 100 * by_sector.get(i, 0) / stock_val if stock_val else 0)
    ok["rs_120"] = ok["ret_120"] - (n500_ret120 or 0)
    ok["rank_calm"] = ok["vol60"].rank()
    ok["rank_rs"] = (-ok["rs_120"].fillna(-9)).rank()
    ok["score"] = ok["rank_calm"] + ok["rank_rs"]
    return ok.sort_values("score")


def reasons(r: pd.Series, n500_ret120: float | None) -> list[str]:
    out = [f"above its 50-day (₹{r['sma50']:,.0f}) and 200-day (₹{r['sma200']:,.0f}) averages at ₹{r['close']:,.2f}",
           f"calm: swings about {100 * r['vol60']:.0f}% a year", f"RSI {r['rsi14']:.0f}, {100 * (r['close'] / r['sma50'] - 1):+.1f}% from its 50-day: not stretched"]
    if r.get("ret_120") is not None and not pd.isna(r.get("ret_120")):
        out.append(f"{100 * r['ret_120']:+.0f}% in 6 months" + (f" against the Nifty 500's {100 * n500_ret120:+.0f}%" if n500_ret120 is not None else ""))
    return out


def make_plan(book: dict, day: str, feats: pd.DataFrame, exit_rows: list[dict], c: dict) -> dict:
    for_session = next_session(dt.date.fromisoformat(day)).isoformat()
    cuts = exit_rows + cut_list(book, day, c)
    sectors = nifty500()
    n500 = None
    try:
        from india import sealed
        ix = sealed.read_index("paper_context", (dt.date.fromisoformat(day) - dt.timedelta(days=200)).isoformat(), ["NIFTY 500"]).sort_values("date")
        ix = ix[ix["date"].astype(str) <= day]
        if len(ix) > 121:
            n500 = float(ix.iloc[-1]["close"]) / float(ix.iloc[-121]["close"]) - 1
    except Exception:  # noqa: BLE001
        pass
    recent = {t["symbol"] for t in book["trades"] if t.get("side") == "SELL" and t.get("filled") and sessions_between(t["day"], day) < c["reentry_sessions"]}
    exclude = set(book["positions"]) | recent | {x["symbol"] for x in cuts}
    cands = candidates(book, feats, sectors, n500, exclude, day, c) if cuts else feats.iloc[0:0]
    week_buys = sum(1 for t in book["trades"] if t.get("side") == "BUY" and t.get("filled") and sessions_between(t["day"], day) < 5)
    room = max(0, c["max_new_per_week"] - week_buys)
    buys, notes, used = [], [], set()
    pool_small = 0.0
    stock_val = sum(v["qty"] * v["last"] for v in book["positions"].values()) or 1.0
    for cut in cuts:
        inr = float(cut["inr"])
        if inr < c["min_buy_inr"]:
            pool_small += inr
            continue
        pick = None
        for _, r in cands.iterrows():
            if r["symbol"] in used or r["close"] * c["min_shares"] > inr:
                continue
            if r["sector_pct_now"] + 100 * inr / stock_val > c["max_sector_pct"]:
                continue
            pick = r
            break
        if pick is None or room <= 0:
            notes.append(f"{cut['symbol']}: the money stays in cash" + (" (this week's new names are used up)" if pick is not None else " (no name passed every filter at that size)"))
            continue
        used.add(pick["symbol"])
        room -= 1
        alts = [a["symbol"] for _, a in cands.iterrows() if a["symbol"] not in used and a["close"] * c["min_shares"] <= inr][:2]
        buys.append({"symbol": pick["symbol"], "inr": round(inr), "for_cut": cut["symbol"], "industry": pick["industry"], "reasons": reasons(pick, n500), "also_considered": alts,
                     "why": f"replaces {cut['symbol']}: " + "; ".join(reasons(pick, n500)[:2]), "stop_pct": c["stop_pct"], "min_hold_sessions": c["min_hold_sessions"]})
    if pool_small >= c["min_buy_inr"] and room > 0:
        pick = next((r for _, r in cands.iterrows() if r["symbol"] not in used and r["close"] * c["min_shares"] <= pool_small and r["sector_pct_now"] + 100 * pool_small / stock_val <= c["max_sector_pct"]), None)
        if pick is not None:
            small = [x["symbol"] for x in cuts if float(x["inr"]) < c["min_buy_inr"]]
            buys.append({"symbol": pick["symbol"], "inr": round(pool_small), "for_cut": "+".join(small), "industry": pick["industry"], "reasons": reasons(pick, n500), "also_considered": [],
                         "why": f"replaces the small stakes {', '.join(small)} together: " + "; ".join(reasons(pick, n500)[:2]), "stop_pct": c["stop_pct"], "min_hold_sessions": c["min_hold_sessions"]})
    plans = _plans()
    row = {"id": f"mp-{for_session}", "written_at": _now(), "written_day": day, "for_session": for_session, "config_sha": c["config_sha"], "rules": c["version"],
           "cuts": cuts, "buys": buys, "no_change": not cuts and not buys, "notes": notes, "freed_inr": round(sum(float(x["inr"]) for x in cuts)),
           "universe": {"nifty500": len(sectors), "with_bars": int(feats["symbol"].isin(sectors).sum()), "passed_filters": int(len(cands))},
           "prev_sha": plans[-1]["sha"] if plans else ""}
    row["words"] = plan_words(row)
    row["brief"] = plan_brief(row)
    row["sha"] = _sha(row)
    return row


def plan_brief(p: dict) -> str:
    """One or two sentences for the voice; the full words are in the view."""
    if p.get("no_change"):
        return f"No change for {_dw(p['for_session'])}: nothing is on the cut list."
    cuts, buys = p.get("cuts") or [], p.get("buys") or []
    w = f"For {_dw(p['for_session'])}: {len(cuts)} cut{'s' if len(cuts) != 1 else ''} ({', '.join(x['symbol'] for x in cuts)}) freeing about ₹{float(p.get('freed_inr') or 0):,.0f}"
    if buys:
        w += "; " + ", ".join(f"{b['symbol']} replaces {b['for_cut']}" for b in buys) + ", each with a 7% stop"
    else:
        w += "; the money stays in cash"
    return w + "."


def plan_words(p: dict) -> str:
    if p.get("no_change"):
        return f"No change for {_dw(p['for_session'])}: nothing on the cut list for the managed book, so it holds what it has."
    parts = []
    for cut in p.get("cuts") or []:
        what = "sells all of" if cut.get("all") else "sells about ₹{:,.0f} of".format(float(cut["inr"]))
        parts.append(f"{what} {cut['symbol']} ({cut.get('kind', '').lower()}: {str(cut.get('why') or '').split('. ')[0].rstrip('.')})")
    for b in p.get("buys") or []:
        parts.append(f"buys about ₹{float(b['inr']):,.0f} of {b['symbol']} to replace {b['for_cut']} ({'; '.join(b['reasons'][:2])}), with a {b['stop_pct']}% stop and a {b['min_hold_sessions']}-session minimum hold")
    w = f"For {_dw(p['for_session'])} the managed book " + "; ".join(parts) + ". Fills at the open; a buy that opens more than the gap limit above the last close is skipped."
    if p.get("notes"):
        w += " " + " ".join(p["notes"]) + "."
    return w


def _dw(d: str) -> str:
    try:
        x = dt.date.fromisoformat(d)
        return x.strftime("%A %-d %b")
    except ValueError:
        return d


def refuse_late(for_session: str) -> None:
    now = dt.datetime.now(IST)
    if now.date() > dt.date.fromisoformat(for_session) or (now.date() == dt.date.fromisoformat(for_session) and now.time() >= dt.time(9, 15)):
        raise RuntimeError(f"the plan for {for_session} cannot be written at {now.strftime('%H:%M')} IST on {now.date()}: the session has opened")


# ------------------------------------------------------------------------------------------------------------------------ run, score, view

def run(day: str | None = None) -> dict:
    c = cfg()
    df = bars()
    last = str(df["date"].max().date())
    day = day or last
    st = _dir() / "state.json"
    book = _load(st)
    opened = False
    if not book:
        book = open_book(day)
        opened = True
        if not book:
            return {"status": "missing", "words": "the account twin has not opened yet, so the managed book cannot start"}
    filled = fill(book, day, df, c) if day in set(df["date"].dt.strftime("%Y-%m-%d")) else []
    mark(book, day, df)
    feats = features(df, day)
    ex = exits(book, day, feats, c)
    plan = None
    try:
        p = make_plan(book, day, feats, ex, c)
        refuse_late(p["for_session"])
        rows = [r for r in _plans() if r.get("for_session") != p["for_session"]]
        if rows and rows[-1]["sha"] != p["prev_sha"]:
            p["prev_sha"] = rows[-1]["sha"]
            p["sha"] = _sha(p)
        _write_jsonl(_dir() / "plans.jsonl", rows + [p])
        plan = p
    except Exception as e:  # noqa: BLE001
        plan = {"error": f"{type(e).__name__}: {str(e)[:160]}", "for_session": next_session(dt.date.fromisoformat(day)).isoformat()}
    st.write_text(json.dumps(book, indent=1))
    v = view(book, day, plan, filled, c, opened)
    (_dir() / "view.json").write_text(json.dumps(v, indent=1))
    return v


def view(book: dict, day: str, plan: dict | None, filled: list[dict], c: dict, opened: bool = False) -> dict:
    value = value_of(book)
    start = float(book["start_inr"])
    n = len(book["sessions"])
    reps = [{"symbol": s, **{k: round(v, 2) if isinstance(v, float) else v for k, v in p.items()}, "value_inr": round(p["qty"] * p["last"]),
             "pnl_pct": round(100 * (p["last"] / p["avg"] - 1), 1), "held_sessions": sessions_between(p["entered"], day) if p.get("entered") and p["entered"] < day else 0}
            for s, p in book["positions"].items() if p.get("source") == "replacement"]
    ok, chain = chain_ok()
    clock = {"sessions": n, "of": c["judge_after_sessions"], "left": max(0, c["judge_after_sessions"] - n), "start_day": book["start_day"],
             "words": f"Session {n} of {c['judge_after_sessions']} for the managed book; nothing is read into its result before session {c['judge_after_sessions']}."}
    words = (f"The managed book (paper): ₹{value:,.0f}, {100 * (value / start - 1):+.2f}% since {book['start_day']}; "
             f"{len(reps)} replacement{'s' if len(reps) != 1 else ''} held, {sum(1 for t in book['trades'] if t.get('filled'))} fills so far. ")
    if filled:
        words += "Today it " + "; ".join(f"{'bought' if t['side'] == 'BUY' else 'sold'} {t.get('qty')} {t['symbol']} at ₹{t.get('price'):,.2f}" if t.get("filled") else f"skipped {t['symbol']} ({t['skipped']})" for t in filled) + ". "
    if plan and not plan.get("error"):
        words += plan["words"]
    elif plan:
        words += f"No plan could be written for {plan.get('for_session')}: {plan['error']}."
    return {"built_at": _now(), "paper": True, "day": day, "opened_today": opened, "start_day": book["start_day"], "start_inr": round(start), "value_inr": round(value),
            "return_pct": round(100 * (value / start - 1), 2), "stocks_inr": round(sum(v["qty"] * v["last"] for v in book["positions"].values())), "cash_inr": round(book["cash_inr"]),
            "options_inr": round(book["options_inr"]), "positions": len(book["positions"]), "replacements": sorted(reps, key=lambda r: -r["value_inr"]), "filled_today": filled,
            "plan": plan, "trades_count": len(book["trades"]), "costs_inr": round(book["costs_inr"], 2), "clock": clock, "chain": chain, "chain_ok": ok, "rules": c["version"], "words": words}


def score(day: str | None = None) -> dict:
    """The replacement ledger, +5 and +20 sessions after each fill: did the cut name fall (the cut was right), did the replacement rise, and the
    difference. Scored from the exchange's closes; written back into paper/managed/ledger.jsonl."""
    df = bars()
    day = day or str(df["date"].max().date())
    close = df.pivot(index="date", columns="symbol", values="close")
    led = _jsonl(_dir() / "ledger.jsonl")
    n_new = 0
    for r in led:
        if not r.get("filled") or r.get("symbol") not in close:
            continue
        s = close[r["symbol"]].dropna()
        s = s[s.index >= pd.Timestamp(r["for_session"])]
        for h in (5, 20):
            k = f"+{h}"
            if k in (r.get("scored") or {}) or len(s) <= h:
                continue
            ret = float(s.iloc[h] / float(r["price"]) - 1)
            r.setdefault("scored", {})[k] = {"day": str(s.index[h].date()), "ret_pct": round(100 * ret, 2),
                                            "verdict": ("the cut was right" if ret < 0 else "the cut was early") if r["side"] == "SELL" else ("the replacement rose" if ret > 0 else "the replacement fell")}
            n_new += 1
    # replacement minus cut, where both legs of one plan are scored
    by = {}
    for r in led:
        if r.get("filled"):
            by.setdefault((r["plan"], r.get("symbol")), r)
    for r in led:
        if r.get("side") == "BUY" and r.get("filled") and r.get("for_cut"):
            for h in ("+5", "+20"):
                cut = by.get((r["plan"], r["for_cut"]))
                if cut and h in (cut.get("scored") or {}) and h in (r.get("scored") or {}):
                    r["scored"][h]["minus_cut_pct"] = round(r["scored"][h]["ret_pct"] - cut["scored"][h]["ret_pct"], 2)
    _write_jsonl(_dir() / "ledger.jsonl", led)
    rows = [r for r in led if r.get("filled")]
    out = {"scored_at": _now(), "day": day, "fills": len(rows), "new_scores": n_new,
           "cuts_right_5": sum(1 for r in rows if r["side"] == "SELL" and (r.get("scored") or {}).get("+5", {}).get("ret_pct", 0) < 0),
           "cuts_scored_5": sum(1 for r in rows if r["side"] == "SELL" and "+5" in (r.get("scored") or {})),
           "replacements_up_20": sum(1 for r in rows if r["side"] == "BUY" and (r.get("scored") or {}).get("+20", {}).get("ret_pct", 0) > 0),
           "replacements_scored_20": sum(1 for r in rows if r["side"] == "BUY" and "+20" in (r.get("scored") or {}))}
    (_dir() / "score.json").write_text(json.dumps(out, indent=1))
    return out


def show() -> None:
    v = _load(_dir() / "view.json", {}) or {}
    print(v.get("words") or "no managed book yet: run `python -m india.managed run`")
    if v.get("clock"):
        print(v["clock"]["words"], "|", v.get("chain"))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "show"
    if cmd == "run":
        run(sys.argv[2] if len(sys.argv) > 2 else None)
        show()
    elif cmd == "score":
        print(json.dumps(score(), indent=1))
    else:
        show()
