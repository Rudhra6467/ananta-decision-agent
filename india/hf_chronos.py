"""HF-CHRONOS: Hugging Face's Chronos-Bolt as a zero-shot forecaster of NIFTY 50 and NIFTY BANK (Madhav, 25 Oct 2026: "see where hugging
face fits for us ... for predictions / reconstructions or comparisons"). Spec, registered before any run: registrations/hf_chronos_v1.json.

  python -m india.hf_chronos check      sample sizes only (no means, no verdicts): a code check before the recorded run
  python -m india.hf_chronos run        the registered backtest on 2010-2023 (research tree only), recorded in the registry, results page
  python -m india.hf_chronos forward    the next session's forecasts into the forecast ledger (source "chronos"), from the last 300 closes

Runs in the venv ~/ananta_venvs/hf (torch, chronos-forecasting); torch is imported only when a forecast is made, so the tests run anywhere.
Paper only: nothing here trades or feeds a book. The backtest never imports india/sealed.py; the forward step reads recent closes through the
logged paper_context purpose, as the day plan and the daily call do.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from india import paths

SPEC = Path(__file__).resolve().parent / "registrations" / "hf_chronos_v1.json"
RESULTS = Path(__file__).resolve().parent / "registrations" / "hf_chronos_results_v1.md"
MODEL_ID = "amazon/chronos-bolt-small"
REVISION = "772f3d25d38aec6d914c8949dab4462e2d46f5d8"
CONTEXT = 300
HORIZONS = (1, 5)
PRED_LEN = 5
QL = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
NAMES = {"NIFTY": "NIFTY 50", "BANKNIFTY": "NIFTY BANK"}
SPLIT = 2018
START, END = "2010-01-01", "2024-01-01"            # research origins; END is exclusive and nothing at or after it is read
STUDY, FAMILY = "HF-CHRONOS", "forecast_hf"
VARIANTS = {**{f"{ix}|h{h}|hit": 1 for ix in NAMES for h in HORIZONS}, **{f"{ix}|h{h}|vs_call": 1 for ix in NAMES for h in HORIZONS},
            **{f"{ix}|h1|longflat_vs_hold": 1 for ix in NAMES}}
UNION_K = len(VARIANTS)                            # 10, frozen in the spec
BANDS = {1: 0.003, 5: 0.007}                       # the forecast ledger's neutral band per horizon (forward rows)
BASIS = f"chronos: {MODEL_ID}@{REVISION[:7]}, zero-shot, context {CONTEXT} closes"


# ------------------------------------------------------------------------------------------------------------------------------ the model
_PIPE = None


def pipeline():
    """The model, loaded once (MPS on Apple silicon when it works, else CPU)."""
    global _PIPE
    if _PIPE is None:
        import torch
        from chronos import BaseChronosPipeline

        dev = "mps" if torch.backends.mps.is_available() else "cpu"
        try:
            _PIPE = BaseChronosPipeline.from_pretrained(MODEL_ID, revision=REVISION, device_map=dev, torch_dtype=torch.float32)
        except Exception:  # noqa: BLE001  MPS refused: CPU is slower but the same numbers
            _PIPE = BaseChronosPipeline.from_pretrained(MODEL_ID, revision=REVISION, device_map="cpu", torch_dtype=torch.float32)
    return _PIPE


def predict(contexts: list[np.ndarray], pipe=None, batch: int = 256) -> np.ndarray:
    """Quantile forecasts, shape (n, PRED_LEN, len(QL)), for a list of 1-D close arrays."""
    import torch

    pipe = pipe or pipeline()
    out = []
    for i in range(0, len(contexts), batch):
        xs = [torch.tensor(np.asarray(c, dtype="float32")) for c in contexts[i:i + batch]]
        q, _ = pipe.predict_quantiles(xs, prediction_length=PRED_LEN, quantile_levels=QL)
        out.append(q.detach().cpu().numpy())
    return np.concatenate(out, axis=0) if out else np.zeros((0, PRED_LEN, len(QL)))


def cdf_at(q: np.ndarray, x: float) -> float:
    """The forecast distribution's value at x from the nine quantiles: straight lines between them, extended beyond 0.1/0.9, clipped."""
    q = np.maximum.accumulate(np.asarray(q, dtype=float))           # quantiles never cross
    lv = np.asarray(QL)
    if x <= q[0]:
        slope = (lv[1] - lv[0]) / max(q[1] - q[0], 1e-12)
        return float(min(0.99, max(0.01, lv[0] - (q[0] - x) * slope)))
    if x >= q[-1]:
        slope = (lv[-1] - lv[-2]) / max(q[-1] - q[-2], 1e-12)
        return float(min(0.99, max(0.01, lv[-1] + (x - q[-1]) * slope)))
    return float(np.interp(x, q, lv))


def p_up(q: np.ndarray, last: float) -> float:
    return 1.0 - cdf_at(q, last)


def scenarios(q: np.ndarray, last: float, band: float) -> dict:
    """bull / bear / neutral probabilities for the forecast ledger (they sum to 1)."""
    bull = 1.0 - cdf_at(q, last * (1 + band))
    bear = cdf_at(q, last * (1 - band))
    neutral = max(0.0, 1.0 - bull - bear)
    s = bull + bear + neutral
    return {"bull": bull / s, "bear": bear / s, "neutral": neutral / s}


# --------------------------------------------------------------------------------------------------------------------- the research data
def research_closes(name: str) -> pd.Series:
    """Daily closes from the research tree only (silver), dates before 2024-01-01. Never the sealed tree."""
    p = paths.data_dir() / "silver" / "kite_index" / "day" / "day.parquet"
    d = pd.read_parquet(p, columns=["index_name", "date", "close"])
    d = d[d["index_name"] == name].copy()
    d["date"] = pd.to_datetime(d["date"])
    d = d[d["date"] < pd.Timestamp(END)].drop_duplicates("date").sort_values("date")
    return d.set_index("date")["close"].astype(float)


def call_rule(c: pd.Series) -> pd.Series:
    """india/dailycall.py v0 applied to a close series: BULLISH / BEARISH / NEUTRAL per session (uses closes up to that session only)."""
    vs50 = c / c.rolling(50).mean() - 1
    r1 = c.pct_change()
    out = pd.Series("NEUTRAL", index=c.index)
    out[vs50 > 0.05] = "BEARISH"
    out[(vs50 < 0) | (r1 < -0.015)] = "BULLISH"
    out[vs50.isna()] = None
    return out


def build(ix: str, pipe=None, cache: bool = True) -> pd.DataFrame:
    """One row per origin session 2010-2023 with the forecast quantiles (h1, h5), probabilities, the call and the later outcomes."""
    gp = paths.gold() / "studies" / f"HF_chronos_{ix}.parquet"
    if cache and gp.exists():
        df = pd.read_parquet(gp)
        if df.attrs.get("revision", REVISION) == REVISION:
            return df
    c = research_closes(NAMES[ix])
    vals = c.values
    pos = [i for i, d in enumerate(c.index) if d >= pd.Timestamp(START) and i >= CONTEXT - 1]
    q = predict([vals[i - CONTEXT + 1:i + 1] for i in pos], pipe=pipe)
    calls = call_rule(c)
    rows = []
    for k, i in enumerate(pos):
        r = {"date": c.index[i], "close": float(vals[i]), "call": calls.iloc[i]}
        for h in HORIZONS:
            qh = q[k, h - 1, :]
            r[f"p_up{h}"] = p_up(qh, vals[i])
            r[f"med{h}"] = float(qh[QL.index(0.5)])
            r[f"q10_{h}"], r[f"q90_{h}"] = float(qh[0]), float(qh[-1])
            r[f"ret{h}"] = float(vals[i + h] / vals[i] - 1) if i + h < len(vals) else float("nan")
        rows.append(r)
    df = pd.DataFrame(rows)
    df.attrs["revision"] = REVISION
    if cache:
        gp.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(gp)
    return df


# ------------------------------------------------------------------------------------------------------------------------------ outcomes
def outcome_series(df: pd.DataFrame, variant: str) -> pd.Series:
    """The per-session outcome a variant is scored on, indexed by origin date (NaN rows dropped)."""
    _, hz, kind = variant.split("|")
    h = int(hz[1:])
    d = df.set_index("date")
    ret, med = d[f"ret{h}"], d[f"med{h}"]
    ok = ret.notna() & (ret != 0) & (med != d["close"])
    hit = ((med > d["close"]) == (ret > 0)).astype(float)
    if kind == "hit":
        return (hit - 0.5)[ok]
    if kind == "vs_call":
        directional = d["call"].isin(["BULLISH", "BEARISH"])
        rule_hit = ((d["call"] == "BULLISH") == (ret > 0)).astype(float)
        return (hit - rule_hit)[ok & directional]
    if kind == "longflat_vs_hold":
        from india import costs

        r1 = d["ret1"]
        p = (d["p_up1"] > 0.5).astype(float)
        change = p.diff().abs().fillna(p.iloc[0] if len(p) else 0.0)
        leg = pd.Series({t: costs.round_trip("futures", 1e6, 1e6, year=t.year, turnover_rank=1, when=t.date())["total"] / 2e6 for t in d.index})
        y = p * r1 - leg * change - r1
        return y[r1.notna()]
    raise ValueError(variant)


def qblock(y: pd.Series) -> dict:
    """Mean of calendar-quarter means and its t across quarters, for dev (before 2018) and validation (2018 on)."""
    out = {}
    per = pd.to_datetime(y.index).to_period("Q")
    for name, sel in (("dev", per.year < SPLIT), ("val", per.year >= SPLIT)):
        m = y[sel].groupby(per[sel]).mean()
        n = int(len(m))
        if n < 3:
            out[name] = (float("nan"), float("nan"), n)
            continue
        se = float(m.std(ddof=1) / math.sqrt(n))
        out[name] = (float(m.mean()), float(m.mean() / se) if se else float("nan"), n)
    return out


def coverage(df: pd.DataFrame, h: int) -> dict:
    d = df.dropna(subset=[f"ret{h}"])
    real = d["close"] * (1 + d[f"ret{h}"])
    inside = ((real >= d[f"q10_{h}"]) & (real <= d[f"q90_{h}"])).astype(float)
    yr = pd.to_datetime(d["date"]).dt.year
    return {"dev": round(float(inside[yr < SPLIT].mean()), 3), "val": round(float(inside[yr >= SPLIT].mean()), 3)}


def raw_rates(df: pd.DataFrame, h: int) -> dict:
    """Plain hit rates per period (Chronos, the call rule on its call days, and Chronos on those same days)."""
    d = df.dropna(subset=[f"ret{h}"])
    d = d[(d[f"ret{h}"] != 0) & (d[f"med{h}"] != d["close"])]
    yr = pd.to_datetime(d["date"]).dt.year
    hit = (d[f"med{h}"] > d["close"]) == (d[f"ret{h}"] > 0)
    calld = d["call"].isin(["BULLISH", "BEARISH"])
    rule = (d["call"] == "BULLISH") == (d[f"ret{h}"] > 0)
    out = {}
    for name, sel in (("dev", yr < SPLIT), ("val", yr >= SPLIT)):
        out[name] = {"sessions": int(sel.sum()), "chronos_hit": round(float(hit[sel].mean()), 4),
                     "call_days": int((sel & calld).sum()), "call_rule_hit": round(float(rule[sel & calld].mean()), 4) if (sel & calld).any() else None,
                     "chronos_hit_on_call_days": round(float(hit[sel & calld].mean()), 4) if (sel & calld).any() else None,
                     "share_up_forecasts": round(float((d[f"med{h}"] > d["close"])[sel].mean()), 4), "share_up_outcomes": round(float((d[f"ret{h}"] > 0)[sel].mean()), 4)}
    return out


# ----------------------------------------------------------------------------------------------------------------------------- commands
def check() -> None:
    """Sample sizes only: the number of origins and quarters per index and period. No means, no verdicts."""
    for ix, name in NAMES.items():
        c = research_closes(name)
        pos = [d for i, d in enumerate(c.index) if d >= pd.Timestamp(START) and i >= CONTEXT - 1]
        yr = pd.Series([d.year for d in pos])
        q = pd.Series(pd.to_datetime(pos)).dt.to_period("Q")
        print(ix, "origins", len(pos), "first", pos[0].date() if pos else None, "last", pos[-1].date() if pos else None,
              "dev quarters", int(q[yr.values < SPLIT].nunique()), "val quarters", int(q[yr.values >= SPLIT].nunique()), "last close", c.index[-1].date(), flush=True)


def run() -> list[dict]:
    from india import registry

    spec = json.loads(SPEC.read_text())
    assert spec["variants"] == VARIANTS and spec["model"]["revision"] == REVISION, "the code and the registered spec disagree"
    pipe = pipeline()                      # load the model first, so a failed download leaves no orphan registration
    reg = registry.register(STUDY, family=FAMILY, title="Hugging Face Chronos-Bolt: zero-shot direction forecasts of Nifty 50 and Bank Nifty",
                            hypothesis=spec["question"], variants=list(VARIANTS), union_k=UNION_K,
                            note=f"spec registrations/hf_chronos_v1.json; model {MODEL_ID}@{REVISION[:7]}; context {CONTEXT}; research tree 2010-2023 only")
    frames = {ix: build(ix, pipe=pipe) for ix in NAMES}
    rows = []
    for v, expect in VARIANTS.items():
        ix, hz, _ = v.split("|")
        df = frames[ix]
        y = outcome_series(df, v)
        b = qblock(y)
        extra = {"sessions": int(len(y)), "raw": raw_rates(df, int(hz[1:])), "coverage_10_90": coverage(df, int(hz[1:]))}
        line = registry.record(reg, v, b["dev"], b["val"], extra=extra, expect=expect)
        rows.append({"variant": v, "verdict": line["verdict"], "dev": line["dev"], "val": line["val"], "z": line["z"], "extra": extra})
        print(f"{v:28s} {line['verdict']:12s} dev {b['dev'][0]:+.4f} t {b['dev'][1]:+.2f} q{b['dev'][2]} | val {b['val'][0]:+.4f} t {b['val'][1]:+.2f} q{b['val'][2]}", flush=True)
    calib = {ix: {f"h{h}": coverage(frames[ix], h) for h in HORIZONS} for ix in NAMES}
    out = {"generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "rows": rows, "calibration": calib}
    (paths.manifest_dir() / "hf_chronos_results.json").write_text(json.dumps(out, indent=1, default=str))
    write_results(rows, calib)
    return rows


def write_results(rows: list[dict], calib: dict) -> None:
    def pct(x):
        return "-" if x is None or (isinstance(x, float) and x != x) else f"{100 * x:.1f}%"

    L = ["# HF-CHRONOS v1 results: a Hugging Face forecaster against the coin flip and Ananta's daily call", "",
         f"Generated {dt.datetime.now(dt.timezone.utc):%d %b %Y %H:%M} UTC by `python -m india.hf_chronos run`, from the spec registered before the run "
         f"(`hf_chronos_v1.json`). Model {MODEL_ID}@{REVISION[:7]}, zero-shot, the previous {CONTEXT} closes. Research tree only: dev 2010-2017, "
         "validation 2018-2023. Bar: two-sided Bonferroni z for 10 tries (2.81), t across calendar-quarter means.", "",
         "## The verdicts", "", "| version | verdict | dev mean | dev t | val mean | val t | quarters dev/val |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        d, v = r["dev"], r["val"]
        L.append(f"| {r['variant']} | {r['verdict']} | {d[0]:+.4f} | {d[1]:+.2f} | {v[0]:+.4f} | {v[1]:+.2f} | {d[2]}/{v[2]} |")
    L += ["", "Means: hit versions are the hit rate minus 50%; vs_call is Chronos's hit rate minus the daily-call rule's on the rule's call days; "
          "longflat_vs_hold is the long/flat rule's net return per session minus holding the index.", "", "## Plain hit rates", "",
          "| index | horizon | period | sessions | Chronos right | call-rule days | call rule right | Chronos right on those days | forecasts 'up' | outcomes up |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    seen = set()
    for r in rows:
        ix, hz, kind = r["variant"].split("|")
        if (ix, hz) in seen or kind != "hit":
            continue
        seen.add((ix, hz))
        for per in ("dev", "val"):
            x = r["extra"]["raw"][per]
            L.append(f"| {ix} | {hz} | {per} | {x['sessions']} | {pct(x['chronos_hit'])} | {x['call_days']} | {pct(x['call_rule_hit'])} | "
                     f"{pct(x['chronos_hit_on_call_days'])} | {pct(x['share_up_forecasts'])} | {pct(x['share_up_outcomes'])} |")
    L += ["", "## Calibration (share of outcomes inside the forecast's 10%-90% band; honest is about 80%)", "", "| index | horizon | dev | val |", "|---|---|---|---|"]
    for ix, hs in calib.items():
        for hz, c in hs.items():
            L.append(f"| {ix} | {hz} | {pct(c['dev'])} | {pct(c['val'])} |")
    L += ["", "## Reading", "", "- A pass needs |t| at 2.81 in both periods with the expected sign (VALIDATED), or 2.81 in one and 1.65 in the other (CONDITIONAL).",
          "- Against 'always up' (descriptive, not a registered row): the last column is what a forecaster that always says 'up' would score, because "
          "the indices rose on most sessions. Chronos says 'up' far more often than the market rose, so most of its edge over 50% is that upward drift, "
          "not skill: compare its 'right' column with the 'outcomes up' column.",
          "- Chronos may have seen these indices in its pretraining, so a pass here would still need the forward record; a fail here is a fail.",
          "- From 26 Oct 2026 Chronos writes the next session's forecast to the forecast ledger every evening (source chronos), scored beside the rule, "
          "the reviewer and the coin flip in the morning scorecard. Nothing trades on it."]
    RESULTS.write_text("\n".join(L) + "\n")


# ------------------------------------------------------------------------------------------------------------------------------- forward
def _prev_session(session: dt.date, hol: set) -> dt.date:
    d = session - dt.timedelta(days=1)
    while d.weekday() >= 5 or d in hol:
        d -= dt.timedelta(days=1)
    return d


def _next_session(hol: set, now: dt.datetime | None = None) -> dt.date:
    ist = (now or dt.datetime.now(dt.timezone.utc)).astimezone(dt.timezone(dt.timedelta(hours=5, minutes=30)))
    d = ist.date() if ist.time() < dt.time(9, 15) else ist.date() + dt.timedelta(days=1)
    while d.weekday() >= 5 or d in hol:
        d += dt.timedelta(days=1)
    return d


def _holidays() -> set:
    try:
        from india import dayplan
        return dayplan.holidays(refresh=False)
    except Exception:  # noqa: BLE001
        return set()


def _written(session: str) -> set:
    from india import forecast

    if not forecast.LEDGER.exists():
        return set()
    out = set()
    for line in forecast.LEDGER.read_text().splitlines():
        if line.strip():
            r = json.loads(line)
            if r.get("kind") == "forecast" and str(r.get("basis", "")).startswith("chronos") and r.get("session") == session:
                out.add((r["subject"], int(r["horizon_sessions"])))
    return out


def forward(now: dt.datetime | None = None, pipe=None) -> dict:
    """The next session's forecasts (Nifty 50 and Bank Nifty, 1 and 5 sessions) into the forecast ledger, from the last 300 closes read
    through the logged paper_context purpose. Skips (and says why) when the closes are stale or the rows are already written."""
    from india import forecast, sealed

    hol = _holidays()
    session = _next_session(hol, now)
    want_last = _prev_session(session, hol)
    since = (dt.date.today() - dt.timedelta(days=455)).isoformat()
    ix = sealed.read_index("paper_context", since, list(NAMES.values()))
    ix["date"] = pd.to_datetime(ix["date"])
    done = _written(session.isoformat())
    res = {"session": session.isoformat(), "written": [], "skipped": []}
    for name in NAMES.values():
        c = ix[ix["index_name"] == name].drop_duplicates("date").sort_values("date").set_index("date")["close"].astype(float)
        if c.empty or c.index[-1].date() != want_last:
            res["skipped"].append({"subject": name, "why": f"stale closes: the last close is {c.index[-1].date() if len(c) else 'none'}, expected {want_last}"})
            continue
        todo = [h for h in HORIZONS if (name, h) not in done]
        if not todo:
            res["skipped"].append({"subject": name, "why": "already written"})
            continue
        ctx = c.values[-CONTEXT:]
        q = predict([ctx], pipe=pipe)[0]
        for h in todo:
            sc = scenarios(q[h - 1], float(c.values[-1]), BANDS[h])
            try:
                row = forecast.write(name, session.isoformat(), sc, horizon_sessions=h, invalidation="none (a model forecast; scored, never traded)",
                                     basis=f"{BASIS} through {c.index[-1].date()} ({len(ctx)} used); backtest: registrations/hf_chronos_results_v1.md",
                                     kind="pre_open", neutral_band=BANDS[h],
                                     notes=f"p_up {p_up(q[h - 1], float(c.values[-1])):.3f}; band 10-90% {q[h - 1][0]:.1f}..{q[h - 1][-1]:.1f}")
            except ValueError as e:                     # too late for the session's open: recorded, never written after the fact
                res["skipped"].append({"subject": name, "horizon": h, "why": str(e)[:200]})
                continue
            res["written"].append({"subject": name, "horizon": h, "forecast_id": row["forecast_id"], "scenarios": {k: round(v, 3) for k, v in sc.items()}})
    res["at"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    (paths.manifest_dir() / "hf_chronos_forward.json").write_text(json.dumps(res, indent=1, default=str))
    return res


if __name__ == "__main__":
    paths.ensure()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    if cmd == "check":
        check()
    elif cmd == "run":
        run()
    elif cmd == "forward":
        print(json.dumps(forward(), indent=1, default=str))
    elif cmd == "report":                  # rewrite the results page from the recorded run (no new forecast, no new registry row)
        m = json.loads((paths.manifest_dir() / "hf_chronos_results.json").read_text())
        write_results(m["rows"], m["calibration"])
        print(RESULTS)
