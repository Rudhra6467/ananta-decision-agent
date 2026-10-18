"""Intraday studies on index minutes (silver/kite_index/minute, 2015-2023; dev 2015-2017, validation 2018-2023). One observation per index-day, so days do not
overlap and the t-statistic is across days. Spot side only: what the index does, which is what O-04 and the opening-hour ideas stand on.

  python -m india.istudies i01    first 30 / 60 minutes: does the opening direction carry to the close? (M-01/M-02, "wait longer")
  python -m india.istudies i05    expiry days after 13:30: does a break of the 13:00-13:29 range carry to 15:15, and how big are the afternoon moves (O-04 spot side)
  python -m india.istudies i06    time-of-day map: average absolute 1-minute move and direction by minute (descriptive, written to gold/studies/I06_map.csv)
"""
from __future__ import annotations

import math
import sys

import duckdb
import numpy as np
import pandas as pd

from india import paths, registry

NAMES = ["NIFTY 50", "NIFTY BANK", "NIFTY FIN SERVICE", "NIFTY MID SELECT"]
SYM = {"NIFTY 50": "NIFTY", "NIFTY BANK": "BANKNIFTY", "NIFTY FIN SERVICE": "FINNIFTY", "NIFTY MID SELECT": "MIDCPNIFTY"}
SPLIT = 2018


def _mins() -> pd.DataFrame:
    files = [str(p) for p in (paths.data_dir() / "silver/kite_index/minute").glob("year=*/part.parquet")]
    con = duckdb.connect()
    df = con.execute(f"select index_name, ts, open, high, low, close from read_parquet({files!r}) where list_contains(?, index_name)", [NAMES]).df()
    con.close()
    df["ts"] = pd.to_datetime(df["ts"])
    df["day"] = df["ts"].dt.normalize()
    df["hm"] = df["ts"].dt.strftime("%H:%M")
    return df


def _stat(x: pd.Series) -> tuple[float, float, int]:
    x = x.dropna()
    if len(x) < 3:
        return float("nan"), float("nan"), int(len(x))
    se = x.std(ddof=1) / math.sqrt(len(x))
    return float(x.mean()), float(x.mean() / se) if se else float("nan"), int(len(x))


def _px(g: pd.DataFrame, hm: str, col: str = "close"):
    x = g[g["hm"] == hm]
    return float(x[col].iloc[0]) if len(x) else np.nan


def i01() -> dict:
    df = _mins()
    rows = []
    for (name, day), g in df.groupby(["index_name", "day"]):
        if len(g) < 360:
            continue
        o = _px(g, "09:15", "open")
        c945, c1015, c1529 = _px(g, "09:44"), _px(g, "10:14"), _px(g, "15:29")
        rows.append({"index": name, "day": day, "r30": c945 / o - 1, "rest30": c1529 / c945 - 1, "r60": c1015 / o - 1, "rest60": c1529 / c1015 - 1})
    d = pd.DataFrame(rows)
    d["year"] = d["day"].dt.year
    reg = registry.register("I01", family="intraday", title="First 30 / 60 minutes and the rest of the day (index)",
                            hypothesis="The direction of the first 30 (or 60) minutes carries on to the close: the rest-of-day return signed by the opening direction is positive (M-01/M-02).",
                            variants=[f"{w}|{n}" for w in ("first30", "first60") for n in NAMES], note="one row per index-day; t across days; spot only")
    out = {}
    for w, a, b in (("first30", "r30", "rest30"), ("first60", "r60", "rest60")):
        for n in NAMES:
            x = d[d["index"] == n]
            signed = np.sign(x[a]) * x[b]
            dev, val = _stat(signed[x["year"] < SPLIT]), _stat(signed[x["year"] >= SPLIT])
            line = registry.record(reg, f"{w}|{n}", dev, val, extra={"same_direction_share_val": float((np.sign(x[a]) == np.sign(x[b]))[x["year"] >= SPLIT].mean())}, expect=1)
            out[f"{w}|{n}"] = line["verdict"]
            print(f"I01 {w} {n:18s} {line['verdict']:12s} dev {dev[0]*1e4:+.1f}bp t {dev[1]:+.1f} n{dev[2]} | val {val[0]*1e4:+.1f}bp t {val[1]:+.1f} n{val[2]}", flush=True)
    registry.mirror_to_catalog()
    return out


def i05() -> dict:
    df = _mins()
    cal = pd.read_parquet(paths.data_dir() / "silver/fo_calendar/expiries.parquet")
    cal = cal[cal["instrument"] == "OPTIDX"]
    exp = {(r.symbol, pd.Timestamp(r.expiry)) for r in cal.itertuples()}
    rows = []
    for (name, day), g in df.groupby(["index_name", "day"]):
        if len(g) < 360:
            continue
        rng = g[(g["hm"] >= "13:00") & (g["hm"] <= "13:29")]
        aft = g[(g["hm"] >= "13:30") & (g["hm"] <= "15:15")]
        if len(rng) < 25 or len(aft) < 100:
            continue
        hi, lo = rng["high"].max(), rng["low"].min()
        p1330 = float(aft["open"].iloc[0])
        brk = aft[(aft["close"] > hi) | (aft["close"] < lo)]
        r = {"index": name, "day": day, "expiry": (SYM[name], day) in exp, "range_pct": (hi - lo) / p1330, "move_1330_1515": float(aft["close"].iloc[-1]) / p1330 - 1,
             "abs_move": abs(float(aft["close"].iloc[-1]) / p1330 - 1), "broke": len(brk) > 0}
        if len(brk):
            t0 = brk.index[0]
            up = brk["close"].iloc[0] > hi
            px0 = float(brk["close"].iloc[0])
            r["broke_hm"] = brk["hm"].iloc[0]
            r["cont"] = (float(aft["close"].iloc[-1]) / px0 - 1) * (1 if up else -1)
            later = aft.loc[t0:]
            r["max_fav"] = ((later["high"].max() / px0 - 1) if up else (1 - later["low"].min() / px0))
        rows.append(r)
    d = pd.DataFrame(rows)
    d["year"] = d["day"].dt.year
    d.to_parquet(paths.gold() / "studies" / "I05_days.parquet")
    reg = registry.register("I05", family="intraday", title="Expiry-day afternoon: break of the 13:00-13:29 range (spot side of O-04)",
                            hypothesis="On expiry days, after the first close outside the 13:00-13:29 range, the index keeps moving the break's way to 15:15 (continuation > 0).",
                            variants=[f"cont_expiry|{n}" for n in NAMES] + [f"cont_other|{n}" for n in NAMES], note="one row per index-day; t across days")
    out = {}
    for n in NAMES:
        for tag, m in (("cont_expiry", True), ("cont_other", False)):
            x = d[(d["index"] == n) & (d["expiry"] == m)]
            dev, val = _stat(x.loc[x["year"] < SPLIT, "cont"]), _stat(x.loc[x["year"] >= SPLIT, "cont"])
            v = x[x["year"] >= SPLIT]
            extra = {"val_days": int(len(v)), "val_broke_share": float(v["broke"].mean()) if len(v) else None, "val_abs_move_median": float(v["abs_move"].median()) if len(v) else None,
                     "val_range_median": float(v["range_pct"].median()) if len(v) else None, "val_max_fav_median": float(v["max_fav"].median()) if len(v) and "max_fav" in v else None}
            line = registry.record(reg, f"{tag}|{n}", dev, val, extra=extra, expect=1)
            out[f"{tag}|{n}"] = line["verdict"]
            print(f"I05 {tag:12s} {n:18s} {line['verdict']:12s} dev {dev[0]*1e4:+.1f}bp t {dev[1]:+.1f} n{dev[2]} | val {val[0]*1e4:+.1f}bp t {val[1]:+.1f} n{val[2]} | "
                  f"val broke {extra['val_broke_share'] or 0:.0%}, |13:30-15:15| median {(extra['val_abs_move_median'] or 0)*100:.2f}%, best move after break median {(extra['val_max_fav_median'] or 0)*100:.2f}%", flush=True)
    registry.mirror_to_catalog()
    return out


def i06() -> pd.DataFrame:
    df = _mins().sort_values(["index_name", "ts"])
    df = df[(df["hm"] >= "09:15") & (df["hm"] <= "15:29")]  # normal session only (special sessions such as Muhurat trading are left out)
    df["r"] = df.groupby(["index_name", "day"])["close"].pct_change()
    df["year"] = df["ts"].dt.year
    m = df.groupby(["index_name", "hm"]).agg(abs_move_bp=("r", lambda x: float(x.abs().mean() * 1e4)), up_share=("r", lambda x: float((x > 0).mean())), n=("r", "size")).reset_index()
    m.to_csv(paths.gold() / "studies" / "I06_map.csv", index=False)
    top = m[m["index_name"] == "NIFTY 50"].sort_values("abs_move_bp", ascending=False).head(8)
    print("I06 NIFTY 50 most active minutes (mean |1-min move|, bp):", ", ".join(f"{r.hm} {r.abs_move_bp:.1f}" for r in top.itertuples()), flush=True)
    return m


def i02() -> dict:
    """Intraday level-break exits on the index (spot side). A position is opened at the 09:45 open in the direction of the first 30 minutes (I01 showed that
    direction has no edge, so this is a neutral way to get positions to exit). Exits, each decided on a 1-minute close and filled at the next minute's open:
      hold     out at 15:15
      or_break the opening range (09:15-09:44) is broken the other way
      pdl      the previous day's low (long) / high (short) is broken
      stop50   0.5% against the entry
    Paired against hold, day by day; points in basis points of the index, no costs (spot)."""
    df = _mins()
    df = df[(df["hm"] >= "09:15") & (df["hm"] <= "15:29")]
    days = {}
    for (name, day), g in df.groupby(["index_name", "day"]):
        if len(g) >= 360:
            days[(name, day)] = g.reset_index(drop=True)
    rows = []
    keys = sorted(days)
    prev = {}
    for name, day in keys:
        g = days[(name, day)]
        p = prev.get(name)
        prev[name] = (float(g["high"].max()), float(g["low"].min()))
        if p is None:
            continue
        orng = g[g["hm"] <= "09:44"]
        rest = g[(g["hm"] >= "09:45") & (g["hm"] <= "15:15")].reset_index(drop=True)
        if len(orng) < 25 or len(rest) < 300:
            continue
        side = 1 if orng["close"].iloc[-1] > orng["open"].iloc[0] else -1
        entry = float(rest["open"].iloc[0])
        hi, lo = float(orng["high"].max()), float(orng["low"].min())
        pdh, pdl = p
        out = {"index": name, "day": day, "side": side}
        c, o = rest["close"].values, rest["open"].values
        exit_px = {"hold": float(rest["close"].iloc[-1])}
        for nm, test in (("or_break", lambda x: x < lo if side > 0 else x > hi), ("pdl", lambda x: x < pdl if side > 0 else x > pdh),
                         ("stop50", lambda x: (x / entry - 1) * side < -0.005)):
            px = exit_px["hold"]
            for i in range(len(c) - 1):
                if test(c[i]):
                    px = float(o[i + 1])
                    break
            exit_px[nm] = px
        for nm, px in exit_px.items():
            out[nm] = (px / entry - 1) * side * 1e4
        rows.append(out)
    d = pd.DataFrame(rows)
    d["year"] = pd.to_datetime(d["day"]).dt.year
    d.to_parquet(paths.gold() / "studies" / "I02_days.parquet")
    reg = registry.register("I02", family="intraday", title="Intraday level-break exits on the index (spot side)",
                            hypothesis="Leaving an intraday index position on an opening-range break, a previous-day-level break or a 0.5% stop earns more than holding to 15:15.",
                            variants=[f"{x}|{n}" for x in ("or_break", "pdl", "stop50") for n in NAMES], note="09:45 entry in the first-30-minute direction; next-minute fills; bp, no costs")
    out = {}
    for n in NAMES:
        x = d[d["index"] == n]
        for e in ("or_break", "pdl", "stop50"):
            diff = x[e] - x["hold"]
            dev, val = _stat(diff[x["year"] < SPLIT] / 1e4), _stat(diff[x["year"] >= SPLIT] / 1e4)
            line = registry.record(reg, f"{e}|{n}", dev, val, extra={"val_mean_bp": float(x.loc[x["year"] >= SPLIT, e].mean()), "val_hold_bp": float(x.loc[x["year"] >= SPLIT, "hold"].mean()),
                                   "val_p5_bp": float(x.loc[x["year"] >= SPLIT, e].quantile(0.05)), "val_hold_p5_bp": float(x.loc[x["year"] >= SPLIT, "hold"].quantile(0.05))}, expect=1)
            out[f"{e}|{n}"] = line["verdict"]
            print(f"I02 {e:9s} {n:18s} {line['verdict']:12s} dev {dev[0]*1e4:+.1f}bp t {dev[1]:+.1f} n{dev[2]} | val {val[0]*1e4:+.1f}bp t {val[1]:+.1f} n{val[2]} | "
                  f"val p5 {x.loc[x['year'] >= SPLIT, e].quantile(0.05):.0f}bp vs hold {x.loc[x['year'] >= SPLIT, 'hold'].quantile(0.05):.0f}bp", flush=True)
    registry.mirror_to_catalog()
    return out


if __name__ == "__main__":
    paths.ensure()
    w = sys.argv[1] if len(sys.argv) > 1 else "all"
    for k, f in (("i01", i01), ("i02", i02), ("i05", i05), ("i06", i06)):
        if w in (k, "all"):
            f()
