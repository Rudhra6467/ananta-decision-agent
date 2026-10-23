"""SP3 cross-check (spec outputs): an independent bar-by-bar re-derivation of 300+ outcomes with exitlab._exit on the holding bars read
afresh (not the matrix code), the in_window_events cases, and (after the books run) 20 book days recomputed from the trade list.
Run before any result is read:   PYTHONPATH=. python india/checks/sp3_crosscheck.py outcomes
                                   PYTHONPATH=. python india/checks/sp3_crosscheck.py book
Writes manifests/sp3_crosscheck.json."""
import json, sys, datetime as dt
import numpy as np, pandas as pd
sys.path.insert(0, "/Users/vamsie/code/ananta-records")
from india import exitlab, paths, sp3run as R

G = paths.gold() / "studies"


def window_by_hand(b, sig, stops_row, caf, spl_dates):
    """The valid window and its forced end, written out plainly: bars after the signal, cut at the first gap over 10 days (halt: exit at the resume
    open), at the first unconfirmed corporate action (close before it), at a one-day move over 50% near a flag or split record, or at the end of
    the stock's bars (permanent stop at L, else data_end / end)."""
    d = b["dates"]
    i0 = int(np.searchsorted(d, sig, side="right"))
    bars = list(range(i0, min(len(d), i0 + R.W)))
    if not bars:
        return None
    reason, px, fb = "end", b["c"][bars[-1]], len(bars) - 1
    if len(bars) < R.W:
        if stops_row is not None and stops_row["end_reason"] != "followed" and d[-1] == np.datetime64(stops_row["last_session"].date()):
            reason = stops_row["end_reason"]
            px = 0.0 if reason == "end_failed" else b["c"][bars[-1]]
        else:
            reason = "data_end"
    nv = len(bars)
    for k in range(1, len(bars)):
        if (d[bars[k]] - d[bars[k - 1]]).astype(int) > R.HALT_DAYS:
            nv, reason, px, fb = k, "halt", b["o"][bars[k]], k
            break
    for ev in caf:
        if sig < ev <= d[bars[nv - 1]]:
            m = sum(1 for k in range(nv) if d[bars[k]] < ev)
            if m == 0:
                return None
            if m < nv:
                nv, reason, px, fb = m, "ca_artifact", b["c"][bars[m - 1]], m - 1
            break
    prev = b["c"][i0 - 1] if i0 > 0 and d[i0 - 1] == sig else b["c"][i0]
    cl = [prev] + [b["c"][bars[k]] for k in range(nv)]
    for k in range(1, len(cl)):
        if abs(cl[k] / cl[k - 1] - 1) > R.BIG_MOVE:
            lo, hi = d[max(0, i0 + k - 1 - 5)], d[min(len(d) - 1, i0 + k - 1 + 5)]
            if any(lo <= r <= hi for r in spl_dates) or any(lo <= r <= hi for r in caf):
                if k - 1 == 0:
                    return None
                nv, reason, px, fb = k - 1, "ca_artifact_bigmove", b["c"][bars[k - 2]], k - 2
                break
    return i0, nv, reason, px, fb


def check_outcomes(n_sample: int = 400, seed: int = 23) -> dict:
    cand = pd.read_parquet(G / "SP3_candidates.parquet").set_index("cand_id")
    out = pd.read_parquet(G / "SP3_outcomes.parquet")
    out = out[~out["action"].str.startswith("random")]
    rng = np.random.default_rng(seed)
    pick = out.iloc[rng.choice(len(out), n_sample, replace=False)]
    forced = out[out["reason"].isin(["halt", "ca_artifact", "ca_artifact_bigmove", "end_scheme", "relist_no_factor", "data_end"])]
    pick = pd.concat([pick, forced.iloc[rng.choice(len(forced), min(100, len(forced)), replace=False)]])
    bars = R.load_bars_index()
    caf_all = R.ca_events()
    spl_all = R.split_records()
    stops = R.stops_table().drop_duplicates("sid").set_index("sid")
    names = pd.read_parquet(paths.data_dir() / "silver/security_master/names.parquet", columns=["symbol", "entity"]).drop_duplicates()
    ent_syms = names.groupby("entity")["symbol"].apply(set).to_dict()
    kinds = {a[0]: a for a in R.ACTIONS}
    pol_kind = {"hold": "hold", "target": "target", "trail": "atr_trail", "sma": "sma_close", "swing": "swing_low", "scale_half": "scale_half", "hold_low20": "hold"}
    agree, diffs = 0, []
    for r in pick.itertuples():
        c = cand.loc[r.cand_id]
        b = bars[c["sid"]]
        sig = np.datetime64(pd.Timestamp(c["signal_date"]).date())
        caf = caf_all.get(c["sid"], np.array([], dtype="datetime64[D]"))
        spl = np.concatenate([spl_all.get(s, np.array([], dtype="datetime64[D]")) for s in ent_syms.get(c["sid"], {c["sid"]})] or [np.array([], dtype="datetime64[D]")])
        w = window_by_hand(b, sig, stops.loc[c["sid"]] if c["sid"] in stops.index else None, caf, spl)
        if w is None:
            diffs.append((int(r.cand_id), r.action, "no window by hand")); continue
        i0, nv, reason, fpx, fb = w
        nm, kind, n, s = kinds[r.action]
        p = exitlab.Policy(nm, pol_kind[kind], n, ("low20",) if kind == "hold_low20" else ())
        o, h, l, cc = (b[k][i0:i0 + nv] for k in ("o", "h", "l", "c"))
        risk = (s if s is not None else np.inf) * c["atr14"]
        k, px, why, _ = exitlab._exit(p, o, h, l, cc, o[0], risk, aux={"ll20": b["ll20"][i0:i0 + nv]})
        if why == "end":                      # nothing exited inside the valid bars: the forced end applies
            k, px, why = fb, fpx, reason
        hs = c["hs"]
        gross = (px * (1 - hs)) / (o[0] * (1 + hs)) - 1
        ok = (k == r.exit_bar) and (abs(gross - r.gross) < 1e-9) and (why == r.reason or (why in ("sig_low20", "time") and r.reason == "time_or_low20"))
        if ok:
            agree += 1
        else:
            diffs.append((int(r.cand_id), r.action, f"hand bar {k} px {px:.4f} {why} vs run bar {r.exit_bar} px {r.exit_px:.4f} {r.reason}"))
    res = {"sampled": int(len(pick)), "agree": agree, "differ": len(diffs), "examples": diffs[:20]}
    # in_window_events listed from the candidate table (per window, before any outcome is read)
    ok = cand[cand["status"] == "OK"]
    res["in_window_events_by_family"] = {f: {k: int(v) for k, v in g["forced_reason"].value_counts().items()} for f, g in ok.groupby("family")}
    res["late_rows"] = int(ok["late"].sum())
    return res


def check_book(n_days: int = 20, seed: int = 29) -> dict:
    """20 book days of the K=5 policy book recomputed from SP3_policy_trades.parquet and the holding bars: equity = cash + marked positions."""
    tr = pd.read_parquet(G / "SP3_policy_trades.parquet")
    tr = tr[(tr["book"] == "policy") & (tr["K"] == 5)]
    eq = pd.read_parquet(G / "SP3_book_daily.parquet")
    eq = eq[(eq["book"] == "policy") & (eq["K"] == 5)].set_index("date")["equity"]
    bars = R.load_bars_index()
    rng = np.random.default_rng(seed)
    days = sorted(rng.choice(eq.index.to_numpy(), n_days, replace=False))
    book_inr = 60000.0
    agree, rows = 0, []
    for d in days:
        d = pd.Timestamp(d)
        closed = tr[tr["exit_date"] <= d]
        realised = float((closed["pnl_rs"]).sum())
        open_ = tr[(tr["entry_date"] <= d) & (tr["exit_date"] > d)]
        mtm = 0.0
        for t in open_.itertuples():
            b = bars[t.sid]
            i = int(np.searchsorted(b["dates"], np.datetime64(d.date()), side="right")) - 1
            mtm += t.shares * t.raw_entry_fill * (b["c"][i] / t.entry_fill - 1) - t.cost_in   # the entry fee is paid when the position opens
        hand = book_inr + realised + mtm
        ok = abs(hand - float(eq.loc[d])) < 1.0
        agree += int(ok)
        rows.append({"date": str(d.date()), "by_hand": round(hand, 2), "book": round(float(eq.loc[d]), 2), "open_positions": int(len(open_)), "agree": ok})
    return {"days": n_days, "agree": agree, "rows": rows}


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "outcomes"
    p = paths.manifest_dir() / "sp3_crosscheck.json"
    prev = json.loads(p.read_text()) if p.exists() else {}
    res = check_outcomes() if what == "outcomes" else check_book()
    prev[what] = {"at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), **res}
    p.write_text(json.dumps(prev, indent=1, default=str))
    print(json.dumps({k: v for k, v in res.items() if k not in ("rows",)}, indent=1, default=str))
