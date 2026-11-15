"""SF1: does a stock's strength flip when the market is falling? A forward SHADOW (registration india/registrations/sf1_v1.json, frozen
15 Nov 2026 on Madhav's "go with your best recommendations and continue to complete").

  python -m india.sf1 record    evening, after the managed book's run: one sealed row for the next session (regime, strong / weak / control lists)
  python -m india.sf1 score     nightly or evening: every row whose 20 sessions have closed is scored once; the summary and the verdict state
  python -m india.sf1 show

It changes no decision: no decision module imports it (tests/test_india_sf1.py checks), it reads only what the managed book already reads
(india/managed.bars for the adjusted daily bars; india/sealed.read_index purpose paper_context for the Nifty 50), and it writes only under
paper/shadow/sf1/. India only. A row is written once per entry session, carries the sha of the row before it and of the frozen spec, and is
refused on or after 09:15 IST of its entry session, so it is a forecast, never hindsight. A scored row is never rewritten.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from india import managed, paths

SPEC = Path(__file__).parent / "registrations" / "sf1_v1.json"
START = "2026-11-16"            # the first entry session (spec definitions.start); earlier rows are refused
HORIZON = 20                    # sessions, counting the entry session
N_CONTROL = 50
NW_LAGS = 19
MIN_FALLING, MIN_SPELLS, SPELL_LEN, EXTRA = 60, 3, 10, 30


def _dir() -> Path:
    d = paths.data_dir() / "paper" / "shadow" / "sf1"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def _jsonl(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()] if p.exists() else []


def _append(p: Path, row: dict) -> None:
    with p.open("a") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")


def _sha(row: dict) -> str:
    return hashlib.sha256(json.dumps({k: v for k, v in row.items() if k != "sha"}, sort_keys=True).encode()).hexdigest()


def spec_sha() -> str:
    spec = json.loads(SPEC.read_text())
    if not spec.get("frozen_at"):
        raise RuntimeError("SF1 is not frozen: nothing is recorded before the registration is")
    return hashlib.sha256(SPEC.read_bytes()).hexdigest()[:16]


# ------------------------------------------------------------------------------------------------------------------------ pure parts

def regime_of(closes: pd.Series, asof: str) -> dict:
    """Nifty 50 closes (date index) -> the regime on `asof`: FALLING below both averages, RISING above both, MIXED otherwise;
    MISSING when the index has no row on `asof` or too little history (never filled)."""
    s = closes.dropna().sort_index()
    s = s[s.index <= pd.Timestamp(asof)]
    if s.empty or s.index[-1] != pd.Timestamp(asof):
        return {"regime": "MISSING", "why": f"no Nifty 50 row on {asof}" + (f" (last {s.index[-1].date()})" if len(s) else "")}
    if len(s) < 200:
        return {"regime": "MISSING", "why": f"only {len(s)} Nifty 50 closes, 200 needed"}
    c, a50, a200 = float(s.iloc[-1]), float(s.tail(50).mean()), float(s.tail(200).mean())
    reg = "FALLING" if c < a50 and c < a200 else "RISING" if c > a50 and c > a200 else "MIXED"
    return {"regime": reg, "nifty_close": round(c, 2), "nifty_sma50": round(a50, 2), "nifty_sma200": round(a200, 2)}


def universe(feats: pd.DataFrame, n500: set, asof: str, c: dict) -> pd.DataFrame:
    """Nifty 500 names with a bar on `asof` (features() already needs 210 bars), the managed book's price and turnover floors."""
    f = feats[feats["symbol"].isin(n500) & (feats["date"] == asof)].copy()
    f = f[f["close"] >= c["min_price_inr"]]
    if "turnover_med60" in f:
        f = f[f["turnover_med60"].fillna(0) >= c["min_turnover_cr"] * 1e7]
    return f.sort_values("symbol").reset_index(drop=True)


def buckets(u: pd.DataFrame) -> dict:
    """strong: 0% < close/50-day - 1 <= 20% and 20-session return in the top third; weak: under the 50-day and in the bottom third.
    Thirds of that evening's universe."""
    if len(u) < 30:
        return {"strong": [], "weak": [], "cuts": None}
    lo, hi = float(u["ret_20"].quantile(1 / 3)), float(u["ret_20"].quantile(2 / 3))
    d50 = u["close"] / u["sma50"] - 1
    strong = u[(d50 > 0) & (d50 <= 0.20) & (u["ret_20"] >= hi)]["symbol"].tolist()
    weak = u[(d50 < 0) & (u["ret_20"] <= lo)]["symbol"].tolist()
    return {"strong": sorted(strong), "weak": sorted(weak), "cuts": {"ret_20_low": round(lo, 6), "ret_20_high": round(hi, 6)}}


def control(symbols: list[str], asof: str, n: int = N_CONTROL) -> list[str]:
    key = lambda s: hashlib.sha256(f"{s}|{asof}|SF1".encode()).hexdigest()
    return sorted(sorted(symbols, key=key)[:n])


def window(sessions: pd.DatetimeIndex, entry: str) -> tuple[pd.Timestamp, pd.Timestamp] | None:
    """The entry session and the 20th session counting it, on the market's own session list; None until it has closed."""
    s = sessions[sessions >= pd.Timestamp(entry)]
    if len(s) < HORIZON or s[0] != pd.Timestamp(entry):
        return None
    return s[0], s[HORIZON - 1]


def stock_ret(opens: pd.Series, closes: pd.Series, t0: pd.Timestamp, t1: pd.Timestamp) -> float | None:
    """Open of t0 to the close of t1 (or the last close before t1 inside the window); None without a bar on t0."""
    if t0 not in opens.index or not np.isfinite(opens.get(t0, np.nan)) or opens[t0] <= 0:
        return None
    cl = closes[(closes.index >= t0) & (closes.index <= t1)].dropna()
    return float(cl.iloc[-1] / opens[t0] - 1) if len(cl) else None


def score_row(row: dict, opens: pd.DataFrame, closes: pd.DataFrame, sessions: pd.DatetimeIndex) -> dict | None:
    w = window(sessions, row["entry_session"])
    if w is None:
        return None
    t0, t1 = w
    out = {"entry_session": row["entry_session"], "asof": row["asof"], "regime": row["regime"], "row_sha": row["sha"],
           "exit_session": str(t1.date()), "scored_at": _now()}
    for b in ("strong", "weak", "control", "managed_buys"):
        rets, missing = [], 0
        for s in row.get(b) or []:
            r = stock_ret(opens[s], closes[s], t0, t1) if s in opens and s in closes else None
            if r is None:
                missing += 1
            else:
                rets.append(r)
        out[b] = {"n": len(rets), "left_out": missing, "mean_bps": round(1e4 * float(np.mean(rets)), 2) if rets else None}
    ctl = out["control"]["mean_bps"]
    for b in ("strong", "weak", "managed_buys"):
        m = out[b]["mean_bps"]
        out[b]["excess_bps"] = round(m - ctl, 2) if m is not None and ctl is not None else None
    s, k = out["strong"]["excess_bps"], out["weak"]["excess_bps"]
    out["d_bps"] = round(s - k, 2) if s is not None and k is not None else None
    return out


def nw_t(x: np.ndarray, lags: int = NW_LAGS) -> float | None:
    """Newey-West t of the mean (Bartlett weights); None under 3 values."""
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 3:
        return None
    e = x - x.mean()
    v = float(e @ e) / n
    for L in range(1, min(lags, n - 1) + 1):
        v += 2 * (1 - L / (lags + 1)) * float(e[L:] @ e[:-L]) / n
    return float(x.mean() / math.sqrt(v / n)) if v > 0 else None


def spells(regimes: list[str]) -> list[tuple[str, int, int]]:
    """Runs of the same regime over consecutive recording evenings: (regime, first index, length)."""
    out = []
    for i, r in enumerate(regimes):
        if out and out[-1][0] == r:
            out[-1] = (r, out[-1][1], out[-1][2] + 1)
        else:
            out.append((r, i, 1))
    return out


def summarise(scores: list[dict], state: dict) -> dict:
    """The verdict state per the frozen bar. `state` keeps the one re-read point and a final verdict, which is never reopened."""
    scores = sorted(scores, key=lambda s: s["entry_session"])
    fall = [s for s in scores if s["regime"] == "FALLING" and s.get("d_bps") is not None]
    d = np.array([s["d_bps"] for s in fall], float)
    long = []
    for reg, first, n in spells([s["regime"] for s in scores]):
        if reg == "FALLING" and n >= SPELL_LEN:
            ds = [s["d_bps"] for s in scores[first:first + n] if s.get("d_bps") is not None]
            if ds:
                long.append({"from": scores[first]["entry_session"], "evenings": n, "mean_d_bps": round(float(np.mean(ds)), 2)})
    D = float(d.mean()) if len(d) else None
    t = nw_t(d) if len(d) else None
    share = (sum(1 for sp in long if sp["mean_d_bps"] < 0) / len(long)) if long else None
    enough = len(d) >= MIN_FALLING and len(long) >= MIN_SPELLS
    verdict = state.get("final")
    if not verdict:
        if not enough:
            verdict = "INSUFFICIENT"
        elif D >= 0:
            verdict = "REJECTED_FORWARD"
        elif t is not None and t <= -2.0 and share is not None and share >= 2 / 3:
            verdict = "SUPPORTED_FORWARD"
        elif state.get("reread_at") is None:
            state["reread_at"] = len(d) + EXTRA
            verdict = "INCONCLUSIVE"
        elif len(d) < state["reread_at"]:
            verdict = "INCONCLUSIVE"
        else:
            verdict = "CLOSED_INCONCLUSIVE"
        if verdict in ("REJECTED_FORWARD", "SUPPORTED_FORWARD", "CLOSED_INCONCLUSIVE"):
            state["final"], state["final_at"] = verdict, _now()
    rise = np.array([s["weak"]["excess_bps"] for s in scores if s["regime"] == "RISING" and s["weak"].get("excess_bps") is not None], float)
    mb = {}
    for reg in ("FALLING", "RISING", "MIXED"):
        xs = [s["managed_buys"]["excess_bps"] for s in scores if s["regime"] == reg and s["managed_buys"].get("excess_bps") is not None]
        mb[reg] = {"evenings": len(xs), "mean_excess_bps": round(float(np.mean(xs)), 2) if xs else None}
    by = {r: sum(1 for s in scores if s["regime"] == r) for r in ("FALLING", "RISING", "MIXED", "MISSING")}
    out = {"study": "SF1", "verdict": verdict, "scored_evenings": len(scores), "by_regime": by,
           "primary": {"falling_evenings": int(len(d)), "falling_spells_10plus": long, "D_bps": round(D, 2) if D is not None else None,
                       "nw_t": round(t, 2) if t is not None else None, "share_of_spells_negative": round(share, 3) if share is not None else None,
                       "needs": f"{MIN_FALLING} falling evenings over {MIN_SPELLS} spells of {SPELL_LEN}+", "reread_at": state.get("reread_at")},
           "secondary_rising_weak": {"evenings": int(len(rise)), "mean_excess_bps": round(float(rise.mean()), 2) if len(rise) else None,
                                     "nw_t": round(nw_t(rise), 2) if len(rise) >= 3 and nw_t(rise) is not None else None},
           "descriptive_managed_buys": mb}
    out["words"] = words(out)
    return out


def words(o: dict) -> str:
    p = o["primary"]
    w = (f"SF1 asks whether a stock's strength flips when the market is falling. {o['scored_evenings']} evenings scored so far "
         f"({o['by_regime']['FALLING']} falling, {o['by_regime']['RISING']} rising, {o['by_regime']['MIXED']} mixed). ")
    if o["verdict"] == "INSUFFICIENT":
        w += (f"Not enough yet: {p['falling_evenings']} of {MIN_FALLING} falling evenings and {len(p['falling_spells_10plus'])} of {MIN_SPELLS} "
              f"falling spells of {SPELL_LEN}+ evenings. Nothing is read into it before then.")
    else:
        w += (f"Verdict {o['verdict']}: strong minus weak in falling markets {p['D_bps']:+.0f} basis points over 20 sessions "
              f"(t {p['nw_t']}), negative in {100 * (p['share_of_spells_negative'] or 0):.0f}% of the falling spells.")
    w += " It is a shadow: no decision uses it."
    return w


# ------------------------------------------------------------------------------------------------------------------------ record, score, show

def chain_ok(rows: list[dict]) -> tuple[bool, str]:
    prev = ""
    for i, r in enumerate(rows):
        if r.get("prev_sha", "") != prev or _sha(r) != r.get("sha"):
            return False, f"row {i} ({r.get('entry_session')}) breaks the chain"
        prev = r["sha"]
    return True, "chain intact"


def _nifty(asof: str) -> pd.Series:
    from india import sealed
    since = (dt.date.fromisoformat(asof) - dt.timedelta(days=420)).isoformat()
    ix = sealed.read_index("paper_context", since, ["NIFTY 50"])
    ix["date"] = pd.to_datetime(ix["date"])
    return ix.set_index("date")["close"].astype(float).sort_index()


def _managed_buys(entry: str) -> list[str] | None:
    plan = next((p for p in reversed(managed._plans()) if p.get("for_session") == entry and not p.get("error")), None)
    return None if plan is None else sorted({b["symbol"] for b in plan.get("buys") or []})


def record(day: str | None = None, bars: pd.DataFrame | None = None, nifty: pd.Series | None = None, n500: set | None = None) -> dict:
    sha = spec_sha()
    df = managed.bars() if bars is None else bars
    asof = day or str(df["date"].max().date())
    entry = managed.next_session(dt.date.fromisoformat(asof)).isoformat()
    if entry < START:
        return {"status": "refused", "words": f"SF1 records entry sessions from {START}; {entry} is earlier"}
    p = _dir() / "rows.jsonl"
    rows = _jsonl(p)
    ok, why = chain_ok(rows)
    if not ok:
        raise RuntimeError(f"SF1 rows: {why}; nothing is written on a broken chain")
    if rows and rows[0]["spec_sha"] != sha:
        raise RuntimeError(f"SF1's registration changed after its first row (sha {rows[0]['spec_sha']} -> {sha}); a frozen spec is never edited")
    kept = next((r for r in rows if r["entry_session"] == entry), None)
    if kept:
        return {"status": "kept", "entry_session": entry, "regime": kept["regime"], "words": f"SF1's row for {entry} was already written; it is kept"}
    managed.refuse_late(entry)
    n500 = set(managed.nifty500()) if n500 is None else n500
    feats = managed.features(df[df["symbol"].isin(n500)], asof)
    u = universe(feats, n500, asof, managed.cfg())
    reg = regime_of(_nifty(asof) if nifty is None else nifty, asof)
    bk = buckets(u)
    row = {"study": "SF1", "spec_sha": sha, "asof": asof, "entry_session": entry, "written_at": _now(), **reg,
           "n_universe": int(len(u)), "cuts": bk["cuts"], "strong": bk["strong"], "weak": bk["weak"], "control": control(u["symbol"].tolist(), asof),
           "managed_buys": _managed_buys(entry), "prev_sha": rows[-1]["sha"] if rows else ""}
    row["sha"] = _sha(row)
    _append(p, row)
    return {"status": "written", "entry_session": entry, "regime": row["regime"], "strong": len(row["strong"]), "weak": len(row["weak"]),
            "control": len(row["control"]), "words": f"SF1 row for {entry} written: market {row['regime'].lower()}, {len(row['strong'])} strong, "
            f"{len(row['weak'])} weak, {len(row['control'])} control stocks out of {row['n_universe']}"}


def score(bars: pd.DataFrame | None = None) -> dict:
    rows = _jsonl(_dir() / "rows.jsonl")
    ok, why = chain_ok(rows)
    if not ok:
        raise RuntimeError(f"SF1 rows: {why}; nothing is scored on a broken chain")
    sp = _dir() / "scores.jsonl"
    scored = _jsonl(sp)
    done = {s["entry_session"] for s in scored}
    todo = [r for r in rows if r["entry_session"] not in done and r["entry_session"] >= START]
    new = 0
    if todo:
        df = managed.bars() if bars is None else bars
        syms = sorted({s for r in todo for b in ("strong", "weak", "control", "managed_buys") for s in (r.get(b) or [])})
        d = df[df["symbol"].isin(syms) & (df["date"] >= pd.Timestamp(todo[0]["entry_session"]))]
        opens = d.pivot(index="date", columns="symbol", values="open")
        closes = d.pivot(index="date", columns="symbol", values="close")
        sessions = pd.DatetimeIndex(sorted(df.loc[df["date"] >= pd.Timestamp(todo[0]["entry_session"]), "date"].unique()))
        for r in todo:
            after = sessions[sessions >= pd.Timestamp(r["entry_session"])]
            if len(after) >= HORIZON and after[0] != pd.Timestamp(r["entry_session"]):
                sc = {"entry_session": r["entry_session"], "asof": r["asof"], "regime": r["regime"], "row_sha": r["sha"], "scored_at": _now(),
                      "void": "the entry session did not trade", "d_bps": None, **{b: {"n": 0, "excess_bps": None} for b in ("strong", "weak", "control", "managed_buys")}}
            else:
                sc = score_row(r, opens, closes, sessions)
            if sc is None:
                break                                   # rows mature in order: a later one cannot be ready before this one
            _append(sp, sc)
            scored.append(sc)
            new += 1
    stp = _dir() / "state.json"
    state = json.loads(stp.read_text()) if stp.exists() else {}
    out = summarise(scored, state)
    out.update({"rows": len(rows), "new_scores": new, "updated_at": _now(), "spec_sha": rows[0]["spec_sha"] if rows else None})
    stp.write_text(json.dumps(state, indent=1))
    (_dir() / "score.json").write_text(json.dumps(out, indent=1))
    return out


def show() -> dict:
    p = _dir() / "score.json"
    if p.exists():
        return json.loads(p.read_text())
    rows = _jsonl(_dir() / "rows.jsonl")
    return {"study": "SF1", "rows": len(rows), "words": f"SF1 has {len(rows)} recorded evenings and none scored yet (each needs 20 sessions)."}


def main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else "show"
    fn = {"record": record, "score": score, "show": show}.get(cmd)
    if fn is None:
        print(__doc__)
        return 2
    out = fn()
    print(json.dumps({k: v for k, v in out.items() if k not in ("strong", "weak", "control")}, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
