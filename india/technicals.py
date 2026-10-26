"""The India technicals panel: the basic indicators, computed from Ananta's own daily data, as of the last close (26 Oct 2026).

Madhav, 26 Oct: "clear gap is moving-average crossovers, like the 50-day crossing the 200-day. If Ananta doesn't know that, it probably has
trouble with other basic technical indicators too, such as RSI, MACD, support and resistance, and volume signals. It may also have no live
price data underneath, so it can't say whether a crossover has actually happened."

  python -m india.technicals run      build manifests/technicals.json (the panel) and print one line per name
  python -m india.technicals show     print the panel as plain lines

For NIFTY 50, NIFTY BANK, every stock in the account (paper/account/view.json) and the next session's picks (paper/decisions/<day>.json), as of
the last daily close it has (the date is always stated; nothing intraday):
  close; the 20-, 50- and 200-day simple averages and the distance from each; the 50/200 and 20/50 cross state with the date of the last cross
  and how many sessions ago (a "golden cross" is the 50-day moving above the 200-day, a "death cross" below); RSI(14) (Wilder) and its zone;
  MACD(12,26,9) line, signal, histogram and the date of the last signal-line cross; the 52-week high and low and the distance; support and
  resistance as the nearest swing low below and swing high above the close (a pivot with 5 sessions each side, last 60 sessions) plus the
  round levels; volume against its 20-day average (stocks; Kite reports 0 volume for indices, so it is not available there).
Data: indices through the logged sealed purpose paper_context (india/sealed.read_index, as the day plan and the daily call read them); stocks
through the paper engine's adjusted loader (india/paper.load_adjusted, purpose paper_lookback). Both cap the window at 460 calendar days, so a
cross older than about 115 sessions (the span on which a 200-day average exists) is reported as "no cross since <date>", never guessed.
knowledge(): what Ananta has TESTED about each indicator family, from the registry's latest verdicts and the teacher cards, read fresh each time.
Description only: nothing here trades, and no indicator below is a rule unless the registry says it passed.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from india import paths

RULES = "technicals-v1-2026-10-26"
INDICES = ["NIFTY 50", "NIFTY BANK"]
LOOKBACK_DAYS = 455            # inside the sealed readers' 460-day cap
PIVOT = 5                      # a swing high/low needs this many sessions on each side
SR_WINDOW = 60                 # swing points are looked for in the last 60 sessions
REFRESH_HOURS = 6


def _out() -> Path:
    return paths.manifest_dir() / "technicals.json"


# ------------------------------------------------------------------------------------------------------------------------------ the maths

def sma(x: pd.Series, n: int) -> pd.Series:
    return x.rolling(n, min_periods=n).mean()


def rsi_wilder(close: pd.Series, n: int = 14) -> pd.Series:
    """Wilder's RSI: the first average gain/loss is the simple mean of the first n changes, then each is (prev * (n-1) + now) / n."""
    c = close.astype(float).values
    out = np.full(len(c), np.nan)
    if len(c) <= n:
        return pd.Series(out, index=close.index)
    d = np.diff(c)
    g, l = np.where(d > 0, d, 0.0), np.where(d < 0, -d, 0.0)
    ag, al = g[:n].mean(), l[:n].mean()
    out[n] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    for i in range(n, len(d)):
        ag = (ag * (n - 1) + g[i]) / n
        al = (al * (n - 1) + l[i]) / n
        out[i + 1] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    return pd.Series(out, index=close.index)


def macd(close: pd.Series, fast: int = 12, slow: int = 26, sig: int = 9) -> tuple[pd.Series, pd.Series, pd.Series]:
    c = close.astype(float)
    line = c.ewm(span=fast, adjust=False).mean() - c.ewm(span=slow, adjust=False).mean()
    signal = line.ewm(span=sig, adjust=False).mean()
    line.iloc[: slow - 1] = np.nan                 # not defined before the slow average has its window
    signal.iloc[: slow + sig - 2] = np.nan
    return line, signal, line - signal


def last_cross(a: pd.Series, b: pd.Series, dates: pd.Series) -> dict:
    """Where a stands against b on the last row, and the last day a crossed b (a sign change of a - b) inside the rows where both exist."""
    d = (a - b)
    ok = d.notna().values
    if not ok.any():
        return {"state": None, "last_cross": None, "direction": None, "sessions_ago": None, "searched_from": None}
    idx = np.flatnonzero(ok)
    s = np.sign(d.values[idx])
    state = "above" if s[-1] > 0 else ("below" if s[-1] < 0 else "equal")
    ch = np.flatnonzero((s[1:] != s[:-1]) & (s[1:] != 0))
    first = str(pd.Timestamp(dates.iloc[idx[0]]).date())
    if not len(ch):
        return {"state": state, "last_cross": None, "direction": None, "sessions_ago": None, "searched_from": first}
    k = idx[ch[-1] + 1]
    return {"state": state, "last_cross": str(pd.Timestamp(dates.iloc[k]).date()), "direction": "up" if s[ch[-1] + 1] > 0 else "down",
            "sessions_ago": int(len(d) - 1 - k), "searched_from": first}


def swings(high: pd.Series, low: pd.Series, k: int = PIVOT, window: int = SR_WINDOW) -> tuple[list[tuple[int, float]], list[tuple[int, float]]]:
    """Swing highs and lows: a bar whose high (low) is the highest (lowest) of the k bars on each side, in the last `window` bars."""
    h, l = high.astype(float).values, low.astype(float).values
    n = len(h)
    hi, lo = [], []
    for i in range(max(k, n - window), n - k):
        if h[i] == max(h[i - k:i + k + 1]):
            hi.append((i, float(h[i])))
        if l[i] == min(l[i - k:i + k + 1]):
            lo.append((i, float(l[i])))
    return hi, lo


def round_step(price: float) -> float:
    for lim, step in ((50, 1), (100, 5), (250, 10), (1000, 50), (2500, 100), (10000, 250), (25000, 500), (60000, 1000)):
        if price < lim:
            return float(step)
    return 2000.0


def _rsi_zone(r: float | None) -> str | None:
    if r is None or r != r:
        return None
    return "overbought, over 70" if r > 70 else "oversold, under 30" if r < 30 else "neutral, leaning strong" if r >= 55 else "neutral, leaning weak" if r <= 45 else "neutral"


def _f(x, nd=2):
    return None if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))) else round(float(x), nd)


def panel(name: str, df: pd.DataFrame, kind: str) -> dict:
    """One name's panel from daily rows (date, open, high, low, close, volume), oldest first. kind: index | stock."""
    df = df.dropna(subset=["close"]).sort_values("date").reset_index(drop=True)
    if len(df) < 30:
        return {"name": name, "kind": kind, "status": "too_short", "sessions": len(df), "words": f"{name}: only {len(df)} sessions of history, too few for the indicators."}
    c, dates = df["close"].astype(float), pd.to_datetime(df["date"])
    hi = df["high"].astype(float) if kind == "stock" else c
    lo = df["low"].astype(float) if kind == "stock" else c
    s20, s50, s200 = sma(c, 20), sma(c, 50), sma(c, 200)
    last = c.iloc[-1]
    rsi = rsi_wilder(c)
    ml, ms, mh = macd(c)
    x50_200, x20_50 = last_cross(s50, s200, dates), last_cross(s20, s50, dates)
    mx = last_cross(ml, ms, dates)
    w = min(250, len(df))
    h52, l52 = float(hi.tail(w).max()), float(lo.tail(w).min())
    sh, sl = swings(hi, lo)
    res = sorted([(v, i) for i, v in sh if v > last], key=lambda t: t[0])
    sup = sorted([(v, i) for i, v in sl if v < last], key=lambda t: -t[0])
    step = round_step(last)
    vol = None
    if kind == "stock" and "volume" in df and df["volume"].tail(21).gt(0).sum() >= 15:
        v20 = float(df["volume"].iloc[-21:-1].mean())
        vol = {"last": int(df["volume"].iloc[-1]), "avg20": int(v20), "ratio": _f(df["volume"].iloc[-1] / v20) if v20 else None}
    jumps = (c.pct_change().abs() > 0.35)
    jump = [str(pd.Timestamp(dates[i]).date()) for i in np.flatnonzero(jumps.values)][-1:] if kind == "stock" else []
    p = {"name": name, "kind": kind, "status": "ok", "as_of": str(dates.iloc[-1].date()), "sessions": len(df), "close": _f(last),
         "prev_close": _f(c.iloc[-2]), "change_1d": _f(last / c.iloc[-2] - 1, 4),
         "sma": {"20": _f(s20.iloc[-1]), "50": _f(s50.iloc[-1]), "200": _f(s200.iloc[-1])},
         "vs_sma": {k: _f(last / v.iloc[-1] - 1, 4) if v.iloc[-1] == v.iloc[-1] else None for k, v in (("20", s20), ("50", s50), ("200", s200))},
         "cross_50_200": {**x50_200, "name": ("golden cross (50-day above 200-day)" if x50_200["state"] == "above" else "death cross (50-day below 200-day)" if x50_200["state"] == "below" else None)},
         "cross_20_50": x20_50,
         "rsi14": _f(rsi.iloc[-1], 1), "rsi_zone": _rsi_zone(rsi.iloc[-1]),
         "macd": {"line": _f(ml.iloc[-1]), "signal": _f(ms.iloc[-1]), "hist": _f(mh.iloc[-1]), "state": mx["state"], "last_signal_cross": mx["last_cross"],
                  "cross_direction": mx["direction"], "sessions_ago": mx["sessions_ago"]},
         "high_52w": _f(h52), "low_52w": _f(l52), "vs_high_52w": _f(last / h52 - 1, 4), "vs_low_52w": _f(last / l52 - 1, 4), "window_52w_sessions": w,
         "support": {"swing_low": _f(sup[0][0]) if sup else None, "swing_low_date": str(dates[sup[0][1]].date()) if sup else None,
                     "round": _f(math.floor(last / step) * step)},
         "resistance": {"swing_high": _f(res[0][0]) if res else None, "swing_high_date": str(dates[res[0][1]].date()) if res else None,
                        "round": _f(math.ceil(last / step) * step if last % step else last + step)},
         "sr_basis": ("daily closes (index highs and lows are not in the reader)" if kind == "index" else "daily highs and lows") + f", pivots of {PIVOT} sessions each side in the last {SR_WINDOW}",
         "volume": vol if kind == "stock" else {"note": "not available: Kite reports 0 volume for indices"},
         "big_jump": jump[0] if jump else None}
    p["words"] = words(p)
    return p


def _dw(d: str | None) -> str:
    try:
        return dt.date.fromisoformat(str(d)[:10]).strftime("%a %-d %b")
    except (TypeError, ValueError):
        return str(d)


def _pc(x) -> str:
    return "n/a" if x is None else f"{x * 100:+.1f}%"


def words(p: dict) -> str:
    """One plain line a person can say aloud."""
    if p.get("status") != "ok":
        return p.get("words", "")
    vs = p["vs_sma"]
    above = [k for k in ("20", "50", "200") if vs.get(k) is not None and vs[k] > 0]
    below = [k for k in ("20", "50", "200") if vs.get(k) is not None and vs[k] < 0]
    pos = ("above its " + ", ".join(above) + "-day averages" if above and not below else "below its " + ", ".join(below) + "-day averages" if below and not above
           else f"above its {', '.join(above)}-day and below its {', '.join(below)}-day averages")
    x = p["cross_50_200"]
    if x["state"] is None:
        xs = "too little history for a 200-day average"
    elif x["last_cross"]:
        xs = (f"the 50-day crossed {'above' if x['direction'] == 'up' else 'below'} the 200-day on {_dw(x['last_cross'])} ({x['sessions_ago']} sessions ago: "
              f"a {'golden' if x['direction'] == 'up' else 'death'} cross)")
    else:
        xs = f"the 50-day has been {x['state']} the 200-day with no cross since {_dw(x['searched_from'])}"
    m = p["macd"]
    ms = (f"MACD {'above' if m['state'] == 'above' else 'below'} its signal" + (f" since {_dw(m['last_signal_cross'])}" if m.get("last_signal_cross") else "")) if m.get("state") else "MACD n/a"
    sup, res = p["support"], p["resistance"]
    sr = (f"support near {sup['swing_low']:,.0f}" if sup.get("swing_low") else f"no swing low below; round support {sup['round']:,.0f}") + ", " + \
         (f"resistance near {res['swing_high']:,.0f}" if res.get("swing_high") else f"no swing high above; round resistance {res['round']:,.0f}")
    vol = p.get("volume") or {}
    vw = f"; volume {vol['ratio']:.1f}x its 20-day average" if vol.get("ratio") else ""
    jw = f" (note: a {_dw(p['big_jump'])} price jump over 35% looks like a corporate action, so averages across it are unreliable)" if p.get("big_jump") else ""
    return (f"{p['name']} closed at {p['close']:,.2f} on {_dw(p['as_of'])} ({_pc(p['change_1d'])}): {pos}; {xs}; RSI {p['rsi14']:.0f} ({p['rsi_zone']}); {ms}; "
            f"{sr}; {_pc(p['vs_high_52w'])} from its 52-week high{vw}.{jw}")


# ------------------------------------------------------------------------------------------------------------------------------ the data

def index_rows(names: list[str] | None = None, since: str | None = None) -> pd.DataFrame:
    """Daily index closes through the logged paper_context purpose (the same reader as the day plan and the daily call)."""
    from india import sealed
    since = since or (dt.date.today() - dt.timedelta(days=LOOKBACK_DAYS)).isoformat()
    df = sealed.read_index("paper_context", since, names or INDICES)
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values(["index_name", "date"]).reset_index(drop=True)


def latest_index(names: list[str] | None = None) -> dict:
    """Each index's newest close with its date, the 1-day change and the distance from its 50- and 200-day averages (the morning view uses it)."""
    names = names or ["NIFTY 50", "NIFTY BANK", "INDIA VIX"]
    out = {}
    df = index_rows(names)
    for nm, g in df.groupby("index_name"):
        c = g["close"].astype(float).reset_index(drop=True)
        if len(c) < 2:
            continue
        out[nm] = {"date": str(g["date"].iloc[-1].date()), "close": float(c.iloc[-1]), "d1": float(c.iloc[-1] / c.iloc[-2] - 1),
                   "vs_sma50": float(c.iloc[-1] / c.tail(50).mean() - 1) if len(c) >= 50 else None,
                   "vs_sma200": float(c.iloc[-1] / c.tail(200).mean() - 1) if len(c) >= 200 else None}
    return out


def names_to_follow() -> dict:
    """The account's holdings and the next session's non-random picks, with where each came from."""
    d = paths.data_dir() / "paper"
    hold, picks = [], []
    try:
        v = json.loads((d / "account" / "view.json").read_text())
        hold = [p["symbol"] for p in v.get("positions") or [] if p.get("symbol")]
    except (OSError, ValueError):
        pass
    days = sorted(p.stem for p in (d / "decisions").glob("????-??-??.json"))
    if days:
        try:
            j = json.loads((d / "decisions" / f"{days[-1]}.json").read_text())
            picks = [x["symbol"] for x in j.get("signals") or [] if x.get("symbol") and x.get("campaign") != "CTL"]
        except (OSError, ValueError):
            pass
    return {"holdings": hold, "picks": picks, "picks_day": days[-1] if days else None}


def stock_rows(symbols: list[str]) -> pd.DataFrame:
    from india import paper
    df = paper.load_adjusted()
    df = df[df["symbol"].isin(symbols)]
    return pd.DataFrame({"symbol": df["symbol"], "date": df["date"], "open": df["adj_open"], "high": df["adj_high"], "low": df["adj_low"],
                         "close": df["adj_close"], "volume": df["volume"]})


def history_crosses(indices: dict) -> None:
    """26 Oct (Madhav said yes): the 460-day paper_context window cannot see a 50/200 cross older than about May, so the panel said "no cross
    since 20 May". The dates come from sealed.index_cross_dates (purpose technicals_history: cross dates only, no price leaves the loader):
    the last cross fills in when the window shows none, and the last three 50/200 crosses are kept for "when did it last cross?"."""
    from india import sealed
    names = [n for n, p in indices.items() if p.get("status") == "ok"]
    if not names:
        return
    ev = sealed.index_cross_dates("technicals_history", names)
    for n in names:
        p = indices[n]
        for pair, key in (("50/200", "cross_50_200"), ("20/50", "cross_20_50")):
            e = [x for x in ev if x["index_name"] == n and x["pair"] == pair and x["date"] <= p["as_of"]]
            x = p[key]
            if pair == "50/200":
                x["history"] = [{"date": q["date"], "direction": q["direction"]} for q in e[-3:]]
            if e and not x.get("last_cross") and x.get("state") in ("above", "below") and (e[-1]["direction"] == "up") == (x["state"] == "above"):
                x.update({"last_cross": e[-1]["date"], "direction": e[-1]["direction"], "sessions_ago": e[-1]["sessions_ago"],
                          "from_history": "cross date from the index history since 2015 (technicals_history)"})
        p["words"] = words(p)


def run() -> dict:
    who = names_to_follow()
    out = {"rules": RULES, "built_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "basis": "daily closes, as of the date on each row; nothing intraday",
           "indices": {}, "stocks": {}, "holdings": who["holdings"], "picks": who["picks"], "picks_day": who["picks_day"], "errors": []}
    try:
        ix = index_rows(INDICES)
        for nm, g in ix.groupby("index_name"):
            out["indices"][nm] = panel(nm, g.assign(open=g["close"], high=g["close"], low=g["close"], volume=0), "index")
    except Exception as e:  # noqa: BLE001  the panel says what failed, never guesses
        out["errors"].append(f"indices: {type(e).__name__}: {e}"[:200])
    try:
        history_crosses(out["indices"])
    except Exception as e:  # noqa: BLE001
        out["errors"].append(f"cross history: {type(e).__name__}: {e}"[:200])
    syms = sorted(set(who["holdings"]) | set(who["picks"]))
    if syms:
        try:
            st = stock_rows(syms)
            for s in syms:
                g = st[st["symbol"] == s]
                out["stocks"][s] = panel(s, g, "stock") if len(g) else {"name": s, "kind": "stock", "status": "no_rows", "words": f"{s}: no daily rows in the last {LOOKBACK_DAYS} days."}
                out["stocks"][s]["role"] = ("holding" if s in who["holdings"] else "") + (" and pick" if s in who["holdings"] and s in who["picks"] else "pick" if s in who["picks"] else "")
        except Exception as e:  # noqa: BLE001
            out["errors"].append(f"stocks: {type(e).__name__}: {e}"[:200])
    as_of = sorted({p.get("as_of") for p in list(out["indices"].values()) + list(out["stocks"].values()) if p.get("as_of")})
    out["as_of"] = as_of[-1] if as_of else None
    _out().write_text(json.dumps(out, indent=1, default=str))
    return out


def section(refresh: bool = True) -> dict:
    """For the read model: the panel (rebuilt when older than REFRESH_HOURS or the picks day changed), trimmed to what Ask needs."""
    p = _out()
    j = None
    if p.exists():
        try:
            j = json.loads(p.read_text())
        except ValueError:
            j = None
    stale = j is None or (dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(j["built_at"])).total_seconds() > REFRESH_HOURS * 3600 \
        or j.get("picks_day") != names_to_follow()["picks_day"]
    if refresh and stale:
        j = run()
    if not j:
        return {"status": "missing", "source": str(p)}
    keep = ("name", "kind", "status", "as_of", "close", "change_1d", "sma", "vs_sma", "cross_50_200", "cross_20_50", "rsi14", "rsi_zone", "macd", "high_52w", "low_52w",
            "vs_high_52w", "vs_low_52w", "support", "resistance", "sr_basis", "volume", "big_jump", "role", "words")
    trim = lambda d: {k: d.get(k) for k in keep if k in d}   # noqa: E731
    return {"status": "ok", "source": str(p), "rules": j.get("rules"), "built_at": j.get("built_at"), "as_of": j.get("as_of"), "basis": j.get("basis"),
            "indices": {k: trim(v) for k, v in (j.get("indices") or {}).items()}, "stocks": {k: trim(v) for k, v in (j.get("stocks") or {}).items()},
            "errors": j.get("errors") or [],
            "meaning": "the basic indicators from Ananta's own daily data as of the last close (no intraday); description only, not a rule; "
                       "whether an indicator was ever tested is in indicator_knowledge"}


# ------------------------------------------------------------------------------------------------------------------------------ what was tested

# The registry's condition and exit names in plain words (india/conditions.py, india/exitlab.py)
COND_WORDS = {
    "rsi_gt70": "RSI(14) over 70 when bought", "rsi_lt30": "RSI(14) under 30 when bought", "stoch_lt20": "the stochastic under 20 when bought",
    "wk_outside_up": "a weekly outside-up bar", "ext_sma50_gt20": "bought more than 20% above the 50-day average", "ext_ret20_gt25": "up more than 25% in 20 sessions",
    "ext_ret60_gt50": "up more than 50% in 60 sessions", "decline_ret60_lt_m30": "down more than 30% in 60 sessions", "vol_heat2": "volume over 2x its average",
    "deliv_high": "a high delivery share", "rv20_high": "high 20-day volatility", "vix_gt20": "India VIX over 20", "vix_rising": "India VIX rising",
    "breadth_lt30": "under 30% of stocks above their 200-day", "breadth_lt40": "under 40% of stocks above their 200-day", "breadth_thrust": "a breadth thrust",
    "usdinr_rising": "the rupee weakening (USD/INR rising)", "brent_rising": "crude oil rising", "nasdaq_gt200d": "the Nasdaq above its 200-day",
    "us10y_up_60d": "the US 10-year yield up over 60 days", "fii_long_gt60": "foreign institutions over 60% long in index futures",
    "fii_long_lt40": "foreign institutions under 40% long in index futures", "fii_rising5": "foreign institutions' long share rising for 5 days",
    "client_long_gt60": "retail clients over 60% long in index futures",
}
EXIT_WORDS = {"sma_close_10": "selling on a close below the 10-day average", "sma_close_20": "selling on a close below the 20-day average",
              "sma_close_50": "selling on a close below the 50-day average", "swing_low_5": "selling below the last 5-session swing low",
              "swing_low_10": "selling below the last 10-session swing low", "swing_low_20": "selling below the last 20-session swing low"}
FAMILIES = {
    "moving averages and crossovers": {"conds": ["ext_sma50_gt20"], "exits": ["sma_close_10", "sma_close_20", "sma_close_50"],
                                       "cards": r"moving average|\bdma\b|\bema\b|50-day|200-day|crossover|golden|death cross|stage 2|ichimoku|adx",
                                       "studies": [("XO1", r"\|(?:gc|dc|x2050\w*|state50gt200|converge)\|")]},
    "RSI and stochastic": {"conds": ["rsi_gt70", "rsi_lt30", "stoch_lt20"], "cards": r"\brsi\b|stochastic|divergence|oversold|overbought"},
    "MACD": {"conds": [], "cards": r"\bmacd\b", "studies": [("XO1", r"\|macd(?:up|dn)\|")]},
    "volume": {"conds": ["vol_heat2", "deliv_high"], "cards": r"volume|delivery"},
    "support and resistance": {"conds": [], "exits": ["swing_low_5", "swing_low_10", "swing_low_20"], "cards": r"support|resistance|retest|breakout level|pivot",
                               "studies": [("SR1", None)]},
    "breadth": {"conds": ["breadth_lt30", "breadth_lt40", "breadth_thrust"], "cards": r"breadth"},
    "India VIX (the fear gauge)": {"conds": ["vix_gt20", "vix_rising"], "cards": r"\bvix\b"},
    "FII flows and positioning": {"conds": ["fii_long_gt60", "fii_long_lt40", "fii_rising5", "client_long_gt60"], "cards": r"\bfii\b|foreign|\bfpi\b",
                                  "studies": [("FII1", None)],
                                  "untested_note": "domestic institutions' (DII) flows: no free history, captured each evening from 26 Oct, so not tested"},
    "USD/INR (the rupee)": {"conds": ["usdinr_rising"], "cards": r"dollar|rupee|usd", "studies": [("FX1", None)]},
}
# The plain words of the 26 Oct studies' versions (india/xstudies.py; registrations xo1/fx1/fii1_v1): who, what event, which outcome.
SUBJ = {"NIFTY": "Nifty", "BANK": "Bank Nifty", "STK": "liquid-250 stocks"}
EVENT = {"gc": "50-day crossing above the 200-day (golden cross)", "dc": "50-day crossing below the 200-day (death cross)",
         "x2050up": "20-day crossing above the 50-day", "x2050dn": "20-day crossing below the 50-day",
         "x2050up_uptrend": "20-day crossing above the 50-day in an uptrend", "x2050up_downtrend": "20-day crossing above the 50-day in a downtrend",
         "macdup": "MACD crossing above its signal line", "macddn": "MACD crossing below its signal line",
         "state50gt200": "holding while the 50-day is above the 200-day", "converge": "the averages bunched together (a bigger move after?)",
         "weak5": "a sharp weak-rupee week", "weak1": "a sharp weak-rupee day", "h42_up5": "a strong-dollar stretch (TWT-H42)",
         "h42_break3y": "the dollar at a 3-year high against the rupee (TWT-H42)", "neg5": "a sharp 5-day foreign outflow",
         "neg1": "a sharp one-day foreign outflow", "pos5": "a sharp 5-day foreign inflow", "pos1": "a sharp one-day foreign inflow",
         "bounce20": "a bounce off 20-session support (touched it, closed up within 1.5% above)",
         "bounce60": "a bounce off 60-session support (touched it, closed up within 1.5% above)",
         "break20": "a close above 20-session resistance", "break60": "a close above 60-session resistance",
         "breakdown60": "a close below 60-session support"}
OUT = {"fwd60": "next 60 sessions", "fwd20": "next 20 sessions", "net60": "next 60 sessions against ordinary days", "net20": "next 20 sessions against ordinary days",
       "abs20": "size of the move over 20 sessions", "nfwd1": "Nifty next session", "nfwd5": "Nifty next 5 sessions", "nfwd20": "Nifty next 20 sessions",
       "nfwd21": "Nifty next 21 sessions", "nfwd63": "Nifty next 63 sessions", "bankfwd20": "Bank Nifty next 20 sessions",
       "itx20": "IT against the Nifty over 20 sessions", "pharmax20": "pharma against the Nifty over 20 sessions"}
HEADLINE = {   # the conclusion of each study, shown only once its rows are in the ledger (results pages: india/registrations/*_results_v1.md)
    ("XO1", "moving averages and crossovers"): "Tested 26 Oct (study XO1, 2000-2023): no moving-average crossover is a usable buy or sell signal. On liquid-250 stocks the "
        "golden cross was followed by about 2.7% WORSE returns over 60 sessions than ordinary days and the 20-day crossing above the 50-day by about 0.5-0.7% worse "
        "over 20 (both the reverse of the claim); death crosses rejected; traded after costs about zero; bunched averages were followed by smaller moves, not bigger. "
        "Nifty and Bank Nifty 50/200 crosses are too rare to judge (8 and 5 each way)",
    ("XO1", "MACD"): "Tested 26 Oct (study XO1): MACD crossing its signal line is not a usable signal on Nifty, Bank Nifty or liquid-250 stocks (upward crosses rejected "
        "everywhere; the downward cross on stocks inconclusive)",
    ("FX1", "USD/INR (the rupee)"): "Tested 26 Oct (study FX1, 2010-2023, FRED USD/INR): sharp weak-rupee weeks and days were followed by no weaker Nifty or Bank Nifty "
        "and gave no edge to IT or pharma (all rejected); TWT-H42 (strong dollar hurts the Nifty) inconclusive, and its one strong reading points the other way "
        "(the Nifty about 4% better over 21 sessions after a weak-rupee stretch in 2018-2023)",
    ("SR1", "support and resistance"): "Tested 26 Oct (study SR1, 2000-2023, the panel's own swing levels): support and resistance are not a usable entry "
        "signal. On liquid-250 stocks a close above resistance was followed by about 0.5-1% WORSE returns over 20 sessions than ordinary days (the reverse "
        "of the claim; about zero as a trade after costs); a bounce off support had no edge over ordinary days, and a close below support was not followed "
        "by weaker returns; on the Nifty and Bank Nifty neither the bounce nor the breakout made a difference",
    ("FII1", "FII flows and positioning"): "Tested 26 Oct (study FII1, NSDL FPI cash flows 2010-2023): sharp foreign outflow or inflow days and weeks were followed by "
        "no weaker or stronger Nifty over 1, 5 or 20 sessions (all 8 rejected); flows follow the market (correlation 0.2-0.46 with the previous session's Nifty move, "
        "about zero with the next) and the same-day link is tiny (TWT-H48)",
}


def _study_spec(s) -> tuple[str, str | None]:
    return s if isinstance(s, tuple) else (s, None)


def _study_rows(res: dict, s: str, vre: str | None) -> list[dict]:
    return [r for (st, v), r in sorted(res.items()) if (st == s or st.startswith(s + "-")) and (not vre or re.search(vre, v + "|"))]


def _study_row_words(r: dict) -> str:
    parts = r["variant"].split("|")
    subj = SUBJ.get(parts[0]) if parts[0] in SUBJ else None
    rest = parts[1:] if subj else parts
    ev = EVENT.get(rest[0], rest[0]) if rest else r["variant"]
    out = OUT.get(rest[1], rest[1]) if len(rest) > 1 else ""
    trade = " (as a trade after costs)" if "absolute" in parts else ""
    if trade:
        out = out.replace(" against ordinary days", "")
    d, v = (r.get("dev") or [None, None]), (r.get("val") or [None, None])
    num = ""
    if r["verdict"] in ("OPPOSITE", "VALIDATED", "CONDITIONAL") and d[0] is not None and v[0] is not None:
        num = f" ({_pc(d[0])} in 2000-2017, {_pc(v[0])} in 2018-2023)"
    return f"{(subj + ', ') if subj else ''}{ev}{', ' + out if out else ''}{trade}: {r['verdict']}{num}"


REF_EXIT = "hold_20d"


def _latest_results() -> dict:
    from india import registry
    out = {}
    for r in registry._rows():
        if r.get("kind") == "result":
            out[(r["study"], r["variant"])] = r
    return out


def _cond_row(res: dict, cond: str) -> dict | None:
    """The cleanest test of one condition: the ANY entry set with the 20-session hold, else any row of that condition (P01/E04/C02/C05/C08/C09; C06 is per-day)."""
    cands = [r for (s, v), r in res.items() if v.split("|")[0] == cond and (v.endswith("|" + REF_EXIT) or "|" not in v)]
    if not cands:
        return None
    cands.sort(key=lambda r: (not r["study"].endswith("-ANY"), r["study"]))
    return cands[0]


def _cond_counts(res: dict, study: str, cond: str) -> dict:
    from collections import Counter
    return dict(Counter(r["verdict"] for (s, v), r in res.items() if s == study and v.split("|")[0] == cond))


def _say_row(r: dict, what: str, counts: dict | None = None) -> str:
    d, v = (r.get("dev") or [None])[0], (r.get("val") or [None])[0]
    allv = (" (across its " + str(sum(counts.values())) + " exit versions: " + ", ".join(f"{n} {k}" for k, n in sorted(counts.items(), key=lambda t: -t[1])) + ")") \
        if counts and sum(counts.values()) > 1 else ""
    opp = " (the reverse of what was claimed)" if r["verdict"] == "OPPOSITE" else ""
    if d is None or d != d:
        return f"{what}: {r['verdict']}{opp} (too few quarters to measure){allv}"
    vv = _pc(v) if v is not None and v == v else "n/a"
    if r["study"] == "C06":      # a per-day study of the index (participant data from 2012)
        return (f"{what}: the Nifty did {'better' if d > 0 else 'worse'} over the next 5 sessions than on other days ({_pc(d)} in 2012-2017, {vv} in 2018-2023): "
                f"{r['verdict']}{opp}")
    return (f"{what}: trades {'earned more' if d > 0 else 'earned less'} over 20 sessions than the rest ({_pc(d)} in 2000-2017, {vv} in 2018-2023, quarter averages): "
            f"{r['verdict']}{opp}{allv}")


def knowledge() -> dict:
    """What Ananta has tested about each indicator family, read fresh from the registry and the teacher cards, in plain words."""
    try:
        res = _latest_results()
    except Exception as e:  # noqa: BLE001
        return {"status": "unavailable", "why": str(e)[:120]}
    cards = []
    try:
        cards = json.loads((paths.gold() / "teachers" / "summary.json").read_text()).get("cards") or []
    except (OSError, ValueError):
        pass
    fams = {}
    for fam, spec in FAMILIES.items():
        tested = []
        for c in spec.get("conds", []):
            r = _cond_row(res, c)
            if r:
                cnt = _cond_counts(res, r["study"], c)
                tested.append({"what": COND_WORDS.get(c, c), "study": r["study"], "variant": r["variant"], "verdict": r["verdict"], "all_exits": cnt,
                               "words": _say_row(r, COND_WORDS.get(c, c), cnt)})
        for e in spec.get("exits", []):
            r = res.get(("E02-ANY", e))
            if r:
                tested.append({"what": EXIT_WORDS.get(e, e), "study": "E02-ANY", "variant": e, "verdict": r["verdict"],
                               "words": f"{EXIT_WORDS.get(e, e)} as an exit (against holding 20 sessions): {r['verdict']}"})
        heads = []
        for spec_s in spec.get("studies", []):
            s, vre = _study_spec(spec_s)
            rows = _study_rows(res, s, vre)
            if rows:
                from collections import Counter
                cnt = dict(Counter(r["verdict"] for r in rows))
                if (s, fam) in HEADLINE:
                    heads.append(HEADLINE[(s, fam)])
                tested.append({"what": f"study {s}", "study": s, "verdict": cnt, "versions": [_study_row_words(r) for r in rows],
                               "words": f"study {s} ({len(rows)} versions): " + ", ".join(f"{n} {k}" for k, n in sorted(cnt.items(), key=lambda t: -t[1]))})
        rx = re.compile(spec["cards"], re.I)
        cs = [{"id": c["id"], "title": c.get("title"), "verdict": c.get("verdict") or c.get("status"), "plain": c.get("plain"), "_t": bool(rx.search(c.get("title") or ""))}
              for c in cards if rx.search(f"{c.get('title', '')} {c.get('rule', '')}") and c.get("status") in ("TEST", "LINKED", "DESCRIPTIVE")]
        cs = [{k: v for k, v in c.items() if k != "_t"} for c in sorted(cs, key=lambda c: not c["_t"])]     # a match in the title first
        being = [_study_spec(x)[0] for x in spec.get("studies", []) if not _study_rows(res, *_study_spec(x))]
        fams[fam] = {"tested": tested, "teacher_cards": cs[:8], "headline": "".join(h + ". " for h in heads).strip() or None,
                     "not_tested": (spec.get("untested_note", "") + (" (being tested: no ledger row yet)" if being else "")) if (spec.get("untested_note") or being) else None,
                     "words": (f"{fam}: " + ("".join(h + ". " for h in heads)) + ("; ".join(t["words"] for t in tested[:3]) if tested else "no registry test") +
                               (f". Teacher cards: " + "; ".join(f"{c['id']} {c['title']} ({c['verdict']})" for c in cs[:3]) if cs else "") +
                               (f". Not tested: {spec['untested_note']}" if spec.get("untested_note") else "") + ".")}
    return {"status": "ok", "rules": RULES, "source": "manifests/test_ledger.jsonl (latest verdict per study and version) and gold/teachers/summary.json",
            "verdict_meaning": "VALIDATED = held in both periods at the strict bar; CONDITIONAL = held, one period below the strict bar; REJECTED = did not hold; "
                               "OPPOSITE = the reverse of the claim showed up; INCONCLUSIVE = too little data to judge",
            "families": fams}


# ------------------------------------------------------------------------------------------------------------------------------ cli

if __name__ == "__main__":
    paths.ensure()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    j = run() if cmd == "run" else json.loads(_out().read_text())
    for p in list(j["indices"].values()) + list(j["stocks"].values()):
        print(p.get("words"))
    if j.get("errors"):
        print("errors:", j["errors"])
