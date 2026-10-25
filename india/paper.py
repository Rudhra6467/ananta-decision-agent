"""The paper engine for Indian stocks: everything on, every exit rule tracked side by side, real prices, paper money, full Indian costs.

  python -m india.paper run          fetch the latest cash file, settle, decide today's, follow the baseline book, write the marks
  python -m india.paper report       what the executed book looks like now
  python -m india.paper compare      executed book against the unfiltered baseline, per campaign and exit policy
  python -m india.paper settle | decide | baseline | marks      one step each
  python -m india.paper reconstruct 2026-10-16                  rebuild the candidate journal for a decision written before journals existed (labelled)
  python -m india.paper universe 2026-10-16                     rebuild the liquid-universe file for a decision written before those files existed (labelled)

What it does (the point is to see how Ananta works in the real market and where it lacks, not to size anything):
* Three campaigns, defined before any result was seen (the same entry sets as study E02): BRK (20-day breakout on 1.5x volume, above the 200-day average),
  PULL (uptrend pulled back 5% under the 20-day average) and CTL (a seeded random draw of liquid stocks: the control, so the entries can be told from luck).
* Two books. The BASELINE book follows every candidate the entry rules produce anywhere in the universe, uncapped and unfiltered. The EXECUTED book is the
  subset a trader with limits would take: the most liquid stocks (liq_top), at most N signals a day per campaign, one open position per stock per campaign,
  no re-entry within reentry_days. Every candidate is written to the decision journal with status chosen or rejected and the reason, so any filter can be
  scored against the baseline later. Limits and sizing live in india/paper_config.json; its sha is written into every decision and trade.
* Every candidate becomes one paper trade per exit policy (18 policies plus a random-exit control, exitlab.DEFAULT_POLICIES), each with the same 2 ATR initial
  stop, delivery costs and the labelled spread estimate. All policies see the same entry, so the difference between them is the exit.
* A decision file is written after the close of day T and before the open of T+1 (decided_at, data_through, a hash over signals, journal and config).
  It is never rewritten. The fill is the official open of T+1, read only at settle time. Close-based exits fill at the next open; stops and targets fill
  inside the bar at the level, or at the open if the bar gaps through it.
* Market context at decision time (Nifty 50 and India VIX against their averages, breadth of the liquid universe) is recorded with each decision. If an index
  row for the decision date is missing the context says so; nothing is substituted.
* Prices are the exchange's raw file adjusted with the corporate-action factors table (splits and bonuses), the same as the lab.
* Leak rule: the decision for day T uses rows dated T and earlier only. A test (india/leakcheck.py) edits every later row and checks the decision does not change.
* The only sealed-year reads are the indicator lookback and the index context, through india.sealed; no performance is computed on holdout rows by research code.
* With each decision the liquid universe of that day (liq_top names) is written beside it, derived numbers only (ranks, the day's bar against the
  sessions before it): the missed-movers review (india/missed.py, 20 Oct 2026) takes its universe and every indicator from this file, so that
  review computes nothing on history itself.
Files: paper/decisions/<data date>.json, <data date>.universe.json, paper/state.json (executed trades), paper/events.jsonl, paper/marks.jsonl,
paper/baseline.parquet (every candidate x policy).
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import random
import sys

import numpy as np
import pandas as pd

from india import backfill, catalog, costs, exitlab, paths, sealed, settings, silver

LOOKBACK_CAL_DAYS = 400
RULES_VERSION = "paper-v1.2-2026-10-18"   # v1.1: funds/ETFs out, applied corporate-action factors only; v1.2: REV campaign (RSI(14) under 30, from P01 VALIDATED)
JOURNAL_VERSION = 2                       # v2 adds the candidate journal, market context, config sha
POLICIES = {p.name: p for p in exitlab.DEFAULT_POLICIES}
POLICIES["random_exit"] = exitlab.Policy("random_exit", "random")
CHOSEN_FIELDS = ("campaign", "sid", "symbol", "atr14", "close", "raw_close", "liq_rank", "vol_ratio20", "dist_sma20", "dist_sma200")
EXTRA_FIELDS = ("dist_sma50", "ret_20", "ret_60", "rv20", "med60_turnover", "breakout20", "ca_ambiguous_200", "rsi14")


def pdir():
    d = paths.data_dir() / "paper"
    (d / "decisions").mkdir(parents=True, exist_ok=True)
    return d


def _state() -> dict:
    p = pdir() / "state.json"
    return json.loads(p.read_text()) if p.exists() else {"trades": {}, "decisions": {}, "version": RULES_VERSION}


def _save(state: dict) -> None:
    tmp = pdir() / "state.json.tmp"
    tmp.write_text(json.dumps(state, indent=1, default=str))
    tmp.replace(pdir() / "state.json")


def _event(ev: dict) -> None:
    with (pdir() / "events.jsonl").open("a") as fh:
        fh.write(json.dumps(ev, default=str) + "\n")


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


# ----------------------------------------------------------------------------------------------- data

def load_adjusted(since: str | None = None, until: str | None = None, raw: pd.DataFrame | None = None) -> pd.DataFrame:
    """Raw EQ rows adjusted with the factors table. Zero prices (no trade that day) take the close. `until` cuts rows after that date (used by the leak test)."""
    since = since or (dt.date.today() - dt.timedelta(days=LOOKBACK_CAL_DAYS)).isoformat()
    df = raw.copy() if raw is not None else sealed.read_cm("paper_lookback", since)
    df["date"] = pd.to_datetime(df["date"])
    if until:
        df = df[df["date"] <= pd.Timestamp(until)]
    for c in ("open", "high", "low"):
        df[c] = df[c].where(df[c] > 0, df["close"])
    fx = pd.read_parquet(paths.data_dir() / "silver/corporate_actions/factors.parquet")
    amb = fx[fx.get("inside", False) & ~fx.get("apply", True)] if "apply" in fx else fx.iloc[0:0]
    fx = fx[fx["factor"].notna() & (fx["factor"] > 0) & (fx["apply"] if "apply" in fx else True)][["symbol", "ex_date", "factor"]]
    df = df.sort_values(["symbol", "date"]).reset_index(drop=True)
    ent = pd.read_parquet(paths.data_dir() / "silver/security_master/names.parquet", columns=["isin", "entity"]).drop_duplicates("isin")
    df = df.merge(ent, on="isin", how="left")
    df["sid"] = df["entity"].fillna(df["symbol"])
    df = df.sort_values(["symbol", "date"]).reset_index(drop=True)
    cum = np.ones(len(df))
    by = {s: g for s, g in fx.groupby("symbol")}
    syms = df["symbol"].values
    dates = df["date"].values
    bounds = np.r_[np.flatnonzero(syms[1:] != syms[:-1]) + 1, len(df)]
    first = 0
    for end in bounds:
        s = syms[first]
        if s in by:
            for ex, f in zip(by[s]["ex_date"].values, by[s]["factor"].values):
                cum[first:end] *= np.where(dates[first:end] < ex, f, 1.0)
        first = end
    for c in ("open", "high", "low", "close"):
        df["adj_" + c] = df[c] / cum
    df["cum_factor"] = cum
    df = df.sort_values(["sid", "date", "turnover"], ascending=[True, True, False]).drop_duplicates(["sid", "date"]).reset_index(drop=True)
    # mutual-fund units and ETFs (ISIN INF...) trade in series EQ but are not stocks: flagged, kept out of the stock universe in features()
    df["is_fund"] = df["isin"].fillna("").str.startswith("INF")
    amb_dates = {(r.symbol, pd.Timestamp(r.ex_date)) for r in amb.itertuples()}
    df["ca_ambiguous"] = [((s, d) in amb_dates) for s, d in zip(df["symbol"], df["date"])] if amb_dates else False
    return df


def _atr14(g: pd.DataFrame) -> float:
    h, l, c = (g["adj_" + k].values for k in ("high", "low", "close"))
    pc = np.r_[np.nan, c[:-1]]
    tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    tr[0] = h[0] - l[0]
    return float(np.nanmean(tr[-14:]))


def _rsi14(c: np.ndarray) -> float:
    """Wilder RSI(14) on adjusted closes, the same recursion as the lab (india.studies2._indicators: ewm alpha 1/14, adjust False, min 14); started from
    the lookback's first bar, so a small start-up difference remains early in a 400-day window and has died out by the last bar."""
    if len(c) < 15:
        return float("nan")
    d = np.diff(c)
    au = pd.Series(np.maximum(d, 0.0)).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean().iloc[-1]
    ad = pd.Series(np.maximum(-d, 0.0)).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean().iloc[-1]
    return float(100 - 100 / (1 + au / ad)) if ad > 0 else 100.0


def features(df: pd.DataFrame, asof: pd.Timestamp, min_price: float = 10) -> pd.DataFrame:
    """One row per stock on `asof` with 126+ sessions of history, from rows dated on or before it. Mirrors india.lab (checked by leakcheck.parity)."""
    df = df[df["date"] <= asof]
    if "is_fund" in df:
        df = df[~df["is_fund"]]
    out = []
    for sid, g in df.groupby("sid", sort=False):
        if g["date"].iloc[-1] != asof or len(g) < 126:
            continue
        o, h, l, c = (g["adj_" + k].values for k in ("open", "high", "low", "close"))
        v = g["volume"].values.astype(float)
        t = g["turnover"].values.astype(float)
        pc = np.r_[np.nan, c[:-1]]
        tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
        tr[0] = h[0] - l[0]
        out.append({"sid": sid, "symbol": g["symbol"].iloc[-1], "close": c[-1], "raw_close": g["close"].iloc[-1], "atr14": float(np.nanmean(tr[-14:])), "med60_turnover": float(np.median(t[-60:])),
                    "vol_ratio20": float(v[-1] / np.mean(v[-21:-1])) if np.mean(v[-21:-1]) > 0 else np.nan,
                    "dist_sma20": float(c[-1] / np.mean(c[-20:]) - 1), "dist_sma50": float(c[-1] / np.mean(c[-50:]) - 1), "dist_sma200": float(c[-1] / np.mean(c[-200:]) - 1),
                    "breakout20": bool(c[-1] > np.max(h[-21:-1])), "ret_20": float(c[-1] / c[-21] - 1), "ret_60": float(c[-1] / c[-61] - 1),
                    "rv20": float(np.std(np.diff(c[-21:]) / c[-21:-1], ddof=1)),
                    "ca_ambiguous_200": bool(g["ca_ambiguous"].iloc[-200:].any()) if "ca_ambiguous" in g else False, "rsi14": _rsi14(c)})
    f = pd.DataFrame(out)
    if f.empty:
        return f
    f = f[f["raw_close"] > min_price].copy()
    f["liq_rank"] = f["med60_turnover"].rank(ascending=False, method="min").astype(int)
    return f.sort_values("liq_rank").reset_index(drop=True)


def signals(f: pd.DataFrame, asof: pd.Timestamp, s: dict | None = None) -> dict[str, pd.DataFrame]:
    """Candidates per campaign across the whole universe, in the executed book's order of preference. BRK and PULL are not limited to liquid stocks here:
    the liquidity limit is applied (and recorded as a rejection reason) in decide(). CTL is drawn from the liquid universe because it is the control for the executed book."""
    s = s or settings.load()["stock"]
    ok = f[f["atr14"].notna()]
    liq = ok[ok["liq_rank"] <= s["liq_top"]]
    brk = ok[ok["breakout20"] & (ok["vol_ratio20"] > 1.5) & (ok["dist_sma200"] > 0)].sort_values("vol_ratio20", ascending=False, kind="mergesort")
    pull = ok[(ok["dist_sma200"] > 0) & (ok["dist_sma20"] < -0.05)].sort_values("dist_sma20", kind="mergesort")
    rng = random.Random(int(asof.strftime("%Y%m%d")))
    idx = sorted(liq.index)
    ctl = liq.loc[rng.sample(idx, min(len(idx), s["ctl_draw"]))] if idx else liq  # draw 40, the open-position filter trims to the cap
    rev = ok[ok["rsi14"] < 30].sort_values("rsi14", kind="mergesort") if "rsi14" in ok else ok.iloc[0:0]
    return {"BRK": brk, "PULL": pull, "REV": rev, "CTL": ctl}


def _f(x) -> float | None:
    return None if x is None or not np.isfinite(x) else round(float(x), 6)


def universe_snapshot(df: pd.DataFrame, f: pd.DataFrame, asof: pd.Timestamp, liq_top: int) -> list[dict]:
    """The executed book's universe on `asof` (liq_rank <= liq_top) with the derived numbers the missed-movers review describes a day's move with:
    the day's bar against the sessions before it (prior 20-session range, 250-session high and low, RSI and averages as of the close before).
    From rows dated on or before `asof` only; adjusted prices; no raw price is written."""
    liq = f[f["liq_rank"] <= liq_top].set_index("sid")
    d = df[(df["date"] <= asof) & df["sid"].isin(set(liq.index))]
    out = []
    for sid, g in d.groupby("sid", sort=False):
        if g["date"].iloc[-1] != asof or len(g) < 22:
            continue
        o, h, l, c = (g["adj_" + k].values.astype(float) for k in ("open", "high", "low", "close"))
        t = g["turnover"].values.astype(float)
        r = liq.loc[sid]
        ph, pl = float(np.max(h[-21:-1])), float(np.min(l[-21:-1]))
        med = float(r["med60_turnover"])
        out.append({"sid": sid, "symbol": r["symbol"], "isin": g["isin"].iloc[-1] if "isin" in g else None, "liq_rank": int(r["liq_rank"]),
                    "ret_1": _f(c[-1] / c[-2] - 1), "gap": _f(o[-1] / c[-2] - 1), "oc": _f(c[-1] / o[-1] - 1),
                    "vol_ratio20": _f(r["vol_ratio20"]), "turnover_vs_med60": _f(t[-1] / med) if med > 0 else None,
                    "breakout20": bool(c[-1] > ph), "breakdown20": bool(c[-1] < pl), "base20_range": _f((ph - pl) / c[-2]),
                    "new_high_250": bool(c[-1] > np.max(h[-251:-1])) if len(c) >= 251 else None,
                    "new_low_250": bool(c[-1] < np.min(l[-251:-1])) if len(c) >= 251 else None,
                    "rsi14": _f(r["rsi14"]), "rsi14_prev": _f(_rsi14(c[:-1])),
                    "dist_sma20": _f(r["dist_sma20"]), "dist_sma20_prev": _f(c[-2] / np.mean(c[-21:-1]) - 1),
                    "dist_sma200": _f(r["dist_sma200"]), "dist_sma200_prev": _f(c[-2] / np.mean(c[-201:-1]) - 1) if len(c) >= 201 else None,
                    "ret_20_prev": _f(c[-2] / c[-22] - 1), "atr_pct": _f(r["atr14"] / c[-1])})
    return sorted(out, key=lambda x: x["liq_rank"])


def _write_universe(key: str, rows: list[dict], liq_top: int, source: str) -> None:
    body = {"key": key, "written_at": _now(), "source": source, "rules": RULES_VERSION, "liq_top": liq_top, "n": len(rows), "rows": rows}
    tmp = pdir() / "decisions" / f"{key}.universe.json.tmp"
    tmp.write_text(json.dumps(body, indent=0, default=str))
    tmp.replace(pdir() / "decisions" / f"{key}.universe.json")


def universe(key: str) -> dict:
    """For a decision written before universe files existed: the liquid universe of `key` rebuilt from rows dated on or before it (the engine's
    own lookback read), saved as <key>.universe.json and labelled reconstructed. An existing file is never replaced."""
    if (pdir() / "decisions" / f"{key}.universe.json").exists():
        return {"key": key, "status": "exists"}
    if not (pdir() / "decisions" / f"{key}.json").exists():
        raise SystemExit(f"no decision file for {key}")
    s = settings.load()["stock"]
    df = load_adjusted(until=key)
    asof = pd.Timestamp(key)
    rows = universe_snapshot(df, features(df, asof, s["min_price"]), asof, s["liq_top"])
    _write_universe(key, rows, s["liq_top"], "reconstructed after the fact from rows dated on or before the decision date (the engine's lookback read); "
                                             "not the file written at decision time")
    return {"key": key, "status": "reconstructed", "n": len(rows)}


def context(f: pd.DataFrame, asof: pd.Timestamp, liq_top: int) -> dict:
    """Market state at decision time. Missing or stale index rows are reported as such, never filled."""
    liq = f[f["liq_rank"] <= liq_top]
    out = {"n_universe": int(len(f)), "n_liq": int(len(liq)),
           "breadth200_liq": float((liq["dist_sma200"] > 0).mean()) if len(liq) else None, "breadth50_liq": float((liq["dist_sma50"] > 0).mean()) if len(liq) else None,
           "breadth200_all": float((f["dist_sma200"] > 0).mean()) if len(f) else None,
           # the research breadth (india.conditions) is measured on the 500 most liquid stocks: the same measure, so live and historical splits match
           "breadth200": float((f.loc[f["liq_rank"] <= 500, "dist_sma200"] > 0).mean()) if len(f) else None}
    try:
        idx = sealed.read_index("paper_context", (asof - pd.Timedelta(days=420)).strftime("%Y-%m-%d"), ["NIFTY 50", "INDIA VIX", "NIFTY SMLCAP 100", "NIFTY 100"])
        idx["date"] = pd.to_datetime(idx["date"])
        for name, tag in (("NIFTY 50", "nifty"), ("INDIA VIX", "vix")):
            g = idx[(idx["index_name"] == name) & (idx["date"] <= asof)].sort_values("date")
            if g.empty:
                out[tag + "_status"] = "missing"
                continue
            last = g["date"].iloc[-1]
            if last != asof:
                out[tag + "_status"] = f"stale: last row {last.date()}"
                continue
            c = g["close"].values
            out[tag + "_status"] = "ok"
            out[tag + "_close"] = float(c[-1])
            out[tag + "_vs_sma50"] = float(c[-1] / np.mean(c[-50:]) - 1) if len(c) >= 50 else None
            out[tag + "_vs_sma200"] = float(c[-1] / np.mean(c[-200:]) - 1) if len(c) >= 200 else None
        sm = idx[idx["index_name"] == "NIFTY SMLCAP 100"].set_index("date")["close"]
        lg = idx[idx["index_name"] == "NIFTY 100"].set_index("date")["close"]
        ratio = (sm / lg).dropna().sort_index()
        ratio = ratio[ratio.index <= asof]
        if len(ratio) >= 50 and ratio.index[-1] == asof:
            out["small_ratio_vs_sma50"] = float(ratio.iloc[-1] / ratio.iloc[-50:].mean() - 1)
        else:
            out["small_ratio_status"] = "missing or stale"
    except Exception as e:  # context is recorded, not required: a failure is written down and the decision goes ahead
        out["index_status"] = f"missing: {type(e).__name__}: {e}"[:200]
    return out


# ----------------------------------------------------------------------------------------------- decide

def fetch_latest() -> dict:
    today = dt.date.today()
    backfill.run("cm_bhavcopy", today - dt.timedelta(days=4), today, 1.0)
    out = {"fetch": "ok", "silver": silver.build_cm_year(today.year)}
    out["calendar"] = silver.build_calendar()   # a new cash file is a new trading day (19 Oct: verify failed until the calendar was rebuilt)
    return out


def _num(x):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) or pd.isna(x) else (bool(x) if isinstance(x, (bool, np.bool_)) else float(x) if not isinstance(x, str) else x)


def _cand(camp: str, r: pd.Series) -> dict:
    rec = {"campaign": camp, "sid": r["sid"], "symbol": r["symbol"], "atr14": float(r["atr14"]), "close": float(r["close"]), "raw_close": float(r["raw_close"]),
           "liq_rank": int(r["liq_rank"]), "vol_ratio20": _num(r["vol_ratio20"]), "dist_sma20": float(r["dist_sma20"]), "dist_sma200": float(r["dist_sma200"])}
    return rec


def _sha(body: dict) -> str:
    return hashlib.sha256(json.dumps({k: body.get(k) for k in ("rules", "data_through", "signals", "journal", "config_sha")}, sort_keys=True, default=str).encode()).hexdigest()


MIN_CASH_ROWS = 1000   # a session's cash file with fewer stocks than this is a partial file


def input_check(ctx: dict, stocks_on_date: int, asof: pd.Timestamp) -> dict:
    """Madhav, 25 Oct 2026: a decision made on stale inputs is MARKED, never stopped and never dropped from the record. Lists every input that was
    missing or older than the decision's session (the index rows, VIX, the small-cap ratio, a thin cash file, a cash file older than the last
    completed session). The paper rules are unchanged; the mark travels with the decision into the read model, the app and the evidence counts."""
    stale = []
    for tag, name in (("nifty", "Nifty 50"), ("vix", "India VIX")):
        st = ctx.get(tag + "_status")
        if st and st != "ok":
            stale.append(f"{name}: {st}")
    if ctx.get("small_ratio_status"):
        stale.append(f"small-cap ratio: {ctx['small_ratio_status']}")
    if ctx.get("index_status"):
        stale.append(f"index file: {ctx['index_status']}")
    if stocks_on_date < MIN_CASH_ROWS:
        stale.append(f"cash file: only {stocks_on_date} stocks on {asof.date()}")
    try:
        cal = pd.read_parquet(paths.data_dir() / "silver" / "calendar" / "calendar.parquet")
        now_ist = pd.Timestamp.now(tz="Asia/Kolkata")
        done = pd.to_datetime(cal.loc[cal["is_trading_day"].astype(bool), "date"])
        done = done[(done.dt.date < now_ist.date()) | ((done.dt.date == now_ist.date()) & (now_ist.hour >= 16))]
        if len(done) and done.max() > asof:
            stale.append(f"cash file: decided on {asof.date()} although the {done.max().date()} session had closed")
    except Exception:  # noqa: BLE001  the calendar check is extra; the index checks above always run
        pass
    return {"stale": stale, "marked": bool(stale), "rule": "stale inputs are marked, never stopped or dropped (Madhav, 25 Oct 2026)"}


def decide(state: dict | None = None, raw: pd.DataFrame | None = None, write: bool = True, asof: str | None = None) -> dict:
    state = state or _state()
    cfg = settings.load()
    s = cfg["stock"]
    df = load_adjusted(raw=raw, until=asof)
    last = df["date"].max()
    key = last.strftime("%Y-%m-%d")
    if key in state["decisions"]:
        return {"status": "already decided", "data_through": key}
    f = features(df, last, s["min_price"])
    if f.empty:
        return {"status": "no features", "data_through": key}
    sigs = signals(f, last, s)
    open_by = {(t["campaign"], t["sid"]) for t in state["trades"].values() if t["status"] in ("pending", "open")}
    recent = {}
    for t in state["trades"].values():
        recent[(t["campaign"], t["sid"])] = max(recent.get((t["campaign"], t["sid"]), ""), t["signal_date"])
    chosen, journal = [], []
    fx = f.set_index("sid")
    for camp, d in sigs.items():
        n = 0
        for _, r in d.iterrows():
            k = (camp, r["sid"])
            rec = _cand(camp, r)
            if r.get("ca_ambiguous_200", False):
                reason = "ambiguous_corporate_action"   # an unconfirmed split/bonus in the last 200 sessions: indicators cannot be trusted
            elif r["liq_rank"] > s["liq_top"]:
                reason = "outside_liq_top"
            elif k in open_by:
                reason = "open_position"
            elif k in recent and (last - pd.Timestamp(recent[k])).days < s["reentry_days"]:
                reason = "reentry_gap"
            elif n >= s["caps"][camp]:
                reason = "cap_reached"
            else:
                reason = None
                n += 1
                chosen.append(rec)
            extra = {c: _num(fx.at[r["sid"], c]) for c in EXTRA_FIELDS}
            journal.append({**rec, **extra, "status": "chosen" if reason is None else "rejected", "reason": reason})
    counts = {camp: {"candidates": int(len(d)), "in_liq_top": int((d["liq_rank"] <= s["liq_top"]).sum()), "chosen": sum(1 for c in chosen if c["campaign"] == camp)} for camp, d in sigs.items()}
    on_date = int(df.loc[df["date"] == last, "sid"].nunique())
    body = {"rules": RULES_VERSION, "journal_version": JOURNAL_VERSION, "config_version": cfg["version"], "config_sha": settings.sha(), "data_through": key, "decided_at": _now(),
            "universe": {"stocks_with_a_row": on_date, "with_features": int(len(f)), "excluded": on_date - int(len(f)),
                         "excluded_reason": f"under 126 sessions of history or raw close at or below Rs {s['min_price']}"},
            "context": context(f, last, s["liq_top"]), "candidates": counts, "signals": chosen, "journal": journal, "sha_scheme": 2}
    body["inputs"] = input_check(body["context"], on_date, last)
    body["sha256"] = _sha(body)
    if write:
        path = pdir() / "decisions" / f"{key}.json"
        if path.exists():
            raise FileExistsError(f"decision file for {key} already exists and is never rewritten")
        path.write_text(json.dumps(body, indent=1, default=str))
        state["decisions"][key] = {"status": "pending", "signals": len(chosen), "sha256": body["sha256"]}
        _save(state)
        try:   # the review's universe file; a failure here is reported, it never undoes or blocks the decision
            _write_universe(key, universe_snapshot(df, f, last, s["liq_top"]), s["liq_top"], "recorded at decision time")
            uni = "written"
        except Exception as e:
            uni = f"FAILED {type(e).__name__}: {e}"[:200]
        return {"status": "decided", "data_through": key, "signals": len(chosen), "candidates": counts, "universe_file": uni, "body": body}
    return {"status": "decided", "data_through": key, "signals": len(chosen), "candidates": counts, "body": body}


def reconstruct(key: str) -> dict:
    """For a decision written before journals existed: rebuild its candidate journal from rows dated on or before `key`, with the trade state as it stood
    then (no trades before the first decision), check the chosen list matches the original file, and save it beside the original as <key>.journal.json,
    labelled reconstructed. The original file is not touched."""
    orig = json.loads((pdir() / "decisions" / f"{key}.json").read_text())
    if orig.get("journal") is not None:
        return {"status": "has a journal already"}
    prior = {k: v for k, v in _state()["trades"].items() if v["signal_date"] < key}
    again = decide(state={"trades": prior, "decisions": {}}, write=False, asof=key)["body"]
    a = [(x["campaign"], x["sid"]) for x in orig["signals"]]
    b = [(x["campaign"], x["sid"]) for x in again["signals"]]
    diffs = max((abs(x[c] - y[c]) / max(abs(x[c]), 1e-9) for x, y in zip(orig["signals"], again["signals"]) for c in ("atr14", "close", "dist_sma20", "dist_sma200")), default=0.0)
    out = {"key": key, "reconstructed_at": _now(), "label": "reconstructed after the fact from rows dated on or before the decision date; not the record written before the open",
           "original_sha256": orig["sha256"], "chosen_match": a == b, "max_rel_diff_chosen_fields": diffs, "journal": again["journal"], "candidates": again["candidates"],
           "context": again["context"], "universe": again["universe"], "config_sha": again["config_sha"]}
    if a != b:
        out["label"] += "; WARNING the chosen list differs from the original file"
    (pdir() / "decisions" / f"{key}.journal.json").write_text(json.dumps(out, indent=1, default=str))
    return {k: v for k, v in out.items() if k not in ("journal",)}


def journal_for(key: str) -> tuple[list | None, str]:
    body = json.loads((pdir() / "decisions" / f"{key}.json").read_text())
    if body.get("journal") is not None:
        return body["journal"], "recorded"
    p = pdir() / "decisions" / f"{key}.journal.json"
    if p.exists():
        return json.loads(p.read_text())["journal"], "reconstructed"
    return None, "missing"


# ----------------------------------------------------------------------------------------------- trades

def _fill_info(key: str, nxt: pd.Timestamp, g: pd.DataFrame | None) -> dict | None:
    """The fill session's bar and the risk fraction, shared by every policy of one candidate."""
    row = None if g is None else g[g["date"] == nxt]
    if row is None or row.empty:
        return None
    entry_adj = float(row["adj_open"].iloc[0])
    # risk is carried as a fraction of the entry price so later corporate actions rescale it consistently; the 14-day range is
    # recomputed from the bars up to the signal date under today's factors, so a split between decision and fill cannot skew it
    return {"entry_adj": entry_adj, "entry_raw": float(row["open"].iloc[0]), "low_raw": float(row["low"].iloc[0]), "high_raw": float(row["high"].iloc[0]),
            "risk_frac": exitlab.STOP_ATR * _atr14(g[g["date"] <= pd.Timestamp(key)]) / entry_adj}


def _open_trade(book: str, key: str, s: dict, pol: exitlab.Policy, nxt: pd.Timestamp, g: pd.DataFrame | None, dsha: str, cfg: dict, cfg_sha: str, fi: dict | None = None) -> dict:
    tid = f"{key}|{s['campaign']}|{s['sid']}|{pol.name}"
    base = {"id": tid, "book": book, "campaign": s["campaign"], "sid": s["sid"], "symbol": s["symbol"], "policy": pol.name, "signal_date": key, "liq_rank": s["liq_rank"],
            "decision_sha": dsha, "config_sha": cfg_sha}
    if g is not None and "is_fund" in g and bool(g["is_fund"].iloc[-1]):
        # the first decision (rules v1, 16 Oct) predates the fund/ETF exclusion: the record stays, the trade is voided with the reason
        return {**base, "status": "voided", "note": "fund or ETF unit (ISIN INF...): outside the stock universe from rules v1.1"}
    fi = fi if fi is not None else _fill_info(key, nxt, g)
    if fi is None:
        return {**base, "status": "unfilled", "note": "no print on the fill session"}
    entry_adj, risk_frac = fi["entry_adj"], fi["risk_frac"]
    if risk_frac >= 1:
        return {**base, "status": "skipped", "note": "stop below zero"}
    qty, notional = settings.size(cfg, entry_adj, risk_frac)
    rand_day = random.Random(tid).randint(1, exitlab.HORIZON) if pol.kind == "random" else None
    return {**base, "entry_date": nxt.strftime("%Y-%m-%d"), "entry_raw": fi["entry_raw"], "entry_adj": entry_adj, "bar_low_raw": fi["low_raw"],
            "bar_high_raw": fi["high_raw"], "risk_frac": risk_frac, "rand_day": rand_day, "notional": notional, "sizing": cfg["stock"]["sizing"], "status": "open"}


def _window(g: pd.DataFrame, entry_date: str) -> dict | None:
    w = g[g["date"] >= pd.Timestamp(entry_date)].head(exitlab.HORIZON + 1)
    if w.empty:
        return None
    return {"o": w["adj_open"].values, "h": w["adj_high"].values, "l": w["adj_low"].values, "c": w["adj_close"].values, "dates": pd.DatetimeIndex(w["date"].values)}


def _step(t: dict, g: pd.DataFrame, win: dict | None = None) -> bool:
    """Walk an open trade through the bars so far. Returns True if it closed on this pass. `win` lets the baseline book share one window across policies."""
    win = win if win is not None else _window(g, t["entry_date"])
    if win is None:
        return False
    o, h, l, c = win["o"], win["h"], win["l"], win["c"]
    dts = win["dates"]
    entry = float(o[0])  # the factors table can change after entry (a split announced later): re-anchor on the current adjusted entry
    risk = t["risk_frac"] * entry
    k, px, why, peak = exitlab._exit(POLICIES[t["policy"]], o, h, l, c, entry, risk, live=True, rand_day=t.get("rand_day"))
    t["last_close_adj"] = float(c[-1])
    t["last_date"] = dts[-1].strftime("%Y-%m-%d")
    t["bars_seen"] = int(len(dts))
    t["peak_adj"] = float(max(peak, h.max()))
    if why in ("open", "pending"):
        t["unrealised_ret"] = float(c[-1] / entry - 1)
        return False
    notional = float(t.get("notional", 50_000.0))
    qty = notional / entry
    rt = costs.round_trip("delivery", notional, px * qty, year=int(dts[k].year), turnover_rank=t.get("liq_rank"))
    net = px * qty - notional - rt["total"]
    move = peak - entry
    t.update({"status": "closed", "exit_date": dts[k].strftime("%Y-%m-%d"), "exit_reason": why, "exit_adj": float(px), "exit_bar_low_adj": float(l[k]), "exit_bar_high_adj": float(h[k]),
              "gross_ret": float(px / entry - 1), "net_inr": float(net), "net_ret": float(net / notional), "cost_inr": float(rt["total"]), "hold_days": int(k + 1),
              "r_net": float(net / notional / t["risk_frac"]), "mfe_r": float(move / risk), "capture": float(np.clip((px - entry) / move, -1, 1)) if move > 0 else None,
              "giveback_r": float((peak - px) / risk)})
    t.pop("unrealised_ret", None)
    return True


def settle(state: dict | None = None, df: pd.DataFrame | None = None) -> dict:
    """Fill pending decisions at the next session's open (executed book), then step every open trade through the bars so far."""
    state = state or _state()
    cfg, cfg_sha = settings.load(), settings.sha()
    df = load_adjusted() if df is None else df
    latest = df["date"].max()
    filled = closed = unfilled = skipped = 0
    bars_by = {s: g.reset_index(drop=True) for s, g in df.groupby("sid")}
    for key, dmeta in sorted(state["decisions"].items()):
        if dmeta["status"] != "pending":
            continue
        nxt = df.loc[df["date"] > pd.Timestamp(key), "date"].min()
        if pd.isna(nxt):
            continue  # no session after the decision yet
        body = json.loads((pdir() / "decisions" / f"{key}.json").read_text())
        for s in body["signals"]:
            for pol in POLICIES.values():
                tid = f"{key}|{s['campaign']}|{s['sid']}|{pol.name}"
                if tid in state["trades"]:
                    continue
                t = _open_trade("exec", key, s, pol, nxt, bars_by.get(s["sid"]), dmeta["sha256"], cfg, cfg_sha)
                state["trades"][tid] = t
                if t["status"] == "open":
                    _event({"event": "open", "id": tid, "at": _now(), "entry_date": t["entry_date"], "entry_raw": t["entry_raw"], "notional": t["notional"]})
                    filled += 1
                elif t["status"] in ("unfilled", "voided"):
                    unfilled += 1
                else:
                    skipped += 1
        dmeta["status"] = "filled"
        dmeta["filled_on"] = nxt.strftime("%Y-%m-%d")
    for tid, t in state["trades"].items():
        if t["status"] == "open" and _step(t, bars_by[t["sid"]]):
            _event({"event": "close", "id": tid, "at": _now(), "exit_date": t["exit_date"], "reason": t["exit_reason"], "net_inr": t["net_inr"], "cost_inr": t["cost_inr"]})
            closed += 1
    _save(state)
    return {"filled": filled, "unfilled": unfilled, "skipped": skipped, "closed": closed, "latest_session": latest.strftime("%Y-%m-%d")}


def baseline(df: pd.DataFrame | None = None) -> dict:
    """Follow every journal candidate (chosen and rejected) through every policy. Closed rows are cached; open ones are re-walked each run."""
    cfg, cfg_sha = settings.load(), settings.sha()
    df = load_adjusted() if df is None else df
    bars_by = {s: g.reset_index(drop=True) for s, g in df.groupby("sid")}
    cache_p = pdir() / "baseline_closed.parquet"
    cache = {}
    if cache_p.exists():
        cache = {r["id"]: r for r in pd.read_parquet(cache_p).to_dict("records")}
    rows, missing, waiting = [], [], []
    for p in sorted((pdir() / "decisions").glob("????-??-??.json")):
        key = p.stem
        journal, how = journal_for(key)
        if journal is None:
            missing.append(key)
            continue
        nxt = df.loc[df["date"] > pd.Timestamp(key), "date"].min()
        if pd.isna(nxt):
            waiting.append(key)
            continue
        dsha = json.loads(p.read_text())["sha256"]
        for c in journal:
            g = bars_by.get(c["sid"])
            fi = win = None
            prepared = False
            for pol in POLICIES.values():
                tid = f"{key}|{c['campaign']}|{c['sid']}|{pol.name}"
                if tid in cache:
                    rows.append(cache[tid])
                    continue
                if not prepared:  # one fill bar and one price window per candidate, shared by its 19 policies
                    fi = _fill_info(key, nxt, g)
                    win = _window(g, nxt.strftime("%Y-%m-%d")) if fi is not None else None
                    prepared = True
                t = _open_trade("baseline", key, c, pol, nxt, g, dsha, cfg, cfg_sha, fi=fi)
                if t["status"] == "open":
                    _step(t, g, win)
                t.update({"journal_status": c["status"], "journal_reason": c["reason"], "journal_source": how})
                for k in EXTRA_FIELDS + ("vol_ratio20", "dist_sma20", "dist_sma200"):
                    t["f_" + k] = c.get(k)
                rows.append(t)
    out = pd.DataFrame(rows)
    if not out.empty:
        out.to_parquet(pdir() / "baseline.parquet", index=False)
        out[out["status"].isin(["closed", "unfilled", "skipped", "voided"])].to_parquet(cache_p, index=False)
    st = out["status"].value_counts().to_dict() if not out.empty else {}
    return {"rows": int(len(out)), "status": st, "decisions_waiting_for_fill": waiting, "decisions_without_journal": missing}


# ----------------------------------------------------------------------------------------------- marks and reports

def _summ(g: pd.DataFrame) -> dict:
    cl = g[g["status"] == "closed"]
    op = g[g["status"] == "open"]
    notional_open = op["notional"].fillna(50_000.0) if "notional" in op else pd.Series(50_000.0, index=op.index)
    return {"closed": int(len(cl)), "open": int(len(op)), "realised_inr": float(cl["net_inr"].sum()) if len(cl) else 0.0,
            "open_unrealised_inr": float((op["unrealised_ret"].fillna(0) * notional_open).sum()) if len(op) and "unrealised_ret" in op else 0.0,
            "mean_net_ret": float(cl["net_ret"].mean()) if len(cl) else None, "win_rate": float((cl["net_inr"] > 0).mean()) if len(cl) else None,
            "expectancy_R": float(cl["r_net"].mean()) if len(cl) else None,
            "capture_median": float(cl["capture"].dropna().median()) if len(cl) and cl["capture"].notna().any() else None}


MARK_COLS = ("at", "book", "campaign", "policy", "closed", "open", "realised_inr", "open_unrealised_inr", "mean_net_ret", "win_rate", "expectancy_R", "capture_median")


def marks(state: dict | None = None) -> list[dict]:
    state = state or _state()
    rows = []
    now = _now()
    books = {"exec": pd.DataFrame(state["trades"].values())}
    bp = pdir() / "baseline.parquet"
    if bp.exists():
        books["baseline"] = pd.read_parquet(bp)
    for book, t in books.items():
        if t.empty:
            continue
        for (camp, pol), g in t[t["status"].isin(["open", "closed"])].groupby(["campaign", "policy"]):
            rows.append({"at": now, "book": book, "campaign": camp, "policy": pol, **_summ(g)})
    if not rows:
        return rows
    with (pdir() / "marks.jsonl").open("a") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    con = catalog.connect()
    # create first (newer DuckDB raises on table_info for a missing table) and quote "at" (a reserved word in newer DuckDB): the first marks night, 19 Oct 2026, stopped here
    con.execute("create table if not exists paper_marks (\"at\" varchar, campaign varchar, policy varchar, closed integer, open integer, realised_inr double, open_unrealised_inr double, "
                "mean_net_ret double, win_rate double, expectancy_R double, capture_median double, book varchar)")
    cols = [r[1] for r in con.execute("pragma table_info('paper_marks')").fetchall()]
    if "book" not in cols:
        con.execute("alter table paper_marks add column book varchar")
    con.executemany(f"insert into paper_marks ({', '.join(chr(34) + c + chr(34) for c in MARK_COLS)}) values ({', '.join('?' * len(MARK_COLS))})", [[r[k] for k in MARK_COLS] for r in rows])
    con.close()
    return rows


def compare() -> pd.DataFrame:
    """Executed book against the baseline: same campaign and policy, and inside the baseline the chosen candidates against each rejection reason.
    This is where a limit or filter earns its place: if rejected candidates do as well as chosen ones, the limit is costing nothing but also adding nothing."""
    bp = pdir() / "baseline.parquet"
    if not bp.exists():
        print("no baseline yet (first fill happens on the session after the first decision)")
        return pd.DataFrame()
    b = pd.read_parquet(bp)
    b = b[b["status"].isin(["open", "closed"])]
    b["slice"] = np.where(b["journal_status"] == "chosen", "chosen", "rejected:" + b["journal_reason"].fillna("?"))
    rows = []
    for (camp, pol, sl), g in b.groupby(["campaign", "policy", "slice"]):
        rows.append({"campaign": camp, "policy": pol, "slice": sl, **_summ(g)})
    for (camp, pol), g in b.groupby(["campaign", "policy"]):
        rows.append({"campaign": camp, "policy": pol, "slice": "ALL (baseline)", **_summ(g)})
    out = pd.DataFrame(rows).sort_values(["campaign", "policy", "slice"])
    print(out.to_string(index=False))
    return out


def run() -> dict:
    paths.ensure()
    out = {"config": settings.load()["version"], "config_sha": settings.sha()}
    try:
        out["fetch"] = fetch_latest()
    except Exception as e:  # the nightly job heals missing days; the engine works with what is there
        out["fetch"] = f"FAILED {type(e).__name__}: {e}"
    state = _state()
    df = load_adjusted()
    out["settle"] = settle(state, df)
    d = decide(state)
    d.pop("body", None)
    out["decide"] = d
    try:
        out["baseline"] = baseline(df)
    except Exception as e:
        out["baseline"] = f"FAILED {type(e).__name__}: {e}"
    try:
        out["marks"] = len(marks(state))
    except Exception as e:  # a marks failure must not stop the filter slices, the daily call and the report
        out["marks"] = f"FAILED {type(e).__name__}: {e}"
    try:
        from india import filters
        out["filter_slices"] = len(filters.run())
    except Exception as e:
        out["filter_slices"] = f"FAILED {type(e).__name__}: {e}"
    try:
        from india import dailycall
        out["daily_call"] = dailycall.run().get("call", {}).get("call", "already written")
    except Exception as e:
        out["daily_call"] = f"FAILED {type(e).__name__}: {e}"
    try:
        from india import report
        report.build()
        out["report"] = "written"
    except Exception as e:
        out["report"] = f"FAILED {type(e).__name__}: {e}"
    catalog.heartbeat("paper.run", not str(out["fetch"]).startswith("FAILED") and not str(out["baseline"]).startswith("FAILED"), json.dumps(out, default=str)[:480])
    print(json.dumps(out, default=str, indent=1), flush=True)
    return out


def report() -> None:
    state = _state()
    t = pd.DataFrame(state["trades"].values())
    print(f"decisions {len(state['decisions'])}  executed trades {len(t)}  config {settings.load()['version']} ({settings.sha()})")
    if t.empty:
        return
    print(t["status"].value_counts().to_string())
    cl = t[t["status"] == "closed"]
    if len(cl):
        summ = cl.groupby(["campaign", "policy"]).agg(n=("net_inr", "size"), net_inr=("net_inr", "sum"), mean_ret=("net_ret", "mean"), win=("net_inr", lambda x: (x > 0).mean()),
                                                      R=("r_net", "mean"), capture=("capture", "median")).round(3)
        print(summ.to_string())


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "report"
    if cmd == "reconstruct":
        print(json.dumps(reconstruct(sys.argv[2]), indent=1, default=str))
    elif cmd == "universe":
        print(json.dumps(universe(sys.argv[2]), indent=1, default=str))
    else:
        {"run": run, "report": report, "compare": compare, "settle": lambda: print(settle()), "decide": lambda: print({k: v for k, v in decide().items() if k != "body"}),
         "baseline": lambda: print(baseline()), "marks": lambda: print(len(marks()))}[cmd]()
