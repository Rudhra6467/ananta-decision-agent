"""Missed movers: each evening, the day's biggest movers in the liquid 250 against what the stock paper book held or fired on (India learning
loop, approved by Madhav 20 Oct 2026; carried over from the crypto loop, where a hit counted the same whatever it made).

  python -m india.missed evening [YYYY-MM-DD]     default: today's date on the Mac (Toronto), the IST session that closed this morning

Run it after the paper engine's evening run (india.paper run), which writes the day's decision, its universe file and the marks.

What it reads
* The day's cash rows through india.sealed.read_review (purpose paper_review: series-EQ rows dated on or after 2026-10-16 only, logged; a start
  before that is refused). Only the day's own row is used: close-to-close (close against the exchange's previous close), open-to-close, the gap,
  and whether the close sat at a price band. Nothing is computed on history here.
* The paper engine's own decision-time file paper/decisions/<date>.universe.json: the liquid universe (liq_rank <= 250, the executed book's
  universe rule) and the derived numbers that describe the day (prior 20-session range, 52-week high and low, RSI and averages as of the close
  before). Days before those files existed are rebuilt by `python -m india.paper universe <date>` and labelled reconstructed.
* The paper book: the decision journals (every candidate, chosen or rejected with the reason), paper/state.json (executed trades and their
  marks) and paper/baseline.parquet (every candidate followed through every exit). There is no separate watch list in the India book; the
  baseline book, which follows every candidate the families produce whether the book took it or not, is the watch.

What it decides, for each of the top 20 gainers and top 20 losers by close-to-close and by open-to-close (one list per side, both measures)
* Caught: an executed paper trade from a research family (BRK, PULL, REV) held it through the day; scored by its paper P&L so far (mean of the
  18 exit policies, the random-exit control left out, with the best and worst), not just counted. A catch by CTL, the random control, is
  shown apart: it is luck by construction. A loser the book held is "held into the fall", scored the same way.
* A miss gets one class:
  (a) a family fired on it in the 20 sessions before the day but the book did not hold it: rejected (the journal's reason) or taken and
      already exited; the baseline book says what holding it would have made so far
  (b) no family was positioned for it: the situation in plain market words (gap up and held, breaking out of a tight base, ...). Every loser
      not held is a (b) or a (c): the India book has no short family
  (c) not tradable that day: the close sat at a price band (locked), or the day traded under a quarter of its 60-session median turnover
  A family that fired on the day's own close is noted: it reacts after the move (entry at the next open), it was not positioned for it.

Pattern rule (fixed 20 Oct 2026, before any result): the same class-(b) situation on 3 or more distinct sessions within 10 sessions writes one
DRAFT entry to india/registrations/missed_drafts.jsonl (at most one per situation per 10 sessions). A draft is a candidate research idea, never a
rule: it reaches paper only by being registered in india/registry.py before it is run, tested on the development and validation years (never
the holdout), and passing the registry bar; only then can it go to the paper book.

Writes manifests/missed_<date>.json (derived numbers only: symbols, returns, classes, P&L; no raw price row) and one line per date in
india/registrations/missed_movers.md (a re-run replaces its line).
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from india import dayplan, paper, paths, sealed

REVIEW_START = "2026-10-16"      # the stock paper's first decision day; the only start this module ever reads from (leakcheck.paper_review)
TOP_N = 20
LOOKBACK_SESSIONS = 20
PATTERN_DAYS, PATTERN_WINDOW = 3, 10
BANDS = (0.02, 0.05, 0.10, 0.20)  # NSE price bands
BAND_TOL = 0.0015
BASE_TIGHT = 0.15                 # a prior 20-session range under 15% of the price is a base
THIN_DAY = 0.25                   # the day's turnover under a quarter of its 60-session median: not tradable at size
RESEARCH = ("BRK", "PULL", "REV")
CONTROL = "CTL"
REG = Path(__file__).parent / "registrations"
REASON_WORDS = {"outside_liq_top": "outside the liquid 250 on the signal day", "cap_reached": "the day's cap for the family was full",
                "open_position": "the book already held it in that family", "reentry_gap": "inside the 14-day re-entry gap",
                "ambiguous_corporate_action": "an unconfirmed split or bonus in the last 200 sessions"}


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def _r(x, n=4):
    return None if x is None or (isinstance(x, float) and not np.isfinite(x)) else round(float(x), n)


# ----------------------------------------------------------------------------------------------------------------------------- sessions
def _holidays() -> set:
    try:
        return dayplan.holidays(refresh=False)
    except Exception:
        return set()


def sessions_until(day: dt.date, n: int) -> list[dt.date]:
    """The last n NSE sessions on or before `day`: weekdays that are not NSE holidays, with the calendar's own verdict where it has one."""
    hol = _holidays()
    cal = {}
    p = paths.data_dir() / "silver/calendar/calendar.parquet"
    if p.exists():
        c = pd.read_parquet(p, columns=["date", "is_trading_day"])
        cal = dict(zip(pd.to_datetime(c["date"]).dt.date, c["is_trading_day"].astype(bool)))
    out, d = [], day
    while len(out) < n and d > day - dt.timedelta(days=n * 3 + 30):
        if cal.get(d, d.weekday() < 5 and d not in hol):
            out.append(d)
        d -= dt.timedelta(days=1)
    return sorted(out)


def non_session(day: dt.date) -> str | None:
    if day in sessions_until(day, 1):
        return None
    return "weekend" if day.weekday() >= 5 else "NSE holiday"


# ----------------------------------------------------------------------------------------------------------------------------- inputs
def day_rows(day: dt.date) -> pd.DataFrame:
    rows = sealed.read_review("paper_review", REVIEW_START, until=day.isoformat())
    rows["date"] = pd.to_datetime(rows["date"]).dt.date
    return rows[rows["date"] == day].copy()


def load_universe(day: dt.date) -> dict | None:
    p = paper.pdir() / "decisions" / f"{day.isoformat()}.universe.json"
    return json.loads(p.read_text()) if p.exists() else None


def _book() -> tuple[pd.DataFrame, pd.DataFrame]:
    sp = paper.pdir() / "state.json"
    ex = pd.DataFrame(json.loads(sp.read_text())["trades"].values()) if sp.exists() else pd.DataFrame()
    bp = paper.pdir() / "baseline.parquet"
    base = pd.read_parquet(bp) if bp.exists() else pd.DataFrame()
    return ex, base


def _journals(keys: list[str]) -> dict[str, tuple[list, str]]:
    out = {}
    for k in keys:
        try:
            out[k] = paper.journal_for(k)
        except FileNotFoundError:
            out[k] = (None, "missing")
    return out


# ----------------------------------------------------------------------------------------------------------------------------- movers
def movers(rows: pd.DataFrame, uni: list[dict], top_n: int = TOP_N) -> pd.DataFrame:
    """The day's movers in the universe: one row per (stock, side), with the lists it is on (cc = close-to-close, oc = open-to-close)."""
    u = pd.DataFrame(uni)
    if u.empty or rows.empty:
        return pd.DataFrame()
    r = rows.sort_values("turnover", ascending=False).drop_duplicates("symbol").copy()
    if "isin" not in u:
        u["isin"] = None
    ui = u[u["isin"].notna()]
    m = ui.merge(r[r["isin"].notna()], on="isin", how="inner", suffixes=("", "_row"))
    rest = u[~u["sid"].isin(set(m["sid"]))]
    if len(rest):
        m = pd.concat([m, rest.merge(r.drop(columns=["isin"]), on="symbol", how="inner", suffixes=("", "_row"))], ignore_index=True)
    m = m.drop_duplicates("sid")
    m = m[(m["prev_close"] > 0) & (m["open"] > 0)].copy()
    m["cc_raw"] = m["close"] / m["prev_close"] - 1
    m["gap_raw"] = m["open"] / m["prev_close"] - 1
    m["oc"] = m["close"] / m["open"] - 1
    # a corporate action on the day: the exchange's previous close and the factors table disagree by more than 1%: use the adjusted figures
    ca = m["ret_1"].notna() & ((m["cc_raw"] - m["ret_1"]).abs() > 0.01)
    m["ca_day"] = ca
    m["cc"] = np.where(ca, m["ret_1"], m["cc_raw"])
    m["gapx"] = np.where(ca & m["gap"].notna(), m["gap"], m["gap_raw"])
    out = []
    for side, sign in (("up", 1), ("down", -1)):
        lists: dict = {}
        for meas in ("cc", "oc"):
            s = m[np.sign(m[meas]) == sign].sort_values(meas, ascending=(sign < 0), kind="mergesort").head(top_n)
            for sid in s["sid"]:
                lists.setdefault(sid, []).append(meas)
        for _, x in m[m["sid"].isin(set(lists))].iterrows():
            band = None
            if (sign > 0 and x["close"] >= x["high"]) or (sign < 0 and x["close"] <= x["low"]):
                band = next((b for b in BANDS if abs(abs(x["cc_raw"]) - b) <= BAND_TOL and np.sign(x["cc_raw"]) == sign), None)
            out.append({**x.to_dict(), "side": side, "lists": lists[x["sid"]], "band": band, "no_range": bool(x["high"] <= x["low"]),
                        "thin": bool(x["turnover_vs_med60"] is not None and x["turnover_vs_med60"] == x["turnover_vs_med60"] and x["turnover_vs_med60"] < THIN_DAY)})
    return pd.DataFrame(out)


def situation(m: dict) -> tuple[str, str]:
    """(key, plain words) for a move: how the day opened and traded, and the structure it moved out of (from the universe file's numbers)."""
    up = m["side"] == "up"
    g, oc = m.get("gapx"), m.get("oc")
    g = 0.0 if g is None or g != g else g
    if up:
        if g >= 0.02:
            ok, ow = ("gap_held", f"gapped up {g:+.1%} and held") if oc >= 0 else ("gap_faded", f"gapped up {g:+.1%} then faded {oc:+.1%}")
        elif oc >= 0.02:
            ok, ow = "intraday_run", f"opened near flat and ran {oc:+.1%}"
        else:
            ok, ow = "steady", "rose through the day"
    else:
        if g <= -0.02:
            ok, ow = ("gap_down_held", f"gapped down {g:+.1%} and stayed down") if oc <= 0 else ("gap_down_recovered", f"gapped down {g:+.1%} then recovered {oc:+.1%}")
        elif oc <= -0.02:
            ok, ow = "intraday_selloff", f"opened near flat and sold off {oc:+.1%}"
        else:
            ok, ow = "steady", "fell through the day"
    v = lambda k: m.get(k) if m.get(k) is not None and m.get(k) == m.get(k) else None
    rsi, d200, d20, r20, base = v("rsi14_prev"), v("dist_sma200_prev"), v("dist_sma20_prev"), v("ret_20_prev"), v("base20_range")
    if up:
        if v("new_high_250"):
            sk, sw = "new_52w_high", "to a 52-week high"
        elif v("breakout20") and base is not None and base <= BASE_TIGHT:
            sk, sw = "breakout_base", f"breaking out of a tight 20-day base ({base:.0%} wide)"
        elif v("breakout20"):
            sk, sw = "breakout_range", "breaking above its 20-day range"
        elif rsi is not None and rsi < 30:
            sk, sw = "oversold_bounce", f"bouncing from oversold (RSI {rsi:.0f})"
        elif d200 is not None and d200 > 0 and d20 is not None and d20 < -0.05:
            sk, sw = "pullback_rebound", "rebounding from a pullback in an uptrend"
        elif r20 is not None and r20 > 0.20:
            sk, sw = "run_extension", f"extending a run of {r20:+.0%} in 20 sessions"
        elif d200 is not None and d200 < 0:
            sk, sw = "downtrend_rise", "rising while below its 200-day average"
        else:
            sk, sw = "inside_range", "inside its range in an uptrend"
    else:
        if v("new_low_250"):
            sk, sw = "new_52w_low", "to a 52-week low"
        elif v("breakdown20"):
            sk, sw = "breakdown_range", "breaking below its 20-day range"
        elif rsi is not None and rsi > 70:
            sk, sw = "overbought_drop", f"dropping from overbought (RSI {rsi:.0f})"
        elif r20 is not None and r20 > 0.20:
            sk, sw = "run_reversal", f"giving back a run of {r20:+.0%} in 20 sessions"
        elif d200 is not None and d200 > 0:
            sk, sw = "uptrend_pullback", "pulling back in an uptrend"
        elif d200 is not None and d200 < 0:
            sk, sw = "downtrend_fall", "falling further below its 200-day average"
        else:
            sk, sw = "inside_range", "inside its range"
    vr = v("vol_ratio20")
    words = f"{ow}, {sw}" + (f", on {vr:.1f}x its 20-day volume" if vr is not None and vr >= 2 else "")
    return f"{m['side']}:{sk}:{ok}", words


# ----------------------------------------------------------------------------------------------------------------------------- the book
def _held(df: pd.DataFrame, sid: str, day: dt.date) -> pd.DataFrame:
    if df.empty or "entry_date" not in df:
        return df.iloc[0:0]
    d = day.isoformat()
    x = df[(df["sid"] == sid) & df["status"].isin(["open", "closed"]) & df["entry_date"].notna()]
    ed = x["exit_date"] if "exit_date" in x else pd.Series(None, index=x.index, dtype=object)
    return x[(x["entry_date"] <= d) & ((x["status"] == "open") | (ed.fillna("") >= d))]


def pnl(df: pd.DataFrame) -> dict:
    """Paper P&L so far over the exit policies (random_exit left out): closed trades at their net, open trades at their mark."""
    x = df[df["policy"] != "random_exit"]
    if x.empty:
        return {}
    notional = x["notional"].fillna(50_000.0) if "notional" in x else pd.Series(50_000.0, index=x.index)
    ur = x["unrealised_ret"].fillna(0.0) if "unrealised_ret" in x else pd.Series(0.0, index=x.index)
    net = x["net_inr"] if "net_inr" in x else pd.Series(np.nan, index=x.index)
    v = np.where(x["status"] == "closed", net.fillna(0.0), ur * notional)
    s = pd.Series(v, index=x["policy"].values)
    return {"policies": int(len(s)), "open": int((x["status"] == "open").sum()), "closed": int((x["status"] == "closed").sum()),
            "mean_inr": round(float(s.mean()), 0), "best_inr": round(float(s.max()), 0), "best": str(s.idxmax()), "worst_inr": round(float(s.min()), 0),
            "worst": str(s.idxmin()), "mean_ret": _r(float(s.mean()) / float(notional.mean())),
            "marks_through": str(x["last_date"].dropna().max()) if "last_date" in x and x["last_date"].notna().any() else None}


def _groups(held: pd.DataFrame, day: dt.date, move: dict) -> list[dict]:
    out = []
    for (sd, camp), g in held.groupby(["signal_date", "campaign"]):
        entered_on_day = bool((g["entry_date"] == day.isoformat()).all())
        day_ret = move["oc"] if entered_on_day else move["cc"]
        notional = float(g["notional"].fillna(50_000.0).mean()) if "notional" in g else 50_000.0
        out.append({"signal_date": sd, "family": camp, "entered_on_day": entered_on_day, "pnl_so_far": pnl(g),
                    "day_move_inr": round(day_ret * notional, 0), "exited_on_day": int((g.get("exit_date", pd.Series(dtype=object)) == day.isoformat()).sum())})
    return out


def classify(m: dict, day: dt.date, window: list[str], journals: dict, ex: pd.DataFrame, base: pd.DataFrame) -> dict:
    sid, up = m["sid"], m["side"] == "up"
    fires = []
    for k in window:
        j, src = journals.get(k, (None, "missing"))
        for c in j or []:
            if c["sid"] == sid:
                fires.append({"date": k, "family": c["campaign"], "status": c["status"], "reason": c.get("reason"), "journal": src})
    j_day, _ = journals.get(day.isoformat(), (None, "missing"))
    same_day = sorted({c["campaign"] for c in (j_day or []) if c["sid"] == sid})
    held = _held(ex, sid, day)
    move = {"cc": m["cc"], "oc": m["oc"]}
    rec = {"symbol": m["symbol"], "sid": sid, "side": m["side"], "lists": m["lists"], "liq_rank": int(m["liq_rank"]),
           "cc": _r(m["cc"]), "oc": _r(m["oc"]), "gap": _r(m["gapx"]), "corporate_action_on_day": bool(m["ca_day"]),
           "fired_in_window": fires, "fired_on_day_close": same_day}
    key, words = situation(m)
    rec["situation_key"], rec["situation"] = key, words
    research_held = held[held["campaign"].isin(RESEARCH)] if len(held) else held
    if len(held):
        rec["held"] = _groups(held, day, move)
    if up and len(research_held):
        rec["status"], rec["class"] = "caught", None
        return rec
    if up and len(held):
        rec["status"], rec["class"] = "caught_by_control", None
        rec["why"] = "held only by CTL, the random control draw: luck by construction"
        return rec
    if not up and len(held):
        rec["status"], rec["class"] = "held_into_fall", None
        return rec
    rec["status"] = "missed"
    research_fires = [f for f in fires if f["family"] in RESEARCH]
    if up and research_fires:
        f = research_fires[-1]
        if f["status"] == "rejected":
            why = f"{f['family']} fired on {f['date']}; rejected: {REASON_WORDS.get(f['reason'], f['reason'])}"
        else:
            tk = ex[(ex["sid"] == sid) & (ex["signal_date"] == f["date"]) & (ex["campaign"] == f["family"])] if len(ex) else ex
            if len(tk) and (tk["status"] == "closed").all():
                why = (f"{f['family']} fired on {f['date']} and the book took it; every exit had closed before the day "
                       f"(last exit {tk['exit_date'].max()}; {', '.join(sorted(tk['exit_reason'].dropna().unique())[:4])})")
            elif len(tk):
                why = f"{f['family']} fired on {f['date']} and the book took it; the trade was {', '.join(sorted(tk['status'].unique()))} ({tk['note'].dropna().iloc[0] if 'note' in tk and tk['note'].notna().any() else 'no fill'})"
            else:
                why = f"{f['family']} fired on {f['date']} and was chosen; no executed trade on record"
        rec["class"], rec["why"] = "a", why
        bl = _held(base, sid, day) if len(base) else base
        if len(bl):
            bl = bl[bl["campaign"].isin(RESEARCH) & bl["signal_date"].isin({x["date"] for x in research_fires})]
            if len(bl):
                rec["baseline_would_have"] = _groups(bl, day, move)
        return rec
    band = m.get("band")
    band = band if band is not None and band == band else None
    if band is not None or m["no_range"]:
        rec["class"] = "c"
        rec["why"] = (f"closed locked at the {band:.0%} price band" if band is not None else "no range all day (locked)")
        return rec
    if m["thin"]:
        rec["class"], rec["why"] = "c", f"thin day: turnover {m['turnover_vs_med60']:.0%} of its 60-session median"
        return rec
    rec["class"] = "b"
    rec["why"] = ("no family was positioned for it" if up else "no short family: the India book is long only") + (
        f"; {'/'.join(same_day)} fired on the day's close (it reacts after the move, entry at the next open)" if same_day else "")
    if not up and research_fires:
        rec["why"] += f"; a long family had fired in the window ({', '.join(sorted({f['family'] + ' ' + f['date'] for f in research_fires}))})"
    return rec


# ----------------------------------------------------------------------------------------------------------------------------- pattern rule
def pattern_drafts(day: str, window: list[str], b_by_day: dict[str, dict[str, dict]], drafts: list[dict]) -> list[dict]:
    """The fixed rule: a class-(b) situation seen on PATTERN_DAYS or more distinct sessions of the last PATTERN_WINDOW sessions (window, ending on
    `day`) and not already drafted inside that window. b_by_day: {session: {situation_key: {"situation": words, "examples": [...]}}}."""
    win = sorted(window)[-PATTERN_WINDOW:]
    seen: dict[str, list[str]] = {}
    for d in win:
        for key in (b_by_day.get(d) or {}):
            seen.setdefault(key, []).append(d)
    out = []
    for key, days in sorted(seen.items()):
        if len(days) < PATTERN_DAYS:
            continue
        if any(x.get("key") == key and x.get("written_for") in win for x in drafts):
            continue
        ex = [e for d in days for e in b_by_day[d][key].get("examples", [])][:12]
        words = b_by_day[days[-1]][key]["situation"]
        side = key.split(":")[0]
        out.append({"status": "DRAFT", "kind": "missed-movers pattern", "key": key, "side": side, "situation_example": words, "days": days,
                    "examples": ex, "written_for": day, "written_at": _now(),
                    "rule": f"the same class-(b) situation on {PATTERN_DAYS}+ sessions within {PATTERN_WINDOW} (fixed 20 Oct 2026)",
                    "question": (f"Is there an entry rule, known before the move, that would have been positioned for {'rises' if side == 'up' else 'falls'} "
                                 f"of this kind ({key.split(':', 1)[1].replace(':', ', ').replace('_', ' ')})? To be tested on the development and validation "
                                 "years only (2000-2023)."),
                    "note": "a candidate research idea, never a rule: it reaches paper only after it is registered in india/registry.py before it is run "
                            "and passes the registry bar"})
    return out


def _b_by_day(window: list[str], today: dict | None) -> dict:
    out = {}
    for d in window:
        if today is not None and d == today["date"]:
            man = today
        else:
            p = paths.manifest_dir() / f"missed_{d}.json"
            if not p.exists():
                continue
            man = json.loads(p.read_text())
        for r in man.get("movers", []):
            if r.get("class") == "b":
                e = out.setdefault(d, {}).setdefault(r["situation_key"], {"situation": r["situation"], "examples": []})
                e["examples"].append({"date": d, "symbol": r["symbol"], "cc": r["cc"], "oc": r["oc"]})
    return out


# ----------------------------------------------------------------------------------------------------------------------------- outputs
def _summary(rows: list[dict]) -> dict:
    up = [r for r in rows if r["side"] == "up"]
    dn = [r for r in rows if r["side"] == "down"]
    caught = [r for r in up if r["status"] == "caught"]
    ctl = [r for r in up if r["status"] == "caught_by_control"]
    hif = [r for r in dn if r["status"] == "held_into_fall"]

    def so_far(rs: list[dict], fams: tuple) -> float:
        return round(sum(g["pnl_so_far"].get("mean_inr", 0) for r in rs for g in r.get("held", []) if g["family"] in fams), 0)

    def captured(r: dict) -> float:   # the part of the close-to-close move a research position was there for (entered at the open: open-to-close)
        gs = [g for g in r.get("held", []) if g["family"] in RESEARCH]
        return r["cc"] if any(not g["entered_on_day"] for g in gs) else r["oc"]

    top_cc = [r for r in up if "cc" in r["lists"]]
    tot = sum(r["cc"] for r in top_cc)
    cap = sum(captured(r) for r in caught if "cc" in r["lists"])
    bsit: dict = {}
    for r in rows:
        if r.get("class") == "b":
            bsit.setdefault(r["situation_key"], []).append(r["symbol"])
    count = lambda rs, c: sum(1 for r in rs if r.get("class") == c)
    return {"up": {"movers": len(up), "caught": len(caught), "caught_by_control": len(ctl), "a": count(up, "a"), "b": count(up, "b"), "c": count(up, "c"),
                   "catches_pnl_so_far_inr": so_far(caught, RESEARCH), "control_pnl_so_far_inr": so_far(ctl, (CONTROL,)),
                   "share_of_top20_cc_move_caught": _r(cap / tot) if tot else None},
            "down": {"movers": len(dn), "held_into_fall": len(hif), "held_pnl_so_far_inr": so_far(hif, RESEARCH + (CONTROL,)), "b": count(dn, "b"), "c": count(dn, "c")},
            "b_situations": {k: v for k, v in sorted(bsit.items(), key=lambda kv: -len(kv[1]))}}


def _inr(x) -> str:
    return f"Rs {x:+,.0f}"


def md_line(man: dict) -> str:
    d = man["date"]
    if man["status"] != "ok":
        return f"| {d} | {man['status']} | | | | | |"
    s = man["summary"]
    u, w = s["up"], s["down"]
    words = {}
    for r in man["movers"]:
        if r.get("class") == "b":
            words.setdefault(r["situation_key"], r["situation"])
    top = "; ".join(f"{k.split(':', 1)[1].replace(':', ', ').replace('_', ' ')} x{len(v)}" for k, v in list(s["b_situations"].items())[:3])
    share = f", {u['share_of_top20_cc_move_caught']:.1%} of the top-20 move" if u["share_of_top20_cc_move_caught"] is not None else ""
    return (f"| {d} | {u['movers']} up | caught {u['caught']} ({_inr(u['catches_pnl_so_far_inr'])} so far{share}); control {u['caught_by_control']} "
            f"({_inr(u['control_pnl_so_far_inr'])}) | a {u['a']} / b {u['b']} / c {u['c']} | {w['movers']} down: held {w['held_into_fall']} "
            f"({_inr(w['held_pnl_so_far_inr'])}) / b {w['b']} / c {w['c']} | {top} | {len(man.get('drafts_written', []))} |")


MD_HEAD = """# Missed movers (india.missed, each evening after the paper run)

One line per session: the day's top 20 gainers and losers in the liquid 250 (close-to-close and open-to-close lists together), against what the
stock paper book held or fired on in the 20 sessions before. A catch is scored by its paper P&L so far (mean of the 18 exits); CTL, the random
control, is counted apart. Misses: (a) a family fired, the book did not hold it; (b) no family was positioned (situation in plain words; every
loser not held is here or in c, the book being long only); (c) not tradable (locked at a band, or a thin day). Manifest per day:
manifests/missed_<date>.json. Drafts from the pattern rule (3+ sessions in 10): missed_drafts.jsonl, research ideas only.

| date | gainers | catches (P&L so far) | gainer misses | losers | top (b) situations | drafts |
|---|---|---|---|---|---|---|
"""


def write_md(man: dict, reg: Path | None = None) -> str:
    reg = reg or REG
    p = reg / "missed_movers.md"
    line = md_line(man)
    text = p.read_text() if p.exists() else MD_HEAD
    lines = [x for x in text.splitlines() if not x.startswith(f"| {man['date']} |")]
    body = [x for x in lines if x.startswith("| 20")]
    head = [x for x in lines if not x.startswith("| 20")]
    body = sorted(body + [line])
    p.write_text("\n".join(head + body) + "\n")
    return line


def evening(day: dt.date | None = None, reg: Path | None = None, log=print) -> dict:
    day = day or dt.date.today()
    reg = reg or REG
    reg.mkdir(parents=True, exist_ok=True)
    man: dict = {"date": day.isoformat(), "made_at": _now(), "rules": "missed-v1-2026-10-20"}
    why = non_session(day)
    if why:
        man["status"] = f"no session ({why})"
    elif day < dt.date.fromisoformat(REVIEW_START):
        man["status"] = f"before the paper's first day ({REVIEW_START})"
    else:
        uni = load_universe(day)
        rows = day_rows(day)
        if rows.empty:
            man["status"] = "no cash rows for the day yet (the cash file is fetched by the paper run)"
        elif uni is None:
            man["status"] = f"no universe file for the day (paper run lost?): python -m india.paper universe {day}"
        else:
            man["status"] = "ok"
            man["universe"] = {"source": uni["source"], "n": uni["n"], "liq_top": uni["liq_top"]}
            mv = movers(rows, uni["rows"])
            sess = [d.isoformat() for d in sessions_until(day - dt.timedelta(days=1), LOOKBACK_SESSIONS)]
            keys = sorted(p.stem for p in (paper.pdir() / "decisions").glob("????-??-??.json"))
            window = [k for k in keys if k in set(sess)]
            journals = _journals(window + ([day.isoformat()] if day.isoformat() in keys else []))
            ex, base = _book()
            res = [classify(r, day, window, journals, ex, base) for r in mv.to_dict("records")]
            res.sort(key=lambda r: (r["side"] != "up", -abs(r["cc"] or 0)))
            man.update({"window_decisions": window, "decision_on_day": day.isoformat() in keys,
                        "journal_sources": {k: v[1] for k, v in journals.items()}, "movers": res, "summary": _summary(res)})
    if man["status"] == "ok":
        sw = [d.isoformat() for d in sessions_until(day, PATTERN_WINDOW)]
        dp = reg / "missed_drafts.jsonl"
        drafts = [json.loads(x) for x in dp.read_text().splitlines() if x.strip()] if dp.exists() else []
        new = pattern_drafts(day.isoformat(), sw, _b_by_day(sw, man), drafts)
        with dp.open("a") as fh:
            for x in new:
                fh.write(json.dumps(x, default=str) + "\n")
        man["drafts_written"] = [x["key"] for x in new]
    man["md_line"] = md_line(man)
    paths.manifest_dir().mkdir(parents=True, exist_ok=True)
    (paths.manifest_dir() / f"missed_{day.isoformat()}.json").write_text(json.dumps(man, indent=1, default=str))
    write_md(man, reg)
    log(man["md_line"])
    return man


if __name__ == "__main__":
    paths.ensure()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "evening"
    if cmd != "evening":
        raise SystemExit(__doc__)
    d = dt.date.fromisoformat(sys.argv[2]) if len(sys.argv) > 2 else None
    r = evening(d)
    print(json.dumps({k: r.get(k) for k in ("date", "status", "summary", "drafts_written")}, indent=1, default=str))
