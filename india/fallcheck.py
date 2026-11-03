"""The big-falls check (data audit step 6, 3 Nov 2026): every one-day fall of over 45% in a liquid stock (rank 500 or better) with no applied
split or bonus within 3 days, sorted into what it most likely is. Research years only (the features table ends 2023-12-29).

  python -m india.fallcheck        writes manifests/big_falls.json, registrations/big_falls_v1.csv and registrations/big_falls_v1.md

Each fall gets one label, from the evidence in this order:
  known_action_not_applied  the corporate-actions table holds a split or bonus within 3 days that was left out (apply = False)
  likely_missed_action      the fall is close to a split or bonus ratio (1/2, 1/3, 2/3, 1/5, 1/10 ...), the price stays down 20 sessions later,
                            and turnover in shares rises after it (more shares in issue), or a filing nearby names a split, bonus or sub-division
  likely_demerger           a filing within 60 days before names a demerger, scheme of arrangement or spin-off
  no_evidence_found         none of the above: a true fall (crash, fraud, result shock), or an action the check cannot see (filed under an
                            older symbol, a capital return, a merger swap); each needs a look before it is called a true price
Nothing is changed in the adjusted prices: the labels are evidence for Madhav and for a later fix of the corporate-actions table.
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

REG = Path(__file__).parent / "registrations"
FALL, RANK, ACT_DAYS, NEWS_DAYS = -0.45, 500, 3, 60
RATIOS = {"1:2 split or 1:1 bonus": 1 / 2, "1:3 / 2:1 bonus": 1 / 3, "3:2 bonus": 2 / 5, "1:4 / 3:1 bonus": 1 / 4, "1:5 split": 1 / 5,
          "1:10 split": 1 / 10, "2:5 split": 2 / 5, "1:2 bonus": 2 / 3, "3:4 bonus": 4 / 7, "1:20": 1 / 20}
TOL = 0.04
SPLIT_WORDS = re.compile(r"\b(?:split|sub-?division|sub divi|bonus|face value)\b", re.I)
DEMERGE_WORDS = re.compile(r"\b(?:de-?merger|demerge|scheme of arrangement|spin[- ]?off|hive[- ]?off)\b", re.I)


def nearest_ratio(r: float) -> tuple[str | None, float]:
    best = min(RATIOS.items(), key=lambda kv: abs(r / kv[1] - 1))
    return (best[0], best[1]) if abs(r / best[1] - 1) <= TOL else (None, float("nan"))


def classify(ratio: float, stays_down: bool, volume_up: float | None, known_unapplied: bool, split_news: bool, demerger_news: bool) -> str:
    if known_unapplied:
        return "known_action_not_applied"
    name, _ = nearest_ratio(ratio)
    if name and stays_down and ((volume_up or 0) >= 1.5 or split_news):
        return "likely_missed_action"
    if demerger_news:
        return "likely_demerger"
    if split_news and stays_down:
        return "likely_missed_action"
    return "no_evidence_found"


def _news() -> pd.DataFrame:
    frames = []
    a = paths.data_dir() / "silver" / "announce" / "announcements.parquet"
    if a.exists():
        x = pd.read_parquet(a, columns=["symbol", "an_dt", "category", "text"])
        frames.append(pd.DataFrame({"symbol": x["symbol"], "date": pd.to_datetime(x["an_dt"]).dt.normalize(), "text": x["category"].astype(str) + " " + x["text"].astype(str)}))
    p = paths.data_dir() / "silver" / "pr" / "announcements.parquet"
    if p.exists():
        x = pd.read_parquet(p)
        cols = [c for c in ("subject", "text", "category") if c in x]
        frames.append(pd.DataFrame({"symbol": x["symbol"], "date": pd.to_datetime(x["date"]), "text": x[cols].astype(str).agg(" ".join, axis=1)}))
    if not frames:
        return pd.DataFrame(columns=["symbol", "date", "text"])
    n = pd.concat(frames, ignore_index=True)
    return n[n["text"].str.contains(SPLIT_WORDS) | n["text"].str.contains(DEMERGE_WORDS)]


def run(write: bool = True) -> dict:
    D = paths.data_dir()
    feat = pd.read_parquet(paths.gold() / "features" / "daily.parquet", columns=["date", "sid", "symbol", "liq_rank", "c", "volume", "ret_1"])
    feat["date"] = pd.to_datetime(feat["date"])
    fx = pd.read_parquet(D / "silver" / "corporate_actions" / "factors.parquet", columns=["symbol", "ex_date", "kind", "factor", "apply", "status"])
    fx["ex_date"] = pd.to_datetime(fx["ex_date"])
    ev = feat[(feat["ret_1"] < FALL) & (feat["liq_rank"] <= RANK)].copy()
    applied = fx[fx["apply"].astype(bool) & fx["factor"].notna() & (fx["factor"] > 0)]
    def near(df, r):
        g = df[df["symbol"] == r.symbol]
        return g[(g["ex_date"] - r.date).abs() <= pd.Timedelta(days=ACT_DAYS)]
    ev = ev[[near(applied, r).empty for r in ev.itertuples()]]
    news = _news()
    by_sid = {s: g.sort_values("date").reset_index(drop=True) for s, g in feat[feat["sid"].isin(ev["sid"])].groupby("sid")}
    rows = []
    for r in ev.itertuples():
        g = by_sid[r.sid]
        i = int(g.index[g["date"] == r.date][0])
        prev_c = g["c"].iloc[i - 1] if i > 0 else np.nan
        ratio = float(r.c / prev_c) if prev_c else np.nan
        later = g["c"].iloc[i + 20] if i + 20 < len(g) else g["c"].iloc[-1]
        stays_down = bool(later < prev_c * 0.8)
        pre = g["volume"].iloc[max(0, i - 20):i].median()
        post = g["volume"].iloc[i + 1:i + 21].median()
        vol_up = float(post / pre) if pre and pre > 0 and pd.notna(post) else None
        unapplied = near(fx[~fx["apply"].astype(bool)], r)
        nn = news[(news["symbol"] == r.symbol) & (news["date"] >= r.date - pd.Timedelta(days=NEWS_DAYS)) & (news["date"] <= r.date + pd.Timedelta(days=ACT_DAYS))]
        split_news = bool(nn["text"].str.contains(SPLIT_WORDS).any())
        dem_news = bool(nn["text"].str.contains(DEMERGE_WORDS).any())
        name, _ = nearest_ratio(ratio) if pd.notna(ratio) else (None, None)
        label = classify(ratio, stays_down, vol_up, not unapplied.empty, split_news, dem_news)
        ex = nn["text"].iloc[0][:140] if len(nn) else ""
        rows.append({"date": r.date.date().isoformat(), "symbol": r.symbol, "sid": r.sid, "liq_rank": int(r.liq_rank), "fall_pct": round(100 * r.ret_1, 1),
                     "close_ratio": round(ratio, 4), "near_ratio": name or "", "down_after_20": stays_down,
                     "shares_traded_after_vs_before": round(vol_up, 2) if vol_up else None,
                     "unapplied_action": (unapplied["kind"].iloc[0] + " " + unapplied["status"].iloc[0]) if not unapplied.empty else "",
                     "filing_nearby": ex, "label": label})
    df = pd.DataFrame(rows).sort_values(["date", "symbol"]).reset_index(drop=True)
    df["year"] = df["date"].str[:4]
    labels = df["label"].value_counts().to_dict()
    since2010 = df[df["year"] >= "2010"]["label"].value_counts().to_dict()
    out = {"built_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "rules": "fallcheck-v1-2026-11-03", "falls": int(len(df)),
           "labels": labels, "labels_since_2010": since2010, "by_year": df.groupby("year")["label"].value_counts().unstack(fill_value=0).to_dict("index"),
           "to_fix": df[df["label"].isin(["known_action_not_applied", "likely_missed_action", "likely_demerger"])][["date", "symbol", "label", "near_ratio", "unapplied_action"]].to_dict("records")}
    if write:
        (paths.manifest_dir() / "big_falls.json").write_text(json.dumps(out, indent=1, default=str))
        df.drop(columns="year").to_csv(REG / "big_falls_v1.csv", index=False, lineterminator="\n")
        (REG / "big_falls_v1.md").write_text(markdown(out, df))
    return out


def markdown(o: dict, df: pd.DataFrame) -> str:
    words = {"known_action_not_applied": "a split or bonus is on file but was left out of the adjustment",
             "likely_missed_action": "looks like a split or bonus that is not on file",
             "likely_demerger": "a demerger or scheme was filed shortly before",
             "no_evidence_found": "no split, bonus or scheme found nearby: a true fall, or an action filed under an older symbol or a payout; needs a look"}
    L = ["# The big-falls check, first version (3 Nov 2026)", "",
         f"Data audit step 6. Every one-day fall of over 45% in a stock ranked in the 500 most traded, with no applied split or bonus within "
         f"{ACT_DAYS} days, from the start of the features table to 2023. {o['falls']} falls. Nothing in the prices is changed by this check.", "",
         "| label | what it means | all years | since 2010 |", "|---|---|---|---|"]
    for k, w in words.items():
        L.append(f"| {k} | {w} | {o['labels'].get(k, 0)} | {o['labels_since_2010'].get(k, 0)} |")
    L += ["", "## The ones to fix (not a true fall)", "", "| date | stock | label | ratio | on file |", "|---|---|---|---|---|"]
    for r in o["to_fix"]:
        L.append(f"| {r['date']} | {r['symbol']} | {r['label']} | {r['near_ratio']} | {r['unapplied_action']} |")
    L += ["", "The full list with the evidence for each fall is in big_falls_v1.csv.", ""]
    return "\n".join(L)


if __name__ == "__main__":
    paths.ensure()
    r = run()
    print(json.dumps({k: r[k] for k in ("falls", "labels", "labels_since_2010")}, indent=1))
    sys.exit(0)
