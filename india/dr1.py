"""DR1 (29 Oct 2026, Phase 3.1 of the reverse-engineering plan): defined-risk option selling on expiry day.

Spec india/registrations/dr1_v1.json, written before any outcome was read. Builds on lab4's GK1 machinery (the same bhavcopy opens and closes,
the same half-spread and cost model), from the selling side, with bought wings so the loss is capped.

  python -m india.dr1 check          event counts per period only (no means, no t, no verdicts)
  python -m india.dr1 run            register with the spec's frozen k, compute, record every variant; manifests/lab5_dr1.json and registrations/dr1_results_v1.md
  python -m india.dr1 table          rewrite the results page from the manifest

Research rows only (2014-2023); nothing from 2024 on, no sealed folder, no holdout row.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from india import costs, paths, registry, sp1
from india.lab3 import _clean, _f
from india.lab4 import CUT, SPLIT, YEARS, _absolute, _counts, _days, _expiries, _index_day

REG_DIR = Path(__file__).resolve().parent / "registrations"
SYM_IDX = {"NIFTY": "NIFTY 50", "BANKNIFTY": "NIFTY BANK"}
TAG = {"NIFTY": "NIFTY", "BANKNIFTY": "BANK"}
STRUCTS = ("straddle", "fly_w1", "fly_w2", "condor_1_2")


def spec() -> dict:
    return json.loads((REG_DIR / "dr1_v1.json").read_text())


def _targets() -> pd.DataFrame:
    """Expiry days (exp0) and the session three trading days before (exp3) per index, where the series is the nearest expiry that day."""
    days = _days()
    pos = {d: i for i, d in enumerate(days)}
    rows = []
    for sym in SYM_IDX:
        ex = _expiries(sym)
        for e in ex:
            if e not in pos:
                continue
            i = pos[e]
            cands = [(e, "exp0")]
            if i - 3 >= 0:
                cands.append((days[i - 3], "exp3"))
            for day, kind in cands:
                nxt = [x for x in ex if x >= day]
                if nxt and nxt[0] == e:
                    rows.append({"symbol": sym, "date": day, "expiry": e, "kind": kind})
    return pd.DataFrame(rows)


def _chains() -> tuple[pd.DataFrame, dict]:
    import duckdb
    D = paths.data_dir()
    T = _targets()
    files = [str(D / "silver/fo_bhavcopy" / f"year={y}" / "part.parquet") for y in YEARS if (D / "silver/fo_bhavcopy" / f"year={y}" / "part.parquet").exists()]
    con = duckdb.connect()
    t = T.assign(date=pd.to_datetime(T["date"]), expiry=pd.to_datetime(T["expiry"]))
    con.register("t", t)
    o = con.execute(f"""select b.symbol, b.date, b.expiry, b.strike, b.opt_type, b.open, b.close, b.volume, t.kind
                        from read_parquet({files!r}, union_by_name=true) b join t on b.symbol = t.symbol and b.date = t.date and b.expiry = t.expiry
                        where b.instrument = 'OPTIDX' and b.date < DATE '2024-01-01' and b.open > 0 and b.close > 0 and b.volume > 0""").df()
    lots = con.execute(f"""select symbol, date, arg_min(coalesce(lot_size, lot_est), expiry) as lot
                           from read_parquet({files!r}, union_by_name=true) where instrument = 'FUTIDX' and symbol in ('NIFTY', 'BANKNIFTY')
                           and date < DATE '2024-01-01' group by 1, 2""").df()
    con.close()
    lots["date"] = pd.to_datetime(lots["date"]).dt.date
    o["date"] = pd.to_datetime(o["date"]).dt.date
    o = o.merge(lots, on=["symbol", "date"], how="left")
    ix = _index_day()
    opn = {(r.index_name, r.date): float(r.open) for r in ix.itertuples()}
    return o, opn


def _leg(row: pd.Series, side: str, lot: float, day: dt.date, sym: str) -> tuple[float, float]:
    """Net rupees of one leg opened at the daily open and closed at the daily close, and the premium at the open. side 'sell' = short at the open."""
    p_in, p_out = float(row["open"]), float(row["close"])
    h_in, h_out = max(sp1.OPT_HALF[sym], 0.0025 * p_in), max(sp1.OPT_HALF[sym], 0.0025 * p_out)
    if side == "sell":
        sell, buy = max(p_in - h_in, 0.0), p_out + h_out
        fees = costs.cost("options", "sell", sell * lot, day.year, when=day) + costs.cost("options", "buy", buy * lot, day.year, when=day)
        return (sell - buy) * lot - fees, p_in * lot
    buy, sell = p_in + h_in, max(p_out - h_out, 0.0)
    fees = costs.cost("options", "buy", buy * lot, day.year, when=day) + costs.cost("options", "sell", sell * lot, day.year, when=day)
    return (sell - buy) * lot - fees, p_in * lot


def _nearest(strikes: list[float], target: float, above: bool) -> float | None:
    cands = [k for k in strikes if (k >= target if above else k <= target)]
    return (min(cands) if above else max(cands)) if cands else None


def structures() -> pd.DataFrame:
    o, opn = _chains()
    out, dropped = [], []
    for (sym, day, kind), g in o.groupby(["symbol", "date", "kind"]):
        spot = opn.get((SYM_IDX[sym], day))
        if spot is None or not (spot > 0):
            continue
        ce, pe = g[g["opt_type"] == "CE"].set_index("strike"), g[g["opt_type"] == "PE"].set_index("strike")
        both = sorted(set(ce.index) & set(pe.index))
        if not both:
            continue
        K = min(both, key=lambda k: abs(k - spot))
        if abs(K / spot - 1) > 0.02:
            continue
        lot = float(ce.loc[K, "lot"]) if ce.loc[K, "lot"] == ce.loc[K, "lot"] else float(pe.loc[K, "lot"])
        if not (lot > 0):
            continue
        base = {"date": pd.Timestamp(day), "symbol": sym, "kind": kind, "strike": K, "spot_open": spot, "lot": lot}
        # straddle: short the ATM call and put
        s_ce, prem_ce = _leg(ce.loc[K], "sell", lot, day, sym)
        s_pe, prem_pe = _leg(pe.loc[K], "sell", lot, day, sym)
        credit = prem_ce + prem_pe
        out.append({**base, "struct": "straddle", "net_rs": s_ce + s_pe, "credit_rs": credit, "risk_rs": np.nan, "ret": (s_ce + s_pe) / credit if credit > 0 else np.nan})
        # iron flies: the straddle plus bought wings w% away
        for name, w in (("fly_w1", 0.01), ("fly_w2", 0.02)):
            kc, kp = _nearest(list(ce.index), K * (1 + w), True), _nearest(list(pe.index), K * (1 - w), False)
            if kc is None or kp is None or kc == K or kp == K:
                continue
            b_ce, pc = _leg(ce.loc[kc], "buy", lot, day, sym)
            b_pe, pp = _leg(pe.loc[kp], "buy", lot, day, sym)
            net = s_ce + s_pe + b_ce + b_pe
            net_credit = credit - pc - pp
            width = min(kc - K, K - kp) * lot
            risk = width - net_credit
            if risk < 0.1 * width:   # a credit near or above the width is a bad opening print on a wing, not a free trade: dropped and counted
                dropped.append({**base, "struct": name, "why": "credit_vs_width"})
                continue
            out.append({**base, "struct": name, "net_rs": net, "credit_rs": net_credit, "risk_rs": risk, "width_rs": width, "ret": net / width, "wing_c": kc, "wing_p": kp})
        # iron condor: short ~1% out, long ~2% out
        sc, sp_ = _nearest(list(ce.index), K * 1.01, True), _nearest(list(pe.index), K * 0.99, False)
        lc, lp = _nearest(list(ce.index), K * 1.02, True), _nearest(list(pe.index), K * 0.98, False)
        if None not in (sc, sp_, lc, lp) and lc > sc and lp < sp_:
            a, pa = _leg(ce.loc[sc], "sell", lot, day, sym)
            b, pb = _leg(pe.loc[sp_], "sell", lot, day, sym)
            c, pcc = _leg(ce.loc[lc], "buy", lot, day, sym)
            d, pd_ = _leg(pe.loc[lp], "buy", lot, day, sym)
            net = a + b + c + d
            net_credit = pa + pb - pcc - pd_
            width = min(lc - sc, sp_ - lp) * lot
            risk = width - net_credit
            if risk < 0.1 * width:
                dropped.append({**base, "struct": "condor_1_2", "why": "credit_vs_width"})
            else:
                out.append({**base, "struct": "condor_1_2", "net_rs": net, "credit_rs": net_credit, "risk_rs": risk, "width_rs": width, "ret": net / width, "short_c": sc, "short_p": sp_, "wing_c": lc, "wing_p": lp})
    df = pd.DataFrame(out)
    df.attrs["dropped"] = pd.DataFrame(dropped)
    return df


def _tail(d: pd.DataFrame) -> dict:
    if not len(d):
        return {}
    x = d.sort_values("date")["net_rs"]
    eq = x.cumsum()
    dd = (eq - eq.cummax()).min()
    losing, run, longest = 0, 0, 0
    for v in x:
        run = run + 1 if v < 0 else 0
        longest = max(longest, run)
    m20 = d[(d["date"] >= "2020-02-20") & (d["date"] <= "2020-04-30")]
    return {"trades": int(len(d)), "win_share": float((x > 0).mean()), "mean_rs": float(x.mean()), "median_rs": float(x.median()),
            "worst_rs": float(x.min()), "worst_day": str(d.loc[x.idxmin(), "date"].date()), "p5_rs": float(x.quantile(0.05)), "best_rs": float(x.max()),
            "max_drawdown_rs": float(dd), "longest_losing_run": int(longest), "credit_rs_median": float(d["credit_rs"].median()),
            "risk_rs_median": float(d["risk_rs"].median()) if d["risk_rs"].notna().any() else None,
            "march_2020": {"trades": int(len(m20)), "net_rs": float(m20["net_rs"].sum()) if len(m20) else 0.0, "worst_rs": float(m20["net_rs"].min()) if len(m20) else None},
            "val_mean_rs": float(x[d["date"].dt.year >= SPLIT].mean()) if (d["date"].dt.year >= SPLIT).any() else None,
            "val_win_share": float((x[d["date"].dt.year >= SPLIT] > 0).mean()) if (d["date"].dt.year >= SPLIT).any() else None}


def results(counts_only: bool = False) -> dict:
    S = structures()
    out = {}
    for sym in SYM_IDX:
        tag = TAG[sym]
        for kind in ("exp0", "exp3"):
            for st in STRUCTS:
                d = S[(S["symbol"] == sym) & (S["kind"] == kind) & (S["struct"] == st)]
                key = f"{tag}|{kind}|{st}"
                if counts_only:
                    out[key] = _counts(d["date"]) if len(d) else {"events_dev": 0, "events_val": 0}
                    continue
                if not len(d):
                    continue
                r = _absolute(d, "ret", "Q")
                r["extra"].update(_tail(d))
                dr = S.attrs.get("dropped")
                if dr is not None and len(dr):
                    r["extra"]["dropped_bad_prints"] = int(((dr["symbol"] == sym) & (dr["kind"] == kind) & (dr["struct"] == st)).sum())
                out[key] = r
    if not counts_only:
        p = paths.gold() / "studies"
        p.mkdir(parents=True, exist_ok=True)
        dr = S.attrs.get("dropped")
        S2 = S.copy()
        S2.attrs = {}
        S2.to_parquet(p / "DR1_structures.parquet", index=False)
        if dr is not None and len(dr):
            dr.to_parquet(p / "DR1_dropped.parquet", index=False)
    return out


def run(rerun_reason: str | None = None) -> dict:
    s = spec()
    k = int(s["bar"]["union_k"])
    if abs(registry.threshold(k) - float(s["bar"]["z"])) > 0.01:
        raise ValueError(f"DR1: the spec's z {s['bar']['z']} does not match k {k}")
    reg = registry.register("DR1", family=s["family"], title=s["title"], hypothesis=s["hypothesis"], variants=list(s["variants"]),
                            note="spec india/registrations/dr1_v1.json (written before the run)", bar_families=s["bar"].get("bar_families"), union_k=k,
                            rerun_reason=rerun_reason)
    res = results()
    rows = []
    for var, expect in s["variants"].items():
        r = res.get(var)
        if r is None:
            line = registry.record(reg, var, (float("nan"), float("nan"), 0), (float("nan"), float("nan"), 0), extra={"missing": True}, expect=expect)
        else:
            line = registry.record(reg, var, tuple(r["dev"]), tuple(r["val"]), extra=_clean(r.get("extra", {})), expect=expect)
        rows.append({"variant": var, "expect": expect, "verdict": line["verdict"], "z": line["z"], "dev": _clean(list(line["dev"])), "val": _clean(list(line["val"])),
                     "extra": _clean(line["extra"])})
    out = {"study": "DR1", "registered_at": reg["at"], "k": k, "rows": rows}
    (paths.manifest_dir() / "lab5_dr1.json").write_text(json.dumps(out, indent=1, default=str))
    registry.mirror_to_catalog()
    table(out)
    return out


TAKEAWAY = [      # written after the run of 29-30 Oct 2026, from the numbers in the table below
    "**Expiry-day decay is real from the selling side too, but at Rs 50,000 it is not capturable: the bought wings that make the trade affordable cost about "
    "as much as the decay earns, and four legs of spread and charges take the rest. Nothing here passes.**",
    "- **Naked short straddle at the expiry-day open, bought back at the close (315 Nifty and 424 Bank Nifty expiry days):** +10.8% and +13.0% of the premium "
    "in 2018-23 (t +2.7 and +4.1; Rs +689 and Rs +1,396 a lot on a median credit of Rs 5,250-6,060; 65% winners) but about -8% and -2% in 2014-17 (monthly "
    "expiries only for Nifty): REJECTED at the two-period bar. Worst day Rs -25,000 a lot, 5th percentile Rs -6,000 to -8,600, and the margin is about "
    "Rs 1-1.5 lakh a lot: out of reach for the options sleeve whatever the verdict.",
    "- **Iron fly with wings 1% away (the affordable version, margin about Rs 10,000):** the wings cost about Rs 700-1,250 a structure plus two more legs of "
    "spread and charges; net Rs -159 (Nifty, OPPOSITE) and Rs -135 (Bank Nifty) a structure, 53-55% winners, longest losing run 7-9.",
    "- **Iron fly with wings 2% away (margin about Rs 17,500-18,750):** Rs +119 and Rs +358 a structure (t +1.3 in validation), 60% winners: positive but far "
    "under the bar, and March 2020 cost Rs -15,300 (Nifty) in a month.",
    "- **Iron condor, short 1% out, long 2% out:** credit only Rs 330-700 a structure; Nifty lost (OPPOSITE, 35% winners, an 18-trade losing run), Bank Nifty "
    "about zero.",
    "- **The control (the same structures three sessions before expiry, closed the same day):** every defined-risk version lost 4-16% of the width in both "
    "periods (VALIDATED the wrong way, 20-37% winners): without expiry-day decay, four legs of friction are a steady loss. So the expiry-day effect is real "
    "and specific; the friction is what kills the affordable version of it.",
    "- **Fills:** each leg at the exchange file's daily open and close. The open is a thin print (dropped where a wing's credit reached the width: 0-20 cases "
    "a variant); an intraday entry after the first 15 minutes, or a stop, is not modelled and could move these numbers either way.",
    "- **What Ananta does with this:** no paper trial of expiry-day selling at the sleeve's size; the finding joins the exit book as a fact ('the decay is "
    "there, the price of the insurance eats it'). If the sleeve ever grows past Rs 1.5 lakh the naked straddle's 2018-23 record could be re-examined with "
    "intraday fills from the live recorder, which has been collecting real option quotes since 18 Oct. No rule changes.",
]


def table(out: dict | None = None) -> Path:
    if out is None:
        out = json.loads((paths.manifest_dir() / "lab5_dr1.json").read_text())
    s = spec()
    L = [f"# DR1 results: {s['title']}", "", f"Registered {out['registered_at']} (spec `dr1_v1.json`, written before the run); family {s['family']}, "
         f"k = {out['k']}, z = {registry.threshold(out['k']):.2f}. Development 2014-2017, validation 2018-2023; nothing from 2024 on. HISTORICAL BACKTEST, paper only.", "",
         "Fills: every leg at its daily open and daily close in the exchange file, with the half-spread model and the option charges of the day. The opening print of an "
         "option is a thin fill (a known weakness, carried over from GK1). ret = net rupees / premium received for the naked straddle, net rupees / capital at risk "
         "(net rupees / wing width x lot, about the exchange margin of a spread) for the defined-risk structures; a structure whose credit is 90%+ of the width (a bad wing print) is dropped and counted. exp3 rows are the control: the same structures three "
         "sessions before expiry.", "",
         "## In plain words", "", *TAKEAWAY, "", "## The rows", "",
         "Verdicts: VALIDATED and CONDITIONAL would be passes; OPPOSITE means significantly the other way round; INCONCLUSIVE means too few independent blocks "
         "(16 needed per period) or a reading below the bar. A control row (expected 0) that comes out REJECTED or INCONCLUSIVE is a clean control.", "",
         "| variant | expected | verdict | dev mean | dev t | dev blocks | val mean | val t | val blocks | trades | win | mean Rs | worst Rs | p5 Rs | max DD Rs | losing run | Mar-2020 Rs |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in out["rows"]:
        e = r["extra"] or {}
        d, v = r["dev"], r["val"]
        m20 = e.get("march_2020") or {}
        L.append(f"| {r['variant']} | {'+' if r['expect'] > 0 else ('-' if r['expect'] < 0 else '0')} | {r['verdict']} | {_f(d[0])} | {_f(d[1], False)} | {d[2]} | {_f(v[0])} | {_f(v[1], False)} | {v[2]} | "
                 f"{e.get('trades', 'n/a')} | {_f(e.get('win_share')) if e.get('win_share') is not None else 'n/a'} | {e.get('mean_rs', 0):+.0f} | {e.get('worst_rs', 0):+.0f} | "
                 f"{e.get('p5_rs', 0):+.0f} | {e.get('max_drawdown_rs', 0):+.0f} | {e.get('longest_losing_run', 'n/a')} | {m20.get('net_rs', 0):+.0f} |")
    L += ["", "Rupees are per one structure of one lot (the lot of the day). The naked straddle's margin (about Rs 1-1.5 lakh a lot) is not in the table; a "
          "defined-risk structure's capital at risk is its risk_rs (median in the manifest).", ""]
    p = REG_DIR / "dr1_results_v1.md"
    p.write_text("\n".join(L) + "\n")
    return p


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    if cmd == "check":
        print(json.dumps(results(counts_only=True), indent=1))
    elif cmd == "run":
        print(json.dumps({k: v for k, v in run(rerun_reason=(sys.argv[2] if len(sys.argv) > 2 else None)).items() if k != "rows"}, indent=1))
        for r in json.loads((paths.manifest_dir() / "lab5_dr1.json").read_text())["rows"]:
            print(r["variant"], r["verdict"], "dev", [round(x, 3) if isinstance(x, float) else x for x in r["dev"]], "val", [round(x, 3) if isinstance(x, float) else x for x in r["val"]])
    elif cmd == "table":
        print(table())
