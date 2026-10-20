"""SP1 paper: the frozen index playbook (registrations/sp1_v2.json) traded on paper from Wed 21 Oct 2026 (Madhav, 19 Oct: "2. yes": a futures
shadow book of 1 lot and a 1-lot option line, written before the fill, scored at night). Nothing here can place an order: Kite is read with
GET only (india/kite.py has no order method) and the files stay on the Mac (paper/ is not in the R2 sync).

  python -m india.sp1paper export            the live model = the spec's fold for the current year (2026: refitted on 2015-2025 with the frozen
                                              rules, the margin c by the same nested CV), checked against the completed holdout run's own 2026
                                              predictions and trades -> paper/sp1/model_2026.json, manifests/sp1paper_model.json
  python -m india.sp1paper replay [dates]    past sessions through the live code (Kite candles cut at each decision time), compared with the
                                              holdout run's state rows and trades; writes no ledger row -> manifests/sp1paper_replay.json
  python -m india.sp1paper prepare [date]    before the session: inputs refreshed, the overnight situation, the D0 choice for each gap bucket, the
                                              breadth universe and the contracts -> paper/sp1/plans/<date>.json (its hash goes in the ledger)
  python -m india.sp1paper live [date]       the session: decisions at 09:15, 09:30, 09:45 and 10:15 IST appended to paper/sp1/decisions.jsonl
  python -m india.sp1paper score [date]      after the close: each trade three ways (the study's index proxy; the 1-lot future and the 1-lot option
                                              at real Kite prices); a NEXTOPEN exit is scored the next evening -> paper/sp1/outcomes.jsonl, book.json
  python -m india.sp1paper run               the launchd entry (22:00 Toronto): prepare, wait for 09:15 IST, live; returns after 10:16 IST
                                              (needs a Kite sign-in made AFTER Zerodha's morning token flush, about 07:00-07:30 IST)
  python -m india.sp1paper verify            hash chains of both ledgers and the timing rule

Fills. The study fills a decision at the open of its entry bar (D0: 09:16; D1: 09:30; D2: 09:45; D3: 10:15) and reads the bars that closed
by then. D0 is decided before 09:16, so its study fill is real. At D1-D3 the bars are read a few seconds after the decision time, so each
trade is also scored with a realistic fill, the open of the minute after the decision row was written; both are kept.
Differences from the study, by construction: a session's data completeness is checked on the bars so far (the study's "at least 360
minutes" and the breadth names' "at least 70 five-minute bars" use the whole day); the entry price used for ORSTOP's availability and the
planned cost is the latest price at the decision (the study used the entry bar's open, a few seconds later).
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import io
import json
import sys
import time
from pathlib import Path
from zoneinfo import ZoneInfo

import duckdb
import numpy as np
import pandas as pd

from india import costs, kite, ocstudy, paths, scenario, sealed, sp1, sp1_holdout

IST = ZoneInfo("Asia/Kolkata")
YEAR = 2026
PAPER_START = dt.date(2026, 10, 21)   # Madhav, 19 Oct 2026: paper from Wednesday 21 October
ROOT = paths.data_dir() / "paper" / "sp1"
MODEL = ROOT / f"model_{YEAR}.json"
DECISIONS = ROOT / "decisions.jsonl"
OUTCOMES = ROOT / "outcomes.jsonl"


def _use(root: Path) -> None:
    """Point the ledgers at another folder (the rehearsal keeps its own, so the paper record starts clean on PAPER_START)."""
    global ROOT, DECISIONS, OUTCOMES
    ROOT, DECISIONS, OUTCOMES = root, root / "decisions.jsonl", root / "outcomes.jsonl"
POINT_TIME = {"D0": dt.time(9, 15), "D1": dt.time(9, 30), "D2": dt.time(9, 45), "D3": dt.time(10, 15)}
LAST_BAR = {"D0": 0, "D1": scenario.DEC["D1"], "D2": scenario.DEC["D2"], "D3": scenario.DEC["D3"]}
READ_DELAY_S = {"D0": 8, "D1": 5, "D2": 5, "D3": 5}
LATE_S = 180            # a decision written later than this after its time is logged but never traded
NAMES = ("NIFTY 50", "NIFTY BANK", "INDIA VIX")


# ----------------------------------------------------------------------------------------------------------------------------- ledgers
def _canon(row: dict) -> str:
    return json.dumps({k: v for k, v in row.items() if k != "hash"}, sort_keys=True, separators=(",", ":"), default=str)


def _rows(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()] if p.exists() else []


def _append(p: Path, row: dict) -> dict:
    p.parent.mkdir(parents=True, exist_ok=True)
    rows = _rows(p)
    row = json.loads(json.dumps(row, default=str))
    row["prev_hash"] = rows[-1]["hash"] if rows else "genesis"
    row["hash"] = hashlib.sha256((row["prev_hash"] + _canon(row)).encode()).hexdigest()
    with p.open("a") as fh:
        fh.write(json.dumps(row) + "\n")
    return row


def verify() -> dict:
    out = {}
    for name, p in (("decisions", DECISIONS), ("outcomes", OUTCOMES)):
        prev, n, bad = "genesis", 0, None
        for i, r in enumerate(_rows(p), 1):
            if r.get("prev_hash") != prev or hashlib.sha256((prev + _canon(r)).encode()).hexdigest() != r.get("hash"):
                bad = i
                break
            prev, n = r["hash"], n + 1
        out[name] = {"rows": n, "chain": "intact" if bad is None else f"BROKEN at line {bad}"}
    late = []
    for r in _rows(DECISIONS):
        if r.get("kind") == "decision" and r.get("tradable") and r.get("choice"):
            t = dt.datetime.fromisoformat(r["decided_at"])
            fill = dt.datetime.combine(dt.date.fromisoformat(r["date"]), dt.time(9, 15), IST) + dt.timedelta(minutes=r["fill_next_bar"])
            if t >= fill:
                late.append(f"{r['date']} {r['index']} {r['point']}")
    out["decided_after_realistic_fill"] = late
    out["ok"] = all(v["chain"] == "intact" for k, v in out.items() if isinstance(v, dict)) and not late
    return out


# ----------------------------------------------------------------------------------------------------------------------------- model
def _holdout_tables():
    """Outcomes and states 2015-2023 (silver/gold) plus the completed holdout run's own rows inside its window (purpose paper_model)."""
    D = paths.data_dir()
    h = sealed.holdout_outputs("sp1_holdout", "paper_model")
    man = json.loads((paths.manifest_dir() / "sp1_holdout_results.json").read_text())
    start, end = (pd.Timestamp(x).date() for x in man["window"])
    og, oh = pd.read_parquet(D / "gold/studies/SP1_outcomes.parquet"), pd.read_parquet(h / "outcomes.parquet")
    sg, sh = pd.read_parquet(D / "gold/scenario/index_states.parquet"), pd.read_parquet(h / "index_states.parquet")
    pt = pd.read_parquet(h / "policy_trades.parquet")
    for x in (og, oh, sg, sh, pt):
        x["date"] = pd.to_datetime(x["date"]).dt.date
    o = pd.concat([og, oh[(oh["date"] >= start) & (oh["date"] <= end)]], ignore_index=True)
    st = pd.concat([sg, sh[(sh["date"] >= start) & (sh["date"] <= end)]], ignore_index=True)
    return o, st, pt, man


def _terc(x, q) -> str:
    if x is None or x != x:
        return "missing"
    return "low" if x <= q[0] else ("mid" if x <= q[1] else "high")


def _fixed3(x, lo, hi, names=("down", "flat", "up")) -> str:
    if x is None or x != x:
        return "missing"
    return names[0] if x <= lo else (names[2] if x >= hi else names[1])


def levels(row: dict, point: str, cut: dict) -> dict:
    """sp1.feature_frame for one state row, with the fold's tercile cut-offs (same rules, same order)."""
    tr = row.get("trend")
    f = {"trend": tr if isinstance(tr, str) else "missing", "vix": _terc(row.get("vix_prev"), cut["vix"]),
         "us": _fixed3(row.get("us_qqq_ret"), -0.005, 0.005), "positioning": _terc(row.get("fii_long_share"), cut["positioning"]),
         "event": "today" if row.get("event_scheduled") else ("recent" if row.get("event_recent") else "none"),
         "expiry": "yes" if row.get("expiry") else "no", "gap": _fixed3(row.get("gap"), -0.0025, 0.0025)}
    if point != "D0":
        f["move"] = _terc(row.get(f"move_{point}"), cut[f"move_{point}"])
        f["breadth"] = _fixed3(row.get(f"breadth_{point}"), 0.40, 0.60, names=("weak", "mid", "strong"))
        f["agreement"] = "yes" if row.get(f"agree_{point}") else "no"
        f["or_width"] = _terc(row.get("or15_atr") if point == "D1" else row.get("or30_atr"), cut[f"or_width_{point}"])
    return f


def xrow(f: dict) -> np.ndarray:
    v = [1.0]
    for c, lv in f.items():
        v.extend(1.0 if lv == x else 0.0 for x in sp1.LEVELS[c][1:])
    return np.array(v)


def predict(m: dict, x: np.ndarray) -> tuple[float, float]:
    b, M = np.asarray(m["beta"]), np.asarray(m["M"])
    X = x[None, :]
    se = np.sqrt(np.maximum(np.einsum("ij,jk,ik->i", X, M, X), 0.0) * m["s2"])
    return float((X @ b)[0]), float(se[0])


def choose(cands: list[dict], c: float) -> dict | None:
    """sp1.run_policy at one point: the highest predicted net among actions with pred_net > c x se and > 0 (ties: lower action id)."""
    q = [x for x in cands if x["pred_net"] > c * x["se"] and x["pred_net"] > 0]
    return sorted(q, key=lambda x: (-x["pred_net"], x["action"]))[0] if q else None


def _model_sha() -> str:
    return hashlib.sha256(MODEL.read_bytes()).hexdigest()[:16]


def load_model() -> dict:
    m = json.loads(MODEL.read_text())
    if m["spec_sha"] != sp1.spec_sha():
        raise SystemExit("the live model was fitted for another version of the registration")
    return m


def export(log=print) -> dict:
    o, st, pt, man = _holdout_tables()
    log("planned costs (as the holdout run computed them)")
    o["pcost"] = sp1.planned_cost_bps(o)
    out = {"spec_sha": sp1.spec_sha(), "year": YEAR, "made_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "trained_on": f"2015-01-01..{YEAR - 1}-12-31, the last {YEAR - 1} session dropped (its NEXTOPEN label is {YEAR}'s first open), as the fold does",
           "indices": {}}
    checks = {}
    for sym in sp1.IDX:
        log(f"{sym}: the {YEAR} fold")
        keep: dict = {}
        pr, lams = sp1.fold_predictions(o, st, sym, YEAR, keep_models=keep)
        c = sp1.calibrate_c(o, st, sym, YEAR, lams)
        c_run = next(f["c"] for f in man["rows"][f"SP1H|{sym}|future_proxy|policy"]["extra"]["folds"] if f["test_year"] == YEAR)
        cut = sp1.tercile_cutoffs(st, sym, YEAR)
        models = {f"{p}|{a}": {"point": p, "action": int(a), "exit": sp1.ACTIONS[a][0], "dir": int(sp1.ACTIONS[a][1]), "lam": float(m.lam),
                                "s2": float(m.s2), "beta": m.beta.tolist(), "M": (m.A_inv @ m.XtX @ m.A_inv).tolist()} for (p, a), m in sorted(keep.items())}
        out["indices"][sym] = {"c": c, "cutoffs": cut, "models": models}
        # parity 1: levels and design rows equal sp1.feature_frame / sp1.design on every row of the year
        s = st[st["index"] == sym].set_index("date").sort_index()
        tr_days = [d for d in s.index if 2015 <= d.year < YEAR][:-1]
        mask = pd.Series(s.index.isin(tr_days), index=s.index)
        yr = [d for d in s.index if d.year == YEAR]
        bad_x = 0
        X_by = {}
        for P in sp1.POINT_ENTRY:
            ff = sp1.feature_frame(s, P, mask)
            Xf = pd.DataFrame(sp1.design(ff), index=ff.index)
            for d in yr:
                x = xrow(levels(s.loc[d].to_dict(), P, cut))
                X_by[(d, P)] = x
                bad_x += int(not np.array_equal(x, Xf.loc[d].to_numpy()))
        # parity 2: the exported models' predictions equal the fold's
        dp = []
        for r in pr.itertuples():
            g, se = predict(models[f"{r.point}|{r.action}"], X_by[(r.date, r.point)])
            dp.append(max(abs(g - r.pred_gross), abs(se - r.se)))
        # parity 3: the sequential live choice equals sp1.run_policy and the holdout run's own trades
        live_tr = []
        for d, g in pr.groupby("date"):
            for P in sp1.POINT_ENTRY:
                gp = g[g["point"] == P]
                cands = [{"action": int(a), "pred_net": float(pg - pc), "se": float(se)} for a, pg, pc, se in zip(gp["action"], gp["pred_gross"], gp["pcost"], gp["se"])]
                ch = choose(cands, c)
                if ch:
                    live_tr.append((d, P, ch["action"]))
                    break
        rp = sp1.run_policy(pr, c)
        rp_set = set(zip(rp["date"], rp["point"], rp["action"].astype(int)))
        m26 = (pt["index"] == sym) & pt["date"].map(lambda d: d.year == YEAR)
        run_set = {(d, p, int(a)) for d, p, a in zip(pt.loc[m26, "date"], pt.loc[m26, "point"], pt.loc[m26, "action"])}
        checks[sym] = {"c": c, "c_in_holdout_run": c_run, "models": len(models), "rows_checked": len(yr), "design_mismatches": bad_x,
                       "max_prediction_diff": float(max(dp) if dp else 0.0), "trades_live": len(live_tr), "trades_run_policy": len(rp_set),
                       "trades_holdout_run": len(run_set), "live_eq_run_policy": set(live_tr) == rp_set, "live_eq_holdout_run": set(live_tr) == run_set}
        log(f"{sym}: {checks[sym]}")
    ok = all(v["c"] == v["c_in_holdout_run"] and v["design_mismatches"] == 0 and v["max_prediction_diff"] < 1e-9 and v["live_eq_holdout_run"]
             and v["live_eq_run_policy"] for v in checks.values())
    if not ok:
        raise SystemExit(f"parity failed, model not written: {checks}")
    MODEL.parent.mkdir(parents=True, exist_ok=True)
    MODEL.write_text(json.dumps(out))
    res = {"model": str(MODEL.relative_to(paths.data_dir())), "model_sha": _model_sha(), "spec_sha": out["spec_sha"], "year": YEAR, "checks": checks, "PASS": ok}
    (paths.manifest_dir() / "sp1paper_model.json").write_text(json.dumps(res, indent=1, default=str))
    return res


# ----------------------------------------------------------------------------------------------------------------------------- inputs
def _ist_now() -> dt.datetime:
    return dt.datetime.now(IST)


def _instruments(k: kite.Kite, exch: str) -> list[dict]:
    today = dt.date.today()
    p = paths.bronze("kite_instruments") / f"{exch}_{today:%Y%m%d}.csv"
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(k.instruments(exch))
    return list(csv.DictReader(io.StringIO(p.read_text())))


def _candles(k: kite.Kite, token: int, interval: str, a: dt.date, b: dt.date) -> pd.DataFrame:
    rows = k.historical_all(int(token), interval, a, b) if interval != "day" else k.historical(int(token), interval, a, b)
    df = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close", "volume"] + (["oi"] if rows and len(rows[0]) > 6 else []))
    if df.empty:
        return pd.DataFrame(columns=["date", "m", "open", "high", "low", "close", "volume"])
    ts = df["ts"].astype(str)
    df["date"] = pd.to_datetime(ts.str[:10]).dt.date
    df["m"] = ts.str[11:13].astype(int) * 60 + ts.str[14:16].astype(int) - 555
    return df[["date", "m", "open", "high", "low", "close", "volume"]]


class _FrameReader:
    """sp1_holdout.universe_ranks reads through rd.q(folder, select, where): here the rows come from the logged paper_lookback read."""

    def __init__(self, df: pd.DataFrame):
        self.df = df

    def q(self, folder, select, where="", params=None, group_by=""):
        con = duckdb.connect()
        con.register("t", self.df)
        out = con.execute(f"select {select} from t" + (f" where {where}" if where else "") + (f" group by {group_by}" if group_by else ""),
                          list(params or [])).df()
        con.close()
        return out


def _specials() -> set[dt.date]:
    sp = json.loads((paths.manifest_dir() / "special_sessions.json").read_text())["dates"]
    return {dt.date.fromisoformat(x) for x in sp}


def refresh(day: dt.date, prev: dt.date, log=print) -> dict:
    """The previous session's files the overnight read needs, if the nightly job has not fetched them yet (NSE 1 request a second)."""
    from india import backfill, flows, silver, usclose

    out = {}
    for name, fn in (("us_close", usclose.update), ("cm_bhavcopy", lambda: backfill.run("cm_bhavcopy", prev, prev, 1.0)),
                     ("cm_silver", lambda: silver.build_cm_year(prev.year)), ("participant_oi", lambda: flows.fetch_days([prev])),
                     ("flows_silver", flows.build)):
        try:
            r = fn()
            out[name] = "ok" if not isinstance(r, dict) else {k: v for k, v in r.items() if k in ("files", "rows", "fetched", "last", "QQQ")}
        except Exception as e:  # a failed refresh shows as a stale input in the plan, never as a silent default
            out[name] = f"FAILED {type(e).__name__}: {str(e)[:120]}"
        log(f"refresh {name}: {out[name]}")
    return out


def overnight(k: kite.Kite, day: dt.date, nse_tokens: dict, nfo: list[dict] | None) -> dict:
    """Everything SP1 knows before 09:15 for each index (scenario.build's overnight columns, computed the same way)."""
    D = paths.data_dir()
    raw = []
    for name in NAMES:
        c = _candles(k, nse_tokens[name], "day", day - dt.timedelta(days=430), day - dt.timedelta(days=1))
        raw.append(c.assign(index_name=name))
    raw = pd.concat(raw, ignore_index=True)
    raw = raw[raw["date"] < day]
    daily = {sym: scenario._daily(name, raw).set_index("date") for sym, name in scenario.IDX.items()}
    vix = scenario._daily("INDIA VIX", raw).set_index("date")["close"]
    sessions = sorted(daily["NIFTY"].index)
    prev = sessions[-1]
    prev3 = set(sessions[-3:])
    us = pd.read_parquet(D / "silver/us/us_close.parquet")
    qqq = us[us["symbol"] == "QQQ"].dropna(subset=["ret"]).set_index("date")["ret"].sort_index()
    q = qqq[qqq.index < day]
    fl = sealed.read_flows("paper_lookback", (day - dt.timedelta(days=40)).isoformat())
    fl = fl[(fl["client_type"] == "FII") & (fl["date"] < day)].sort_values("date")
    fii = (fl["future_index_long"] / (fl["future_index_long"] + fl["future_index_short"])) if len(fl) else pd.Series(dtype=float)
    sched = scenario.scheduled_dates()
    fc = pd.read_parquet(next(p for p in (D / "silver/fo_calendar").iterdir() if p.suffix == ".parquet"))
    fc = fc[fc["instrument"] == "OPTIDX"]
    exp = {s: set(pd.to_datetime(fc.loc[fc["symbol"] == s, "expiry"]).dt.date) for s in scenario.IDX}
    for r in nfo or []:
        if r["name"] in exp and r["instrument_type"] in ("CE", "PE"):
            exp[r["name"]].add(dt.date.fromisoformat(r["expiry"]))
    out = {"date": day.isoformat(), "prev_date": prev.isoformat(), "sessions_tail": [d.isoformat() for d in sessions[-25:]], "rows": {}}
    for sym in scenario.IDX:
        p = daily[sym].loc[prev]
        row = {"date": day, "index": sym, "prev_date": prev, "prev_close": float(p["close"]), "sma50": float(p["sma50"]), "sma200": float(p["sma200"]),
               "atr14_prev": float(p["atr14"]), "vix_prev": float(vix.get(prev, np.nan)),
               "us_qqq_ret": float(q.iloc[-1]) if len(q) else np.nan, "us_qqq_date": q.index[-1] if len(q) else None,
               "fii_long_share": float(fii.iloc[-1]) if len(fii) else np.nan, "fii_date": fl["date"].iloc[-1] if len(fl) else None,
               "event_scheduled": day in sched, "event_recent": any(x in prev3 for x in sched), "expiry": day in exp[sym]}
        row["trend"] = "up" if p["close"] > p["sma50"] and p["close"] > p["sma200"] else ("down" if p["close"] < p["sma50"] and p["close"] < p["sma200"] else "mixed")
        out["rows"][sym] = row
    # staleness, shown in the plan (the study had complete inputs; live inputs can lag)
    last_us_weekday = day - dt.timedelta(days=1)
    while last_us_weekday.weekday() >= 5:
        last_us_weekday -= dt.timedelta(days=1)
    r0 = out["rows"]["NIFTY"]
    out["stale"] = {"us_qqq": (r0["us_qqq_date"] is None or r0["us_qqq_date"] < last_us_weekday),
                    "participant_oi": (r0["fii_date"] is None or r0["fii_date"] < prev)}
    return out


def breadth_universe(k: kite.Kite, day: dt.date, prev: dt.date, sessions: list[dt.date], nse_rows: list[dict], log=print) -> dict:
    """The OC v1 breadth names for `day` (sp1_holdout.breadth): top 50 by 60-session median turnover on the previous session, linked to Kite,
    no ETF, an rvol baseline (median cumulative 5-minute volume of the previous 20 regular sessions, at least 15 valid) at every bar to 10:10."""
    cm = sealed.read_cm("paper_lookback", (day - dt.timedelta(days=440)).isoformat())
    cm["date"] = pd.to_datetime(cm["date"]).dt.date
    cm = cm[cm["date"] < day]
    u = sp1_holdout.universe_ranks(_FrameReader(cm), "-", day - dt.timedelta(days=10))
    up = u[(u["date"] == prev) & (u["rank"] <= 100)].rename(columns={"symbol": "u_symbol"})
    up = up[~up["u_symbol"].str.contains(ocstudy.ETF_RE)]
    top = up[up["rank"] <= 50]
    link = ocstudy.load_link()
    lk = link[link["entity"].isin(set(top["sid"]))]
    tok = {r["tradingsymbol"]: int(r["instrument_token"]) for r in nse_rows if r.get("segment") == "NSE" and r.get("instrument_type") == "EQ"}
    specials = _specials()
    regular = [d for d in sessions if d not in specials and d.weekday() < 5][-20:]
    rows = []
    for ent, g in lk.groupby("entity"):
        for sym_k in sorted(g["kite_symbol"].unique()):
            if sym_k not in tok:
                continue
            c = _candles(k, tok[sym_k], "5minute", regular[0], regular[-1])
            if c.empty:
                continue
            c = c[c["date"].isin(regular) & (c["m"] >= 0) & (c["m"] < 375)]
            for d, gd in c.groupby("date"):
                gd5 = gd[gd["m"] % 5 == 0]
                rec = {"entity": ent, "symbol": sym_k, "date": d, "nb": len(gd5), "h0": int((gd5["m"] == 0).sum()), "dv": float(gd["volume"].sum())}
                for j in range(12):
                    rec[f"cv{j}"] = float(gd.loc[gd["m"] <= 5 * j, "volume"].sum())
                rows.append(rec)
    cv = pd.DataFrame(rows)
    names = []
    if len(cv):
        cv = cv[(cv["nb"] >= 70) & (cv["h0"] == 1)].sort_values("dv", ascending=False).drop_duplicates(["entity", "date"])
        for ent in sorted(set(top["sid"])):
            ce = cv[cv["entity"] == ent]
            base = [float(np.median(ce[f"cv{j}"])) if len(ce) >= 15 else np.nan for j in range(12)]
            if all(b == b and b > 0 for b in base):
                syms = sorted(ce["symbol"].unique())
                names.append({"entity": ent, "symbols": syms, "tokens": [tok[s] for s in syms], "rank": int(top.loc[top["sid"] == ent, "rank"].iloc[0])})
    log(f"breadth universe {day}: top-50 entities {len(top)}, linked {lk['entity'].nunique()}, with an rvol baseline {len(names)}")
    return {"top50": int(len(top)), "linked": int(lk["entity"].nunique()), "names": names, "regular_sessions": [d.isoformat() for d in regular],
            "cash_file_for_previous_session": bool((cm["date"] == prev).any())}


def contracts(nfo: list[dict], day: dt.date) -> dict:
    """Per index: the nearest future expiring after the day (the shadow book; an overnight hold needs it tomorrow), its lot, and the option
    expiry the study's synthetic leg uses (nearest strictly after the day) with its listed strikes."""
    out = {}
    for sym in sp1.IDX:
        futs = sorted((r for r in nfo if r["name"] == sym and r["instrument_type"] == "FUT" and dt.date.fromisoformat(r["expiry"]) > day), key=lambda r: r["expiry"])
        f = futs[0]
        lot_rows = sorted((r for r in nfo if r["name"] == sym and r["instrument_type"] == "FUT" and dt.date.fromisoformat(r["expiry"]) >= day), key=lambda r: r["expiry"])
        opts = [r for r in nfo if r["name"] == sym and r["instrument_type"] in ("CE", "PE") and dt.date.fromisoformat(r["expiry"]) > day]
        e = min(r["expiry"] for r in opts)
        chain = {(float(r["strike"]), r["instrument_type"]): {"tradingsymbol": r["tradingsymbol"], "token": int(r["instrument_token"]), "lot": int(r["lot_size"])}
                 for r in opts if r["expiry"] == e}
        out[sym] = {"future": {"tradingsymbol": f["tradingsymbol"], "token": int(f["instrument_token"]), "expiry": f["expiry"], "lot": int(f["lot_size"])},
                    "lot": int(lot_rows[0]["lot_size"]), "option_expiry": e,
                    "chain": [{"strike": K, "type": t, **v} for (K, t), v in sorted(chain.items())]}
    return out


# ----------------------------------------------------------------------------------------------------------------------------- the situation
def opening(row: dict, arr: dict, other: dict, point: str, breadth: float) -> dict:
    """scenario.build's opening columns that are known at `point`, from the bars that closed by then (arrays from ocstudy.index_arrays)."""
    r = dict(row)
    o, h, l, c = arr["open"], arr["high"], arr["low"], arr["close"]
    r["open"] = float(o[0])
    r["gap"] = float(o[0] / r["prev_close"] - 1)
    if point == "D0":
        return r
    lb = LAST_BAR[point]
    for kk in (15, 30):
        if lb + 1 >= kk:
            w = float(h[:kk].max() - l[:kk].min())
            r[f"or{kk}_w"] = w
            a = r["atr14_prev"]
            r[f"or{kk}_atr"] = w / a if a == a and a > 0 else np.nan
    for dk in ("D1", "D2", "D3"):
        bar = scenario.DEC[dk]
        if bar > lb:
            break
        r[f"move_{dk}"] = float(c[bar] / o[0] - 1)
        m1 = (arr if row["index"] == "NIFTY" else other)
        m2 = (other if row["index"] == "NIFTY" else arr)
        a1 = m1["close"][bar] / m1["open"][0] - 1
        a2 = m2["close"][bar] / m2["open"][0] - 1
        r[f"agree_{dk}"] = bool((a1 >= 0.0005 and a2 >= 0.0005) or (a1 <= -0.0005 and a2 <= -0.0005))
    r[f"breadth_{point}"] = breadth
    return r


def candidates(sym: str, point: str, row: dict, model: dict, arr: dict, entry_est: float, lot: int, day: dt.date) -> tuple[list[dict], dict]:
    """Every action with a model at this point that is available today, with its prediction and planned cost."""
    cut = model["indices"][sym]["cutoffs"]
    f = levels(row, point, cut)
    x = xrow(f)
    atr = row["atr14_prev"]
    orh, orl = float(np.max(arr["high"][:15])), float(np.min(arr["low"][:15]))
    out = []
    for key, m in model["indices"][sym]["models"].items():
        if m["point"] != point:
            continue
        X, d = m["exit"], m["dir"]
        if not (atr == atr):
            continue
        if X == "ORSTOP":
            dist = (entry_est - orl) if d > 0 else (orh - entry_est)
            if not dist >= 0.1 * atr:
                continue
        g, se = predict(m, x)
        pc = float(sp1.planned_cost_bps(pd.DataFrame({"date": [day], "entry": [entry_est], "lot": [float(lot)], "point": [point], "exit": [X]}))[0])
        out.append({"action": m["action"], "exit": X, "dir": d, "pred_gross": g, "se": se, "pcost": pc, "pred_net": g - pc,
                    "qualifies": bool(g - pc > model["indices"][sym]["c"] * se and g - pc > 0)})
    return out, f


def index_bars(k: kite.Kite, day: dt.date, tokens: dict, last_bar: int, live: bool = False) -> tuple[dict, dict]:
    """Today's minute bars of both indices that closed by the decision (bar <= last_bar); D0 reads only the 09:15 bar's open (live: retried for
    up to 40 seconds, then the day's open from the quote). Also the open of the bar after last_bar when Kite already shows it (the study's entry
    price) and the bar counts."""
    arrs, info = {}, {}
    for name in ("NIFTY 50", "NIFTY BANK"):
        c = _candles(k, tokens[name], "minute", day, day)
        c = c[(c["date"] == day) & (c["m"] >= 0)]
        src = "historical"
        if live and last_bar == 0:
            for _ in range(4):
                if (c["m"] == 0).any():
                    break
                time.sleep(10)
                c = _candles(k, tokens[name], "minute", day, day)
                c = c[(c["date"] == day) & (c["m"] >= 0)]
            if not (c["m"] == 0).any():
                try:
                    q = k.get("/quote/ohlc", params=[("i", f"NSE:{name}")])[f"NSE:{name}"]["ohlc"]["open"]
                    c = pd.DataFrame([{"date": day, "m": 0, "open": float(q), "high": float(q), "low": float(q), "close": float(q), "volume": 0}])
                    src = "quote ohlc open"
                except Exception:
                    pass
        nxt = c.loc[c["m"] == last_bar + 1, "open"]
        info[name] = {"bars": int((c["m"] <= last_bar).sum()), "next_open": float(nxt.iloc[0]) if len(nxt) else None, "source": src}
        cut = c[c["m"] <= last_bar].assign(index_name=name)
        if last_bar == 0:
            cut = cut.assign(high=cut["open"], low=cut["open"], close=cut["open"])  # D0: the 09:15 bar is still forming; only its open is used
        a = ocstudy.index_arrays(cut)
        arrs[name] = {f: a[name][f][0] for f in ("open", "high", "low", "close")} if name in a else None
    return arrs, info


def breadth_now(k: kite.Kite, day: dt.date, names: list[dict], point: str) -> tuple[float, int]:
    """Share of the breadth names whose last closed 5-minute bar (scenario.BREADTH_BAR) is above their own 09:15 open (sp1_holdout.breadth)."""
    jb = scenario.BREADTH_BAR[point]
    vals = []
    for nm in names:
        best = None
        for t in nm["tokens"]:
            c = _candles(k, t, "5minute", day, day)
            c = c[(c["date"] == day) & (c["m"] >= 0) & (c["m"] % 5 == 0) & (c["m"] <= 5 * jb)]
            if len(c) and (best is None or len(c) > len(best)):
                best = c
        if best is None or not (best["m"] == 0).any():
            continue
        cl = best.set_index(best["m"] // 5)["close"].reindex(range(jb + 1)).ffill()
        o0 = float(best.loc[best["m"] == 0, "open"].iloc[0])
        vals.append(bool(cl.iloc[jb] > o0) if cl.iloc[jb] == cl.iloc[jb] else False)
    n = len(vals)
    return (float(np.mean(vals)) if n >= ocstudy.MIN_BREADTH_NAMES else np.nan), n


def _jsonable(row: dict) -> dict:
    out = {}
    for kk, v in row.items():
        if isinstance(v, (dt.date, dt.datetime)):
            out[kk] = v.isoformat()
        elif isinstance(v, (np.floating, float)):
            out[kk] = None if v != v else float(v)
        elif isinstance(v, np.bool_):
            out[kk] = bool(v)
        else:
            out[kk] = v
    return out


# ----------------------------------------------------------------------------------------------------------------------------- prepare
def _plan_path(day: dt.date) -> Path:
    return ROOT / "plans" / f"{day.isoformat()}.json"


def prepare(day: dt.date, log=print, refresh_inputs: bool = True, write: bool = True) -> dict:
    model = load_model()
    k = kite.Kite()
    nse_rows = _instruments(k, "NSE")
    nfo = _instruments(k, "NFO")
    tokens = {r["tradingsymbol"]: int(r["instrument_token"]) for r in nse_rows if r.get("segment") == "INDICES"}
    on = overnight(k, day, tokens, nfo)
    prev = dt.date.fromisoformat(on["prev_date"])
    if refresh_inputs:
        rf = refresh(day, prev, log)
        on = {**overnight(k, day, tokens, nfo), "refresh": rf}
    sessions = [dt.date.fromisoformat(x) for x in on["sessions_tail"]]
    uni = breadth_universe(k, day, prev, sessions, nse_rows, log)
    con = contracts(nfo, day)
    d0 = {}
    for sym in sp1.IDX:
        row = on["rows"][sym]
        d0[sym] = {}
        for bucket, g in (("down", -0.004), ("flat", 0.0), ("up", 0.004)):
            r = {**row, "gap": g}
            arr = {"open": np.full(375, np.nan), "high": np.full(375, np.nan), "low": np.full(375, np.nan), "close": np.full(375, np.nan)}
            cands, f = candidates(sym, "D0", r, model, arr, row["prev_close"] * (1 + g), con[sym]["lot"], day)
            ch = choose(cands, model["indices"][sym]["c"])
            d0[sym][bucket] = {"choice": ch, "levels": f}
    plan = {"kind": "plan", "date": day.isoformat(), "made_at": _ist_now().isoformat(timespec="seconds"), "spec_sha": sp1.spec_sha(), "model_sha": _model_sha(),
            "c": {s: model["indices"][s]["c"] for s in sp1.IDX}, "overnight": {s: _jsonable(r) for s, r in on["rows"].items()}, "prev_date": on["prev_date"],
            "sessions_tail": on["sessions_tail"], "stale": {**on["stale"], "cm_bhavcopy": not uni["cash_file_for_previous_session"]}, "refresh": on.get("refresh"), "d0_by_gap_bucket": d0, "breadth": uni, "contracts": con,
            "index_tokens": {n: tokens[n] for n in NAMES}}
    if write:
        p = _plan_path(day)
        p.parent.mkdir(parents=True, exist_ok=True)
        body = json.dumps(plan, indent=1, default=str)
        p.write_text(body)
        _append(DECISIONS, {"kind": "plan", "date": day.isoformat(), "made_at": plan["made_at"], "plan_sha256": hashlib.sha256(body.encode()).hexdigest(),
                            "spec_sha": plan["spec_sha"], "model_sha": plan["model_sha"], "stale": plan["stale"],
                            "d0": {s: {b: (v["choice"]["action"] if v["choice"] else None) for b, v in d0[s].items()} for s in d0}})
    log(f"plan {day}: prev {on['prev_date']}, stale {on['stale']}, breadth names {len(uni['names'])}, "
        f"D0 by gap {[(s, b, (v['choice'] or {}).get('exit'), (v['choice'] or {}).get('dir')) for s in d0 for b, v in d0[s].items()]}")
    return plan


# ----------------------------------------------------------------------------------------------------------------------------- decide
def _row_from_plan(plan: dict, sym: str) -> dict:
    r = dict(plan["overnight"][sym])
    r["date"] = dt.date.fromisoformat(r["date"])
    return r


def decide_point(k: kite.Kite, plan: dict, model: dict, point: str, done: set, live: bool, now_fn=_ist_now) -> list[dict]:
    """Decisions for every index that has not traded yet today, from the bars closed by the decision time."""
    day = dt.date.fromisoformat(plan["date"])
    tokens = plan["index_tokens"]
    arrs, info = index_bars(k, day, tokens, LAST_BAR[point], live=live)
    br, nb = (np.nan, 0)
    if point != "D0":
        br, nb = breadth_now(k, day, plan["breadth"]["names"], point)
    out = []
    for sym, name in scenario.IDX.items():
        if sym in done:
            continue
        other = arrs["NIFTY BANK" if sym == "NIFTY" else "NIFTY 50"]
        arr = arrs[name]
        base = {"kind": "decision", "date": day.isoformat(), "index": sym, "point": point, "spec_sha": plan["spec_sha"], "model_sha": plan["model_sha"],
                "c": plan["c"][sym], "bars_seen": info[name]["bars"], "bars_source": info[name]["source"], "breadth_names": nb}
        if arr is None or other is None or not (arr["open"][0] == arr["open"][0]) or info[name]["bars"] < LAST_BAR[point] + 1 - 3:
            out.append({**base, "decided_at": now_fn().isoformat(timespec="seconds"), "choice": None, "tradable": False,
                        "note": "index bars missing at the decision time: no decision (the study would have dropped the session)"})
            continue
        row = opening(_row_from_plan(plan, sym), arr, other, point, br)
        entry_bar = sp1.POINT_ENTRY[point]
        nxt_open = info[name]["next_open"] if point != "D0" else None
        entry_est = nxt_open if nxt_open is not None else (float(arr["close"][LAST_BAR[point]]) if point != "D0" else float(arr["open"][0]))
        cands, f = candidates(sym, point, row, model, arr, entry_est, plan["contracts"][sym]["lot"], day)
        ch = choose(cands, plan["c"][sym])
        t = now_fn()
        start = dt.datetime.combine(day, POINT_TIME[point], IST)
        m_now = int((t - dt.datetime.combine(day, dt.time(9, 15), IST)).total_seconds() // 60)
        rec = {**base, "decided_at": t.isoformat(timespec="seconds"), "late_s": round((t - start).total_seconds(), 1),
               "tradable": bool(live and (t - start).total_seconds() <= LATE_S), "state": _jsonable(row), "levels": f,
               "candidates": sorted(cands, key=lambda x: x["action"]), "choice": ch, "entry_bar": entry_bar, "entry_estimate": entry_est,
               "fill_next_bar": max(entry_bar, m_now + 1)}
        if ch:
            con = plan["contracts"][sym]
            typ = "CE" if ch["dir"] > 0 else "PE"
            strikes = sorted({x["strike"] for x in con["chain"] if x["type"] == typ})
            K = min(strikes, key=lambda s: (abs(s - entry_est), s)) if strikes else None
            opt = next((x for x in con["chain"] if x["strike"] == K and x["type"] == typ), None)
            rec["contracts"] = {"future": con["future"], "option": {**opt, "expiry": con["option_expiry"]} if opt else None}
            if live:
                try:
                    keys = [f"NSE:{name}", f"NFO:{con['future']['tradingsymbol']}"] + ([f"NFO:{opt['tradingsymbol']}"] if opt else [])
                    q = k.get("/quote/ltp", params=[("i", x) for x in keys])
                    rec["quotes_at_decision"] = {x: q.get(x, {}).get("last_price") for x in keys}
                except Exception as e:
                    rec["quotes_at_decision"] = {"error": type(e).__name__}
        out.append(rec)
    return out


def live(day: dt.date | None = None, log=print) -> dict:
    """The session. Each point waits for its time; a point the process reached late is decided for sequence only (logged, not traded)."""
    day = day or _ist_now().date()
    plan = json.loads(_plan_path(day).read_text())
    model = load_model()
    if plan["model_sha"] != _model_sha():
        raise SystemExit("the plan was written with another model file")
    k = kite.Kite()
    done: set = set()
    for r in _rows(DECISIONS):
        if r.get("kind") == "decision" and r["date"] == day.isoformat() and r.get("choice"):
            done.add(r["index"])
    have_points = {(r["index"], r["point"]) for r in _rows(DECISIONS) if r.get("kind") == "decision" and r["date"] == day.isoformat()}
    summary = []
    for point in sp1.POINT_ENTRY:
        if all((s, point) in have_points for s in sp1.IDX) or len(done) == len(sp1.IDX):
            continue
        at = dt.datetime.combine(day, POINT_TIME[point], IST) + dt.timedelta(seconds=READ_DELAY_S[point])
        while (w := (at - _ist_now()).total_seconds()) > 0:
            time.sleep(min(w, 30))
        try:
            rows = decide_point(k, plan, model, point, done, live=True)
        except kite.NeedLogin as e:
            _append(DECISIONS, {"kind": "error", "date": day.isoformat(), "point": point, "at": _ist_now().isoformat(timespec="seconds"), "error": str(e)})
            log(f"{point}: {e}")
            break
        for r in rows:
            if (r["index"], point) in have_points:
                continue
            _append(DECISIONS, r)
            if r.get("choice"):
                done.add(r["index"])
            ch = r.get("choice") or {}
            summary.append(f"{r['index']} {point}: {(ch.get('exit'), ch.get('dir')) if ch else 'no trade'} (late {r.get('late_s')}s, tradable {r.get('tradable')})")
            log(summary[-1])
    return {"date": day.isoformat(), "decisions": summary}


# ----------------------------------------------------------------------------------------------------------------------------- score
def _minute_arrays(k: kite.Kite, token: int, days: list[dt.date], label: str) -> dict:
    c = _candles(k, token, "minute", min(days), max(days))
    c = c[c["date"].isin(days)].assign(index_name=label)
    a = ocstudy.index_arrays(c)
    return a.get(label)


def _leg_price(a: dict, day: dt.date, bar: int, kind: str) -> float | None:
    if a is None or day not in a["dates"]:
        return None
    i = a["dates"].index(day)
    v = a[kind][i, bar]
    return float(v) if v == v else None


def score(day: dt.date | None = None, log=print) -> dict:
    """Outcomes of every traded decision up to `day` not yet scored, once its exit is known (NEXTOPEN: after the next session's close)."""
    day = day or _ist_now().date()
    k = kite.Kite()
    scored = {(r["date"], r["index"]) for r in _rows(OUTCOMES) if r.get("kind") == "outcome"}
    todo = [r for r in _rows(DECISIONS) if r.get("kind") == "decision" and r.get("choice") and r.get("tradable") and (r["date"], r["index"]) not in scored
            and dt.date.fromisoformat(r["date"]) <= day]
    res = []
    specials = _specials()
    for r in todo:
        d = dt.date.fromisoformat(r["date"])
        plan = json.loads(_plan_path(d).read_text())
        sym, name = r["index"], scenario.IDX[r["index"]]
        prev = dt.date.fromisoformat(plan["prev_date"])
        tok = plan["index_tokens"]
        span = [x for x in pd.date_range(prev, min(day, d + dt.timedelta(days=6))).date]
        im = []
        for nm in ("NIFTY 50", "NIFTY BANK"):
            c = _candles(k, tok[nm], "minute", prev, max(span))
            im.append(c.assign(index_name=nm))
        im = pd.concat(im, ignore_index=True)
        index = ocstudy.index_arrays(im)
        have = index[name]["dates"]
        if d not in have or not index[name]["ok"][have.index(d)]:
            log(f"{r['date']} {sym}: the day's bars are not complete yet")
            continue
        nxt = [x for x in have if x > d]
        days_all = [prev, d] + nxt[:1]
        st_rows = pd.DataFrame([{"date": prev, "index": sym, "atr14_prev": np.nan},
                                {"date": d, "index": sym, "atr14_prev": plan["overnight"][sym]["atr14_prev"]}])
        lots = pd.DataFrame([{"date": x, "symbol": s, "lot": float(plan["contracts"][s]["lot"])} for x in (prev, d) for s in sp1.IDX])
        chains = pd.DataFrame(columns=["date", "symbol", "expiry", "strike", "opt_type", "fwd", "iv", "volume"])
        o = sp1.outcomes(lambda s: None, src={"days": days_all, "specials": specials, "states": st_rows, "index": index, "lots": lots, "chains": chains},
                         out_file=ROOT / "work" / "score_outcomes.parquet")
        hit = o[(o["date"] == d) & (o["point"] == r["point"]) & (o["action"] == r["choice"]["action"])]
        if hit.empty:
            if r["choice"]["exit"] == "NEXTOPEN" and not nxt:
                log(f"{r['date']} {sym}: NEXTOPEN, held overnight; scored after the next session")
                continue
            res.append(_append(OUTCOMES, {"kind": "outcome", "date": r["date"], "index": sym, "point": r["point"], "action": r["choice"]["action"],
                                          "note": "the study's outcome is not defined for this day (e.g. NEXTOPEN with no usable next session)", "decision_hash": r["hash"]}))
            continue
        h = hit.iloc[0]
        e0, tx, stopped, next_day = int(r["entry_bar"]), int(h["exit_min"]), bool(h["stopped"]), bool(h["next_day"])
        day_out = nxt[0] if next_day else d
        fill2 = int(r["fill_next_bar"])
        legs = {}
        for leg in ("future", "option"):
            ct = (r.get("contracts") or {}).get(leg)
            if not ct:
                continue
            a = _minute_arrays(k, ct["token"], [d] + ([day_out] if next_day else []), ct["tradingsymbol"])
            lot = float(ct["lot"])
            p_in = _leg_price(a, d, e0, "open")
            p_in2 = _leg_price(a, d, fill2, "open")
            p_out = _leg_price(a, day_out, 1, "open") if next_day else (_leg_price(a, d, tx, "close") if stopped else _leg_price(a, d, tx, "open"))
            if p_in is None or p_out is None:
                legs[leg] = {"tradingsymbol": ct["tradingsymbol"], "note": "no Kite candles for the contract at the entry or exit minute"}
                continue
            dirc = r["choice"]["dir"]
            out_leg = {"tradingsymbol": ct["tradingsymbol"], "lot": lot, "entry_study": p_in, "entry_realistic": p_in2, "exit": p_out,
                       "exit_rule": "next session 09:16 open" if next_day else ("close of the index stop minute" if stopped else "open of the time-exit minute")}
            for tag, pi in (("study", p_in), ("realistic", p_in2)):
                if pi is None:
                    continue
                if leg == "future":
                    bv, sv = (pi * lot, p_out * lot) if dirc > 0 else (p_out * lot, pi * lot)
                    ticks = 2 + (2 if r["point"] == "D0" else 0) + (2 if next_day else 0)
                    fees = costs.cost("futures", "buy", bv, d.year, when=d) + costs.cost("futures", "sell", sv, day_out.year, when=day_out)
                    gross = dirc * (p_out - pi) * lot
                    out_leg[f"net_rs_{tag}"] = gross - fees - ticks * sp1.TICK * lot
                    out_leg[f"gross_rs_{tag}"] = gross
                else:
                    h_in = max(sp1.OPT_HALF[sym], 0.0025 * pi)
                    h_out = max(sp1.OPT_HALF[sym], 0.0025 * p_out) * (2.0 if stopped else 1.0)
                    buy, sell = pi + h_in, max(p_out - h_out, 0.0)
                    fees = costs.cost("options", "buy", buy * lot, d.year, when=d) + costs.cost("options", "sell", sell * lot, day_out.year, when=day_out)
                    out_leg[f"net_rs_{tag}"] = (sell - buy) * lot - fees
                    out_leg[f"premium_rs_{tag}"] = pi * lot
                    out_leg[f"ret_{tag}"] = out_leg[f"net_rs_{tag}"] / (pi * lot) if pi > 0 else None
            legs[leg] = out_leg
        row = {"kind": "outcome", "date": r["date"], "index": sym, "point": r["point"], "action": int(r["choice"]["action"]), "exit": r["choice"]["exit"],
               "dir": int(r["choice"]["dir"]), "decision_hash": r["hash"], "scored_at": _ist_now().isoformat(timespec="seconds"),
               "index_proxy": {"entry": float(h["entry"]), "exit_px": float(h["exit_px"]), "exit_min": tx, "stopped": stopped, "next_day": next_day,
                               "gross_bps": float(h["gross_bps"]), "cost_bps": float(h["cost_bps"]), "net_bps": float(h["net_bps"]),
                               "pred_net_bps": float(r["choice"]["pred_net"])}, "legs": legs}
        res.append(_append(OUTCOMES, row))
        log(f"{r['date']} {sym} {r['point']} {row['exit']} {row['dir']:+d}: index proxy {row['index_proxy']['net_bps']:.1f} bp; "
            + ", ".join(f"{k2} Rs {v.get('net_rs_study', float('nan')):,.0f}" for k2, v in legs.items() if "net_rs_study" in v))
    book = write_book()
    return {"scored": len(res), "book": book}


def write_book() -> dict:
    """The paper record, derived from the two ledgers every time (never edited by hand)."""
    dec = [r for r in _rows(DECISIONS) if r.get("kind") == "decision"]
    outc = [r for r in _rows(OUTCOMES) if r.get("kind") == "outcome" and "index_proxy" in r]
    days = sorted({r["date"] for r in dec if r.get("tradable") or r.get("choice") is None})
    out = {"updated": _ist_now().isoformat(timespec="seconds"), "sessions": len(days), "by_index": {}}
    for sym in sp1.IDX:
        o = [r for r in outc if r["index"] == sym]
        net = [r["index_proxy"]["net_bps"] for r in o]
        fut = [r["legs"]["future"]["net_rs_study"] for r in o if "net_rs_study" in r["legs"].get("future", {})]
        opt = [r["legs"]["option"]["net_rs_study"] for r in o if "net_rs_study" in r["legs"].get("option", {})]
        opt_r = [r["legs"]["option"]["net_rs_realistic"] for r in o if "net_rs_realistic" in r["legs"].get("option", {})]
        sessions = len({r["date"] for r in dec if r["index"] == sym})
        out["by_index"][sym] = {"sessions": sessions, "trades": len(o), "index_proxy_sum_bps": round(sum(net), 2),
                                "index_proxy_mean_daily_bps": round(sum(net) / sessions, 2) if sessions else None,
                                "future_1lot_rs": round(sum(fut), 0), "option_1lot_rs_study_fill": round(sum(opt), 0), "option_1lot_rs_realistic_fill": round(sum(opt_r), 0)}
    ROOT.mkdir(parents=True, exist_ok=True)
    (ROOT / "book.json").write_text(json.dumps(out, indent=1))
    return out


# ----------------------------------------------------------------------------------------------------------------------------- replay
class _Clock:
    def __init__(self, day: dt.date, point: str):
        self.t = dt.datetime.combine(day, POINT_TIME[point], IST) + dt.timedelta(seconds=READ_DELAY_S[point] + 15)

    def __call__(self):
        return self.t


def replay(dates: list[dt.date], log=print) -> dict:
    """Past sessions through the live code, compared with the completed holdout run's rows. No ledger row is written."""
    model = load_model()
    D = paths.data_dir()
    h = sealed.holdout_outputs("sp1_holdout", "paper_parity")
    sh = pd.read_parquet(h / "index_states.parquet")
    pt = pd.read_parquet(h / "policy_trades.parquet")
    for x in (sh, pt):
        x["date"] = pd.to_datetime(x["date"]).dt.date
    k = kite.Kite()
    report = {"dates": [d.isoformat() for d in dates], "days": {}}
    cols_float = ["prev_close", "sma50", "sma200", "atr14_prev", "vix_prev", "us_qqq_ret", "fii_long_share", "gap", "or15_atr", "or30_atr",
                  "move_D1", "move_D2", "move_D3", "breadth_D1", "breadth_D2", "breadth_D3"]
    cols_other = ["trend", "event_scheduled", "event_recent", "expiry", "agree_D1", "agree_D2", "agree_D3", "prev_date"]
    for d in dates:
        plan = prepare(d, log, refresh_inputs=False, write=False)
        plan = json.loads(json.dumps(plan, default=str))
        rows = {}
        for P in sp1.POINT_ENTRY:   # every point for both indices (state rows complete); the sequence is applied when reading the choice
            for r in decide_point(k, plan, model, P, set(), live=False, now_fn=_Clock(d, P)):
                rows.setdefault(r["index"], []).append(r)
        day_rep = {}
        for sym in sp1.IDX:
            ref = sh[(sh["date"] == d) & (sh["index"] == sym)]
            mine = {}
            for r in rows.get(sym, []):
                mine.update({kk: v for kk, v in (r.get("state") or {}).items() if v is not None})
            diffs = {}
            if len(ref):
                rr = ref.iloc[0]
                for ccol in cols_float:
                    a, b = rr.get(ccol), mine.get(ccol)
                    if ccol not in mine:
                        continue
                    a = float(a) if a is not None and a == a else None
                    if (a is None) != (b is None) or (a is not None and abs(a - b) > 1e-9 * max(1.0, abs(a))):
                        diffs[ccol] = [a, b]
                for ccol in cols_other:
                    if ccol in mine and str(rr.get(ccol))[:10] != str(mine.get(ccol))[:10]:
                        diffs[ccol] = [str(rr.get(ccol)), str(mine.get(ccol))]
            run_tr = pt[(pt["date"] == d) & (pt["index"] == sym)]
            run_choice = (str(run_tr["point"].iloc[0]), int(run_tr["action"].iloc[0])) if len(run_tr) else None
            ch = next(((r["point"], r["choice"]["action"]) for r in rows.get(sym, []) if r.get("choice")), None)
            day_rep[sym] = {"state_rows_in_run": int(len(ref)), "state_differences": diffs, "decision_live_code": ch, "decision_holdout_run": run_choice,
                            "same_decision": ch == run_choice, "breadth_names": [r.get("breadth_names") for r in rows.get(sym, [])]}
            log(f"replay {d} {sym}: live {ch} vs run {run_choice}; state differences {diffs}")
        report["days"][d.isoformat()] = day_rep
    sd = [v for day in report["days"].values() for v in day.values()]
    report["same_decisions"] = f"{sum(v['same_decision'] for v in sd)}/{len(sd)}"
    report["rows_with_state_differences"] = sum(bool(v["state_differences"]) for v in sd)
    report["at"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    (paths.manifest_dir() / "sp1paper_replay.json").write_text(json.dumps(report, indent=1, default=str))
    return report


# ----------------------------------------------------------------------------------------------------------------------------- run
def run(log=print, rehearsal: bool = False) -> dict:
    """launchd entry, 22:00 Toronto every evening: the next NSE session in IST; prepare (waiting for Madhav's Kite sign-in if needed), then live.
    rehearsal: the same at real times into paper/sp1/rehearsal/ (not the paper record), allowed before PAPER_START."""
    from india import dayplan

    day = dayplan.next_session()
    now = _ist_now()
    if day != now.date():
        return {"skipped": f"no session this IST morning (next session {day})"}
    if rehearsal:
        _use(paths.data_dir() / "paper" / "sp1" / "rehearsal")
    elif day < PAPER_START:
        return {"skipped": f"paper starts {PAPER_START}"}
    if day.weekday() >= 5 or day in _specials():
        return {"skipped": f"{day} is a special session (the study excludes them)"}
    deadline = dt.datetime.combine(day, dt.time(9, 10), IST)
    nudged = False
    while True:
        try:
            kite.Kite().get("/user/profile")   # a real call: Zerodha flushes tokens made before about 07:00-07:30 IST, which the file's expiry cannot show
            break
        except kite.NeedLogin as e:
            if _ist_now() >= deadline:
                _append(DECISIONS, {"kind": "error", "date": day.isoformat(), "at": _ist_now().isoformat(timespec="seconds"), "error": f"no Kite sign-in by 09:10 IST: {e}"})
                return {"skipped": "no Kite sign-in"}
            log(f"waiting for the Kite sign-in: {e}")
            if not nudged:
                kite._ntfy("SP1 paper: Kite sign-in needed before 09:10 IST (http://127.0.0.1:8100/kite/login)")
                nudged = True
            time.sleep(300)
    if not _plan_path(day).exists():
        prepare(day, log)
    plan = json.loads(_plan_path(day).read_text())
    if plan["stale"].get("us_qqq"):
        # Tiingo posts the US close about 03:00-04:00 IST; one more try before the open
        at = dt.datetime.combine(day, dt.time(9, 0), IST)
        while (w := (at - _ist_now()).total_seconds()) > 0:
            time.sleep(min(w, 60))
        log("US close was stale in the plan: preparing again before the open")
        prepare(day, log)
    return live(day, log)


if __name__ == "__main__":
    paths.ensure()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    lg = lambda s: print(f"[{dt.datetime.now(IST):%Y-%m-%d %H:%M:%S} IST] {s}", flush=True)
    arg = sys.argv[2:]
    if cmd == "export":
        print(json.dumps(export(lg), indent=1, default=str))
    elif cmd == "replay":
        ds = [dt.date.fromisoformat(x) for x in arg] or [dt.date(2026, 10, x) for x in (12, 13, 14, 15, 16)]
        r = replay(ds, lg)
        print(json.dumps({k2: r[k2] for k2 in ("same_decisions", "rows_with_state_differences")}, indent=1))
    elif cmd == "prepare":
        from india import dayplan
        prepare(dt.date.fromisoformat(arg[0]) if arg else dayplan.next_session(), lg)
    elif cmd == "live":
        print(json.dumps(live(dt.date.fromisoformat(arg[0]) if arg else None, lg), indent=1))
    elif cmd == "score":
        print(json.dumps(score(dt.date.fromisoformat(arg[0]) if arg else None, lg), indent=1, default=str))
    elif cmd == "verify":
        print(json.dumps(verify(), indent=1))
    elif cmd == "run":
        print(json.dumps(run(lg), indent=1, default=str))
    elif cmd == "rehearse":
        print(json.dumps(run(lg, rehearsal=True), indent=1, default=str))
    elif cmd == "rehearse-score":
        _use(paths.data_dir() / "paper" / "sp1" / "rehearsal")
        print(json.dumps(score(dt.date.fromisoformat(arg[0]) if arg else None, lg), indent=1, default=str))
    else:
        raise SystemExit(__doc__)
