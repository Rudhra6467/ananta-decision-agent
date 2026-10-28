"""The quote book: every liquid NSE cash stock and every ETF as of the newest close, the sector and broad indices ranked, and gold and silver in
rupees through their ETFs (Madhav, 27 Oct 2026: the outside review of the India Ask found it had "no price for TCS, Reliance, HDFC Bank", no
sector ranking and no gold price; "the biggest gap").

  python -m india.quotebook build      manifests/quotebook.json (quotes, sectors, broad indices, gold) and manifests/quotebook_names.json
  python -m india.quotebook names      refresh the name lists from NSE (EQUITY_L.csv, eq_etfseclist.csv) into bronze/reference

Data: stocks and ETFs through paper.load_adjusted (the paper engine's own reader, sealed purpose paper_lookback, adjusted for corporate actions;
the 460-day cap means 1-year figures are the longest); indices through technicals.index_rows (purpose paper_context). Every figure carries the
date of the close it is computed from. Nothing here is a signal or a rule: it is what the market did, for the Ask to describe.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from india import paths

RULES = "quotebook-v1-2026-10-27"
MIN_TURNOVER_CR = 1.0            # stocks: 20-day average traded value of at least Rs 1 crore a day; every ETF is kept
WINDOWS = ("1d", "1w", "1m", "3m", "6m", "1y")              # calendar windows: the close on or before the same date one week/month/year back
SECTORS = {"NIFTY AUTO": "Auto", "NIFTY BANK": "Banks", "NIFTY PVT BANK": "Private banks", "NIFTY PSU BANK": "PSU banks",
           "NIFTY FIN SERVICE": "Financial services", "NIFTY CAPITAL MKT": "Capital markets", "NIFTY FMCG": "FMCG", "NIFTY IT": "IT",
           "NIFTY MEDIA": "Media", "NIFTY METAL": "Metals", "NIFTY PHARMA": "Pharma", "NIFTY HEALTHCARE": "Healthcare", "NIFTY REALTY": "Realty",
           "NIFTY ENERGY": "Energy", "NIFTY OIL AND GAS": "Oil and gas", "NIFTY CONSR DURBL": "Consumer durables", "NIFTY INFRA": "Infrastructure",
           "NIFTY IND DEFENCE": "Defence", "NIFTY CONSUMPTION": "Consumption", "NIFTY COMMODITIES": "Commodities", "NIFTY RAILWAYS PSU": "Railway PSUs",
           "NIFTY CPSE": "Central PSUs"}
BROAD = {"NIFTY 50": "Nifty 50", "NIFTY NEXT 50": "Nifty Next 50", "NIFTY 100": "Nifty 100", "NIFTY 500": "Nifty 500", "NIFTY MIDCAP 150": "Nifty Midcap 150",
         "NIFTY MIDCAP 100": "Nifty Midcap 100", "NIFTY SMLCAP 250": "Nifty Smallcap 250", "NIFTY SMLCAP 100": "Nifty Smallcap 100",
         "NIFTY MIDSML 400": "Nifty MidSmallcap 400", "NIFTY TOTAL MKT": "Nifty Total Market"}
GOLD = {"GOLDBEES": "gold", "SILVERBEES": "silver"}
EQUITY_L = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"
ETF_LIST = "https://nsearchives.nseindia.com/content/equities/eq_etfseclist.csv"
# names people say that the company names do not contain (the Ask matches these as whole words)
ALIASES = {
    "TCS": ["tcs", "tata consultancy"], "INFY": ["infosys", "infy"], "RELIANCE": ["reliance", "ril", "reliance industries"],
    "HDFCBANK": ["hdfc bank"], "ICICIBANK": ["icici bank"], "SBIN": ["sbi", "state bank", "state bank of india"], "AXISBANK": ["axis bank"],
    "KOTAKBANK": ["kotak", "kotak bank", "kotak mahindra bank"], "INDUSINDBK": ["indusind", "indusind bank"], "BHARTIARTL": ["airtel", "bharti airtel"],
    "LT": ["l&t", "larsen", "larsen and toubro"], "ITC": ["itc"], "HINDUNILVR": ["hul", "hindustan unilever"], "TMPV": ["tata motors", "tata motors pv"],
    "TMCV": ["tata motors cv", "tata motors commercial"], "MARUTI": ["maruti", "maruti suzuki"], "M&M": ["mahindra", "m&m", "mahindra and mahindra"],
    "ASIANPAINT": ["asian paints"], "BAJFINANCE": ["bajaj finance"], "BAJAJFINSV": ["bajaj finserv"], "BAJAJ-AUTO": ["bajaj auto"], "WIPRO": ["wipro"],
    "HCLTECH": ["hcl tech", "hcl technologies", "hcl"], "TECHM": ["tech mahindra"], "SUNPHARMA": ["sun pharma"], "DRREDDY": ["dr reddy", "dr reddys", "dr. reddy's"],
    "CIPLA": ["cipla"], "DIVISLAB": ["divis", "divi's labs"], "ONGC": ["ongc"], "NTPC": ["ntpc"], "POWERGRID": ["power grid"], "COALINDIA": ["coal india"],
    "TATASTEEL": ["tata steel"], "JSWSTEEL": ["jsw steel"], "HINDALCO": ["hindalco"], "ADANIENT": ["adani enterprises", "adani"], "ADANIPORTS": ["adani ports"],
    "ULTRACEMCO": ["ultratech", "ultratech cement"], "TITAN": ["titan"], "NESTLEIND": ["nestle"], "EICHERMOT": ["eicher", "royal enfield"],
    "HEROMOTOCO": ["hero motocorp", "hero honda"], "BRITANNIA": ["britannia"], "TATAPOWER": ["tata power"], "JIOFIN": ["jio financial", "jio finance", "jiofin"],
    "LICI": ["lic", "life insurance corporation"], "IRFC": ["irfc"], "ETERNAL": ["zomato", "eternal"], "PAYTM": ["paytm"], "NYKAA": ["nykaa"],
    "IDEA": ["vodafone idea", "vi"], "YESBANK": ["yes bank"], "TATACHEM": ["tata chemicals"], "MARICO": ["marico"], "UNITDSPR": ["united spirits"],
    "NATIONALUM": ["nalco", "national aluminium"], "IEX": ["iex", "indian energy exchange"], "NETWORK18": ["network18", "network 18"],
    "KARURVYSYA": ["karur vysya", "karur vysya bank"], "HAL": ["hal", "hindustan aeronautics"], "BEL": ["bel", "bharat electronics"], "IRCTC": ["irctc"],
    "DMART": ["dmart", "avenue supermarts"], "PIDILITIND": ["pidilite"], "DABUR": ["dabur"], "GODREJCP": ["godrej consumer"], "TRENT": ["trent", "zudio"],
    "NIFTYBEES": ["nifty bees", "niftybees", "nifty bees etf", "nippon nifty bees", "nippon india nifty bees"], "GOLDBEES": ["gold bees", "goldbees", "gold bees etf"],
    "SILVERBEES": ["silver bees", "silverbees"], "BANKBEES": ["bank bees", "bankbees"], "JUNIORBEES": ["junior bees", "juniorbees"],
    "LIQUIDBEES": ["liquid bees", "liquidbees"], "ITBEES": ["it bees", "itbees"]}
DROP_WORDS = r"\b(limited|ltd\.?|corporation|corp\.?|company|co\.|the|and|india)\b"


def _out() -> Path:
    return paths.manifest_dir() / "quotebook.json"


def _names_out() -> Path:
    return paths.manifest_dir() / "quotebook_names.json"


def _ref_dir() -> Path:
    d = paths.data_dir() / "bronze" / "reference"
    d.mkdir(parents=True, exist_ok=True)
    return d


def refresh_names(force: bool = False) -> dict:
    """NSE's equity list and ETF list (public CSVs), kept in bronze/reference; fetched again when older than 7 days."""
    import requests

    from india import nse
    out = {}
    for url, fn in ((EQUITY_L, "EQUITY_L.csv"), (ETF_LIST, "eq_etfseclist.csv")):
        p = _ref_dir() / fn
        if p.exists() and not force and (dt.datetime.now().timestamp() - p.stat().st_mtime) < 7 * 86400:
            out[fn] = "kept"
            continue
        try:
            r = requests.get(url, headers=nse.HEADERS, timeout=30)
            if r.status_code == 200 and len(r.content) > 1000 and b"," in r.content[:200]:
                p.write_bytes(r.content)
                out[fn] = f"fetched {len(r.content)} bytes"
            else:
                out[fn] = f"status {r.status_code}, kept the old copy" if p.exists() else f"status {r.status_code}"
        except Exception as e:  # noqa: BLE001
            out[fn] = f"{type(e).__name__}: kept the old copy" if p.exists() else f"{type(e).__name__}"
    return out


def _norm(s: str) -> str:
    s = re.sub(DROP_WORDS, " ", str(s or "").lower().replace("&", " and "))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", s)).strip()


def name_map() -> dict:
    """symbol -> {name, kind (stock|etf), underlying, industry, aliases}; from NSE's lists, the industry labels and Kite's instrument names."""
    names: dict[str, dict] = {}
    eq = _ref_dir() / "EQUITY_L.csv"
    if eq.exists():
        d = pd.read_csv(eq)
        d.columns = [c.strip().upper() for c in d.columns]
        if "NAME OF COMPANY" in d.columns:
            for sym, nm in zip(d["SYMBOL"].astype(str).str.strip(), d["NAME OF COMPANY"].astype(str).str.strip()):
                names[sym] = {"name": nm, "kind": "stock"}
    et = _ref_dir() / "eq_etfseclist.csv"
    if et.exists():
        d = pd.read_csv(et)
        d.columns = [c.strip() for c in d.columns]
        for r in d.to_dict("records"):
            sym = str(r.get("Symbol", "")).strip()
            if sym:
                names[sym] = {"name": str(r.get("SecurityName", sym)).strip(), "kind": "etf", "underlying": str(r.get("Underlying Asset", "")).strip()}
    ki = sorted((paths.data_dir() / "bronze" / "kite_instruments").glob("NSE_*.csv"))
    if ki:
        d = pd.read_csv(ki[-1], usecols=["tradingsymbol", "name", "segment"])
        for sym, nm in zip(d.loc[d["segment"] == "NSE", "tradingsymbol"], d.loc[d["segment"] == "NSE", "name"]):
            if not (isinstance(sym, str) and isinstance(nm, str)):
                continue
            if sym not in names:
                names[sym] = {"name": nm.title(), "kind": "stock"}
            elif names[sym].get("kind") == "etf":           # NSE's ETF list has codes ("NIPINDETFGOLDBEES"); Kite has the readable name
                names[sym]["name"] = nm.title().replace("Etf", "ETF").replace("Bees", "BeES")
    lab = paths.data_dir() / "silver" / "reference" / "industry_labels.parquet"
    if lab.exists():
        d = pd.read_parquet(lab, columns=["symbol", "company", "industry"])
        for sym, comp, ind in zip(d["symbol"], d["company"], d["industry"]):
            e = names.setdefault(sym, {"name": comp, "kind": "stock"})
            e["industry"] = ind
            if not e.get("name"):
                e["name"] = comp
    for sym, al in ALIASES.items():
        names.setdefault(sym, {"name": sym, "kind": "etf" if sym.endswith("BEES") else "stock"})["aliases"] = al
    for sym, e in names.items():
        e["norm"] = _norm(e.get("name", ""))
    return names


def _ret(c: np.ndarray, n: int) -> float | None:
    return float(c[-1] / c[-1 - n] - 1) if len(c) > n and c[-1 - n] > 0 else None


def _start_index(d: np.ndarray, k: str) -> int | None:
    """Index of the last close on or before the calendar date one window back (1w = 7 days, 1m = a calendar month, 1y = 12 months),
    the way returns are quoted everywhere; a session count drifts (252 sessions is more than a year on NSE). None if the data is too short."""
    if k == "1d":
        return len(d) - 2 if len(d) >= 2 else None
    end = pd.Timestamp(d[-1])
    back = end - (pd.Timedelta(days=7) if k == "1w" else pd.DateOffset(months={"1m": 1, "3m": 3, "6m": 6, "1y": 12}[k]))
    i = int(np.searchsorted(d, np.datetime64(back), side="right")) - 1
    if i < 0 or (k != "1w" and (pd.Timestamp(d[0]) > back)):
        return None
    return i


def _r(x, nd=4):
    return None if x is None or (isinstance(x, float) and not np.isfinite(x)) else round(float(x), nd)


def _series_stats(dates: pd.Series, c: np.ndarray, hi: np.ndarray, lo: np.ndarray, nifty: dict | None = None) -> dict:
    from india import technicals as tx
    s = pd.Series(c)
    out = {"as_of": str(pd.Timestamp(dates.iloc[-1]).date()), "close": _r(c[-1], 2), "sessions": int(len(c))}
    dv = pd.to_datetime(dates).values.astype("datetime64[ns]")
    for k in WINDOWS:
        i = _start_index(dv, k)
        r = float(c[-1] / c[i] - 1) if i is not None and c[i] > 0 else None
        out[f"chg_{k}"] = _r(r)
        if nifty is not None and r is not None and nifty.get(f"chg_{k}") is not None:
            out[f"vs_nifty_{k}"] = _r(r - nifty[f"chg_{k}"])
    yr = pd.Timestamp(dates.iloc[-1]).year
    prev = np.flatnonzero(pd.to_datetime(dates).dt.year.values < yr)
    if len(prev):
        out["chg_ytd"] = _r(c[-1] / c[prev[-1]] - 1)
        if nifty is not None and nifty.get("chg_ytd") is not None:
            out["vs_nifty_ytd"] = _r(out["chg_ytd"] - nifty["chg_ytd"])
    w = int(len(c) - np.searchsorted(dv, np.datetime64(pd.Timestamp(dv[-1]) - pd.DateOffset(years=1)), side="right"))   # sessions in the last 52 weeks
    w = max(1, min(w, len(c)))
    h52, l52 = float(np.nanmax(hi[-w:])), float(np.nanmin(lo[-w:]))
    out.update({"high_52w": _r(h52, 2), "low_52w": _r(l52, 2), "vs_high_52w": _r(c[-1] / h52 - 1), "vs_low_52w": _r(c[-1] / l52 - 1), "window_52w": w})
    for n in (20, 50, 200):
        m = tx.sma(s, n).iloc[-1]
        out[f"sma{n}"] = _r(m, 2)
        out[f"vs_sma{n}"] = _r(c[-1] / m - 1) if m == m else None
    rsi = tx.rsi_wilder(s).iloc[-1]
    out["rsi14"] = _r(rsi, 1)
    d = s.pct_change()
    out["vol_60d"] = _r(d.tail(60).std() * np.sqrt(252)) if len(d) > 30 else None
    tail = d.tail(60)
    if tail.notna().any():
        k = tail.abs().idxmax()
        out["biggest_day_60d"] = {"date": str(pd.Timestamp(dates.iloc[k]).date()), "move": _r(d.iloc[k])}
    return out


def _index_block(names: dict, since: str) -> tuple[dict, dict]:
    from india import technicals as tx
    df = tx.index_rows(list(names), since)
    out = {}
    nifty = None
    for nm in ["NIFTY 50"] + [n for n in names if n != "NIFTY 50"]:
        g = df[df["index_name"] == nm].dropna(subset=["close"]).sort_values("date")
        if len(g) < 30:
            continue
        c = g["close"].astype(float).values
        st = _series_stats(g["date"].reset_index(drop=True), c, c, c, nifty)
        st["name"] = names.get(nm, nm)
        st["index"] = nm
        if nm == "NIFTY 50":
            nifty = st
        out[nm] = st
    return out, nifty or {}


def build() -> dict:
    from india import paper
    paths.ensure()
    since = (dt.date.today() - dt.timedelta(days=455)).isoformat()
    idx_names = {**BROAD, **SECTORS}
    idx, nifty = _index_block(idx_names, since)
    df = paper.load_adjusted()
    df = df.sort_values(["sid", "date"])
    last_day = df["date"].max()
    nm = name_map()
    quotes = {}
    for sid, g in df.groupby("sid", sort=False):
        if g["date"].iloc[-1] < last_day - pd.Timedelta(days=10) or len(g) < 5:
            continue                                  # not traded in the last ten days: suspended, delisted or renamed
        sym = str(g["symbol"].iloc[-1])
        fund = bool(g["is_fund"].iloc[-1])
        to20 = float(g["turnover"].tail(20).mean()) / 1e7 if "turnover" in g else 0.0
        if not fund and to20 < MIN_TURNOVER_CR:
            continue
        c = g["adj_close"].astype(float).values
        st = _series_stats(g["date"].reset_index(drop=True), c, g["adj_high"].astype(float).values, g["adj_low"].astype(float).values, nifty)
        st["close"] = _r(float(g["close"].iloc[-1]), 2)                       # the traded price, not the adjusted one
        st["prev_close"] = _r(float(g["close"].iloc[-2]), 2) if len(g) > 1 else None
        st["avg_volume_20d"] = int(g["volume"].tail(20).mean())
        st["avg_turnover_20d_cr"] = _r(to20, 2)
        pc = g["adj_close"].astype(float).pct_change().reset_index(drop=True)
        jumps = np.flatnonzero((pc.abs() > 0.35).values)
        st["price_jump_unadjusted"] = bool(len(jumps))                      # a >35% one-day move left in the data: a corporate action not adjusted
        st["price_jump"] = ({"date": str(pd.Timestamp(g["date"].iloc[jumps[-1]]).date()), "move": _r(float(pc.iloc[jumps[-1]]))}
                            if len(jumps) else None)                         # the newest one: windows that start before it are distorted
        e = nm.get(sym, {})
        st.update({"symbol": sym, "kind": "etf" if fund else "stock", "name": e.get("name") or sym, "industry": e.get("industry"),
                   "underlying": e.get("underlying")})
        quotes[sym] = st
    ranked = sorted([v for k, v in idx.items() if k in SECTORS and v.get("chg_3m") is not None], key=lambda v: -v["chg_3m"])
    for i, v in enumerate(ranked, 1):
        v["rank_3m"] = i
    sectors = [{k: v.get(k) for k in ("index", "name", "as_of", "close", "chg_1w", "chg_1m", "chg_3m", "chg_6m", "chg_1y", "vs_nifty_1m", "vs_nifty_3m",
                                      "vs_sma50", "vs_sma200", "vs_high_52w", "rank_3m")} for v in ranked]
    broad = [{k: v.get(k) for k in ("index", "name", "as_of", "close", "chg_1w", "chg_1m", "chg_3m", "chg_6m", "chg_1y", "vs_sma50", "vs_sma200",
                                    "high_52w", "vs_high_52w", "window_52w")} for k2, v in idx.items() if k2 in BROAD]
    gold = {GOLD[s]: {k: quotes[s].get(k) for k in ("symbol", "name", "as_of", "close", "chg_1w", "chg_1m", "chg_3m", "chg_6m", "chg_1y", "chg_ytd",
                                                     "high_52w", "low_52w", "vs_high_52w", "vol_60d")} for s in GOLD if s in quotes}
    out = {"rules": RULES, "built_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "as_of": str(pd.Timestamp(last_day).date()),
           "basis": ("daily closes as of each row's date; returns from prices adjusted for splits and bonuses, over calendar windows (1w = the "
                     "close on or before the same date a week back, 1m a month, 1y a year); 1y is the longest window (the reader's "
                     "460-day cap); 52-week high/low from daily highs and lows (closes for indices); vs_nifty = the stock's change minus the Nifty 50's "
                     "over the same window; vol_60d = annualised daily swings"),
           "nifty": {k: nifty.get(k) for k in ("as_of", "close", "chg_1d", "chg_1w", "chg_1m", "chg_3m", "chg_6m", "chg_1y", "chg_ytd")},
           "counts": {"stocks": sum(1 for v in quotes.values() if v["kind"] == "stock"), "etfs": sum(1 for v in quotes.values() if v["kind"] == "etf")},
           "filter": f"stocks with at least Rs {MIN_TURNOVER_CR:g} crore traded a day on average over 20 sessions; every ETF",
           "quotes": quotes, "sectors": sectors, "broad": broad, "gold": gold,
           "gold_note": ("gold and silver in rupees through Nippon India Gold BeES and Silver BeES (exchange-traded funds that track the domestic "
                         "price); these are market prices, which can sit a little above or below the fund's NAV, so a gold fund's NAV return can "
                         "differ slightly")}
    _out().write_text(json.dumps(out, default=str))
    small = {s: {k: v for k, v in e.items() if k in ("name", "kind", "underlying", "industry", "aliases", "norm")} for s, e in nm.items()}
    for s in small:
        small[s]["liquid"] = s in quotes
    _names_out().write_text(json.dumps(small))
    return {"as_of": out["as_of"], **out["counts"], "sectors": len(sectors), "broad": len(broad), "gold": list(gold), "names": len(small)}


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "build"
    if cmd == "names":
        print(json.dumps(refresh_names(force=True), indent=1))
    else:
        print(json.dumps(refresh_names(), indent=1))
        print(json.dumps(build(), indent=1))
