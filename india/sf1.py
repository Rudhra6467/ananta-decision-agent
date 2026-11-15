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

import contextlib
import datetime as dt
import fcntl
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from india import costs, managed, paths

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


def code_sha() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:16]


@contextlib.contextmanager
def _locked():
    """One writer at a time (the evening job and a hand run must not both append a row for the same session)."""
    with (_dir() / ".lock").open("w") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


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
    if feats.empty or "symbol" not in feats:
        return pd.DataFrame(columns=["symbol", "date", "close", "sma50", "ret_20"])
    f = feats[feats["symbol"].isin(n500) & (feats["date"] == asof)].copy()
    f = f[f["close"] >= c["min_price_inr"]]
    if "turnover_med60" in f and f["turnover_med60"].notna().any():   # the managed book's own guard: no turnover column means no floor
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


def _next(d: str) -> str:
    return managed.next_session(dt.date.fromisoformat(d)).isoformat()


def runs(scores: list[dict], nxt=None) -> list[dict]:
    """Spells: consecutive scored evenings in the same regime. Two rows are consecutive when the later row was recorded on the close of
    the earlier row's entry session (its asof equals the earlier entry_session): both are frozen in the rows, so no calendar is read and a
    spell reads the same every night. A missed evening or a voided row ends a spell; a voided row is not an evening. `nxt` is unused (kept
    for callers)."""
    out = []
    for s in sorted((s for s in scores if not s.get("void")), key=lambda s: s["entry_session"]):
        if out and out[-1]["regime"] == s["regime"] and s.get("asof") == out[-1]["last"]:
            out[-1]["rows"].append(s)
            out[-1]["last"] = s["entry_session"]
        else:
            out.append({"regime": s["regime"], "rows": [s], "last": s["entry_session"]})
    return out


def summarise(scores: list[dict], state: dict, nxt=None) -> dict:
    """The verdict per the frozen bar. Only evenings inside falling spells of SPELL_LEN+ count toward D, its t and the minimum. After the
    first INCONCLUSIVE nothing is read until EXTRA more counted evenings, then the bar is read once more and the study closes whatever it
    shows. `state` holds reread_at and final; a final verdict is never reopened. Events to persist are listed in state['events']."""
    rs = runs(scores, nxt)
    long = [r for r in rs if r["regime"] == "FALLING" and len(r["rows"]) >= SPELL_LEN]
    d = np.array([s["d_bps"] for r in long for s in r["rows"] if s.get("d_bps") is not None], float)
    spell_means = [float(np.mean(x)) for x in ([s["d_bps"] for s in r["rows"] if s.get("d_bps") is not None] for r in long) if x]
    D = float(d.mean()) if len(d) else None
    t = nw_t(d) if len(d) else None
    share = (sum(1 for m in spell_means if m < 0) / len(spell_means)) if spell_means else None
    enough = len(d) >= MIN_FALLING and len(long) >= MIN_SPELLS
    state.setdefault("events", [])
    verdict = state.get("final")
    if not verdict:
        passes = D is not None and D < 0 and t is not None and t <= -2.0 and share is not None and share >= 2 / 3
        if state.get("reread_at") is not None and len(d) < state["reread_at"]:
            verdict = "INCONCLUSIVE"                                   # waiting for the one re-read: nothing is read in between
        elif not enough:
            verdict = "INSUFFICIENT"
        elif D >= 0:
            verdict = "REJECTED_FORWARD"
        elif passes:
            verdict = "SUPPORTED_FORWARD"
        elif state.get("reread_at") is None:
            state["reread_at"] = int(len(d) + EXTRA)
            state["events"].append({"event": "reread_at", "value": state["reread_at"], "falling_evenings": int(len(d))})
            verdict = "INCONCLUSIVE"
        else:
            verdict = "CLOSED_INCONCLUSIVE"
        if verdict in ("REJECTED_FORWARD", "SUPPORTED_FORWARD", "CLOSED_INCONCLUSIVE"):
            state["final"] = verdict
            state["events"].append({"event": "final", "value": verdict, "falling_evenings": int(len(d)), "D_bps": round(D, 2), "nw_t": t, "share": share})
    live = [s for s in scores if not s.get("void")]
    rise = np.array([s["weak"]["excess_bps"] for s in live if s["regime"] == "RISING" and s["weak"].get("excess_bps") is not None], float)
    mb = {}
    for reg in ("FALLING", "RISING", "MIXED"):
        xs = [s["managed_buys"]["excess_bps"] for s in live if s["regime"] == reg and (s.get("managed_buys") or {}).get("excess_bps") is not None]
        mb[reg] = {"evenings": len(xs), "mean_excess_bps": round(float(np.mean(xs)), 2) if xs else None}
    sizes = {b: round(float(np.mean([s[b]["n"] for s in live])), 1) if live else None for b in ("strong", "weak", "control")}
    rt = nw_t(rise) if len(rise) >= 3 else None
    out = {"study": "SF1", "verdict": verdict, "scored_evenings": len(scores), "voided": sum(1 for s in scores if s.get("void")),
           "by_regime": {r: sum(1 for s in live if s["regime"] == r) for r in ("FALLING", "RISING", "MIXED", "MISSING")},
           "primary": {"counted_falling_evenings": int(len(d)), "falling_spells_10plus": [{"from": r["rows"][0]["entry_session"], "evenings": len(r["rows"]),
                       "mean_d_bps": round(m, 2)} for r, m in zip(long, spell_means)], "D_bps": round(D, 2) if D is not None else None,
                       "nw_t": round(t, 2) if t is not None else None, "share_of_spells_negative": round(share, 3) if share is not None else None,
                       "needs": f"{MIN_FALLING} evenings inside falling spells of {SPELL_LEN}+, over {MIN_SPELLS} such spells", "reread_at": state.get("reread_at")},
           "secondary_rising_weak": {"evenings": int(len(rise)), "mean_excess_bps": round(float(rise.mean()), 2) if len(rise) else None,
                                     "nw_t": round(rt, 2) if rt is not None else None},
           "descriptive_managed_buys": mb, "mean_bucket_sizes": sizes, "round_trip_cost_bps": round_trip_bps()}
    out["words"] = words(out)
    return out


def round_trip_bps(slot: float = 10_000.0) -> float | None:
    try:
        return round(1e4 * (costs.cost("delivery", "buy", slot) + costs.cost("delivery", "sell", slot)) / slot, 1)
    except Exception:  # noqa: BLE001
        return None


def words(o: dict) -> str:
    p = o["primary"]
    w = (f"SF1 asks whether a stock's strength flips when the market is falling. {o['scored_evenings']} evenings scored so far "
         f"({o['by_regime']['FALLING']} falling, {o['by_regime']['RISING']} rising, {o['by_regime']['MIXED']} mixed). ")
    if o["verdict"] == "INSUFFICIENT" or p["D_bps"] is None:
        w += (f"Not enough yet: {p['counted_falling_evenings']} of {MIN_FALLING} evenings inside falling spells of {SPELL_LEN}+, and "
              f"{len(p['falling_spells_10plus'])} of {MIN_SPELLS} such spells. Nothing is read into it before then.")
    elif o["verdict"] == "INCONCLUSIVE":
        w += f"Inconclusive at the first read; it is read once more at {p['reread_at']} counted falling evenings and then closed."
    else:
        w += (f"Verdict {o['verdict']}: strong minus weak in falling markets {p['D_bps']:+.0f} basis points over 20 sessions "
              f"(t {p['nw_t']}), negative in {100 * (p['share_of_spells_negative'] or 0):.0f}% of the falling spells.")
    return w + " It is a shadow: no decision uses it."


# ------------------------------------------------------------------------------------------------------------------------ record, score, show

def chain_ok(rows: list[dict]) -> tuple[bool, str]:
    prev = ""
    for i, r in enumerate(rows):
        if r.get("prev_sha", "") != prev or _sha(r) != r.get("sha"):
            return False, f"row {i} ({r.get('entry_session')}) breaks the chain"
        prev = r["sha"]
    return True, "chain intact"


def _chained_append(p: Path, row: dict, rows: list[dict]) -> dict:
    row = dict(row, prev_sha=rows[-1]["sha"] if rows else "")
    row["sha"] = _sha(row)
    _append(p, row)
    rows.append(row)
    return row


def _nifty(asof: str) -> pd.Series:
    from india import sealed
    since = (dt.date.fromisoformat(asof) - dt.timedelta(days=420)).isoformat()
    ix = sealed.read_index("paper_context", since, ["NIFTY 50"])
    ix["date"] = pd.to_datetime(ix["date"])
    return ix.set_index("date")["close"].astype(float).sort_index()


def _managed_planned(entry: str) -> list[str] | None:
    plan = next((p for p in reversed(managed._plans()) if p.get("for_session") == entry and not p.get("error")), None)
    return None if plan is None else sorted({b["symbol"] for b in plan.get("buys") or []})


def _managed_fills() -> dict[str, list[str]]:
    """The managed book's ACTUAL replacement buys by fill session (paper/managed/ledger.jsonl), for SF1-D."""
    out: dict[str, set] = {}
    for r in managed._jsonl(managed._dir() / "ledger.jsonl"):
        if r.get("side") == "BUY" and r.get("filled") and r.get("symbol"):
            out.setdefault(str(r.get("day") or r.get("for_session")), set()).add(r["symbol"])
    return {k: sorted(v) for k, v in out.items()}


def record(day: str | None = None, bars: pd.DataFrame | None = None, nifty: pd.Series | None = None, n500: set | None = None) -> dict:
    sha = spec_sha()
    if not managed.holidays():
        raise RuntimeError("SF1: the exchange holiday calendar could not be read, so the next session is not known; nothing is written")
    with _locked():
        df = managed.bars() if bars is None else bars
        asof = day or str(df["date"].max().date())
        entry = _next(asof)
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
        row = {"study": "SF1", "spec_sha": sha, "code_sha": code_sha(), "asof": asof, "entry_session": entry, "written_at": _now(), **reg,
               "n_universe": int(len(u)), "universe_status": "ok" if len(u) >= 30 else f"thin: {len(u)} names, buckets left empty",
               "cuts": bk["cuts"], "strong": bk["strong"], "weak": bk["weak"], "control": control(u["symbol"].tolist(), asof),
               "managed_planned": _managed_planned(entry)}
        managed.refuse_late(entry)                     # again: the features take a while, and a row is never written after the open
        row = _chained_append(p, row, rows)
    return {"status": "written", "entry_session": entry, "regime": row["regime"], "strong": len(row["strong"]), "weak": len(row["weak"]),
            "control": len(row["control"]), "words": f"SF1 row for {entry} written: market {row['regime'].lower()}, {len(row['strong'])} strong, "
            f"{len(row['weak'])} weak, {len(row['control'])} control stocks out of {row['n_universe']}"}


def _state(vs: list[dict]) -> dict:
    st: dict = {}
    for e in vs:
        if e["event"] == "reread_at":
            st["reread_at"] = e["value"]
        elif e["event"] == "final":
            st["final"] = e["value"]
    return st


def score(bars: pd.DataFrame | None = None) -> dict:
    with _locked():
        rows = _jsonl(_dir() / "rows.jsonl")
        sp, vp = _dir() / "scores.jsonl", _dir() / "verdicts.jsonl"
        scored, vs = _jsonl(sp), _jsonl(vp)
        for name, xs in (("rows", rows), ("scores", scored), ("verdicts", vs)):
            ok, why = chain_ok(xs)
            if not ok:
                raise RuntimeError(f"SF1 {name}: {why}; nothing is scored on a broken chain")
        if rows and rows[0]["spec_sha"] != spec_sha():
            raise RuntimeError("SF1's registration changed after its first row; nothing is scored against an edited spec")
        by_sha = {r["sha"]: r for r in rows}
        bad = [s["entry_session"] for s in scored if by_sha.get(s.get("row_sha"), {}).get("entry_session") != s["entry_session"]]
        if bad:
            raise RuntimeError(f"SF1 scores {bad[:3]} do not match a recorded row")
        old = json.loads((_dir() / "score.json").read_text()) if (_dir() / "score.json").exists() else {}
        if old.get("verdict") in ("REJECTED_FORWARD", "SUPPORTED_FORWARD", "CLOSED_INCONCLUSIVE") and not vs:
            raise RuntimeError("SF1: score.json holds a final verdict but verdicts.jsonl is gone; a closed study is not reopened")
        done = {s["entry_session"] for s in scored}
        todo = [r for r in rows if r["entry_session"] not in done and r["entry_session"] >= START]
        new = 0
        if todo:
            df = managed.bars() if bars is None else bars
            df = df.drop_duplicates(["symbol", "date"], keep="last")
            fills = _managed_fills()
            syms = sorted({s for r in todo for b in ("strong", "weak", "control") for s in (r.get(b) or [])} | {s for v in fills.values() for s in v})
            since = pd.Timestamp(todo[0]["entry_session"])
            d = df[df["symbol"].isin(syms) & (df["date"] >= since)]
            opens = d.pivot(index="date", columns="symbol", values="open")
            closes = d.pivot(index="date", columns="symbol", values="close")
            sessions = pd.DatetimeIndex(sorted(df.loc[df["date"] >= since, "date"].unique()))
            for r in todo:
                after = sessions[sessions >= pd.Timestamp(r["entry_session"])]
                if len(after) >= HORIZON and after[0] != pd.Timestamp(r["entry_session"]):
                    sc = {"entry_session": r["entry_session"], "asof": r["asof"], "regime": r["regime"], "row_sha": r["sha"], "scored_at": _now(),
                          "void": "the entry session did not trade", "d_bps": None, **{b: {"n": 0, "excess_bps": None} for b in ("strong", "weak", "control", "managed_buys")}}
                else:
                    sc = score_row(dict(r, managed_buys=fills.get(r["entry_session"], [])), opens, closes, sessions)
                if sc is None:
                    break                               # rows mature in order: a later one cannot be ready before this one
                _chained_append(sp, sc, scored)
                new += 1
        state = _state(vs)
        out = summarise(scored, state)
        for e in state.pop("events", []):
            _chained_append(vp, dict(e, at=_now()), vs)
        out.update({"rows": len(rows), "new_scores": new, "updated_at": _now(), "spec_sha": rows[0]["spec_sha"] if rows else None})
        (_dir() / "score.json").write_text(json.dumps(out, indent=1, default=str))
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
