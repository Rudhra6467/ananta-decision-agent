"""The daily India report: what the engine decided, what the paper books did, how the filters look against the baseline, and whether the data is healthy.

  python -m india.report            writes reports/<date>.md under the data folder (and prints it)
Runs at the end of the paper job (22:30 Toronto) and of the evening job. PAPER EXECUTION and CURRENT-MARKET OBSERVATION only; historical results are
referenced by their registry verdict, never recomputed here.
"""
from __future__ import annotations

import datetime as dt
import json
import sys

import pandas as pd

from india import paths, settings


def _j(p):
    return json.loads(p.read_text()) if p.exists() else None


def _fmt_pct(x):
    return "" if x is None or x != x else f"{x*100:+.2f}%"


def build() -> str:
    root = paths.data_dir()
    today = dt.date.today().isoformat()
    L = [f"# Ananta India daily report, {today}", "", f"Config {settings.load()['version']} ({settings.sha()}). Paper money on real prices; nothing here is advice or an order.", ""]
    # ---------------------------------------------------------------- data health
    L += ["## Data health", ""]
    for name in ("leakcheck.json", "integrity.json"):
        r = _j(paths.manifest_dir() / name)
        if r:
            bad = [k for k, v in r.items() if not k.startswith("_") and not v.get("ok")]
            L.append(f"- {name.split('.')[0]}: {'all pass' if not bad else 'FAIL ' + ', '.join(bad)} (run {r.get('_at', '?')})")
    lg = _j(paths.manifest_dir() / "lineage.json")
    if lg:
        L.append(f"- data items: {lg.get('data_items')}; studies {lg.get('studies')}")
    ev = paths.manifest_dir() / "evidence_log.jsonl"
    if ev.exists():
        last = [json.loads(x) for x in ev.read_text().splitlines()[-12:]]
        rec = [r for r in last if r["check"] == "recorder.minutes"]
        if rec:
            m = rec[-1]["metrics"]
            L.append(f"- recorder: " + "; ".join(f"{k} {v.get('last_session')} {v.get('minutes')} min" for k, v in m.items() if isinstance(v, dict)))
    L.append("")
    # ---------------------------------------------------------------- stock paper
    pdir = root / "paper"
    st = _j(pdir / "state.json") or {"trades": {}, "decisions": {}}
    L += ["## Stock paper book (PAPER EXECUTION)", ""]
    if st["decisions"]:
        key = max(st["decisions"])
        body = _j(pdir / "decisions" / f"{key}.json")
        ctx = body.get("context") or (_j(pdir / "decisions" / f"{key}.journal.json") or {}).get("context", {})
        L.append(f"Latest decision: data through {key}, written {body['decided_at']}, {len(body['signals'])} signals; candidates {body.get('candidates')}")
        L.append(f"Market context: Nifty vs 50-day {_fmt_pct(ctx.get('nifty_vs_sma50'))}, vs 200-day {_fmt_pct(ctx.get('nifty_vs_sma200'))}, India VIX {ctx.get('vix_close')}, "
                 f"breadth above 200-day {_fmt_pct(ctx.get('breadth200'))}" + (f" (index rows: {ctx.get('nifty_status')})" if ctx.get("nifty_status") not in (None, "ok") else ""))
        sig = pd.DataFrame(body["signals"])
        if not sig.empty:
            for camp, g in sig.groupby("campaign"):
                L.append(f"- {camp}: " + ", ".join(g["symbol"].tolist()))
        L.append("")
    t = pd.DataFrame(st["trades"].values())
    if not t.empty:
        L.append(f"Executed trades: {t['status'].value_counts().to_dict()}")
        evp = pdir / "events.jsonl"
        if evp.exists():
            evs = [json.loads(x) for x in evp.read_text().splitlines()]
            todays = [e for e in evs if e.get("at", "")[:10] == today]
            L.append(f"Today's events: {sum(e['event']=='open' for e in todays)} opens, {sum(e['event']=='close' for e in todays)} closes")
        cl = t[t["status"] == "closed"]
        if len(cl):
            s = cl.groupby(["campaign", "policy"]).agg(n=("net_inr", "size"), net_inr=("net_inr", "sum"), mean=("net_ret", "mean")).sort_values("net_inr")
            L += ["", "Closed trades by campaign and exit (worst and best five):", "", "| campaign | exit | trades | net Rs | mean |", "|---|---|---|---|---|"]
            for (c, p), r in pd.concat([s.head(5), s.tail(5)]).iterrows():
                L.append(f"| {c} | {p} | {int(r['n'])} | {r['net_inr']:,.0f} | {_fmt_pct(r['mean'])} |")
        op = t[t["status"] == "open"]
        if len(op) and "unrealised_ret" in op:
            L.append(f"\nOpen: {len(op)} trades (all policies), mean unrealised {_fmt_pct(op['unrealised_ret'].mean())}")
    L.append("")
    # ---------------------------------------------------------------- baseline and filters
    bp = pdir / "baseline.parquet"
    L += ["## Baseline book and filters (CURRENT-MARKET OBSERVATION)", ""]
    if bp.exists():
        b = pd.read_parquet(bp)
        L.append(f"Baseline rows {len(b)}: {b['status'].value_counts().to_dict()}; journal {b['journal_status'].value_counts().to_dict()}")
        fs = pdir / "filter_slices.csv"
        if fs.exists():
            f = pd.read_csv(fs)
            f = f[(f["n_on"] + f["n_off"]) > 0]
            keep = f[f["condition"].isin(["ext_sma50_gt20", "ext_ret20_gt25", "nifty_gt50d", "small_lead", "vix_rising"]) & (f["policy"].isin(["hold_20d", "hold_60d", "atr_trail_4"]))]
            if len(keep):
                L += ["", "| condition | campaign | exit | on (n, mean) | off (n, mean) | history |", "|---|---|---|---|---|---|"]
                for r in keep.itertuples():
                    L.append(f"| {r.condition} | {r.campaign} | {r.policy} | {r.n_on}, {_fmt_pct(r.mean_on)} | {r.n_off}, {_fmt_pct(r.mean_off)} | {r.historical} |")
    else:
        L.append("No baseline rows yet (the first fill is the session after the first decision).")
    L.append("")
    # ---------------------------------------------------------------- options
    L += ["## Options paper book (PAPER EXECUTION, recorder minutes)", ""]
    opf = pdir / "options_trades.jsonl"
    if opf.exists():
        rows = [json.loads(x) for x in opf.read_text().splitlines()]
        tr = pd.DataFrame([r for r in rows if r.get("kind") != "skip"])
        sk = [r for r in rows if r.get("kind") == "skip"]
        if len(tr):
            g = tr.groupby(["strategy", "index", "variant"]).agg(days=("day", "nunique"), net_inr=("net_inr", "sum"), worst=("net_inr", "min")).reset_index()
            L += ["| strategy | index | variant | days | net Rs | worst day Rs |", "|---|---|---|---|---|---|"]
            L += [f"| {r.strategy} | {r.index} | {r.variant} | {r.days} | {r.net_inr:,.0f} | {r.worst:,.0f} |" for r in g.itertuples()]
        L.append(f"\nSkipped sessions: {len(sk)}" + (f" (last: {sk[-1].get('note')})" if sk else ""))
    else:
        L.append("No options days yet (the first O-04 expiry day is Monday 19 Oct; needs the recorder, which needs the morning Kite sign-in).")
    L.append("")
    text = "\n".join(L) + "\n"
    out = root / "reports" / f"{today}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text)
    return text


if __name__ == "__main__":
    paths.ensure()
    print(build())
