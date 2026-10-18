"""The paper engine for Indian stocks: everything on, every exit rule tracked side by side, real prices, paper money, full Indian costs.

  python -m india.paper run        fetch the latest cash file, settle yesterday's decisions, decide today's, write the marks
  python -m india.paper report     what the book looks like now
  python -m india.paper settle | decide | marks      one step each

What it does (the point is to see how Ananta works in the real market and where it lacks, not to size anything):
* Three campaigns, defined before any result was seen (the same entry sets as study E02): BRK (20-day breakout on 1.5x volume, above the 200-day average),
  PULL (uptrend pulled back 5% under the 20-day average) and CTL (a seeded random draw of liquid stocks: the control, so the entries can be told from luck).
  Universe: the 250 most liquid stocks by 60-session median turnover. At most 10 BRK, 10 PULL and 5 CTL signals a day, one open position per stock per campaign.
* Every signal becomes one paper trade per exit policy (18 policies plus a random-exit control, exitlab.DEFAULT_POLICIES), each with the same 2 ATR initial stop,
  Rs 50,000 notional, delivery costs and the labelled spread estimate. All policies see the same entry, so the difference between them is the exit.
* A decision file is written after the close of day T and before the open of T+1 (decided_at, data_through, a hash). It is never rewritten. The fill is the official
  open of T+1 from the exchange file, which is only read at settle time, after the decision exists. Close-based exits (moving-average, swing-low, time) fill at the next open;
  stops and targets fill inside the bar at the level, or at the open if the bar gaps through it.
* Prices are the exchange's raw file adjusted with the corporate-action factors table (splits and bonuses), the same as the lab.
* Leak rule: the decision for day T uses rows dated T and earlier only. A test (india/leakcheck.py) edits every later row and checks the decision does not change.
* The only sealed-year read is the indicator lookback through india.sealed; no performance is computed on holdout rows.
Files: paper/decisions/<data date>.json, paper/state.json (trades), paper/events.jsonl (opens and closes), paper/marks.jsonl (one line per run per campaign and policy).
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import random
import sys

import numpy as np
import pandas as pd

from india import backfill, catalog, costs, exitlab, paths, sealed, silver

NOTIONAL = 50_000.0
LOOKBACK_CAL_DAYS = 400
CAPS = {"BRK": 10, "PULL": 10, "CTL": 5}
REENTRY_DAYS = 14
RULES_VERSION = "paper-v1-2026-10-18"
POLICIES = {p.name: p for p in exitlab.DEFAULT_POLICIES}
POLICIES["random_exit"] = exitlab.Policy("random_exit", "random")


def pdir():
    d = paths.data_dir() / "paper"
    (d / "decisions").mkdir(parents=True, exist_ok=True)
    return d


def _state() -> dict:
    p = pdir() / "state.json"
    return json.loads(p.read_text()) if p.exists() else {"trades": {}, "decisions": {}, "version": RULES_VERSION}


def _save(state: dict) -> None:
    tmp = pdir() / "state.json.tmp"
    tmp.write_text(json.dumps(state, indent=1, default=str))
    tmp.replace(pdir() / "state.json")


def _event(ev: dict) -> None:
    with (pdir() / "events.jsonl").open("a") as fh:
        fh.write(json.dumps(ev, default=str) + "\n")


# ----------------------------------------------------------------------------------------------- data

def load_adjusted(since: str | None = None, until: str | None = None, raw: pd.DataFrame | None = None) -> pd.DataFrame:
    """Raw EQ rows adjusted with the factors table. Zero prices (no trade that day) take the close. `until` cuts rows after that date (used by the leak test)."""
    since = since or (dt.date.today() - dt.timedelta(days=LOOKBACK_CAL_DAYS)).isoformat()
    df = raw.copy() if raw is not None else sealed.read_cm("paper_lookback", since)
    df["date"] = pd.to_datetime(df["date"])
    if until:
        df = df[df["date"] <= pd.Timestamp(until)]
    for c in ("open", "high", "low"):
        df[c] = df[c].where(df[c] > 0, df["close"])
    fx = pd.read_parquet(paths.data_dir() / "silver/corporate_actions/factors.parquet", columns=["symbol", "ex_date", "factor"])
    fx = fx[fx["factor"].notna() & (fx["factor"] > 0)]
    df = df.sort_values(["symbol", "date"]).reset_index(drop=True)
    ent = pd.read_parquet(paths.data_dir() / "silver/security_master/names.parquet", columns=["isin", "entity"]).drop_duplicates("isin")
    df = df.merge(ent, on="isin", how="left")
    df["sid"] = df["entity"].fillna(df["symbol"])
    df = df.sort_values(["symbol", "date"]).reset_index(drop=True)
    cum = np.ones(len(df))
    by = {s: g for s, g in fx.groupby("symbol")}
    syms = df["symbol"].values
    dates = df["date"].values
    bounds = np.r_[np.flatnonzero(syms[1:] != syms[:-1]) + 1, len(df)]
    first = 0
    for end in bounds:
        s = syms[first]
        if s in by:
            for ex, f in zip(by[s]["ex_date"].values, by[s]["factor"].values):
                cum[first:end] *= np.where(dates[first:end] < ex, f, 1.0)
        first = end
    for c in ("open", "high", "low", "close"):
        df["adj_" + c] = df[c] / cum
    df["cum_factor"] = cum
    df = df.sort_values(["sid", "date", "turnover"], ascending=[True, True, False]).drop_duplicates(["sid", "date"]).reset_index(drop=True)
    return df


def _atr14(g: pd.DataFrame) -> float:
    h, l, c = (g["adj_" + k].values for k in ("high", "low", "close"))
    pc = np.r_[np.nan, c[:-1]]
    tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    tr[0] = h[0] - l[0]
    return float(np.nanmean(tr[-14:]))


def features(df: pd.DataFrame, asof: pd.Timestamp) -> pd.DataFrame:
    """One row per liquid stock on `asof`, from rows dated on or before it. Mirrors india.lab (checked by leakcheck.parity)."""
    df = df[df["date"] <= asof]
    out = []
    for sid, g in df.groupby("sid", sort=False):
        if g["date"].iloc[-1] != asof or len(g) < 126:
            continue
        o, h, l, c = (g["adj_" + k].values for k in ("open", "high", "low", "close"))
        v = g["volume"].values.astype(float)
        t = g["turnover"].values.astype(float)
        pc = np.r_[np.nan, c[:-1]]
        tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
        tr[0] = h[0] - l[0]
        out.append({"sid": sid, "symbol": g["symbol"].iloc[-1], "close": c[-1], "raw_close": g["close"].iloc[-1], "atr14": float(np.nanmean(tr[-14:])), "med60_turnover": float(np.median(t[-60:])),
                    "vol_ratio20": float(v[-1] / np.mean(v[-21:-1])) if np.mean(v[-21:-1]) > 0 else np.nan,
                    "dist_sma20": float(c[-1] / np.mean(c[-20:]) - 1), "dist_sma50": float(c[-1] / np.mean(c[-50:]) - 1), "dist_sma200": float(c[-1] / np.mean(c[-200:]) - 1),
                    "breakout20": bool(c[-1] > np.max(h[-21:-1])), "ret_20": float(c[-1] / c[-21] - 1)})
    f = pd.DataFrame(out)
    if f.empty:
        return f
    f = f[f["raw_close"] > 10].copy()
    f["liq_rank"] = f["med60_turnover"].rank(ascending=False, method="min").astype(int)
    return f.sort_values("liq_rank").reset_index(drop=True)


def signals(f: pd.DataFrame, asof: pd.Timestamp) -> dict[str, pd.DataFrame]:
    liq = f[(f["liq_rank"] <= 250) & f["atr14"].notna()]
    brk = liq[liq["breakout20"] & (liq["vol_ratio20"] > 1.5) & (liq["dist_sma200"] > 0)].sort_values("vol_ratio20", ascending=False)
    pull = liq[(liq["dist_sma200"] > 0) & (liq["dist_sma20"] < -0.05)].sort_values("dist_sma20")
    rng = random.Random(int(asof.strftime("%Y%m%d")))
    idx = sorted(liq.index)
    ctl = liq.loc[rng.sample(idx, min(len(idx), 40))] if idx else liq  # draw 40, the open-position filter below trims to the cap
    return {"BRK": brk, "PULL": pull, "CTL": ctl}


# ----------------------------------------------------------------------------------------------- steps

def fetch_latest() -> dict:
    today = dt.date.today()
    res = backfill.run("cm_bhavcopy", today - dt.timedelta(days=4), today, 1.0)
    out = {"fetch": "ok"}
    out["silver"] = silver.build_cm_year(today.year)
    return out


def decide(state: dict | None = None, raw: pd.DataFrame | None = None, write: bool = True, asof: str | None = None) -> dict:
    state = state or _state()
    df = load_adjusted(raw=raw, until=asof)
    last = df["date"].max()
    key = last.strftime("%Y-%m-%d")
    if key in state["decisions"]:
        return {"status": "already decided", "data_through": key}
    f = features(df, last)
    if f.empty:
        return {"status": "no features", "data_through": key}
    sigs = signals(f, last)
    open_by = {(t["campaign"], t["sid"]) for t in state["trades"].values() if t["status"] in ("pending", "open")}
    recent = {}
    for t in state["trades"].values():
        recent[(t["campaign"], t["sid"])] = max(recent.get((t["campaign"], t["sid"]), ""), t["signal_date"])
    chosen = []
    for camp, d in sigs.items():
        n = 0
        for _, r in d.iterrows():
            k = (camp, r["sid"])
            if k in open_by:
                continue
            if k in recent and (last - pd.Timestamp(recent[k])).days < REENTRY_DAYS:
                continue
            chosen.append({"campaign": camp, "sid": r["sid"], "symbol": r["symbol"], "atr14": float(r["atr14"]), "close": float(r["close"]), "raw_close": float(r["raw_close"]), "liq_rank": int(r["liq_rank"]),
                           "vol_ratio20": None if pd.isna(r["vol_ratio20"]) else float(r["vol_ratio20"]), "dist_sma20": float(r["dist_sma20"]), "dist_sma200": float(r["dist_sma200"])})
            n += 1
            if n >= CAPS[camp]:
                break
    counts = {camp: int(len(d)) for camp, d in sigs.items()}
    body = {"rules": RULES_VERSION, "data_through": key, "decided_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "universe_size": int(len(f)),
            "candidates": counts, "signals": chosen}
    body["sha256"] = hashlib.sha256(json.dumps({k: body[k] for k in ("rules", "data_through", "signals")}, sort_keys=True).encode()).hexdigest()
    if write:
        path = pdir() / "decisions" / f"{key}.json"
        if path.exists():
            raise FileExistsError(f"decision file for {key} already exists and is never rewritten")
        path.write_text(json.dumps(body, indent=1))
        state["decisions"][key] = {"status": "pending", "signals": len(chosen), "sha256": body["sha256"]}
        _save(state)
    return {"status": "decided", "data_through": key, "signals": len(chosen), "candidates": counts, "body": body}


def settle(state: dict | None = None) -> dict:
    """Fill pending decisions at the next session's open, then step every open trade through the bars so far."""
    state = state or _state()
    df = load_adjusted()
    latest = df["date"].max()
    filled = closed = unfilled = 0
    bars_by = {s: g.reset_index(drop=True) for s, g in df.groupby("sid")}
    for key, dmeta in sorted(state["decisions"].items()):
        if dmeta["status"] != "pending":
            continue
        nxt = df.loc[df["date"] > pd.Timestamp(key), "date"].min()
        if pd.isna(nxt):
            continue  # no session after the decision yet
        body = json.loads((pdir() / "decisions" / f"{key}.json").read_text())
        for s in body["signals"]:
            g = bars_by.get(s["sid"])
            row = None if g is None else g[g["date"] == nxt]
            for pol in POLICIES.values():
                tid = f"{key}|{s['campaign']}|{s['sid']}|{pol.name}"
                if tid in state["trades"]:
                    continue
                if row is None or row.empty:
                    state["trades"][tid] = {"id": tid, "campaign": s["campaign"], "sid": s["sid"], "symbol": s["symbol"], "policy": pol.name, "signal_date": key, "status": "unfilled",
                                            "note": "no print on the fill session"}
                    unfilled += 1
                    continue
                entry_adj = float(row["adj_open"].iloc[0])
                # risk is carried as a fraction of the entry price so later corporate actions rescale it consistently; the 14-day range is
                # recomputed from the bars up to the signal date under today's factors, so a split between decision and fill cannot skew it
                gs = g[g["date"] <= pd.Timestamp(key)]
                risk_frac = exitlab.STOP_ATR * _atr14(gs) / entry_adj
                if risk_frac >= 1:
                    state["trades"][tid] = {"id": tid, "campaign": s["campaign"], "sid": s["sid"], "symbol": s["symbol"], "policy": pol.name, "signal_date": key, "status": "skipped", "note": "stop below zero"}
                    continue
                rand_day = random.Random(tid).randint(1, exitlab.HORIZON) if pol.kind == "random" else None
                state["trades"][tid] = {"id": tid, "campaign": s["campaign"], "sid": s["sid"], "symbol": s["symbol"], "policy": pol.name, "signal_date": key, "entry_date": nxt.strftime("%Y-%m-%d"),
                                        "entry_raw": float(row["open"].iloc[0]), "entry_adj": entry_adj, "risk_frac": risk_frac, "rand_day": rand_day, "liq_rank": s["liq_rank"],
                                        "status": "open", "decision_sha": dmeta["sha256"]}
                _event({"event": "open", "id": tid, "at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "entry_date": nxt.strftime("%Y-%m-%d"), "entry_raw": float(row["open"].iloc[0])})
                filled += 1
        dmeta["status"] = "filled"
        dmeta["filled_on"] = nxt.strftime("%Y-%m-%d")
    for tid, t in state["trades"].items():
        if t["status"] != "open":
            continue
        g = bars_by[t["sid"]]
        w = g[g["date"] >= pd.Timestamp(t["entry_date"])].head(exitlab.HORIZON + 1)
        if w.empty:
            continue
        o, h, l, c = (w["adj_" + k].values for k in ("open", "high", "low", "close"))
        # the factors table can change after entry (a split announced later): re-anchor on the current adjusted entry
        entry = float(o[0])
        risk = t["risk_frac"] * entry
        k, px, why, peak = exitlab._exit(POLICIES[t["policy"]], o, h, l, c, entry, risk, live=True, rand_day=t.get("rand_day"))
        t["last_close_adj"] = float(c[-1])
        t["last_date"] = w["date"].iloc[-1].strftime("%Y-%m-%d")
        t["peak_adj"] = float(max(peak, h.max()))
        if why in ("open", "pending"):
            t["unrealised_ret"] = float(c[-1] / entry - 1)
            continue
        qty = NOTIONAL / entry
        rt = costs.round_trip("delivery", NOTIONAL, px * qty, year=int(w["date"].iloc[k].year), turnover_rank=t.get("liq_rank"))
        net = (px * qty - NOTIONAL - rt["total"])
        move = peak - entry
        t.update({"status": "closed", "exit_date": w["date"].iloc[k].strftime("%Y-%m-%d"), "exit_reason": why, "exit_adj": float(px), "gross_ret": float(px / entry - 1),
                  "net_inr": float(net), "net_ret": float(net / NOTIONAL), "cost_inr": float(rt["total"]), "hold_days": int(k + 1), "r_net": float(net / NOTIONAL / t["risk_frac"]),
                  "mfe_r": float(move / risk), "capture": float(np.clip((px - entry) / move, -1, 1)) if move > 0 else None, "giveback_r": float((peak - px) / risk)})
        t.pop("unrealised_ret", None)
        _event({"event": "close", "id": tid, "at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "exit_date": t["exit_date"], "reason": why, "net_inr": t["net_inr"]})
        closed += 1
    _save(state)
    return {"filled": filled, "unfilled": unfilled, "closed": closed, "latest_session": latest.strftime("%Y-%m-%d")}


def marks(state: dict | None = None) -> list[dict]:
    state = state or _state()
    rows = []
    t = pd.DataFrame(state["trades"].values())
    if t.empty:
        return rows
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    for (camp, pol), g in t[t["status"].isin(["open", "closed"])].groupby(["campaign", "policy"]):
        cl = g[g["status"] == "closed"]
        op = g[g["status"] == "open"]
        rows.append({"at": now, "campaign": camp, "policy": pol, "closed": int(len(cl)), "open": int(len(op)), "realised_inr": float(cl["net_inr"].sum()) if len(cl) else 0.0,
                     "open_unrealised_inr": float((op["unrealised_ret"].fillna(0) * NOTIONAL).sum()) if len(op) and "unrealised_ret" in op else 0.0,
                     "mean_net_ret": float(cl["net_ret"].mean()) if len(cl) else None, "win_rate": float((cl["net_inr"] > 0).mean()) if len(cl) else None,
                     "expectancy_R": float(cl["r_net"].mean()) if len(cl) else None, "capture_median": float(cl["capture"].dropna().median()) if len(cl) and cl["capture"].notna().any() else None})
    with (pdir() / "marks.jsonl").open("a") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    con = catalog.connect()
    con.execute("create table if not exists paper_marks (at varchar, campaign varchar, policy varchar, closed integer, open integer, realised_inr double, open_unrealised_inr double, "
                "mean_net_ret double, win_rate double, expectancy_R double, capture_median double)")
    con.executemany("insert into paper_marks values (?,?,?,?,?,?,?,?,?,?,?)", [[r[k] for k in ("at", "campaign", "policy", "closed", "open", "realised_inr", "open_unrealised_inr", "mean_net_ret",
                                                                                                "win_rate", "expectancy_R", "capture_median")] for r in rows])
    con.close()
    return rows


def run() -> dict:
    paths.ensure()
    out = {}
    try:
        out["fetch"] = fetch_latest()
    except Exception as e:  # the nightly job heals missing days; the engine works with what is there
        out["fetch"] = f"FAILED {type(e).__name__}: {e}"
    state = _state()
    out["settle"] = settle(state)
    d = decide(state)
    d.pop("body", None)
    out["decide"] = d
    out["marks"] = len(marks(state))
    catalog.heartbeat("paper.run", not str(out["fetch"]).startswith("FAILED"), json.dumps(out, default=str)[:480])
    print(json.dumps(out, default=str, indent=1), flush=True)
    return out


def report() -> None:
    state = _state()
    t = pd.DataFrame(state["trades"].values())
    print(f"decisions {len(state['decisions'])}  trades {len(t)}")
    if t.empty:
        return
    print(t["status"].value_counts().to_string())
    cl = t[t["status"] == "closed"]
    if len(cl):
        summ = cl.groupby(["campaign", "policy"]).agg(n=("net_inr", "size"), net_inr=("net_inr", "sum"), mean_ret=("net_ret", "mean"), win=("net_inr", lambda x: (x > 0).mean()),
                                                      R=("r_net", "mean"), capture=("capture", "median")).round(3)
        print(summ.to_string())


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "report"
    {"run": run, "report": report, "settle": lambda: print(settle()), "decide": lambda: print({k: v for k, v in decide().items() if k != "body"}),
     "marks": lambda: print(len(marks()))}[cmd]()
