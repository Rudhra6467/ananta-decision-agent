"""Numbers about the practice books that the screens and Ask were missing (Madhav, 26 Oct 2026: "yes to all").

All of it is plain arithmetic on files the paper job already writes; nothing here decides anything.
- split(): closed and open trades counted apart, per family (flag 44: a win rate that counts closed trades only hides the open winners).
- expectancy(): average result per trade, in % and in R, on closed trades and on closed+open (open ones marked to their last close).
- sharpe_like(): needs at least 20 sessions of the book's daily return; otherwise it says how many sessions exist.
- holdings_risk(): how alike the 14 account holdings move (average pairwise correlation of daily returns, last 60 sessions) and how many sit below their 50-day average.
- slippage(): the gap between the study fill and the realistic fill on SP1 scored option trades.
"""
from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path

from india import paths

REF_POLICY = "hold_20d"
MIN_TRADES = 30          # under this a per-trade average is a guess, and is flagged
MIN_SESSIONS = 20        # under this no Sharpe-like ratio is computed
CORR_WINDOW = 60
SMA_WINDOW = 50
MIN_SLIP_TRADES = 20
FAMILY_WORDS = {"BRK": "breakouts", "CTL": "catch-the-leader", "PULL": "pullbacks", "REV": "reversals"}


def _load(p: Path, default=None):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return default


def _jsonl(p: Path) -> list[dict]:
    out = []
    try:
        for line in Path(p).read_text().splitlines():
            if line.strip():
                try:
                    out.append(json.loads(line))
                except ValueError:
                    pass
    except OSError:
        pass
    return out


def _pct(x: float | None, signed: bool = True) -> str:
    if x is None:
        return "n/a"
    return f"{x * 100:+.1f}%" if signed else f"{x * 100:.1f}%"


# --------------------------------------------------------------------------------------------- trades

def trade_rows(state: dict, policy: str = REF_POLICY) -> list[dict]:
    """One row per exec-book trade on the reference exit: its family, whether it is closed, its result (net of costs when closed, to the last close when
    open), and the result in R (result / the trade's stop distance, when that is recorded)."""
    rows = []
    for t in (state.get("trades") or {}).values():
        if t.get("book") != "exec" or t.get("policy") != policy:
            continue
        closed = t.get("status") != "open"
        if closed:
            ret = t.get("net_ret")
        else:
            e, l = t.get("entry_adj"), t.get("last_close_adj")
            ret = (l / e - 1) if e and l else t.get("unrealised_ret")
        if ret is None:
            continue
        rf = t.get("risk_frac")
        rows.append({"family": t.get("campaign"), "closed": closed, "ret": float(ret), "R": (float(ret) / rf) if rf else None, "notional": float(t.get("notional") or 0)})
    return rows


def _agg(rows: list[dict]) -> dict:
    n = len(rows)
    w = sum(1 for r in rows if r["ret"] > 0)
    avg = sum(r["ret"] for r in rows) / n if n else None
    return {"n": n, "winners": w, "avg": avg, "total_pct": sum(r["ret"] for r in rows) if n else 0.0}


def split(rows: list[dict]) -> dict:
    """Closed and open counted apart, per family and overall, with the words line flag 44 asked for."""
    fams = sorted({r["family"] for r in rows})
    out = {"by_family": {}}
    for f in fams + [None]:
        sel = [r for r in rows if f is None or r["family"] == f]
        c = _agg([r for r in sel if r["closed"]])
        o = _agg([r for r in sel if not r["closed"]])
        rec = {"closed": c, "open": o}
        if f:
            out["by_family"][f] = rec
        else:
            out["total"] = rec
    t = out["total"]
    c, o = t["closed"], t["open"]
    out["words"] = (f"win rate counts closed trades only: {c['winners']} of {c['n']} closed won (avg {_pct(c['avg'])}); "
                    f"of {o['n']} open, {o['winners']} are up (avg {_pct(o['avg'])})") if c["n"] or o["n"] else "no trades in the reference book yet"
    out["per_family_words"] = {f: (f"{FAMILY_WORDS.get(f, f)}: {r['closed']['winners']} of {r['closed']['n']} closed won (avg {_pct(r['closed']['avg'])}); "
                                   f"{r['open']['winners']} of {r['open']['n']} open are up (avg {_pct(r['open']['avg'])})") for f, r in out["by_family"].items()}
    return out


def expectancy(rows: list[dict]) -> dict:
    """Average result per trade, in % and in R, per family and overall; on closed trades, and on closed+open (open marked to the last close)."""
    def one(sel: list[dict]) -> dict:
        n = len(sel)
        rs = [r["R"] for r in sel if r["R"] is not None]
        return {"n": n, "avg_pct": (sum(r["ret"] for r in sel) / n) if n else None, "avg_R": (sum(rs) / len(rs)) if rs else None,
                "too_few": n < MIN_TRADES, "flag": f"too few trades (n<{MIN_TRADES})" if n < MIN_TRADES else None}
    res = {"by_family": {}}
    for f in sorted({r["family"] for r in rows}):
        sel = [r for r in rows if r["family"] == f]
        res["by_family"][f] = {"closed": one([r for r in sel if r["closed"]]), "closed_and_open": one(sel)}
    res["overall"] = {"closed": one([r for r in rows if r["closed"]]), "closed_and_open": one(rows)}
    o = res["overall"]
    def say(x: dict) -> str:
        if not x["n"]:
            return "no trades"
        r = f", {x['avg_R']:+.2f}R" if x["avg_R"] is not None else ""
        return f"{_pct(x['avg_pct'])}{r} per trade over {x['n']}" + (f" ({x['flag']})" if x["flag"] else "")
    res["words"] = f"expectancy: closed {say(o['closed'])}; closed and open marked to the last close {say(o['closed_and_open'])}"
    return res


# --------------------------------------------------------------------------------------------- sharpe

def daily_book_returns(marks: list[dict], policy: str = REF_POLICY) -> list[tuple[str, float]]:
    """The reference book's daily return series from marks.jsonl: the day's change in (realised + open unrealised rupees) over the rupees deployed
    (Rs 50,000 a trade, closed + open) at that mark. Several marks in a day: the last one."""
    per_day: dict[str, dict] = {}
    for m in marks:
        if m.get("book") != "exec" or m.get("policy") != policy:
            continue
        d = str(m.get("at", ""))[:10]
        per_day.setdefault(d, {})[m.get("campaign")] = m          # later rows overwrite earlier ones, so the last mark of the day stays
    series, prev = [], None
    for d in sorted(per_day):
        pnl = sum((m.get("realised_inr") or 0) + (m.get("open_unrealised_inr") or 0) for m in per_day[d].values())
        dep = sum(((m.get("open") or 0) + (m.get("closed") or 0)) * 50000.0 for m in per_day[d].values())
        if prev is not None and dep > 0:
            series.append((d, (pnl - prev) / dep))
        prev = pnl
    return series


def sharpe_like(series: list[tuple[str, float]]) -> dict:
    n = len(series)
    if n < MIN_SESSIONS:
        return {"sessions": n, "value": None, "words": f"only {n} sessions: not computed (needs {MIN_SESSIONS})"}
    xs = [x for _, x in series]
    mu = sum(xs) / n
    sd = math.sqrt(sum((x - mu) ** 2 for x in xs) / (n - 1))
    if sd == 0:
        return {"sessions": n, "value": None, "words": f"{n} sessions, but the daily return never moved: not computed"}
    v = mu / sd * math.sqrt(252)
    return {"sessions": n, "value": round(v, 2), "words": f"Sharpe-like ratio {v:.2f} over {n} sessions (daily return mean over its spread, scaled to a year; no risk-free rate; a rough read)"}


# --------------------------------------------------------------------------------------------- holdings

def holdings_risk(prices, symbols: list[str]) -> dict:
    """`prices`: a frame with columns symbol, date, adj_close (as paper.load_adjusted gives). Average pairwise correlation of daily returns over the last
    60 sessions, and how many of the symbols close below their 50-day average."""
    import numpy as np
    import pandas as pd
    df = prices[prices["symbol"].isin(symbols)]
    wide = df.pivot_table(index="date", columns="symbol", values="adj_close").sort_index()
    if wide.empty:
        return {"status": "missing", "words": "no price history for the holdings"}
    rets = wide.pct_change(fill_method=None).tail(CORR_WINDOW)
    use = [c for c in rets.columns if rets[c].notna().sum() >= int(CORR_WINDOW * 2 / 3)]
    c = rets[use].corr(min_periods=int(CORR_WINDOW / 2))
    vals = [c.iloc[i, j] for i in range(len(use)) for j in range(i + 1, len(use)) if pd.notna(c.iloc[i, j])]
    avg = float(np.mean(vals)) if vals else None
    below, have = [], 0
    for s in wide.columns:
        col = wide[s].dropna()
        if len(col) >= SMA_WINDOW:
            have += 1
            if col.iloc[-1] < col.tail(SMA_WINDOW).mean():
                below.append(s)
    if avg is None:
        div = "too little history to say how alike the holdings move"
    elif avg >= 0.5:
        div = f"the holdings move closely together (average correlation {avg:.2f}); owning 14 names is less diversification than it looks"
    elif avg >= 0.3:
        div = f"the holdings move somewhat together (average correlation {avg:.2f}); diversification is partial"
    else:
        div = f"the holdings move fairly independently (average correlation {avg:.2f}); diversification is real"
    share = (len(below) / have) if have else None
    last = str(wide.index.max())[:10]
    return {"status": "ok", "window_sessions": CORR_WINDOW, "symbols_used": len(use), "symbols_asked": len(symbols), "avg_pairwise_corr": None if avg is None else round(avg, 3),
            "below_50d": sorted(below), "below_50d_share": None if share is None else round(share, 3), "below_50d_of": have, "last_session": last,
            "words": div + (f"; {len(below)} of {have} sit below their 50-day average" if have else "") + f" (last close {last})"}


def latest_holdings() -> list[str]:
    led = paths.data_dir() / "bronze" / "ledger"
    for f in sorted(led.glob("*.json"), reverse=True):
        j = _load(f)
        hs = [h["tradingsymbol"] for h in (j or {}).get("holdings") or [] if (h.get("quantity") or 0) > 0 and h.get("tradingsymbol")]
        if hs:
            return hs
    return []


def account_holdings_risk() -> dict:
    syms = latest_holdings()
    if not syms:
        return {"status": "missing", "words": "no account snapshot with holdings yet"}
    try:
        import datetime as dt
        from india import paper
        since = (dt.date.today() - dt.timedelta(days=170)).isoformat()
        df = paper.load_adjusted(since)
        return holdings_risk(df[["symbol", "date", "adj_close"]], syms)
    except Exception as e:  # noqa: BLE001 - said, never hidden
        return {"status": "error", "words": f"could not read the price history ({type(e).__name__}: {str(e)[:120]})"}


# --------------------------------------------------------------------------------------------- slippage

def slippage(book: dict | None) -> dict:
    """SP1 scored trades: study fill minus realistic fill, per option lot, from paper/sp1/book.json (summed over the indices)."""
    by = (book or {}).get("by_index") or {}
    trades = sum(int(v.get("trades") or 0) for v in by.values())
    gap = sum(float(v.get("option_1lot_rs_study_fill") or 0) - float(v.get("option_1lot_rs_realistic_fill") or 0) for v in by.values())
    if trades < 1:
        return {"trades": 0, "avg_rs_per_lot": None, "words": "slippage: not enough scored trades yet"}
    avg = gap / trades
    enough = trades >= MIN_SLIP_TRADES
    return {"trades": trades, "avg_rs_per_lot": round(avg, 0), "enough": enough,
            "words": f"slippage: {trades} scored trade{'s' if trades != 1 else ''} so far, the realistic fill gives up on average Rs {avg:,.0f} per lot against the study fill"
                     + ("" if enough else f" (not enough to trust; needs {MIN_SLIP_TRADES})")}


# --------------------------------------------------------------------------------------------- build

def build(compute_holdings: bool = True) -> dict:
    pdir = paths.data_dir() / "paper"
    st = _load(pdir / "state.json")
    if not st or "trades" not in st:
        return {"status": "missing", "words": "no paper state yet"}
    rows = trade_rows(st)
    ex = expectancy(rows)
    sp = split(rows)
    sh = sharpe_like(daily_book_returns(_jsonl(pdir / "marks.jsonl")))
    hr = account_holdings_risk() if compute_holdings else {"status": "skipped", "words": "not computed"}
    sl = slippage(_load(pdir / "sp1" / "book.json"))
    return {"status": "ok", "reference_exit": REF_POLICY, "closed_vs_open": sp, "expectancy": ex, "sharpe": sh, "holdings": hr, "slippage": sl,
            "words": " | ".join([sp["words"], ex["words"], sh["words"], hr.get("words", ""), sl["words"]])}
