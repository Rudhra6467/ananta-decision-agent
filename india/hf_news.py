"""HFN1: a financial-news model (ProsusAI/finbert from Hugging Face, run locally, zero-shot) reads NSE company announcements (Madhav, 25 Oct 2026).

  ~/ananta_venvs/hf/bin/python -m india.hf_news rate         rate every distinct announcement text of 2010-2023 (cached by text hash)
  ~/ananta_venvs/lake/bin/python -m india.hf_news run        the registered test (registrations/hf_news_v1.json) into the ledger
  ~/ananta_venvs/hf/bin/python -m india.hf_news forward      rate the newest live session files (bronze/announce_api) into paper/news_read/<day>.json

The spec was frozen before any rating or outcome was computed. Research reads silver/pr (2010-2023) only, never 2024+ or the sealed folders. The forward
part reads the same live session file the reconstruction card reads, only for live paper days (on or after 2026-10-16), and writes a record that no
book, rule or score reads: the card shows its counts as a note, never a reason to trade. Paper only; nothing here places an order.
"""
from __future__ import annotations

import datetime as dt
import gzip
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from india import paths

MODEL = "ProsusAI/finbert"
REVISION = "0bc2ac10dda6929bcb1f77ccc43c7ec5c424f031"
MAX_TOKENS = 128
SPLIT = 2018
LAST_RESEARCH_DAY = pd.Timestamp("2023-12-29")
FORWARD_START = dt.date(2026, 10, 16)          # the stock paper's first decision day; the forward record never reads an earlier (historical) file
SKIP_CATS = {"nav", "share_cert"}
SPEC = Path(__file__).resolve().parent / "registrations" / "hf_news_v1.json"


def text_hash(t: str) -> str:
    return hashlib.sha1((t or "").strip().encode("utf-8", "ignore")).hexdigest()[:16]


def cache_path() -> Path:
    return paths.gold() / "studies" / "hf_news_ratings.parquet"


def load_cache() -> pd.DataFrame:
    p = cache_path()
    if p.exists():
        return pd.read_parquet(p)
    return pd.DataFrame(columns=["h", "p_pos", "p_neg", "p_neu", "rev"])


# ------------------------------------------------------------------------------------------------------------------------------ the model
class Reader:
    """FinBERT on the Mac's GPU (MPS) when present. Loaded only by rate/forward, so the test run needs no torch."""

    def __init__(self, batch: int = 128):
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        self.torch = torch
        self.dev = "mps" if torch.backends.mps.is_available() else "cpu"
        self.tok = AutoTokenizer.from_pretrained(MODEL, revision=REVISION)
        self.m = AutoModelForSequenceClassification.from_pretrained(MODEL, revision=REVISION).to(self.dev).eval()
        lab = {v.lower(): int(k) for k, v in self.m.config.id2label.items()}
        self.ix = (lab["positive"], lab["negative"], lab["neutral"])
        self.batch = batch

    def probs(self, texts: list[str]) -> np.ndarray:
        out = []
        for i in range(0, len(texts), self.batch):
            enc = self.tok(texts[i:i + self.batch], truncation=True, max_length=MAX_TOKENS, padding=True, return_tensors="pt").to(self.dev)
            with self.torch.no_grad():
                p = self.torch.softmax(self.m(**enc).logits.float(), dim=-1).cpu().numpy()
            out.append(p[:, list(self.ix)])
        return np.vstack(out) if out else np.zeros((0, 3))


def rate_texts(texts: dict[str, str], reader: Reader | None = None, every: int = 20000, save: bool = True) -> pd.DataFrame:
    """Rate the texts (hash -> text) not yet in the cache; the cache is written every `every` texts so a stopped run resumes."""
    cache = load_cache()
    have = set(cache["h"])
    todo = sorted(((h, t) for h, t in texts.items() if h not in have), key=lambda x: len(x[1]))   # similar lengths batch together: far less padding
    if not todo:
        return cache
    reader = reader or Reader()
    parts = [cache]
    for i in range(0, len(todo), every):
        chunk = todo[i:i + every]
        p = reader.probs([t for _, t in chunk])
        parts.append(pd.DataFrame({"h": [h for h, _ in chunk], "p_pos": p[:, 0], "p_neg": p[:, 1], "p_neu": p[:, 2], "rev": REVISION}))
        if save:
            pd.concat(parts, ignore_index=True).to_parquet(cache_path())
        print(f"rated {min(i + every, len(todo))} of {len(todo)}", flush=True)
    return pd.concat(parts, ignore_index=True)


def label(p_pos: float, p_neg: float, p_neu: float) -> str:
    return ("positive", "negative", "neutral")[int(np.argmax([p_pos, p_neg, p_neu]))]


# ------------------------------------------------------------------------------------------------------------------------- research data
def announcements() -> pd.DataFrame:
    """2010-2023 announcements on stock-days of the lab universe (silver/pr only; the research window ends 2023-12-29)."""
    a = pd.read_parquet(paths.data_dir() / "silver/pr/announcements.parquet", columns=["date", "symbol", "category", "text"])
    a["date"] = pd.to_datetime(a["date"])
    a = a[(a["date"] <= LAST_RESEARCH_DAY) & ~a["category"].isin(SKIP_CATS)]
    f = pd.read_parquet(paths.gold() / "features" / "daily.parquet", columns=["date", "sid", "symbol"])
    f["date"] = pd.to_datetime(f["date"])
    a = a.merge(f, on=["date", "symbol"], how="inner")
    a["text"] = a["text"].fillna("").astype(str)
    a["h"] = a["text"].map(text_hash)
    return a


def drifts(ev: pd.DataFrame) -> pd.DataFrame:
    """Close d to close d+5 and d+20 (sessions of the adjusted bars) minus Nifty over the same sessions; the file of day d is known after its close."""
    bars = pd.read_parquet(paths.gold() / "bars" / "adj_daily.parquet", columns=["sid", "date", "c"])
    bars["date"] = pd.to_datetime(bars["date"])
    bars = bars[bars["date"] <= LAST_RESEARCH_DAY]   # the research window ends 2023-12-29: a late-December day without 20 sessions after it is dropped (as V02)
    ix = pd.read_parquet(paths.data_dir() / "silver/kite_index/day/day.parquet")
    nifty = ix[ix["index_name"] == "NIFTY 50"].assign(date=lambda d: pd.to_datetime(d["date"])).set_index("date")["close"].sort_index()
    sessions = pd.DatetimeIndex(sorted(bars["date"].unique()))
    by = {s: g.set_index("date")["c"] for s, g in bars.groupby("sid")}
    out = []
    for r in ev[["date", "sid"]].drop_duplicates().itertuples():
        c = by.get(r.sid)
        i = sessions.searchsorted(r.date)
        if c is None or i >= len(sessions) or sessions[i] != r.date:
            continue
        row = {"date": r.date, "sid": r.sid}
        for k in (5, 20):
            if i + k >= len(sessions):
                row[f"drift{k}"] = np.nan
                continue
            d0, dk = sessions[i], sessions[i + k]
            if d0 in c.index and dk in c.index and d0 in nifty.index and dk in nifty.index:
                v = (c[dk] / c[d0] - 1) - (nifty[dk] / nifty[d0] - 1)
                row[f"drift{k}"] = v if abs(v) <= 1.0 else np.nan
            else:
                row[f"drift{k}"] = np.nan
        out.append(row)
    return pd.DataFrame(out)


def stock_days(a: pd.DataFrame, ratings: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    x = a.merge(ratings[["h", "p_pos", "p_neg", "p_neu"]], on="h", how="inner")
    x["tone"] = x["p_pos"] - x["p_neg"]
    x["lab"] = [label(p, n, u) for p, n, u in zip(x["p_pos"], x["p_neg"], x["p_neu"])]
    g = x.groupby(["date", "sid"])
    sd = g.agg(tone=("tone", "mean"), n_pos=("lab", lambda s: int((s == "positive").sum())), n_neg=("lab", lambda s: int((s == "negative").sum())),
               n=("lab", "size")).reset_index()
    sd["label"] = np.select([(sd["n_pos"] > 0) & (sd["n_neg"] == 0), (sd["n_neg"] > 0) & (sd["n_pos"] == 0), (sd["n_pos"] > 0) & (sd["n_neg"] > 0)],
                            ["positive", "negative", "mixed"], "neutral")
    cats = x.groupby(["date", "sid", "category"]).agg(ctone=("tone", "mean"), cpos=("lab", lambda s: (s == "positive").any()), cneg=("lab", lambda s: (s == "negative").any())).reset_index()
    return sd, cats


def _stat(q: pd.Series) -> tuple[float, float, int]:
    q = q.dropna()
    if len(q) < 3:
        return float("nan"), float("nan"), int(len(q))
    se = q.std(ddof=1) / math.sqrt(len(q))
    return float(q.mean()), float(q.mean() / se) if se else float("nan"), int(len(q))


def quarter_series(sd: pd.DataFrame, cats: pd.DataFrame) -> dict[str, pd.Series]:
    """One value per calendar quarter for each registered variant (the t is over these quarter values)."""
    sd = sd.assign(q=sd["date"].dt.to_period("Q"))
    pos, neg = sd[sd["label"] == "positive"], sd[sd["label"] == "negative"]
    out = {}
    for k in (5, 20):
        mp, mn = pos.groupby("q")[f"drift{k}"].mean(), neg.groupby("q")[f"drift{k}"].mean()
        out[f"pos|drift{k}"], out[f"neg|drift{k}"] = mp, mn
        out[f"spread|drift{k}"] = (mp - mn).dropna()
    c = cats.merge(sd[["date", "sid", "drift20"]], on=["date", "sid"], how="inner")
    c["q"] = c["date"].dt.to_period("Q")
    cp = c[c["cpos"] & ~c["cneg"]].groupby(["q", "category"])["drift20"].mean()
    cn = c[c["cneg"] & ~c["cpos"]].groupby(["q", "category"])["drift20"].mean()
    both = pd.concat([cp.rename("p"), cn.rename("n")], axis=1).dropna()
    out["within_cat|drift20"] = (both["p"] - both["n"]).groupby(level=0).mean()
    rk = []
    for q, g in sd.dropna(subset=["drift20"]).groupby("q"):
        if len(g) >= 30:
            rk.append((q, g["tone"].rank().corr(g["drift20"].rank())))
    out["rank|drift20"] = pd.Series(dict(rk))
    return out


def run(write_registry: bool = True) -> dict:
    from india import registry

    spec = json.loads(SPEC.read_text())
    a = announcements()
    ratings = load_cache()
    missing = set(a["h"]) - set(ratings["h"])
    if missing:
        raise RuntimeError(f"{len(missing)} texts not rated yet: run `rate` first")
    sd, cats = stock_days(a, ratings)
    dr = drifts(sd)
    sd = sd.merge(dr, on=["date", "sid"], how="inner")
    qs = quarter_series(sd, cats)
    reg = None
    if write_registry:
        reg = registry.register("HFN1", family=spec["bar"]["family"], title=spec["title"], hypothesis=spec["title"], variants=list(spec["variants"]),
                                note=f"{MODEL}@{REVISION[:12]}; registrations/hf_news_v1.json", bar_families=spec["bar"]["bar_families"], union_k=spec["bar"]["union_k"])
    rows = {}
    for var, meta in spec["variants"].items():
        s = qs[var]
        idx = pd.PeriodIndex(s.index, freq="Q") if len(s) else s.index
        s.index = idx
        dev, val = _stat(s[[p.year < SPLIT for p in s.index]]), _stat(s[[p.year >= SPLIT for p in s.index]])
        line = registry.record(reg, var, dev, val, expect=meta["expect"], extra={"stock_days": int(len(sd))}) if reg else {"verdict": "(not recorded)", "z": None}
        rows[var] = {"verdict": line["verdict"], "z": line.get("z"), "dev": dev, "val": val}
        print(f"HFN1 {var:20s} {line['verdict']:12s} dev {dev[0]*100 if var != 'rank|drift20' else dev[0]:+.3f} t {dev[1]:+.2f} q{dev[2]} | val "
              f"{val[0]*100 if var != 'rank|drift20' else val[0]:+.3f} t {val[1]:+.2f} q{val[2]}", flush=True)
    lab = sd["label"].value_counts().to_dict()
    out = {"generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "model": f"{MODEL}@{REVISION}", "announcements": int(len(a)),
           "stock_days": int(len(sd)), "labels": lab, "rows": rows,
           "mean_drift20_by_label": {k: float(v) for k, v in sd.groupby("label")["drift20"].mean().items()},
           "positive_share_by_category": {c: round(float(g["cpos"].mean()), 4) for c, g in cats.groupby("category")},
           "negative_share_by_category": {c: round(float(g["cneg"].mean()), 4) for c, g in cats.groupby("category")}}
    (paths.manifest_dir() / "hf_news_results.json").write_text(json.dumps(out, indent=1, default=str))
    if write_registry:
        registry.mirror_to_catalog()
    return out


# ------------------------------------------------------------------------------------------------------------------------------ forward
def news_dir() -> Path:
    d = paths.data_dir() / "paper" / "news_read"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _session_files(days_back: int = 7, today: dt.date | None = None) -> list[tuple[dt.date, Path]]:
    today = today or dt.date.today()
    out = []
    for y in {today.year, (today - dt.timedelta(days=days_back)).year}:
        for p in sorted((paths.bronze("announce_api") / str(y)).glob("*.json.gz")):
            try:
                d = dt.datetime.strptime(p.name[:8], "%Y%m%d").date()
            except ValueError:
                continue
            if d >= max(FORWARD_START, today - dt.timedelta(days=days_back)) and d <= today:
                out.append((d, p))
    return sorted(out)


def forward_day(day: dt.date, src: Path, reader: Reader | None = None) -> dict:
    """Rate one live session file; written once (a day already rated is left as it is: the record is append-only)."""
    if day < FORWARD_START:
        raise PermissionError(f"forward rating refused: {day} is before the paper's first day {FORWARD_START} (live days only)")
    dst = news_dir() / f"{day}.json"
    if dst.exists():
        return json.loads(dst.read_text())
    rows = json.load(gzip.open(src))
    rows = rows if isinstance(rows, list) else (rows.get("rows") or [])
    items = [{"symbol": str(r.get("symbol") or "").strip(), "category": r.get("desc"), "public_ist": r.get("exchdisstime"),
              "text": f"{r.get('desc') or ''} {r.get('attchmntText') or ''}".strip()} for r in rows]
    items = [x for x in items if x["symbol"] and x["text"]]
    reader = reader or Reader()
    p = reader.probs([x["text"] for x in items]) if items else np.zeros((0, 3))
    for x, q in zip(items, p):
        x.update({"p_pos": round(float(q[0]), 4), "p_neg": round(float(q[1]), 4), "label": label(*q), "h": text_hash(x["text"])})
        x["text"] = x["text"][:200]
    counts = {k: sum(1 for x in items if x["label"] == k) for k in ("positive", "negative", "neutral")}
    rec = {"day": str(day), "source": str(src), "model": f"{MODEL}@{REVISION}", "rated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "rows": len(items), "counts": counts, "items": items,
           "rule": "a record only: no book, rule, score or Ask reads it to decide anything; the reconstruction card shows the counts as a note"}
    dst.write_text(json.dumps(rec, indent=1))
    with (news_dir() / "log.jsonl").open("a") as fh:
        fh.write(json.dumps({"day": str(day), "rows": len(items), "counts": counts, "rated_at": rec["rated_at"]}) + "\n")
    return rec


def forward(days_back: int = 7) -> list[dict]:
    todo = [(d, p) for d, p in _session_files(days_back) if not (news_dir() / f"{d}.json").exists()]
    if not todo:
        print("forward: nothing new", flush=True)
        return []
    reader = Reader()
    out = []
    for d, p in todo:
        r = forward_day(d, p, reader)
        print(f"forward {d}: {r['rows']} announcements, {r['counts']}", flush=True)
        out.append({"day": str(d), "rows": r["rows"], "counts": r["counts"]})
    return out


def read_note(day: str, names: dict | None = None) -> dict | None:
    """The counts for the reconstruction card (universe names only when given). None when the day was not rated."""
    p = news_dir() / f"{day}.json"
    if not p.exists():
        return None
    r = json.loads(p.read_text())
    items = [x for x in r.get("items", []) if names is None or x["symbol"] in names]
    c = {k: sum(1 for x in items if x["label"] == k) for k in ("positive", "negative", "neutral")}
    top = sorted((x for x in items if x["label"] != "neutral"), key=lambda x: -max(x["p_pos"], x["p_neg"]))[:5]
    return {"counts": c, "rows": len(items), "strongest": [{"symbol": x["symbol"], "label": x["label"], "text": x["text"][:120]} for x in top],
            "words": f"the news read (FinBERT): {c['positive']} positive, {c['negative']} negative, {c['neutral']} neutral announcements; a note, never a reason to trade"}


def main(argv: list[str]) -> None:
    cmd = argv[1] if len(argv) > 1 else "run"
    if cmd == "rate":
        a = announcements()
        texts = dict(zip(a["h"], a["text"]))
        print(f"{len(a)} announcements, {len(texts)} distinct texts", flush=True)
        rate_texts(texts)
    elif cmd == "run":
        print(json.dumps(run(), default=str)[:2000])
    elif cmd == "forward":
        print(forward(int(argv[2]) if len(argv) > 2 else 7))


if __name__ == "__main__":
    main(sys.argv)
