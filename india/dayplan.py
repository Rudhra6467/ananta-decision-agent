"""The pre-open day plan (Market Brain daily cycle, step 1; v1 of 19 Oct 2026).

  python -m india.dayplan        writes paper/dayplans/<next session>.json and one pre-open forecast in the forecast ledger

v1 contents, honestly limited:
- the next NSE session (NSE holiday master, refreshed daily; manifests/nse_holidays.json)
- the overnight world: last values and one-day changes of the S&P 500, Nasdaq, US VIX, Brent, USD/INR and the US 10-year (FRED, each with its
  own date so staleness shows), India's last close context (Nifty 50, Bank Nifty, India VIX against their 50/200-day averages, through the
  logged paper_context purpose) and the last published FII/DII cash figures (NSE, saved daily to bronze/fiidii, which also starts that history)
- the forecast: CLIMATOLOGY only, the share of up / flat / down Nifty sessions 2005-2023 with a +/-0.3% neutral band. It has no skill by
  design: it is the baseline every later forecast (analogues, event types, playbooks) must beat in the ledger's scores.
- no GIFT Nifty (no free source wired yet); scheduled events join once the event registry's calendars are loaded.
"""
from __future__ import annotations

import datetime as dt
import json
import sys

import pandas as pd

from india import forecast, nse, paths, sealed

D = paths.data_dir()
FRED = {"SP500": "SP500", "NASDAQ": "NASDAQCOM", "USVIX": "VIXCLS", "BRENT_SPOT_EUROPE": "DCOILBRENTEU", "USDINR": "DEXINUS", "US10Y": "DGS10"}


def holidays(refresh: bool = True) -> set[dt.date]:
    p = paths.manifest_dir() / "nse_holidays.json"
    if refresh:
        try:
            st, body, _ = nse.Fetcher(rate_s=1.0).get("https://www.nseindia.com/api/holiday-master?type=trading")
            if st == 200 and body.strip().startswith(b"{"):
                p.write_bytes(body)
        except Exception:
            pass
    src = p if p.exists() else paths.manifest_dir() / "nse_holidays_2026.json"
    if not src.exists():
        return set()
    d = json.loads(src.read_text())
    return {dt.datetime.strptime(x["tradingDate"], "%d-%b-%Y").date() for x in d.get("CM", [])}


def next_session(after: dt.date | None = None) -> dt.date:
    hol = holidays()
    ist_now = dt.datetime.now(dt.timezone(dt.timedelta(hours=5, minutes=30)))
    d = after or (ist_now.date() if ist_now.time() < dt.time(9, 15) else ist_now.date() + dt.timedelta(days=1))
    while d.weekday() >= 5 or d in hol:
        d += dt.timedelta(days=1)
    return d


def overnight() -> dict:
    mac = pd.read_parquet(next(p for p in (D / "silver/macro").iterdir() if p.suffix == ".parquet"))
    out = {}
    for k, s in FRED.items():
        x = mac[mac["series"] == s].dropna().sort_values("date")
        if len(x) >= 2:
            a, b = x.iloc[-2], x.iloc[-1]
            chg = (b["value"] - a["value"]) if k == "US10Y" else (b["value"] / a["value"] - 1)
            out[k] = {"date": str(pd.Timestamp(b["date"]).date()), "value": float(b["value"]), "change": float(chg), "unit": "pp" if k == "US10Y" else "return"}
    since = (dt.date.today() - dt.timedelta(days=420)).isoformat()
    ix = sealed.read_index("paper_context", since, ["NIFTY 50", "NIFTY BANK", "INDIA VIX"])
    for name, g in ix.groupby("index_name"):
        g = g.sort_values("date")
        c = g["close"]
        out[name] = {"date": str(g["date"].iloc[-1])[:10], "close": float(c.iloc[-1]), "d1": float(c.iloc[-1] / c.iloc[-2] - 1),
                     "vs_sma50": float(c.iloc[-1] / c.tail(50).mean() - 1), "vs_sma200": float(c.iloc[-1] / c.tail(200).mean() - 1) if len(c) >= 200 else None}
    try:
        st, body, _ = nse.Fetcher(rate_s=1.0).get("https://www.nseindia.com/api/fiidiiTradeReact")
        if st == 200:
            rows = json.loads(body)
            day = rows[0]["date"] if rows else dt.date.today().isoformat()
            p = paths.bronze("fiidii") / f"{dt.datetime.strptime(day, '%d-%b-%Y'):%Y%m%d}.json"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(body)
            out["FII_DII"] = {r["category"]: {"date": r["date"], "net_crore": float(r["netValue"])} for r in rows}
    except Exception as e:
        out["FII_DII"] = {"error": f"{type(e).__name__}"}
    return out


def climatology(band: float = 0.003) -> dict:
    d = pd.read_parquet(D / "silver/kite_index/day/day.parquet")
    n = d[(d["index_name"] == "NIFTY 50")].drop_duplicates("date").sort_values("date")
    n = n[(pd.to_datetime(n["date"]) >= "2005-01-01") & (pd.to_datetime(n["date"]) < "2024-01-01")]
    r = n["close"].pct_change().dropna()
    return {"bull": float((r > band).mean()), "bear": float((r < -band).mean()), "neutral": float(((r >= -band) & (r <= band)).mean()), "sessions": int(len(r))}


def run() -> dict:
    s = next_session()
    out = D / "paper" / "dayplans" / f"{s}.json"
    if out.exists():
        return {"session": str(s), "note": "already written", "path": str(out)}
    snap = overnight()
    clim = climatology()
    p = {k: clim[k] for k in ("bull", "bear", "neutral")}
    tot = sum(p.values())
    p = {k: v / tot for k, v in p.items()}
    fc = forecast.write("NIFTY 50", s.isoformat(), p, horizon_sessions=1, invalidation="none (climatology baseline)",
                        basis=f"climatology: Nifty 50 sessions 2005-2023 (n={clim['sessions']}), neutral band +/-0.3%; no skill by design",
                        kind="pre_open", notes="day plan v1")
    plan = {"session": str(s), "written_at": fc["made_at"], "overnight": snap, "forecast_id": fc["forecast_id"], "forecast": p,
            "scenarios_text": {"bull": "Nifty closes more than 0.3% up", "bear": "Nifty closes more than 0.3% down", "neutral": "within +/-0.3%"},
            "limits": ["no GIFT Nifty", "no event calendar yet", "climatology forecast only"]}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(plan, indent=1, default=str))
    return {"session": str(s), "forecast_id": fc["forecast_id"], "forecast": {k: round(v, 3) for k, v in p.items()}, "path": str(out)}


if __name__ == "__main__":
    print(json.dumps(run(), indent=1, default=str))
