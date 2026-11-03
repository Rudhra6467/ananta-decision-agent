"""V02T and HFN1T (Madhav, 3 Nov 2026: "yes to all your recommendations and next steps"): the two frozen announcement studies, V02 (announcement
categories, 20-session drift) and HFN1 (the FinBERT reading), run again on NSE's timestamped announcements instead of the old PR-zip files, which
thin out in mid-2021 to 2022 (22,367 lines in 2022 against 120,937 timestamped). Same rules, same categories, same outcome windows; the only
changes are the source and its point-in-time timing. Research years only (to 2023-12-29).

  python -m india.annstudies freeze         write registrations/v02t_v1.json and hfn1t_v1.json BEFORE any outcome is read
  python -m india.annstudies counts         announcements and stock-days per period (no outcome)
  ~/ananta_venvs/hf/bin/python -m india.annstudies rate     rate the timestamped texts not yet in the FinBERT cache
  python -m india.annstudies run v02t|hfn1t register, compute, record; manifests/<study>.json and registrations/<study>_results_v1.md

Timing (the one rule that differs, because the source has a time of day): an announcement disseminated on a trading day at or before 15:30 IST
is known before that session's close, so its outcome runs from that close (as the PR file of day d after the close of d); after 15:30, or on a
non-trading day, from the close of the next session.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from india import paths

HERE = Path(__file__).parent
REG = HERE / "registrations"
APPROVED = "Madhav, 3 Nov 2026 (chat: 'yes to all your recommendations and next steps'; the data audit named V02 and HFN1 as readers of the thin PR files)"
LAST = pd.Timestamp("2023-12-29")
CLOSE = dt.time(15, 30)
CODE = ["india/annstudies.py", "india/vstudies.py", "india/hf_news.py", "india/przip.py"]


def _sha(rel: str) -> str:
    return hashlib.sha256((HERE.parent / rel).read_bytes()).hexdigest()[:16]


def _sessions() -> pd.DatetimeIndex:
    cal = pd.read_parquet(paths.data_dir() / "silver/calendar/calendar.parquet")
    return pd.DatetimeIndex(sorted(pd.to_datetime(cal.loc[cal["is_trading_day"], "date"])))


def timestamped() -> pd.DataFrame:
    """The timestamped announcements, 2010 to 2023-12-29, each with the session whose close is the first one after it was disseminated, and the
    V02 category from the same keyword rules as the PR files (india.przip._cat on NSE's category and the subject text)."""
    from india.hf_news import text_hash
    from india.przip import _cat
    a = pd.read_parquet(paths.data_dir() / "silver/announce/announcements.parquet", columns=["symbol", "category", "text", "an_dt", "exchdisstime", "file_date"])
    a = a[a["file_date"] <= LAST]
    t = pd.to_datetime(a["exchdisstime"]).fillna(pd.to_datetime(a["an_dt"]))
    a = a.assign(t=t).dropna(subset=["t"])
    s = _sessions()
    day = a["t"].dt.normalize()
    i = s.searchsorted(day)                                  # the first session on or after the day
    i = np.clip(i, 0, len(s) - 1)
    same = (s[i] == day) & (a["t"].dt.time <= CLOSE)
    j = np.where(same, i, np.where(s[i] == day, i + 1, i))   # a trading day after 15:30 -> the next session; a non-trading day -> the next session
    ok = j < len(s)
    a = a[ok].copy()
    a["date"] = s[j[ok]]
    a = a[a["date"] <= LAST]
    a["nse_category"] = a["category"].astype(str)
    a["category"] = (a["nse_category"] + " " + a["text"].astype(str)).map(_cat)
    a["text"] = a["text"].fillna("").astype(str)
    a["h"] = a["text"].map(text_hash)
    return a


def _universe(a: pd.DataFrame) -> pd.DataFrame:
    f = pd.read_parquet(paths.gold() / "features" / "daily.parquet", columns=["date", "sid", "symbol", "liq_rank", "c", "ret_1"])
    f["date"] = pd.to_datetime(f["date"])
    return a.merge(f, on=["date", "symbol"], how="inner")   # a features row that day: the lab's 500 most liquid (as V02 and HFN1)


def freeze() -> dict:
    from india import registry
    out = {}
    for p in (REG / "v02t_v1.json", REG / "hfn1t_v1.json"):
        if p.exists():
            raise SystemExit(f"{p.name} exists: frozen once")
    v02 = [r for r in registry._rows() if r.get("kind") == "registration" and r.get("study") == "V02"][-1]
    cats = [c for c in v02["variants"] if not c.startswith("band_hit")]
    from india.vstudies import V02_EXPECT
    s1 = {"study": "V02T", "family": "events", "frozen_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "approved": APPROVED,
          "title": "V02 on the timestamped announcements: announcement categories, 20-session drift after the day (top-500 stocks)",
          "hypothesis": "After an announcement of a given category, the stock's 20-session return beyond Nifty differs from zero in the stated direction "
                        "(V02's rule, on NSE's timestamped announcements instead of the PR files)",
          "variants": {c: V02_EXPECT.get(c, 0) for c in cats}, "source": "silver/announce/announcements.parquet (NSE corporate announcements API), to 2023-12-29",
          "category_rule": "india.przip._cat on NSE's category plus the subject text (the PR files' keyword rules); price-band hits are left out (not announcements)",
          "timing": __doc__.split("Timing")[1].strip().split("\n\n")[0], "outcome": "as V02: close of the event session to close 20 sessions later, minus Nifty; |drift| above 100% dropped",
          "bar": "the registry's standard family rule (family events, all rows ever counted)", "periods": "2010-2017 dev, 2018-2023 val; quarter blocks",
          "code_sha": {c: _sha(c) for c in CODE}}
    hf = json.loads((REG / "hf_news_v1.json").read_text())
    fam_rows = {(r["study"], r["variant"]) for r in registry._rows() if r.get("kind") == "result" and r.get("family") in ("events", "news_tone")}
    k = len(fam_rows) + len(s1["variants"]) + len(hf["variants"])
    s2 = {"study": "HFN1T", "family": "news_tone", "frozen_at": s1["frozen_at"], "approved": APPROVED,
          "title": "HFN1 on the timestamped announcements: does FinBERT's reading tell where the stock goes next?",
          "model": hf["model"], "variants": hf["variants"], "statistics": hf["statistics"], "aggregation": hf["aggregation"],
          "source": s1["source"], "timing": s1["timing"], "categories": "as V02T; nav and share_cert left out (as HFN1)",
          "bar": {"family": "news_tone", "bar_families": ["events", "news_tone"], "union_k": k, "z": round(registry.threshold(k), 3),
                  "why": f"{len(fam_rows)} distinct events and news_tone rows today, plus V02T's {len(s1['variants'])} and these {len(hf['variants'])}"},
          "code_sha": s1["code_sha"]}
    (REG / "v02t_v1.json").write_text(json.dumps(s1, indent=1))
    (REG / "hfn1t_v1.json").write_text(json.dumps(s2, indent=1))
    out = {"V02T": {"variants": len(s1["variants"])}, "HFN1T": {"union_k": k, "z": s2["bar"]["z"]}}
    return out


def counts() -> dict:
    a = _universe(timestamped())
    y = a["date"].dt.year
    return {"announcements_dev": int((y < 2018).sum()), "announcements_val": int((y >= 2018).sum()), "stock_days": int(a[["date", "sid"]].drop_duplicates().shape[0]),
            "distinct_texts": int(a["h"].nunique()), "by_year": {int(k): int(v) for k, v in y.value_counts().sort_index().items()}}


def rate() -> dict:
    from india import hf_news
    a = _universe(timestamped())
    a = a[~a["category"].isin(hf_news.SKIP_CATS)]
    texts = dict(zip(a["h"], a["text"]))
    c = hf_news.rate_texts(texts)
    return {"texts": len(texts), "cache": int(len(c))}


def _check(spec: dict) -> None:
    if not spec.get("approved"):
        raise SystemExit("not approved")
    for c, h in spec["code_sha"].items():
        if c != "india/annstudies.py" and _sha(c) != h:
            raise SystemExit(f"{c} changed since the freeze")


def run_v02t() -> dict:
    from india import registry
    from india.vstudies import SPLIT, _q
    s = json.loads((REG / "v02t_v1.json").read_text())
    _check(s)
    ev = _universe(timestamped())
    ev = ev[ev["category"].isin(s["variants"])].drop_duplicates(["date", "symbol", "category"])
    bars = pd.read_parquet(paths.gold() / "bars" / "adj_daily.parquet", columns=["sid", "date", "c"])
    bars["date"] = pd.to_datetime(bars["date"])
    ix = pd.read_parquet(paths.data_dir() / "silver/kite_index/day/day.parquet")
    nifty = ix[ix["index_name"] == "NIFTY 50"].assign(date=lambda d: pd.to_datetime(d["date"])).set_index("date")["close"].sort_index()
    sessions = pd.DatetimeIndex(sorted(bars["date"].unique()))
    by = {sid: g.set_index("date")["c"] for sid, g in bars.groupby("sid")}
    rows = []
    for r in ev.itertuples():
        c = by.get(r.sid)
        i = sessions.searchsorted(r.date)
        if c is None or i + 20 >= len(sessions):
            continue
        d0, d20 = sessions[i], sessions[i + 20]
        if d0 not in c.index or d20 not in c.index or d0 not in nifty.index or d20 not in nifty.index:
            continue
        drift = (c[d20] / c[d0] - 1) - (nifty[d20] / nifty[d0] - 1)
        if abs(drift) > 1.0:
            continue
        rows.append({"date": r.date, "sid": r.sid, "category": r.category, "react": r.ret_1, "drift20": drift})
    df = pd.DataFrame(rows)
    df["y"] = df["date"].dt.year
    reg = registry.register("V02T", family="events", title=s["title"], hypothesis=s["hypothesis"], variants=list(s["variants"]),
                            note=f"spec india/registrations/v02t_v1.json frozen {s['frozen_at']}")
    out = []
    for cat, expect in s["variants"].items():
        x = df[df["category"] == cat]
        x = x.assign(day0=x["date"])
        dev, val = _q(x[x["y"] < SPLIT], "drift20"), _q(x[x["y"] >= SPLIT], "drift20")
        line = registry.record(reg, cat, dev, val, extra={"n": int(len(x)), "n_dev": int((x["y"] < SPLIT).sum()), "n_val": int((x["y"] >= SPLIT).sum()),
                                                          "react_mean": float(x["react"].mean()) if len(x) else None}, expect=expect)
        out.append({"variant": cat, "verdict": line["verdict"], "dev": list(dev), "val": list(val), "n": int(len(x))})
    registry.mirror_to_catalog()
    res = {"study": "V02T", "at": reg["at"], "events": int(len(df)), "rows": out}
    (paths.manifest_dir() / "v02t.json").write_text(json.dumps(res, indent=1, default=str))
    page_v02t(res)
    return res


def run_hfn1t() -> dict:
    from india import hf_news, registry
    s = json.loads((REG / "hfn1t_v1.json").read_text())
    _check(s)
    a = _universe(timestamped())
    a = a[~a["category"].isin(hf_news.SKIP_CATS)]
    ratings = hf_news.load_cache()
    missing = set(a["h"]) - set(ratings["h"])
    if missing:
        raise SystemExit(f"{len(missing)} texts not rated yet: run `rate` first")
    sd, cats = hf_news.stock_days(a, ratings)
    sd = sd.merge(hf_news.drifts(sd), on=["date", "sid"], how="inner")
    qs = hf_news.quarter_series(sd, cats)
    reg = registry.register("HFN1T", family=s["bar"]["family"], title=s["title"], hypothesis=s["title"], variants=list(s["variants"]),
                            note=f"spec india/registrations/hfn1t_v1.json frozen {s['frozen_at']}", bar_families=s["bar"]["bar_families"], union_k=s["bar"]["union_k"])
    out = []
    for var, meta in s["variants"].items():
        q = qs[var]
        q.index = pd.PeriodIndex(q.index, freq="Q") if len(q) else q.index
        dev = hf_news._stat(q[[p.year < hf_news.SPLIT for p in q.index]])
        val = hf_news._stat(q[[p.year >= hf_news.SPLIT for p in q.index]])
        line = registry.record(reg, var, dev, val, expect=meta["expect"], extra={"stock_days": int(len(sd))})
        out.append({"variant": var, "verdict": line["verdict"], "dev": list(dev), "val": list(val)})
    registry.mirror_to_catalog()
    res = {"study": "HFN1T", "at": reg["at"], "announcements": int(len(a)), "stock_days": int(len(sd)), "labels": sd["label"].value_counts().to_dict(), "rows": out}
    (paths.manifest_dir() / "hfn1t.json").write_text(json.dumps(res, indent=1, default=str))
    page_hfn1t(res)
    return res


def _orig(study: str) -> dict:
    from india import registry
    return {r["variant"]: r for r in registry._rows() if r.get("kind") == "result" and r.get("study") == study}


def _t(x) -> str:
    try:
        return f"{float(x):+.1f}"
    except (TypeError, ValueError):
        return ""


def page_v02t(res: dict) -> Path:
    o = _orig("V02")
    L = ["# V02T results: V02 on the timestamped announcements (3 Nov 2026)", "", f"Frozen spec registrations/v02t_v1.json ({APPROVED}). HISTORICAL BACKTEST, "
         "research years only. Drift = close of the event session to 20 sessions later, minus Nifty, before costs.", "",
         "| category | V02 (PR files) dev t | val t | verdict | V02T dev mean | t | val mean | t | n | verdict |", "|---|---|---|---|---|---|---|---|---|---|"]
    for r in res["rows"]:
        v = o.get(r["variant"]) or {}
        L.append(f"| {r['variant']} | {_t((v.get('dev') or [None, None])[1])} | {_t((v.get('val') or [None, None])[1])} | {v.get('verdict', '')} | "
                 f"{100 * (r['dev'][0] or 0):+.2f}% | {_t(r['dev'][1])} | {100 * (r['val'][0] or 0):+.2f}% | {_t(r['val'][1])} | {r['n']:,} | {r['verdict']} |")
    (REG / "v02t_results_v1.md").write_text("\n".join(L + [""]))
    return REG / "v02t_results_v1.md"


def page_hfn1t(res: dict) -> Path:
    o = _orig("HFN1")
    L = ["# HFN1T results: the FinBERT reading on the timestamped announcements (3 Nov 2026)", "", f"Frozen spec registrations/hfn1t_v1.json ({APPROVED}). "
         f"HISTORICAL BACKTEST, research years only, before costs. {res['announcements']:,} announcements on {res['stock_days']:,} stock-days.", "",
         "| variant | HFN1 (PR files) dev t | val t | verdict | HFN1T dev t | val t | verdict |", "|---|---|---|---|---|---|---|"]
    for r in res["rows"]:
        v = o.get(r["variant"]) or {}
        L.append(f"| {r['variant']} | {_t((v.get('dev') or [None, None])[1])} | {_t((v.get('val') or [None, None])[1])} | {v.get('verdict', '')} | "
                 f"{_t(r['dev'][1])} | {_t(r['val'][1])} | {r['verdict']} |")
    (REG / "hfn1t_results_v1.md").write_text("\n".join(L + [""]))
    return REG / "hfn1t_results_v1.md"


if __name__ == "__main__":
    paths.ensure()
    w = sys.argv[1] if len(sys.argv) > 1 else ""
    if w == "freeze":
        print(json.dumps(freeze(), indent=1))
    elif w == "counts":
        print(json.dumps(counts(), indent=1))
    elif w == "rate":
        print(json.dumps(rate(), indent=1))
    elif w == "run":
        print(json.dumps(run_v02t() if sys.argv[2] == "v02t" else run_hfn1t(), indent=1, default=str))
    else:
        print(__doc__)
