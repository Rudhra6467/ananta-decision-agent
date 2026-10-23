"""G01 (first version): the exit policy book. DESCRIPTIVE, from the registered E02/E03 trade files; no new hypothesis is tested here.

  python -m india.exitbook        writes gold/studies/G01_exit_book.csv and prints the book per entry set and period

Why: per-trade means say no exit beats holding as long, but exits also free capital earlier and cut the tail. This book scores every exit policy on
  per trade      mean net, 5th and 1st percentile, worst, mean days held, net per 20 sessions held (capital speed), excess over the time-matched null
  as a book      10 equal slots, signals taken in date order (same-day order seeded), a trade takes 1/10 of equity at entry, a full book skips the signal;
                 growth per year, worst drawdown of closed-trade equity, growth over drawdown (MAR), trades taken, share of signals skipped
The book is how a trader with limited slots would live with each exit. It is read beside the registry verdicts, never instead of them.
"""
from __future__ import annotations

import heapq
import sys

import numpy as np
import pandas as pd

from india import paths

SPLIT = 2018
SLOTS = 10


def _book(t: pd.DataFrame, seed: int = 3) -> dict:
    t = t.sample(frac=1.0, random_state=seed).sort_values("signal_date", kind="mergesort")
    entry = t["signal_date"] + pd.offsets.BDay(1)
    exitd = entry + pd.to_timedelta((t["hold_days"].values * 7 / 5).round().astype(int), unit="D")
    eq, busy, taken, skipped = 1.0, [], 0, 0
    curve = []
    open_alloc = {}
    events = []
    for e0, e1, r, k in zip(entry.values, exitd.values, t["net_ret"].values, range(len(t))):
        while busy and busy[0][0] <= e0:
            d, kk = heapq.heappop(busy)
            a, rr = open_alloc.pop(kk)
            eq += a * rr
            curve.append((d, eq))
        if len(busy) >= SLOTS:
            skipped += 1
            continue
        open_alloc[k] = (eq / SLOTS, r)
        heapq.heappush(busy, (e1, k))
        taken += 1
    while busy:
        d, kk = heapq.heappop(busy)
        a, rr = open_alloc.pop(kk)
        eq += a * rr
        curve.append((d, eq))
    if not curve:
        return {}
    c = pd.Series([v for _, v in curve], index=pd.to_datetime([d for d, _ in curve]))
    years = max((c.index[-1] - t["signal_date"].min()).days / 365.25, 0.5)
    growth = c.iloc[-1] ** (1 / years) - 1 if c.iloc[-1] > 0 else -1.0
    dd = float((c / c.cummax() - 1).min())
    return {"book_growth_pa": float(growth), "book_max_dd": dd, "book_mar": float(growth / abs(dd)) if dd < 0 else np.nan, "book_trades": taken, "book_skip_share": skipped / max(1, taken + skipped)}


def run() -> pd.DataFrame:
    rows = []
    for name in ("BRK", "PULL", "ANY"):
        frames = []
        for f in (f"E02-{name}_trades.parquet", f"E03-{name}_trades.parquet"):
            p = paths.gold() / "studies" / f
            if p.exists():
                frames.append(pd.read_parquet(p, columns=["sid", "signal_date", "policy", "hold_days", "net_ret", "null_net_ret"]))
        tr = pd.concat(frames).drop_duplicates(["sid", "signal_date", "policy"])
        tr = tr[tr["signal_date"] >= "2000-01-01"]
        tr["period"] = np.where(tr["signal_date"].dt.year < SPLIT, "dev", "val")
        for (pol, per), g in tr.groupby(["policy", "period"]):
            if pol == "random_exit":
                g = g.drop_duplicates(["sid", "signal_date"])
            x = g["net_ret"]
            r = {"entry_set": name, "policy": pol, "period": per, "trades": len(g), "mean_net": x.mean(), "p5": x.quantile(0.05), "p1": x.quantile(0.01), "worst": x.min(),
                 "days": g["hold_days"].mean(), "net_per_20d": x.mean() / g["hold_days"].mean() * 20, "excess_vs_null": (g["net_ret"] - g["null_net_ret"]).mean()}
            r.update(_book(g))
            rows.append(r)
    out = pd.DataFrame(rows)
    out.to_csv(paths.gold() / "studies" / "G01_exit_book.csv", index=False)
    pd.set_option("display.width", 250)
    for (name, per), g in out.groupby(["entry_set", "period"]):
        g = g.sort_values("book_mar", ascending=False)
        print(f"\n== {name} {per}: exit policies ranked by book growth over drawdown (10 slots)")
        print(g[["policy", "trades", "mean_net", "p5", "worst", "days", "net_per_20d", "book_growth_pa", "book_max_dd", "book_mar", "book_skip_share"]]
              .round(4).head(12).to_string(index=False))
    return out




# ----------------------------------------------------------------------------------------------- E10 portfolio drawdown rule

def _book_daily(t: pd.DataFrame, bars: dict, sessions: np.ndarray, rule: tuple | None, seed: int = 3) -> pd.Series:
    """Daily marked-to-market equity of a 10-slot book. Each trade's own exit (day and price) comes from the registered trade file; between entry and exit
    it is marked at the adjusted close. rule = (drawdown, pause): when equity falls `drawdown` below its peak, every open trade is closed at the next open
    and no new trade is taken for `pause` sessions; the peak then restarts from the equity after the flatten."""
    t = t.sample(frac=1.0, random_state=seed).sort_values("signal_date", kind="mergesort")
    sig_by_day: dict = {}
    for r in t.itertuples():
        i = int(np.searchsorted(sessions, np.datetime64(r.signal_date.date()), side="right"))
        sig_by_day.setdefault(i, []).append(r)
    cash, peak, pause_until, flatten_next = 1.0, 1.0, -1, False
    open_ = []  # dicts: sid, qty, i_exit, exit_px
    eq = np.full(len(sessions), np.nan)
    for i in range(len(sessions)):
        # exits due today (their own rule): realised at the trade's own exit price
        still = []
        for p in open_:
            if p["i_exit"] <= i:
                cash += p["qty"] * p["exit_px"]
            else:
                still.append(p)
        open_ = still
        if flatten_next:
            for p in open_:
                b = bars.get(p["sid"])
                j = int(np.searchsorted(b[0], sessions[i]))
                px = b[1][j] if j < len(b[0]) and b[0][j] == sessions[i] else p["last"]
                cash += p["qty"] * px * (1 - 0.0015)  # sale costs about 0.15% (STT, charges, half-spread)
            open_ = []
            flatten_next = False
        # new entries at today's open, from signals of the previous session
        if i >= pause_until:
            for r in sig_by_day.get(i, []):
                if len(open_) >= SLOTS:
                    break
                b = bars.get(r.sid)
                if b is None:
                    continue
                j = int(np.searchsorted(b[0], sessions[i]))
                if j >= len(b[0]) or b[0][j] != sessions[i]:
                    continue
                total = cash + sum(p["qty"] * p["last"] for p in open_)
                alloc = min(cash, total / SLOTS)
                if alloc <= 0:
                    break
                entry = b[1][j]
                k = min(j + int(r.hold_days) - 1, len(b[0]) - 1)
                exit_px = entry * (1 + r.net_ret)  # the trade's net outcome, costs included, as recorded
                i_exit = int(np.searchsorted(sessions, b[0][k])) + (0 if r.reason in ("stop", "target") else 1)
                open_.append({"sid": r.sid, "qty": alloc / entry, "i_exit": i_exit, "exit_px": exit_px, "last": entry})
                cash -= alloc
        # mark at today's close
        for p in open_:
            b = bars[p["sid"]]
            j = int(np.searchsorted(b[0], sessions[i]))
            if j < len(b[0]) and b[0][j] == sessions[i]:
                p["last"] = b[4][j]
        eq[i] = cash + sum(p["qty"] * p["last"] for p in open_)
        peak = max(peak, eq[i])
        if rule and open_ and eq[i] < (1 - rule[0]) * peak:
            flatten_next, pause_until, peak = True, i + 1 + rule[1], eq[i]
    return pd.Series(eq, index=pd.to_datetime(sessions))


def e10(entry_set: str = "BRK", policy: str = "hold_60d") -> dict:
    """TWT-H25: review or exit everything when open drawdown reaches 7-8%. Registered: quarterly book return with the rule minus without it."""
    import math

    from india import exitlab, registry
    t = pd.read_parquet(paths.gold() / "studies" / f"E02-{entry_set}_trades.parquet", columns=["sid", "signal_date", "policy", "hold_days", "net_ret", "reason"])
    t = t[(t["policy"] == policy) & (t["signal_date"] >= "2000-01-01")]
    bars = exitlab.load_bars(sids=t["sid"].unique())
    sessions = np.array(sorted({d for b in bars.values() for d in b[0] if d >= np.datetime64("2000-01-03")}))
    rules = {"none": None, "dd8_pause10": (0.08, 10), "dd7_pause10": (0.07, 10), "dd8_pause20": (0.08, 20), "dd12_pause10": (0.12, 10)}
    curves = {k: _book_daily(t, bars, sessions, v) for k, v in rules.items()}
    q = {k: c.resample("QE").last().pct_change().dropna() for k, c in curves.items()}
    reg = registry.register(f"E10-{entry_set}", family="portfolio", title=f"Portfolio drawdown rule on a 10-slot {entry_set} book ({policy} exits)",
                            hypothesis="Closing everything when the book is 7-8% below its peak and pausing new entries raises the book's quarterly return (TWT-H25).",
                            variants=[k for k in rules if k != "none"], note="daily marked-to-market book; quarter returns paired against the same book without the rule")
    out = {}
    for k in rules:
        if k == "none":
            continue
        d = (q[k] - q["none"]).dropna()
        st = {}
        for per, m in (("dev", d.index.year < SPLIT), ("val", d.index.year >= SPLIT)):
            x = d[m]
            se = x.std(ddof=1) / math.sqrt(len(x)) if len(x) > 2 else float("nan")
            st[per] = (float(x.mean()), float(x.mean() / se) if se else float("nan"), int(len(x)))
        def summ(c, lo, hi):
            c = c[(c.index >= lo) & (c.index <= hi)].dropna()
            yrs = (c.index[-1] - c.index[0]).days / 365.25
            return {"growth_pa": float((c.iloc[-1] / c.iloc[0]) ** (1 / yrs) - 1), "max_dd": float((c / c.cummax() - 1).min())}
        extra = {p: {"rule": summ(curves[k], lo, hi), "none": summ(curves["none"], lo, hi)} for p, lo, hi in (("dev", "2000-01-01", "2017-12-31"), ("val", "2018-01-01", "2023-12-31"))}
        line = registry.record(reg, k, st["dev"], st["val"], extra=extra, expect=1)
        out[k] = line["verdict"]
        print(f"E10-{entry_set} {k:13s} {line['verdict']:12s} dev q {st['dev'][0]*100:+.2f}% t {st['dev'][1]:+.1f} | val q {st['val'][0]*100:+.2f}% t {st['val'][1]:+.1f} | "
              f"val growth {extra['val']['rule']['growth_pa']*100:+.1f}%/yr dd {extra['val']['rule']['max_dd']*100:.0f}% vs none {extra['val']['none']['growth_pa']*100:+.1f}%/yr dd {extra['val']['none']['max_dd']*100:.0f}% | "
              f"dev growth {extra['dev']['rule']['growth_pa']*100:+.1f}% dd {extra['dev']['rule']['max_dd']*100:.0f}% vs {extra['dev']['none']['growth_pa']*100:+.1f}% dd {extra['dev']['none']['max_dd']*100:.0f}%", flush=True)
    pd.DataFrame(curves).to_parquet(paths.gold() / "studies" / f"E10-{entry_set}_curves.parquet")
    registry.mirror_to_catalog()
    return out


# ----------------------------------------------------------------------------------------------- G01 v2: the book by situation, with a verdict

SITUATIONS = ("all", "above_both", "mixed", "below_both")
MIN_TRADES = 300          # a cell (entry set x situation x period) with fewer trades per policy is INCONCLUSIVE
DEV_TOP, VAL_TOP = 3, 5   # the rule, declared before the run: a dev top-3 exit HELD if it is val top-5 with positive excess and net


def nifty_state() -> pd.Series:
    """Nifty 50 trend on each session, SP3's first situation axis: close against its 50- and 200-day averages -> above_both / below_both / mixed.
    Read from the silver index file (2003+); earlier sessions get no state and fall only into the 'all' cell."""
    p = paths.silver("kite_index") / "day" / "day.parquet"
    d = pd.read_parquet(p, columns=["index_name", "date", "close"])
    d = d[d["index_name"] == "NIFTY 50"].sort_values("date")
    c = d.set_index(pd.to_datetime(d["date"]))["close"]
    s50, s200 = c.rolling(50).mean(), c.rolling(200).mean()
    st = pd.Series(np.where((c > s50) & (c > s200), "above_both", np.where((c < s50) & (c < s200), "below_both", "mixed")), index=c.index)
    return st[s200.notna()]


def _cells(tr: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (sit, pol, per), g in tr.groupby(["situation", "policy", "period"]):
        if pol == "random_exit":
            g = g.drop_duplicates(["sid", "signal_date"])
        x = g["net_ret"]
        ex = g["net_ret"] - g["null_net_ret"]
        r = {"situation": sit, "policy": pol, "period": per, "trades": len(g), "mean_net": x.mean(), "p5": x.quantile(0.05), "worst": x.min(),
             "days": g["hold_days"].mean(), "net_per_20d": x.mean() / max(g["hold_days"].mean(), 1) * 20, "excess_vs_null": ex.mean(),
             "excess_t": float(ex.mean() / (ex.std(ddof=1) / np.sqrt(len(ex)))) if len(ex) > 2 and ex.std(ddof=1) > 0 else np.nan}
        r.update(_book(g))
        rows.append(r)
    return pd.DataFrame(rows)


def judge(cells: pd.DataFrame) -> pd.DataFrame:
    """The pre-declared rule on one entry set's cells. Rank by the 10-slot book's growth over drawdown within (situation, period), random_exit
    excluded. dev leader = dev top-3. HELD = dev leader that is val top-5 with positive val net per trade and positive val book growth; NOT_HELD = dev
    leader that is not; INCONCLUSIVE = too few trades in either period. Non-leaders carry no verdict. Excess over the time-matched null is reported,
    not required: E02 found no exit beats its own-duration hold on average, so the book chooses among exits by capital speed and drawdown."""
    c = cells[cells["policy"] != "random_exit"].copy()
    c["rank"] = c.groupby(["situation", "period"])["book_mar"].rank(ascending=False, method="first", na_option="bottom")
    dev = c[c["period"] == "dev"].set_index(["situation", "policy"])
    val = c[c["period"] == "val"].set_index(["situation", "policy"])
    out = []
    for key in dev.index:
        if key not in val.index:
            continue
        d, v = dev.loc[key], val.loc[key]
        leader = d["rank"] <= DEV_TOP
        if not leader:
            verdict = ""
        elif d["trades"] < MIN_TRADES or v["trades"] < MIN_TRADES:
            verdict = "INCONCLUSIVE"
        elif v["rank"] <= VAL_TOP and v["mean_net"] > 0 and v["book_growth_pa"] > 0:
            verdict = "HELD"
        else:
            verdict = "NOT_HELD"
        out.append({"situation": key[0], "policy": key[1], "dev_rank": int(d["rank"]), "val_rank": int(v["rank"]), "dev_trades": int(d["trades"]), "val_trades": int(v["trades"]),
                    "dev_mar": d["book_mar"], "val_mar": v["book_mar"], "dev_excess": d["excess_vs_null"], "val_excess": v["excess_vs_null"], "val_excess_t": v["excess_t"],
                    "dev_net": d["mean_net"], "val_net": v["mean_net"], "val_p5": v["p5"], "val_days": v["days"], "val_growth_pa": v["book_growth_pa"], "val_max_dd": v["book_max_dd"],
                    "verdict": verdict})
    return pd.DataFrame(out)


def book_by_situation(entry_sets: tuple[str, ...] = ("BRK", "PULL", "ANY")) -> dict:
    """G01 v2. Writes gold/studies/G01_exit_book_by_situation.csv (every cell), gold/studies/G01_verdicts.csv (the judged leaders),
    registrations/exit_policy_book.md (the book a trader reads) and manifests/g01_exit_book.json (inputs with sha256, the chosen exits)."""
    import datetime as dt
    import hashlib
    import json

    state = nifty_state()
    inputs, all_cells, all_verdicts, chosen = [], [], [], {}
    for name in entry_sets:
        frames = []
        for f in (f"E02-{name}_trades.parquet", f"E03-{name}_trades.parquet"):
            p = paths.gold() / "studies" / f
            if not p.exists():
                continue
            inputs.append({"file": f, "sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "bytes": p.stat().st_size})
            frames.append(pd.read_parquet(p, columns=["sid", "signal_date", "policy", "hold_days", "net_ret", "null_net_ret"]))
        if not frames:
            continue
        tr = pd.concat(frames).drop_duplicates(["sid", "signal_date", "policy"])
        tr = tr[tr["signal_date"] >= "2000-01-01"].copy()
        tr["period"] = np.where(tr["signal_date"].dt.year < SPLIT, "dev", "val")
        tr["situation"] = state.reindex(pd.to_datetime(tr["signal_date"]).values).values
        parts = [tr.assign(situation="all"), tr[tr["situation"].notna()]]
        cells = _cells(pd.concat(parts)).assign(entry_set=name)
        verdicts = judge(cells).assign(entry_set=name)
        all_cells.append(cells)
        all_verdicts.append(verdicts)
        for sit in SITUATIONS:
            held = verdicts[(verdicts["situation"] == sit) & (verdicts["verdict"] == "HELD")].sort_values("val_mar", ascending=False)
            tried = verdicts[(verdicts["situation"] == sit) & (verdicts["verdict"] != "")]
            chosen[f"{name}/{sit}"] = ({"policy": held.iloc[0]["policy"], "val_mar": float(held.iloc[0]["val_mar"]), "val_net": float(held.iloc[0]["val_net"]),
                                        "val_excess": float(held.iloc[0]["val_excess"]), "held": int(len(held)), "tried": int(len(tried))} if len(held)
                                       else {"policy": None, "held": 0, "tried": int(len(tried)), "why": "no dev leader held up in validation" if len(tried) else "no cell"})
    cells = pd.concat(all_cells, ignore_index=True)
    verdicts = pd.concat(all_verdicts, ignore_index=True)
    cells.to_csv(paths.gold() / "studies" / "G01_exit_book_by_situation.csv", index=False)
    verdicts.to_csv(paths.gold() / "studies" / "G01_verdicts.csv", index=False)
    _write_book_md(verdicts, chosen)
    man = {"study": "G01", "version": 2, "built_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "split": SPLIT, "slots": SLOTS,
           "rule": {"dev_top": DEV_TOP, "val_top": VAL_TOP, "min_trades": MIN_TRADES, "rank_by": "book_mar", "held": "dev top-3 by book MAR; val top-5, val net>0, val book growth>0 (excess vs null reported, not required: E02)"},
           "situation": "Nifty 50 close vs 50- and 200-day averages at the signal close (SP3 stage_3_situation, first axis)", "inputs": inputs,
           "cells": int(len(cells)), "leaders": int((verdicts["verdict"] != "").sum()), "held": int((verdicts["verdict"] == "HELD").sum()),
           "not_held": int((verdicts["verdict"] == "NOT_HELD").sum()), "inconclusive": int((verdicts["verdict"] == "INCONCLUSIVE").sum()), "chosen": chosen}
    paths.manifest_dir().mkdir(parents=True, exist_ok=True)
    (paths.manifest_dir() / "g01_exit_book.json").write_text(json.dumps(man, indent=1, default=str))
    return man


def _write_book_md(verdicts: pd.DataFrame, chosen: dict) -> None:
    from pathlib import Path

    lines = ["# Exit policy book (G01 v2, generated by `python -m india.exitbook verdict`)", "",
             "For each entry set and situation (Nifty trend at the signal close), the exits that led in development (2000-2017, top 3 by 10-slot book growth "
             "over drawdown) and whether each held up in validation (2018-2023: top 5, positive net per trade, positive book growth). No exit beats its own-duration "
             "hold on average (E02), so excess over the time-matched null is shown, not required: the book chooses among exits by capital speed and drawdown. "
             f"Cells under {MIN_TRADES} trades per policy are INCONCLUSIVE. Read beside the registry verdicts, never instead of them.", "", "## Chosen exit per cell", "",
             "| entry set | situation | exit that held | val MAR | val net/trade | val excess vs null | held / tried |", "|---|---|---|---|---|---|---|"]
    for k, v in chosen.items():
        es, sit = k.split("/")
        if v["policy"]:
            lines.append(f"| {es} | {sit} | **{v['policy']}** | {v['val_mar']:.2f} | {v['val_net']*100:+.2f}% | {v['val_excess']*100:+.2f}% | {v['held']} / {v['tried']} |")
        else:
            lines.append(f"| {es} | {sit} | none ({v.get('why', '')}) | | | | {v['held']} / {v['tried']} |")
    lines += ["", "## Every development leader and its validation verdict", "",
              "| entry set | situation | policy | verdict | dev rank | val rank | dev trades | val trades | dev MAR | val MAR | val net | val p5 | val excess (t) | val growth/yr | val max dd |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    v = verdicts[verdicts["verdict"] != ""].sort_values(["entry_set", "situation", "dev_rank"])
    for r in v.itertuples():
        lines.append(f"| {r.entry_set} | {r.situation} | {r.policy} | {r.verdict} | {r.dev_rank} | {r.val_rank} | {r.dev_trades} | {r.val_trades} | {r.dev_mar:.2f} | {r.val_mar:.2f} | "
                     f"{r.val_net*100:+.2f}% | {r.val_p5*100:+.1f}% | {r.val_excess*100:+.2f}% ({r.val_excess_t:+.1f}) | {r.val_growth_pa*100:+.1f}% | {r.val_max_dd*100:.0f}% |")
    (Path(__file__).parent / "registrations" / "exit_policy_book.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    paths.ensure()
    w = sys.argv[1] if len(sys.argv) > 1 else "book"
    if w == "book":
        run()
    elif w == "verdict":
        m = book_by_situation()
        print(f"G01 v2: {m['cells']} cells, {m['leaders']} dev leaders, HELD {m['held']}, NOT_HELD {m['not_held']}, INCONCLUSIVE {m['inconclusive']}")
        for k, v in m["chosen"].items():
            print(f"  {k:18s} {v['policy'] or 'none':24s} held {v['held']}/{v['tried']}")
    elif w == "e10":
        for es in ("BRK", "PULL", "ANY"):
            e10(es, "hold_60d")
