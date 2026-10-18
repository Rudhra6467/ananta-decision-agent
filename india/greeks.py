"""Implied volatility and Greeks for index options from the daily F&O bhavcopy (Black-76, forward taken from the same-expiry future).

  python -m india.greeks build [year ...]     silver/fo_greeks/year=*/part.parquet  (2024+ goes to sealed/silver)

Why Black-76 on the future: no dividend or index-level input is needed, the future of the same expiry already carries them.
Inputs per row: option settle price (the exchange's own end-of-day price), forward = settle of the same-expiry index future that day,
T = calendar days to expiry / 365 (expiry is the close of the expiry day), flat discount rate RATE (declared; it barely moves an option that lives days).
Rows kept: NIFTY, BANKNIFTY, FINNIFTY, MIDCPNIFTY options with settle above intrinsic, T > 0, strike within 20% of the forward, and either volume or open interest.
Columns: date, symbol, expiry, strike, opt_type, settle, fwd, fwd_source (future | parity), T, iv, delta, gamma, vega_1pct, theta_day, moneyness (ln K/F), volume, open_interest, flag.
flag: ok | no_future (no forward could be built) | below_intrinsic | no_iv. IV is solved by bisection (60 steps, 0.01%..500%); a price under intrinsic or beyond the bracket yields no_iv.
These are END-OF-DAY estimates from exchange settlement prices, not tradable quotes: labelled so in any study that uses them.
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from india import catalog, paths, silver

RATE = 0.065
SYMS = ("NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY")

try:
    from scipy.special import ndtr as _N
except Exception:  # pragma: no cover
    from math import erf, sqrt

    _N = np.vectorize(lambda x: 0.5 * (1 + erf(x / sqrt(2))))


def _pdf(x):
    return np.exp(-0.5 * x * x) / np.sqrt(2 * np.pi)


def black76(F, K, T, sig, call: np.ndarray, r: float = RATE):
    sd = sig * np.sqrt(T)
    d1 = (np.log(F / K) + 0.5 * sd * sd) / sd
    d2 = d1 - sd
    df = np.exp(-r * T)
    c = df * (F * _N(d1) - K * _N(d2))
    p = df * (K * _N(-d2) - F * _N(-d1))
    return np.where(call, c, p), d1, df


def implied_vol(price, F, K, T, call, r: float = RATE) -> np.ndarray:
    lo = np.full(len(price), 1e-4)
    hi = np.full(len(price), 5.0)
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        val, _, _ = black76(F, K, T, mid, call, r)
        up = val < price
        lo = np.where(up, mid, lo)
        hi = np.where(up, hi, mid)
    iv = 0.5 * (lo + hi)
    val, _, _ = black76(F, K, T, iv, call, r)
    bad = (np.abs(val - price) > np.maximum(0.05, 0.01 * price)) | (iv > 4.99) | (iv < 1.1e-4)
    return np.where(bad, np.nan, iv)


def greeks(F, K, T, iv, call, r: float = RATE) -> dict:
    sd = iv * np.sqrt(T)
    d1 = (np.log(F / K) + 0.5 * sd * sd) / sd
    df = np.exp(-r * T)
    delta = df * np.where(call, _N(d1), _N(d1) - 1)
    gamma = df * _pdf(d1) / (F * sd)
    vega = df * F * _pdf(d1) * np.sqrt(T)  # per 1.00 of vol
    # theta by finite difference over one calendar day (keeps rate and carry terms right)
    T1 = np.maximum(T - 1 / 365, 1e-6)
    v0, _, _ = black76(F, K, T, iv, call, r)
    v1, _, _ = black76(F, K, T1, iv, call, r)
    return {"delta": delta, "gamma": gamma, "vega_1pct": vega / 100, "theta_day": v1 - v0}


def build_year(year: int) -> dict:
    import duckdb

    root = paths.data_dir()
    src = silver._year_target("fo_bhavcopy", year)
    if not src.exists():
        return {"year": year, "rows": 0, "note": "no F&O silver"}
    con = duckdb.connect()
    syms = ",".join(f"'{s}'" for s in SYMS)
    df = con.execute(f"""
        select o.date, o.symbol, o.expiry, o.strike, o.opt_type, o.settle, o.close, o.volume, o.open_interest, f.settle as fwd
        from read_parquet('{src}') o
        left join (select date, symbol, expiry, max(settle) as settle from read_parquet('{src}') where instrument = 'FUTIDX' group by 1, 2, 3) f
               on f.date = o.date and f.symbol = o.symbol and f.expiry = o.expiry
        where o.instrument = 'OPTIDX' and o.symbol in ({syms}) and o.opt_type is not null and o.settle > 0 and (o.volume > 0 or o.open_interest > 0)""").df()
    con.close()
    if df.empty:
        return {"year": year, "rows": 0}
    df["date"] = pd.to_datetime(df["date"])
    df["expiry"] = pd.to_datetime(df["expiry"])
    df["T"] = ((df["expiry"] - df["date"]).dt.days + 0.0) / 365.0
    df["fwd_source"] = np.where(df["fwd"].notna() & (df["fwd"] > 0), "future", "")
    need = df["fwd_source"] == ""
    if need.any():  # weekly expiries have no future of their own: forward from put-call parity at the three strikes where call and put prices are closest
        ce = df[df["opt_type"] == "CE"][["date", "symbol", "expiry", "strike", "settle", "T"]]
        pe = df[df["opt_type"] == "PE"][["date", "symbol", "expiry", "strike", "settle"]]
        pr = ce.merge(pe, on=["date", "symbol", "expiry", "strike"], suffixes=("_c", "_p"))
        pr["gap"] = (pr["settle_c"] - pr["settle_p"]).abs()
        pr["F"] = pr["strike"] + np.exp(RATE * pr["T"]) * (pr["settle_c"] - pr["settle_p"])
        pr = pr.sort_values("gap").groupby(["date", "symbol", "expiry"]).head(3)
        fpar = pr.groupby(["date", "symbol", "expiry"])["F"].median().rename("fwd_par").reset_index()
        df = df.merge(fpar, on=["date", "symbol", "expiry"], how="left")
        use_par = (df["fwd_source"] == "") & df["fwd_par"].notna()
        df.loc[use_par, "fwd"] = df.loc[use_par, "fwd_par"]
        df.loc[use_par, "fwd_source"] = "parity"
        df = df.drop(columns=["fwd_par"])
    df["flag"] = "ok"
    df.loc[df["fwd"].isna() | (df["fwd"] <= 0), "flag"] = "no_future"
    df.loc[df["T"] <= 0, "flag"] = "no_future"
    ok = df["flag"] == "ok"
    ok &= (np.abs(np.log(df["strike"].where(ok, 1) / df["fwd"].where(ok, 1))) < 0.2)
    call = (df["opt_type"] == "CE").values
    F, K, T, P = (df[c].values.astype(float) for c in ("fwd", "strike", "T", "settle"))
    disc = np.exp(-RATE * np.where(T > 0, T, 0))
    intrinsic = disc * np.where(call, np.maximum(F - K, 0), np.maximum(K - F, 0))
    below = ok.values & (P < intrinsic - 1e-6)
    df.loc[below, "flag"] = "below_intrinsic"
    use = ok.values & ~below
    iv = np.full(len(df), np.nan)
    if use.any():
        iv[use] = implied_vol(P[use], F[use], K[use], T[use], call[use])
        g = greeks(F[use], K[use], T[use], iv[use], call[use])
    df["iv"] = iv
    for k in ("delta", "gamma", "vega_1pct", "theta_day"):
        df[k] = np.nan
        if use.any():
            df.loc[use, k] = g[k]
    df.loc[use & np.isnan(iv), "flag"] = "no_iv"
    df["moneyness"] = np.log(df["strike"] / df["fwd"])
    keep = df[df["flag"].isin(["ok", "no_iv", "below_intrinsic"]) | (df["flag"] == "no_future")][
        ["date", "symbol", "expiry", "strike", "opt_type", "settle", "fwd", "fwd_source", "T", "iv", "delta", "gamma", "vega_1pct", "theta_day", "moneyness", "volume", "open_interest", "flag"]]
    keep = keep.assign(date=keep["date"].dt.date, expiry=keep["expiry"].dt.date)
    out = silver._year_target("fo_greeks", year)
    out.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pandas(keep, preserve_index=False), out, compression="zstd")
    share = keep["flag"].value_counts(normalize=True).round(4).to_dict()
    return {"year": year, "rows": len(keep), "flags": share, "iv_median_atm": float(keep[(keep["flag"] == "ok") & (keep["moneyness"].abs() < 0.01)]["iv"].median())}


if __name__ == "__main__":
    paths.ensure()
    if sys.argv[1] == "build":
        years = [int(y) for y in sys.argv[2:]] or silver.complete_years("fo_bhavcopy")
        for y in years:
            print(build_year(y), flush=True)
        catalog.heartbeat("greeks.build", True, f"years {years}")
