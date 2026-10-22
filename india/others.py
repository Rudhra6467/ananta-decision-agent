"""Reference traders, every session, held against Ananta India (Madhav, 22 Oct 2026, points 10-13: "our daily reconstruction of trades from
other traders to compare our engine ability and see what's missing", "that way we know where Ananta stands among other traders").

India has no public per-trader fills (nothing like the Hyperliquid tape the crypto loop reads), so the reference traders are rebuilt from
public, point-in-time data, scored at OUR costs on OUR live paper sessions only, and held against Ananta's own decision journal. Reference only:
they are event generators and a yardstick, never teachers or copy signals (the crypto rule D8 holds here).

THE FIXED RULES (written 22 Oct 2026, before any live day was read; they change only with Madhav's yes)
 1. Window: live paper sessions only, from OTHERS_START (the stock paper's first decision day) to the review day, read through sealed.read_others
    (purpose others_review: the only reader india/leakcheck.py allows this module, with a constant start). Nothing on history (2000-2023) is
    computed here: the reference traders exist on live sessions only, so no yardstick can be fitted to the past.
 2. The reference traders:
    HINDSIGHT  the ceiling: the best H-session long trips that closed on the day (entry at the close of session D-H, exit at the close of D)
               among the liquid universe recorded at the entry session, H in HORIZONS; the top TOP_N by net return after our delivery costs per H
               (and the TOP_N worst, as reference: the book is long only). A ceiling nobody reaches; it measures what the sessions offered.
               Each H arrives as the window grows (H=20 from the 21st live session).
    INFORMED   the big money: FII, DII, Pro and Client from the participant-wise open interest: each one's stance at the close (index futures
               net long or short) and that day's change, scored on the next session's Nifty move. The India version of "what the whales did".
    RANDOM     the null: DRAWS draws of TOP_N names with the same H from the same eligible set (seeded by the day and H); the median and the
               5-95% band of their mean net return.
    MARKET     everyone: the mean net return over H of every eligible name (buy and hold).
    ANANTA     its own journal: the research families (BRK, PULL, REV) of the stock paper book, the random control (CTL) apart, and the daily
               call (K02). The index decisions (SP1) join once its scores exist. TEACHER arrives with SL1, DEALS with EV6, FUNDS with the monthly
               mutual-fund portfolio pull (all on the blueprint of 22 Oct 2026).
 3. Costs: a HINDSIGHT, RANDOM, MARKET or ANANTA trip is a NOTIONAL-rupee delivery round trip at india.costs.round_trip with the entry
    session's liquidity rank (the paper book's notional and cost model). Net = exit/entry - 1 - costs/NOTIONAL. Live closes are raw, so a trip
    whose path crosses a corporate action (the exchange's previous close and the prior session's close disagree by more than CA_TOL) is dropped
    and counted, never adjusted by hand.
 4. Ananta at a HINDSIGHT trip (the join india.missed uses): what fired on the name in the decision journals from two sessions before the entry
    session to one after, and what the book held at any time between entry and exit. Class, the first that fits: TAKEN (a research family held
    it), CONTROL (only CTL held it), PASSED (a research family fired, was rejected or never filled), NOT_COVERED (nothing fired). The worst
    trips are reference only (long-only book) and never enter the pattern rule.
 5. The pattern rule (the crypto rule, kept): the same NOT_COVERED situation (the entry session's structure, by H) on PATTERN_DAYS or more distinct
    review sessions within the last PATTERN_WINDOW -> one DRAFT finding in registrations/missed_drafts.jsonl (the India repair-shop queue),
    keyed others:H<h>:<structure>; a research idea, never a rule or a signal; not filed again inside the window.
 6. The league (ratings and rankings): per review session and H, the mean net return of each trader's trips, Ananta's percentile against RANDOM,
    the share of HINDSIGHT trips Ananta had a rule for (TAKEN+PASSED) and took (TAKEN), and the next-session hit rates of each INFORMED stance
    and of Ananta's call, all over the trailing LEAGUE_WINDOW review sessions. Ananta is judged by decision quality (coverage, hit rate,
    percentile against random), never by rupees alone (Madhav, 20 Oct 2026).
 7. Output: manifests/others_<date>.json (every trip and its class), registrations/others_league.md (the page), paper/others_history.jsonl (one
    row per review session) and the drafts. Read by india.report and india.morning.

  python -m india.others evening [YYYY-MM-DD]      after india.missed, in the paper job
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from india import costs, missed, paper, paths, sealed

OTHERS_START = "2026-10-16"        # the stock paper's first decision day; the only start this module ever reads from (leakcheck.paper_review)
RULES = "others-v1-2026-10-22"
HORIZONS = (1, 5, 20)
TOP_N = 20
DRAWS = 200
NOTIONAL = 50_000.0
CA_TOL = 0.08
PARTICIPANTS = ("FII", "DII", "Pro", "Client")
PATTERN_DAYS, PATTERN_WINDOW = 3, 7
LEAGUE_WINDOW = 20
REG = Path(__file__).parent / "registrations"
CLASSES = ("TAKEN", "CONTROL", "PASSED", "NOT_COVERED")


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def _r(x, n=4):
    return None if x is None or x != x else round(float(x), n)


# ------------------------------------------------------------------------------------------------------------------------------ inputs
def live(day: dt.date) -> dict:
    """The live window: cash rows and participant rows from OTHERS_START to the day (sealed purpose others_review)."""
    return sealed.read_others("others_review", OTHERS_START, until=day.isoformat())


def sessions(cash: pd.DataFrame) -> list[str]:
    return sorted({pd.Timestamp(d).date().isoformat() for d in cash["date"].unique()})


def closes(cash: pd.DataFrame) -> tuple[dict, dict, dict]:
    """(close[date][symbol], prev_close[date][symbol], isin->symbol per date) from the cash rows, the highest-turnover row per symbol."""
    c, pc, by_isin = {}, {}, {}
    r = cash.sort_values("turnover", ascending=False).drop_duplicates(["date", "symbol"])
    for d, g in r.groupby(pd.to_datetime(r["date"]).dt.date):
        k = d.isoformat()
        c[k] = dict(zip(g["symbol"], g["close"].astype(float)))
        pc[k] = dict(zip(g["symbol"], g["prev_close"].astype(float)))
        by_isin[k] = {i: s for i, s in zip(g["isin"], g["symbol"]) if isinstance(i, str)}
    return c, pc, by_isin


def universe_at(day: str) -> dict | None:
    """The universe recorded at the decision of `day`, else the latest recorded before it (known at the time; never a later one)."""
    u = missed.load_universe(dt.date.fromisoformat(day))
    if u is not None:
        return u
    keys = sorted(p.stem.split(".")[0] for p in (paper.pdir() / "decisions").glob("????-??-??.universe.json"))
    before = [k for k in keys if k < day]
    return missed.load_universe(dt.date.fromisoformat(before[-1])) if before else None


def symbol_of(row: dict, by_isin: dict) -> str:
    return by_isin.get(row.get("isin") or "", row["symbol"])


def crosses_action(sym: str, path: list[str], c: dict, pc: dict) -> bool:
    """A corporate action inside the path: the exchange's previous close on a session disagrees with the close of the session before by CA_TOL."""
    for a, b in zip(path, path[1:]):
        ca, pb = c.get(a, {}).get(sym), pc.get(b, {}).get(sym)
        if ca is None or pb is None or ca <= 0:
            return True
        if abs(pb / ca - 1) > CA_TOL:
            return True
    return False


def net_return(entry: float, exit_: float, rank: int | None, entry_day: str, exit_day: str) -> float:
    rt = costs.round_trip("delivery", NOTIONAL, NOTIONAL * exit_ / entry, year=int(entry_day[:4]), turnover_rank=rank,
                          when=dt.date.fromisoformat(entry_day), sell_when=dt.date.fromisoformat(exit_day))
    return exit_ / entry - 1 - rt["total"] / NOTIONAL


# ------------------------------------------------------------------------------------------------------------------------------ HINDSIGHT
def eligible(entry_day: str, exit_day: str, path: list[str], c: dict, pc: dict, by_isin: dict) -> tuple[list[dict], int]:
    """Every name in the entry session's recorded universe with a clean price path from entry to exit; the second value counts the dropped."""
    u = universe_at(entry_day)
    if u is None:
        return [], 0
    out, dropped = [], 0
    for row in u["rows"]:
        sym = symbol_of(row, by_isin.get(entry_day, {}))
        e, x = c.get(entry_day, {}).get(sym), c.get(exit_day, {}).get(sym)
        if e is None or x is None or e <= 0 or x <= 0:
            dropped += 1
            continue
        if crosses_action(sym, path, c, pc):
            dropped += 1
            continue
        rank = int(row["liq_rank"]) if row.get("liq_rank") is not None else None
        out.append({"sid": row["sid"], "symbol": row["symbol"], "liq_rank": rank, "entry": e, "exit": x, "urow": row,
                    "net": net_return(e, x, rank, entry_day, exit_day)})
    return out, dropped


def random_band(nets: list[float], seed: int, n: int = TOP_N, draws: int = DRAWS) -> dict:
    a = np.asarray(nets, dtype=float)
    if len(a) < n:
        return {"draws": 0}
    rng = np.random.default_rng(seed)
    means = np.array([rng.choice(a, size=n, replace=False).mean() for _ in range(draws)])
    return {"draws": draws, "median": _r(np.median(means)), "p5": _r(np.percentile(means, 5)), "p95": _r(np.percentile(means, 95)), "_means": means}


def structure_key(row: dict, h: int) -> tuple[str, str]:
    """The entry session's structure (the part of india.missed.situation that does not depend on the day's open and close) by H."""
    m = {**row, "side": "up", "gapx": row.get("gap"), "oc": row.get("oc")}
    key, words = missed.situation(m)
    sk = key.split(":")[1]
    return f"others:H{h}:{sk}", words.split(", ", 1)[1] if ", " in words else words


def ananta_on(trip: dict, entry_day: str, exit_day: str, sess: list[str], journals: dict, ex: pd.DataFrame) -> dict:
    """Rule 4: the journals from two sessions before the entry to one after, and the book between entry and exit."""
    i = sess.index(entry_day)
    window = [k for k in sess[max(0, i - 2): i + 2] if k in journals]
    fires = []
    for k in window:
        j, src = journals.get(k, (None, "missing"))
        for cc in j or []:
            if cc["sid"] == trip["sid"]:
                fires.append({"date": k, "family": cc["campaign"], "status": cc["status"], "reason": cc.get("reason"), "journal": src})
    held = ex.iloc[0:0]
    if len(ex) and "entry_date" in ex:
        x = ex[(ex["sid"] == trip["sid"]) & ex["status"].isin(["open", "closed"]) & ex["entry_date"].notna()]
        ed = x["exit_date"] if "exit_date" in x else pd.Series(None, index=x.index, dtype=object)
        held = x[(x["entry_date"] <= exit_day) & ((x["status"] == "open") | (ed.fillna("") >= entry_day))]
    research = held[held["campaign"].isin(missed.RESEARCH)] if len(held) else held
    research_fires = [f for f in fires if f["family"] in missed.RESEARCH]
    if len(research):
        cls, why = "TAKEN", f"held by {', '.join(sorted(research['campaign'].unique()))} (signal {', '.join(sorted(research['signal_date'].unique()))})"
    elif len(held):
        cls, why = "CONTROL", "held only by CTL, the random control draw: luck by construction"
    elif research_fires:
        f = research_fires[-1]
        why = (f"{f['family']} fired on {f['date']}; rejected: {missed.REASON_WORDS.get(f['reason'], f['reason'])}" if f["status"] == "rejected"
               else f"{f['family']} fired on {f['date']} and was chosen; no executed trade covered {entry_day}..{exit_day}")
        cls = "PASSED"
    else:
        cls, why = "NOT_COVERED", "no family fired in the window"
    return {"fired": fires, "class": cls, "why": why, "held_families": sorted(held["campaign"].unique()) if len(held) else []}


def hindsight(day: str, h: int, sess: list[str], c: dict, pc: dict, by_isin: dict, journals: dict, ex: pd.DataFrame) -> dict | None:
    i = sess.index(day)
    if i - h < 0:
        return None
    entry_day, path = sess[i - h], sess[i - h: i + 1]
    rows, dropped = eligible(entry_day, day, path, c, pc, by_isin)
    if not rows:
        return {"h": h, "entry": entry_day, "exit": day, "eligible": 0, "dropped": dropped}
    nets = [r["net"] for r in rows]
    best = sorted(rows, key=lambda r: -r["net"])[:TOP_N]
    worst = sorted(rows, key=lambda r: r["net"])[:TOP_N]
    seed = int(day.replace("-", "")) * 100 + h
    rb = random_band(nets, seed)

    def rec(r: dict, side: str) -> dict:
        k, words = structure_key(r["urow"], h)
        o = {"symbol": r["symbol"], "sid": r["sid"], "liq_rank": r["liq_rank"], "side": side, "entry_day": entry_day, "exit_day": day,
             "entry": _r(r["entry"], 2), "exit": _r(r["exit"], 2), "net": _r(r["net"]), "situation_key": k, "situation": words}
        if side == "up":
            o.update(ananta_on(r, entry_day, day, sess, journals, ex))
        return o

    ups = [rec(r, "up") for r in best if r["net"] > 0]
    downs = [rec(r, "down") for r in worst if r["net"] < 0]
    # Ananta's own picks over the same H: research positions open at the entry close, held to the exit (or their own exit, if earlier)
    picks = []
    if len(ex) and "entry_date" in ex:
        x = ex[ex["campaign"].isin(missed.RESEARCH) & ex["status"].isin(["open", "closed"]) & (ex["entry_date"] <= entry_day)]
        ed = x["exit_date"] if "exit_date" in x else pd.Series(None, index=x.index, dtype=object)
        x = x[(x["status"] == "open") | (ed.fillna("") > entry_day)].drop_duplicates("sid")
        for _, t in x.iterrows():
            sym = t["symbol"]
            e = c.get(entry_day, {}).get(sym)
            out_day = min(day, t["exit_date"]) if isinstance(t.get("exit_date"), str) and t["exit_date"] else day
            out_day = out_day if out_day in c else day
            xx = c.get(out_day, {}).get(sym)
            if e and xx and not crosses_action(sym, [s for s in path if s <= out_day], c, pc):
                picks.append({"symbol": sym, "sid": t["sid"], "net": _r(net_return(e, xx, int(t["liq_rank"]) if t.get("liq_rank") == t.get("liq_rank") else None, entry_day, out_day)),
                              "entry_day": entry_day, "exit_day": out_day})
    ananta_mean = float(np.mean([p["net"] for p in picks])) if picks else None
    pct = _r(float((rb["_means"] < ananta_mean).mean())) if (picks and rb.get("draws")) else None
    cover = {k: sum(1 for u in ups if u["class"] == k) for k in CLASSES}
    return {"h": h, "entry": entry_day, "exit": day, "eligible": len(rows), "dropped": dropped,
            "hindsight_mean": _r(np.mean([u["net"] for u in ups])) if ups else None, "worst_mean": _r(np.mean([d["net"] for d in downs])) if downs else None,
            "market_mean": _r(np.mean(nets)), "random": {k: v for k, v in rb.items() if k != "_means"},
            "ananta_mean": _r(ananta_mean), "ananta_n": len(picks), "ananta_pct_vs_random": pct, "coverage": cover,
            "best": ups, "worst": downs, "ananta_picks": picks}


# ------------------------------------------------------------------------------------------------------------------------------ INFORMED
def nifty_closes() -> dict[str, float]:
    """The Nifty close recorded with each daily call (paper/calls.jsonl, kind call): the session's close, known that evening."""
    p = paper.pdir() / "calls.jsonl"
    out = {}
    if p.exists():
        for line in p.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                if r.get("kind") == "call" and r.get("close"):
                    out[r["data_through"]] = float(r["close"])
    return out


def ananta_calls() -> dict[str, str]:
    p = paper.pdir() / "calls.jsonl"
    out = {}
    if p.exists():
        for line in p.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                if r.get("kind") == "call":
                    out[r["data_through"]] = r.get("call")
    return out


def informed(day: str, sess: list[str], oi: pd.DataFrame, nifty: dict[str, float], calls: dict[str, str]) -> dict:
    """Each participant's stance (index futures net) and flow (its change) at every close up to the day, scored on the next session's Nifty move;
    Ananta's daily call scored the same way. Hit rates over the last LEAGUE_WINDOW scored sessions."""
    if oi.empty:
        return {"sessions": 0, "note": "no participant rows in the window"}
    o = oi.copy()
    o["d"] = pd.to_datetime(o["date"]).dt.date.astype(str)
    o = o[o["client_type"].isin(PARTICIPANTS)]
    o["net"] = o["future_index_long"] - o["future_index_short"]
    o["stock_net"] = o["future_stock_long"] - o["future_stock_short"]
    rows, latest = [], {}
    for p in PARTICIPANTS:
        g = o[o["client_type"] == p].sort_values("d")
        prev = None
        for _, r in g.iterrows():
            d = r["d"]
            stance = int(np.sign(r["net"])) or 0
            flow = int(np.sign(r["net"] - prev)) if prev is not None else 0
            i = sess.index(d) if d in sess else -1
            nxt = sess[i + 1] if 0 <= i < len(sess) - 1 else None
            move = (nifty[nxt] / nifty[d] - 1) if (nxt and d in nifty and nxt in nifty) else None
            rows.append({"participant": p, "date": d, "net_index_futures": int(r["net"]), "stance": stance, "flow": flow, "next": nxt, "next_move": _r(move),
                         "stance_hit": (None if move is None or stance == 0 else bool(stance * move > 0)),
                         "flow_hit": (None if move is None or flow == 0 else bool(flow * move > 0))})
            latest[p] = {"date": d, "net_index_futures": int(r["net"]), "stance": "long" if stance > 0 else "short" if stance < 0 else "flat",
                         "flow": "added longs" if flow > 0 else "added shorts" if flow < 0 else "unchanged", "net_stock_futures": int(r["stock_net"])}
            prev = r["net"]
    acalls = []
    for d, call in sorted(calls.items()):
        if d not in sess or d > day:
            continue
        i = sess.index(d)
        nxt = sess[i + 1] if i < len(sess) - 1 else None
        move = (nifty[nxt] / nifty[d] - 1) if (nxt and d in nifty and nxt in nifty) else None
        s = 1 if call == "BULLISH" else -1 if call == "BEARISH" else 0
        acalls.append({"date": d, "call": call, "next": nxt, "next_move": _r(move), "hit": None if move is None or s == 0 else bool(s * move > 0)})

    def rate(xs: list, key: str) -> dict:
        scored = [x for x in xs if x.get(key) is not None][-LEAGUE_WINDOW:]
        return {"n": len(scored), "hit_rate": _r(np.mean([x[key] for x in scored]), 3) if scored else None}

    table = {p: {"stance": rate([x for x in rows if x["participant"] == p], "stance_hit"), "flow": rate([x for x in rows if x["participant"] == p], "flow_hit"),
                 "latest": latest.get(p)} for p in PARTICIPANTS}
    table["ANANTA_CALL"] = {"call": rate(acalls, "hit"), "latest": acalls[-1] if acalls else None}
    return {"sessions": len({r["date"] for r in rows}), "table": table, "rows": rows, "ananta_calls": acalls}


# ------------------------------------------------------------------------------------------------------------------------------ history, drafts
def history_path() -> Path:
    return paper.pdir() / "others_history.jsonl"


def read_history() -> list[dict]:
    p = history_path()
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()] if p.exists() else []


def write_history(rows: list[dict]) -> None:
    p = history_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("".join(json.dumps(r, default=str) + "\n" for r in rows))


def league(hist: list[dict], day: str) -> dict:
    """Per H over the trailing LEAGUE_WINDOW review sessions: each trader's mean, Ananta's mean percentile against random, and coverage."""
    win = [r for r in hist if r["date"] <= day and r.get("status") == "ok"][-LEAGUE_WINDOW:]
    out = {"window_sessions": len(win)}
    for h in HORIZONS:
        xs = [r["by_h"][str(h)] for r in win if r.get("by_h", {}).get(str(h)) and r["by_h"][str(h)].get("eligible")]
        if not xs:
            out[str(h)] = {"sessions": 0}
            continue
        m = lambda k: _r(np.mean([x[k] for x in xs if x.get(k) is not None])) if any(x.get(k) is not None for x in xs) else None
        cov = {k: int(sum(x["coverage"].get(k, 0) for x in xs)) for k in CLASSES}
        tot = sum(cov.values())
        out[str(h)] = {"sessions": len(xs), "HINDSIGHT": m("hindsight_mean"), "MARKET": m("market_mean"), "RANDOM": _r(np.mean([x["random"].get("median") for x in xs if x["random"].get("median") is not None])) if any(x["random"].get("median") is not None for x in xs) else None,
                       "ANANTA": m("ananta_mean"), "ananta_pct_vs_random": m("ananta_pct_vs_random"),
                       "coverage": cov, "had_a_rule_share": _r((cov["TAKEN"] + cov["PASSED"]) / tot, 3) if tot else None, "took_share": _r(cov["TAKEN"] / tot, 3) if tot else None}
    return out


def pattern_drafts(day: str, hist: list[dict], drafts: list[dict]) -> list[dict]:
    win = [r for r in hist if r["date"] <= day and r.get("status") == "ok"][-PATTERN_WINDOW:]
    seen: dict[str, dict] = {}
    for r in win:
        for key, ex in (r.get("not_covered") or {}).items():
            e = seen.setdefault(key, {"days": [], "examples": [], "situation": ex.get("situation")})
            e["days"].append(r["date"])
            e["examples"] += ex.get("examples", [])
    wd = {r["date"] for r in win}
    out = []
    for key, e in sorted(seen.items()):
        if len(e["days"]) < PATTERN_DAYS or any(x.get("key") == key and x.get("written_for") in wd for x in drafts):
            continue
        h = key.split(":")[1]
        out.append({"status": "DRAFT", "kind": "reference-traders pattern", "key": key, "side": "up", "situation_example": e["situation"], "days": e["days"],
                    "examples": e["examples"][:12], "written_for": day, "written_at": _now(),
                    "rule": f"the same NOT_COVERED hindsight situation ({h}) on {PATTERN_DAYS}+ review sessions within {PATTERN_WINDOW} (fixed 22 Oct 2026)",
                    "question": (f"Is there an entry rule, known at the entry session, that would have been positioned for the best {h.lstrip('H')}-session rises "
                                 f"of this kind ({key.split(':', 2)[2].replace('_', ' ')})? To be tested on the development and validation years only (2000-2023)."),
                    "note": "a candidate research idea, never a rule: it reaches paper only after it is registered in india/registry.py before it is run and passes the registry bar"})
    return out


# ------------------------------------------------------------------------------------------------------------------------------ page
def _pct(x) -> str:
    return "" if x is None else f"{x:+.2%}"


def _p0(x) -> str:
    return "" if x is None else f"{x:.0%}"


def page(hist: list[dict], lg: dict, day: str, last: dict | None = None) -> str:
    last = last if last is not None else next((r for r in reversed(hist) if r["date"] == day), None)
    lines = ["# Reference traders against Ananta India (india.others, each evening after the missed-movers review)", "",
             "Rules others-v1 (22 Oct 2026) in india/others.py. Every number is on live paper sessions only, after our costs, on a Rs 50,000 delivery trip.",
             "HINDSIGHT is the ceiling (the best trips the sessions offered), RANDOM the null, MARKET buy-and-hold of the liquid universe, ANANTA its own research",
             "picks over the same horizon. Coverage counts, among the best 20 rises per horizon, how many Ananta held (TAKEN), only the random control held (CONTROL),",
             "a family fired but did not hold (PASSED), or nothing fired (NOT_COVERED). INFORMED hit rates score each participant's index-futures stance and that",
             "day's change on the next session's Nifty move; Ananta's daily call is scored the same way. Ratings are decision quality, not rupees.", "",
             f"## League, trailing {LEAGUE_WINDOW} review sessions (through {day}; {lg.get('window_sessions', 0)} sessions)", "",
             "| H | sessions | HINDSIGHT | MARKET | RANDOM (median) | ANANTA | Ananta pct vs random | TAKEN | CONTROL | PASSED | NOT_COVERED | had a rule | took |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for h in HORIZONS:
        x = lg.get(str(h), {})
        if not x.get("sessions"):
            lines.append(f"| {h} | 0 | | | | | | | | | | | |")
            continue
        cv = x["coverage"]
        lines.append(f"| {h} | {x['sessions']} | {_pct(x['HINDSIGHT'])} | {_pct(x['MARKET'])} | {_pct(x['RANDOM'])} | {_pct(x['ANANTA'])} | {_p0(x.get('ananta_pct_vs_random'))} | "
                     f"{cv['TAKEN']} | {cv['CONTROL']} | {cv['PASSED']} | {cv['NOT_COVERED']} | {_p0(x['had_a_rule_share'])} | {_p0(x['took_share'])} |")
    if last and last.get("informed", {}).get("table"):
        t = last["informed"]["table"]
        lines += ["", f"## Informed money and Ananta's call, next-session hit rates (last {LEAGUE_WINDOW} scored sessions)", "",
                  "| who | stance hit rate (n) | flow hit rate (n) | latest |", "|---|---|---|---|"]
        for p in PARTICIPANTS:
            x = t[p]
            lt = x.get("latest") or {}
            lines.append(f"| {p} | {_p0(x['stance']['hit_rate'])} ({x['stance']['n']}) | {_p0(x['flow']['hit_rate'])} ({x['flow']['n']}) | "
                         f"{lt.get('date', '')}: {lt.get('stance', '')} {lt.get('net_index_futures', '')} index futures, {lt.get('flow', '')} |")
        a = t["ANANTA_CALL"]
        la = a.get("latest") or {}
        lines.append(f"| ANANTA call | {_p0(a['call']['hit_rate'])} ({a['call']['n']}) | | {la.get('date', '')}: {la.get('call', '')} |")
    if last and last.get("by_h"):
        for h in HORIZONS:
            x = last["by_h"].get(str(h))
            if not x or not x.get("eligible"):
                continue
            lines += ["", f"## {day}: best {h}-session trips that closed on the day (entry {x['entry']}, {x['eligible']} eligible, {x['dropped']} dropped)", "",
                      "| symbol | net | class | why | situation at entry |", "|---|---|---|---|---|"]
            for u in x["best"][:10]:
                lines.append(f"| {u['symbol']} | {_pct(u['net'])} | {u.get('class', '')} | {u.get('why', '')} | {u['situation']} |")
            if x.get("ananta_picks"):
                lines.append(f"\nAnanta's research picks open at {x['entry']}: {x['ananta_n']}, mean {_pct(x['ananta_mean'])} to {day}; "
                             f"random band {_pct(x['random'].get('p5'))} .. {_pct(x['random'].get('median'))} .. {_pct(x['random'].get('p95'))}; market {_pct(x['market_mean'])}.")
    lines += ["", "## History", "", "| date | status | H1 hindsight / market / Ananta | H5 | H20 | NOT_COVERED keys | drafts |", "|---|---|---|---|---|---|---|"]
    for r in hist[-30:]:
        if r.get("status") != "ok":
            lines.append(f"| {r['date']} | {r.get('status')} | | | | | |")
            continue
        cell = lambda h: (lambda x: "" if not x or not x.get("eligible") else f"{_pct(x['hindsight_mean'])} / {_pct(x['market_mean'])} / {_pct(x['ananta_mean'])}")(r["by_h"].get(str(h)))
        lines.append(f"| {r['date']} | ok | {cell(1)} | {cell(5)} | {cell(20)} | {len(r.get('not_covered') or {})} | {len(r.get('drafts_written') or [])} |")
    return "\n".join(lines) + "\n"


# ------------------------------------------------------------------------------------------------------------------------------ evening
def evening(day: dt.date | None = None, reg: Path | None = None, log=print) -> dict:
    day = day or dt.date.today()
    reg = reg or REG
    reg.mkdir(parents=True, exist_ok=True)
    d = day.isoformat()
    man: dict = {"date": d, "made_at": _now(), "rules": RULES}
    why = missed.non_session(day)
    if why:
        man["status"] = f"no session ({why})"
    elif d < OTHERS_START:
        man["status"] = f"before the paper's first day ({OTHERS_START})"
    else:
        data = live(day)
        cash, oi = data["cash"], data["oi"]
        sess = sessions(cash)
        if d not in sess:
            man["status"] = "no cash rows for the day yet (the cash file is fetched by the paper run)"
        else:
            man["status"] = "ok"
            c, pc, by_isin = closes(cash)
            keys = sorted(p.stem for p in (paper.pdir() / "decisions").glob("????-??-??.json"))
            journals = missed._journals([k for k in keys if k <= d])
            ex, _ = missed._book()
            by_h = {}
            for h in HORIZONS:
                r = hindsight(d, h, sess, c, pc, by_isin, journals, ex)
                if r is not None:
                    by_h[str(h)] = r
            man["by_h"] = by_h
            man["informed"] = informed(d, sess, oi, nifty_closes(), ananta_calls())
            nc: dict = {}
            for h, x in by_h.items():
                for u in x.get("best", []):
                    if u.get("class") == "NOT_COVERED":
                        e = nc.setdefault(u["situation_key"], {"situation": u["situation"], "examples": []})
                        e["examples"].append({"date": d, "h": int(h), "symbol": u["symbol"], "net": u["net"]})
            man["not_covered"] = nc
            man["journal_sources"] = {k: v[1] for k, v in journals.items()}
    hist = [r for r in read_history() if r["date"] != d]
    row = {k: man.get(k) for k in ("date", "made_at", "rules", "status", "not_covered", "journal_sources")}
    if man["status"] == "ok":
        row["by_h"] = {h: {k: v for k, v in x.items() if k not in ("best", "worst", "ananta_picks")} for h, x in man["by_h"].items()}
        row["informed"] = {"sessions": man["informed"].get("sessions"), "table": man["informed"].get("table")}
        dp = reg / "missed_drafts.jsonl"
        drafts = [json.loads(x) for x in dp.read_text().splitlines() if x.strip()] if dp.exists() else []
        new = pattern_drafts(d, sorted(hist + [row], key=lambda r: r["date"]), drafts)
        with dp.open("a") as fh:
            for x in new:
                fh.write(json.dumps(x, default=str) + "\n")
        man["drafts_written"] = row["drafts_written"] = [x["key"] for x in new]
    hist = sorted(hist + [row], key=lambda r: r["date"])
    write_history(hist)
    man["league"] = league(hist, d)
    paths.manifest_dir().mkdir(parents=True, exist_ok=True)
    (paths.manifest_dir() / f"others_{d}.json").write_text(json.dumps(man, indent=1, default=str))
    (reg / "others_league.md").write_text(page(hist, man["league"], d, man if man["status"] == "ok" else None))
    log(json.dumps({"date": d, "status": man["status"], "league": {h: {k: v for k, v in x.items() if k in ("sessions", "HINDSIGHT", "MARKET", "RANDOM", "ANANTA", "ananta_pct_vs_random", "coverage")}
                                                                       for h, x in man["league"].items() if h != "window_sessions"}, "drafts": man.get("drafts_written", [])}, default=str))
    return man


if __name__ == "__main__":
    paths.ensure()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "evening"
    if cmd != "evening":
        raise SystemExit(__doc__)
    evening(dt.date.fromisoformat(sys.argv[2]) if len(sys.argv) > 2 else None)
