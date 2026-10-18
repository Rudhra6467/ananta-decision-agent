"""Portfolio review (V06, first version): the father's holdings read through the engine's lens. SUGGESTIONS FOR MADHAV ONLY: nothing here places,
modifies or cancels an order, and nothing leaves this Mac (the ledger is not synced; the review file is written under reports/, which is not synced).

  python -m india.portfolio            reports/portfolio_<date>.md from the latest ledger snapshot

For each holding: weight, gain, trend (against the 50- and 200-day averages), the saturation flags that VALIDATED in E04 (more than 20% above the 50-day,
or up more than 25% in 20 sessions: historically about 2-3% weaker over the next 20 sessions), liquidity rank, 14-day range as % of price, distance from the
one-year high, unconfirmed corporate actions, today's engine candidacy (BRK/PULL), and the latest filed results when the fundamentals pull has them.
Then concentration, and replacement candidates: today's BRK/PULL candidates in the liquid universe that are not saturated. Every tag says which study stands
behind it; a tag without a validated study is labelled descriptive.
"""
from __future__ import annotations

import datetime as dt
import json
import sys

import numpy as np
import pandas as pd

from india import paths, paper, settings


def _latest_ledger() -> dict | None:
    files = sorted(paths.bronze("ledger").glob("*.json"))
    return json.loads(files[-1].read_text()) if files else None


def _fundamentals() -> pd.DataFrame:
    frames = []
    for part in ("silver", "sealed/silver"):
        p = paths.data_dir() / part / "fundamentals" / "results.parquet"
        if p.exists():
            frames.append(pd.read_parquet(p))
    return pd.concat(frames) if frames else pd.DataFrame()


def build() -> str:
    led = _latest_ledger()
    if not led:
        return "no ledger snapshot yet"
    h = pd.DataFrame(led["holdings"])
    h["value"] = h["quantity"] * h["last_price"]
    h["weight"] = h["value"] / h["value"].sum()
    h["gain"] = h["last_price"] / h["average_price"] - 1
    df = paper.load_adjusted()
    last = df["date"].max()
    f = paper.features(df, last, settings.load()["stock"]["min_price"])
    sig = paper.signals(f, last)
    cand = {(camp, sid) for camp, d in sig.items() if camp != "CTL" for sid in d["sid"]}
    names = pd.read_parquet(paths.data_dir() / "silver/security_master/names.parquet", columns=["isin", "entity"]).drop_duplicates("isin")
    h = h.merge(names, on="isin", how="left")
    h["sid"] = h["entity"].fillna(h["tradingsymbol"])
    fx = f.set_index("sid")
    hi250 = df[df["date"] > last - pd.Timedelta(days=365)].groupby("sid")["adj_high"].max()
    fund = _fundamentals()
    L = [f"# Portfolio review, {dt.date.today().isoformat()} (ledger {led['taken_at']}, prices through {last.date()})", "",
         "Suggestions for Madhav to consider; no order is placed by Ananta. Tags cite the study behind them.", "",
         "| holding | weight | gain | vs 50d | vs 200d | 20d | liq rank | range % | off 1y high | tags |", "|---|---|---|---|---|---|---|---|---|---|"]
    for r in h.sort_values("weight", ascending=False).itertuples():
        tags = []
        if r.sid in fx.index:
            x = fx.loc[r.sid]
            if x["dist_sma50"] > 0.2:
                tags.append("SATURATED >20% over 50d (E04 VALIDATED: weaker next 20 sessions)")
            if x["ret_20"] > 0.25:
                tags.append("SATURATED +25% in 20d (E04 VALIDATED)")
            if x["dist_sma200"] < 0:
                tags.append("below 200d (descriptive)")
            if x.get("ca_ambiguous_200", False):
                tags.append("unconfirmed corporate action in 200 sessions: indicators unreliable")
            for camp in ("BRK", "PULL"):
                if (camp, r.sid) in cand:
                    tags.append(f"today's {camp} candidate")
            off = x["close"] / hi250.get(r.sid, np.nan) - 1
            L.append(f"| {r.tradingsymbol} | {r.weight:.1%} | {r.gain:+.1%} | {x['dist_sma50']:+.1%} | {x['dist_sma200']:+.1%} | {x['ret_20']:+.1%} | {int(x['liq_rank'])} | "
                     f"{x['atr14'] / x['close']:.1%} | {off:+.1%} | {'; '.join(tags) or '-'} |")
        else:
            L.append(f"| {r.tradingsymbol} | {r.weight:.1%} | {r.gain:+.1%} | | | | | | | not in the engine's universe (short history, price under Rs 10, or a fund) |")
    L += ["", f"Concentration: largest holding {h['weight'].max():.1%}; top three {h['weight'].nlargest(3).sum():.1%}; {len(h)} holdings.", ""]
    if not fund.empty:
        fund = fund.sort_values("available_at")
        got = fund[fund["isin"].isin(h["isin"])].groupby("isin").tail(1)
        L += ["## Latest filed results (point in time; derived figures only)", "", "| holding | period end | filed | revenue growth vs same quarter last year | margin (PBT / revenue) |", "|---|---|---|---|---|"]
        for r in got.itertuples():
            prev = fund[(fund["isin"] == r.isin) & (fund["period_end"] < r.period_end)]
            yoy = None
            if len(prev) and pd.notna(r.revenue):
                same = prev[pd.to_datetime(prev["period_end"]).dt.month == pd.Timestamp(r.period_end).month]
                if len(same) and same["revenue"].iloc[-1]:
                    yoy = r.revenue / same["revenue"].iloc[-1] - 1
            sym = h.loc[h["isin"] == r.isin, "tradingsymbol"].iloc[0]
            m = (r.pbt / r.revenue) if pd.notna(r.revenue) and r.revenue else None
            L.append(f"| {sym} | {r.period_end} | {r.available_at} | {'' if yoy is None else f'{yoy:+.1%}'} | {'' if m is None else f'{m:.1%}'} |")
        miss = sorted(set(h["tradingsymbol"]) - set(h.loc[h["isin"].isin(got["isin"]), "tradingsymbol"]))
        L += ["", f"Not yet in the fundamentals pull: {', '.join(miss) or 'none'} (XBRL download in progress)."]
    else:
        L.append("Fundamentals: none parsed yet for these holdings (XBRL download in progress).")
    # replacements
    rep = []
    for camp in ("BRK", "PULL"):
        d = sig[camp]
        d = d[(d["liq_rank"] <= 250) & (d["dist_sma50"] <= 0.2) & (d["ret_20"] <= 0.25) & ~d["sid"].isin(h["sid"])]
        rep += [f"{r.symbol} ({camp}, liq {int(r.liq_rank)})" for r in d.head(8).itertuples()]
    L += ["", "## Replacement candidates to look at (today's engine candidates, liquid, not saturated)", "", ", ".join(rep) or "none today", "",
          "These come from the paper engine's entry rules, which have not beaten random entries on their own (E02); they are places to look, not picks."]
    text = "\n".join(L) + "\n"
    out = paths.data_dir() / "reports" / f"portfolio_{dt.date.today().isoformat()}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text)
    return text


if __name__ == "__main__":
    paths.ensure()
    print(build())
