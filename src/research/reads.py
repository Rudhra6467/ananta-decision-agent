"""Madhav's reads: the three buy setups from his own SOL trades, as a point-in-time reader (repair-shop review #5).

    M1 Capitulation at the lows   (his C1, Jun 5 2026)
    M2 Higher-low retest          (his C2 Jun 25, C4 Jun 26)
    M3 Quiet base after a run     (his C3, Aug 10; entry a = upper half of the base, b = first close above it)

The definitions are frozen in docs/repair_shop/REVIEW_5.md (written before any run). One reader serves both uses:
  * history: `python -m src.research.reads --db .../lab5_5m.sqlite --out ~/ananta_runs/reads`  (DISCOVERY / CONFIRM test)
  * cases:   `python -m src.research.reads cases --db ... --until 2026-09-12`   (does it see what he saw on C1-C4?)
  * live:    `read_coin(D, btcD)` from the Jarvis service on the Explorer's daily bars
Every read returns its four conditions with the value found and the value needed, so the app can show "3 of 4" and why.
Reads are evidence for Madhav and the decision chain, never orders: the Explorer's paper trading is unchanged.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

DAY = 86400
DISC_END = 1704067200            # 2024-01-01 UTC
CONF_END = 1785542400            # 2026-08-01 UTC: the Aug-Sep 2026 holdout starts here
COINS = ["BTC", "ETH", "SOL", "ADA", "DOGE", "AVAX", "BCH", "LINK", "LTC", "XRP"]
VARIANTS = ["M1a", "M1b", "M1c", "M2a", "M2b", "M3a", "M3b"]
PRIMARY = {"M1": "M1a", "M2": "M2a", "M3": "M3a"}
NAMES = {"M1": "Capitulation at the lows", "M2": "Higher-low retest", "M3": "Quiet base after a run"}
CASES = {"M1": "like your Jun 5 SOL buy (C1)", "M2": "like your Jun 25-26 SOL buys (C2, C4)", "M3": "like your Aug 10 SOL buy (C3)"}
EPISODE_GAP = 20 * DAY           # same coin, same read, within 20 days = one episode
EVENT_GAP = 10 * DAY             # episodes within 10 days of an event's first signal = one market event


# ---------------------------------------------------------------------------
# indicators on daily bars (t, o, h, l, c, v)
# ---------------------------------------------------------------------------
def rsi(closes: list[float], n: int = 14) -> list[float | None]:
    out: list[float | None] = [None] * len(closes)
    if len(closes) <= n:
        return out
    g = [max(closes[i] - closes[i - 1], 0) for i in range(1, len(closes))]
    d = [max(closes[i - 1] - closes[i], 0) for i in range(1, len(closes))]
    ag, al = sum(g[:n]) / n, sum(d[:n]) / n
    out[n] = 100 - 100 / (1 + ag / al) if al > 0 else 100.0
    for i in range(n + 1, len(closes)):
        ag = (ag * (n - 1) + g[i - 1]) / n
        al = (al * (n - 1) + d[i - 1]) / n
        out[i] = 100 - 100 / (1 + ag / al) if al > 0 else 100.0
    return out


def sma(x: list[float], n: int) -> list[float | None]:
    out: list[float | None] = [None] * len(x)
    s = 0.0
    for i, v in enumerate(x):
        s += v
        if i >= n:
            s -= x[i - n]
        if i >= n - 1:
            out[i] = s / n
    return out


def ema(x: list[float], n: int) -> list[float | None]:
    out: list[float | None] = [None] * len(x)
    if len(x) < n:
        return out
    k = 2 / (n + 1)
    e = sum(x[:n]) / n
    out[n - 1] = e
    for i in range(n, len(x)):
        e = x[i] * k + e * (1 - k)
        out[i] = e
    return out


class Series:
    """One coin's daily bars with the indicators the reads need, computed once."""

    def __init__(self, D: list[tuple]):
        self.D = D
        self.t = [b[0] for b in D]
        self.o = [b[1] for b in D]
        self.h = [b[2] for b in D]
        self.l = [b[3] for b in D]
        self.c = [b[4] for b in D]
        self.v = [b[5] for b in D]
        self.rsi = rsi(self.c)
        self.sma200 = sma(self.c, 200)
        self.ema50 = ema(self.c, 50)
        tr = [self.h[0] - self.l[0]] + [max(self.h[i], self.c[i - 1]) - min(self.l[i], self.c[i - 1]) for i in range(1, len(D))]
        self.atr = sma(tr, 14)
        self.ix = {t: i for i, t in enumerate(self.t)}

    def at(self, t: int) -> int | None:
        return self.ix.get(t)


def _c(name: str, ok: bool, found: str, need: str) -> dict:
    return {"name": name, "ok": bool(ok), "found": found, "need": need}


def _p(x: float) -> str:
    return f"{x:+.1f}%"


# ---------------------------------------------------------------------------
# the three reads at day i (only bars 0..i are used)
# ---------------------------------------------------------------------------
def m1(S: Series, i: int, B: Series | None, variant: str = "M1a") -> dict | None:
    if i < 365 or S.sma200[i - 99] is None or S.atr[i] is None or S.rsi[i] is None:
        return None
    lo52, hi52 = min(S.l[i - 365:i]), max(S.h[i - 365:i])
    under = 0.50 if variant == "M1c" else 0.60
    near_low = S.l[i] <= 1.03 * lo52
    deep = S.c[i] <= (1 - under) * hi52
    below = sum(1 for k in range(i - 99, i + 1) if S.c[k] < S.sma200[k])
    bi = B.at(S.t[i]) if B is not None else None
    brsi = B.rsi[bi] if bi is not None else None
    panic_coin = S.rsi[i] <= 25
    panic_btc = True if variant == "M1b" else (brsi is not None and brsi <= 30)
    med = statistics.median(S.v[i - 92:i - 2]) if i >= 95 else None
    vmax = max(S.v[i - 2:i + 1])
    vol_ok = bool(med) and vmax >= 2.5 * med
    conds = [
        _c("At the 52-week low, far under the high", near_low and deep,
           f"low {_p(100 * (S.l[i] / lo52 - 1))} vs 52-week low; close {_p(100 * (S.c[i] / hi52 - 1))} vs 52-week high",
           f"low at most +3% above the 52-week low and close at least {int(under * 100)}% under the high"),
        _c("Long fall", below >= 90, f"under the 200-day average on {below} of the last 100 days", "at least 90 of 100"),
        _c("Panic", panic_coin and panic_btc,
           f"RSI {S.rsi[i]:.0f}" + ("" if variant == "M1b" else f", BTC RSI {brsi:.0f}" if brsi is not None else ", BTC RSI unknown"),
           "RSI 25 or lower" + ("" if variant == "M1b" else " and BTC RSI 30 or lower")),
        _c("Capitulation volume", vol_ok, f"biggest of the last 3 days = {vmax / med:.1f}x the 90-day median" if med else "no volume history",
           "2.5x or more"),
    ]
    stop = min(S.l[i - 2:i + 1]) - S.atr[i]
    return {"read": "M1", "variant": variant, "conditions": conds, "stop": stop}


def m2(S: Series, i: int, B: Series | None, variant: str = "M2a") -> dict | None:
    if i < 365 or S.atr[i] is None or S.rsi[i] is None:
        return None
    win = S.l[i - 365:i]
    L0 = min(win)
    j0 = i - 365 + win.index(L0)
    age = i - j0
    rally = max(S.h[j0 + 1:i]) if age > 1 else S.h[j0]
    r0 = S.rsi[j0]
    conds = [
        _c("A first low 8-60 days ago", 8 <= age <= 60, f"52-week low {age} days ago", "8 to 60 days ago"),
        _c("A rally after it", rally >= 1.10 * L0, f"rallied {_p(100 * (rally / L0 - 1))} after that low", "at least +10%"),
        _c("Higher-low retest", L0 < S.l[i] <= 1.12 * L0, f"today's low {_p(100 * (S.l[i] / L0 - 1))} above the first low",
           "above it, at most +12%"),
        _c("Momentum improving", r0 is not None and S.rsi[i] >= r0 + 10,
           f"RSI {S.rsi[i]:.0f} now vs {r0:.0f} at the first low" if r0 is not None else "no RSI at the first low", "10 points higher or more"),
    ]
    if variant == "M2b":
        bi, bj = (B.at(S.t[i]), B.at(S.t[j0])) if B is not None else (None, None)
        ok = bi is not None and bj is not None and min(B.l[bi - 29:bi + 1]) < B.l[bj]
        conds.append(_c("BTC made a lower low, this coin did not", ok, "yes" if ok else "no", "BTC's 30-day low below its low on that day"))
    return {"read": "M2", "variant": variant, "conditions": conds, "stop": L0 - S.atr[i], "first_low": L0,
            "first_low_t": S.t[j0]}


def _base(S: Series, end: int) -> int:
    """Longest run of daily closes ending at `end` that stays inside a 10% band (20..120 days), else 0."""
    n = 0
    lo = hi = S.c[end]
    for k in range(end, max(end - 120, -1), -1):
        lo, hi = min(lo, S.c[k]), max(hi, S.c[k])
        if hi / lo - 1 > 0.10:
            break
        n = end - k + 1
    return n if n >= 20 else 0


def m3(S: Series, i: int, B: Series | None, variant: str = "M3a") -> dict | None:
    if i < 260 or S.atr[i] is None:
        return None
    end = i if variant == "M3a" else i - 1
    n = _base(S, end)
    s = end - n + 1 if n else end - 19
    if s < 110:
        return None
    floor, top = min(S.l[s:end + 1]), max(S.h[s:end + 1])
    pre = range(s - 20, s)
    before = list(range(s - 90, s))
    p = min(before, key=lambda k: S.l[k])
    q = max(range(p, s), key=lambda k: S.h[k])
    run = S.h[q] / S.l[p] - 1
    vb, vp = statistics.mean(S.v[s:end + 1]), statistics.mean(S.v[k] for k in pre)
    rng = lambda ks: statistics.mean((S.h[k] - S.l[k]) / S.c[k] for k in ks)          # noqa: E731
    rb, rp = rng(range(s, end + 1)), rng(pre)
    bi = B.at(S.t[i]) if B is not None else None
    mkt = bi is not None and B.ema50[bi] is not None and B.c[bi] > B.ema50[bi]
    if variant == "M3a":
        pos = (S.c[i] - floor) / (top - floor) if top > floor else 0
        entry = _c("In the upper half of the base", bool(n) and pos >= 0.5, f"close at {100 * pos:.0f}% of the base's range", "50% or higher")
    else:
        entry = _c("First close above the base", bool(n) and S.c[i] > top, f"close {_p(100 * (S.c[i] / top - 1))} vs the base top",
                   "above the top")
    conds = [
        _c("Stuck in a base", bool(n), f"{n} days of closes inside a 10% band" if n else "no 20-day base", "20 days or more"),
        _c("A run before it", run >= 0.25, f"{_p(100 * run)} in the 90 days before the base", "+25% or more"),
        _c("Quiet", bool(n) and vb <= 0.8 * vp and rb <= 0.8 * rp, f"volume {vb / vp:.2f}x, daily range {rb / rp:.2f}x the 20 days before",
           "both 0.8x or less"),
        _c("Market allowed (BTC above its 50-day average)", mkt, "yes" if mkt else "no", "yes (V02)"),
        entry,
    ]
    return {"read": "M3", "variant": variant, "conditions": conds, "stop": floor - 0.5 * S.atr[i], "base_floor": floor, "base_top": top,
            "base_days": n}


READERS = {"M1": m1, "M2": m2, "M3": m3}


def fired(r: dict | None) -> bool:
    return bool(r) and all(c["ok"] for c in r["conditions"])


# ---------------------------------------------------------------------------
# live: one coin, primary reads (plus M3b), for the app and the decision chain
# ---------------------------------------------------------------------------
def read_coin(D: list[tuple], btcD: list[tuple], status: dict | None = None) -> dict:
    """The latest closed day's reads for one coin. `status` = {variant: history status} from the review #5 results."""
    S, B = Series(D), Series(btcD)
    i = len(D) - 1
    out = []
    for variant in ("M1a", "M2a", "M3a", "M3b"):
        r = READERS[variant[:2]](S, i, B, variant)
        if r is None:
            out.append({"read": variant[:2], "variant": variant, "name": NAMES[variant[:2]], "like": CASES[variant[:2]],
                        "state": "NO_DATA", "met": 0, "of": 0, "conditions": []})
            continue
        met = sum(1 for c in r["conditions"] if c["ok"])
        of = len(r["conditions"])
        state = "FIRED" if met == of else "CLOSE" if met >= of - 1 else "NO"
        out.append({**{k: v for k, v in r.items() if k not in ("first_low_t",)}, "name": NAMES[variant[:2]], "like": CASES[variant[:2]],
                    "state": state, "met": met, "of": of, "history": (status or {}).get(variant, "UNTESTED"),
                    "stop_pct": round(100 * (r["stop"] / S.c[i] - 1), 1)})
    return {"day": datetime.fromtimestamp(D[-1][0], timezone.utc).strftime("%Y-%m-%d"), "close": D[-1][4], "reads": out}


# ---------------------------------------------------------------------------
# history test (review #5)
# ---------------------------------------------------------------------------
def cost(coin: str) -> float:
    from src.intelligence.explorer_engine import HALF_SPREAD, NDAX_FEE

    return NDAX_FEE + HALF_SPREAD.get(coin, 0.004)


def signals(S: Series, B: Series, variant: str) -> list[int]:
    """Signal days (first fire of each episode)."""
    if variant == "M2b" and B is S:
        return []
    out, last = [], None
    for i in range(len(S.t) - 1):
        if fired(READERS[variant[:2]](S, i, B, variant)):
            if last is None or S.t[i] - S.t[last] > EPISODE_GAP:
                out.append(i)
            last = i
    return out


def outcome(S: Series, i: int, stop: float, coin: str) -> dict | None:
    e = i + 1
    k = cost(coin)
    res = {"t": S.t[i]}
    for H in (7, 30, 90):
        res[f"r{H}"] = S.o[e + H] / S.o[e] * (1 - k) ** 2 - 1 if e + H < len(S.t) else None
    if res["r30"] is None:
        return None
    res["mae30"] = min(S.l[e:e + 30]) / S.o[e] - 1
    exit_px, hit = S.o[e + 30], False
    for d in range(e, e + 30):
        if S.o[d] <= stop:
            exit_px, hit = S.o[d], True
            break
        if S.l[d] <= stop:
            exit_px, hit = stop, True
            break
    res["managed30"] = exit_px / S.o[e] * (1 - k) ** 2 - 1
    res["stopped"] = hit
    return res


def drift(S: Series, coin: str, p0: int, p1: int, H: int) -> float | None:
    k = cost(coin)
    xs = [S.o[i + 1 + H] / S.o[i + 1] * (1 - k) ** 2 - 1 for i in range(len(S.t) - 1 - H) if p0 <= S.t[i] < p1]
    return statistics.mean(xs) if xs else None


def events(rows: list[dict]) -> list[list[dict]]:
    out: list[list[dict]] = []
    for r in sorted(rows, key=lambda x: x["t"]):
        if out and r["t"] - out[-1][0]["t"] <= EVENT_GAP:
            out[-1].append(r)
        else:
            out.append([r])
    return out


def summarize(rows: list[dict]) -> dict:
    if not rows:
        return {"episodes": 0, "events": 0}
    ev = events(rows)
    ex = [statistics.mean(r["x30"] for r in e) for e in ev]
    n = len(ex)
    m = statistics.mean(ex)
    sd = statistics.stdev(ex) if n > 1 else 0.0
    pc = lambda xs: round(100 * statistics.mean(xs), 2) if xs else None                  # noqa: E731
    return {"episodes": len(rows), "events": n,
            "mean_excess30_pct": round(100 * m, 2), "t_events": round(m / (sd / n ** 0.5), 2) if sd > 0 else None,
            "mean_net7_pct": pc([r["r7"] for r in rows if r["r7"] is not None]),
            "mean_net30_pct": pc([r["r30"] for r in rows]), "median_net30_pct": round(100 * statistics.median(r["r30"] for r in rows), 2),
            "win_rate30": round(sum(1 for r in rows if r["r30"] > 0) / len(rows), 2),
            "mean_net90_pct": pc([r["r90"] for r in rows if r["r90"] is not None]),
            "mean_excess90_pct": pc([r["x90"] for r in rows if r.get("x90") is not None]),
            "mean_deepest_drop30_pct": pc([r["mae30"] for r in rows]),
            "managed30_pct": pc([r["managed30"] for r in rows]), "stopped_rate": round(sum(r["stopped"] for r in rows) / len(rows), 2),
            "by_coin": {c: sum(1 for r in rows if r["coin"] == c) for c in sorted({r["coin"] for r in rows})},
            "event_dates": [datetime.fromtimestamp(e[0]["t"], timezone.utc).strftime("%Y-%m-%d") + f" ({len(e)})" for e in ev]}


def verdict(d: dict, c: dict) -> str:
    if d.get("events", 0) < 8 or c.get("events", 0) < 3:
        return "INSUFFICIENT"
    if not (d["mean_excess30_pct"] > 0 and (d["t_events"] or 0) >= 1.5):
        return "NOT_SUPPORTED"
    return "SUPPORTED" if c["mean_excess30_pct"] > 0 else "NOT_CONFIRMED"


def history(D: dict[str, list[tuple]]) -> dict:
    SS = {c: Series(D[c]) for c in D}
    B = SS["BTC"]
    splits = {"DISCOVERY": (0, DISC_END), "CONFIRM": (DISC_END, CONF_END)}
    drifts = {(c, s, H): drift(SS[c], c, *splits[s], H) for c in SS for s in splits for H in (30, 90)}
    report = {}
    for v in VARIANTS:
        rows = {s: [] for s in splits}
        for c, S in SS.items():
            for i in signals(S, B, v):
                if S.t[i] >= CONF_END:
                    continue
                r = READERS[v[:2]](S, i, B, v)
                o = outcome(S, i, r["stop"], c)
                if o is None:
                    continue
                s = "DISCOVERY" if S.t[i] < DISC_END else "CONFIRM"
                o["coin"] = c
                o["x30"] = o["r30"] - drifts[(c, s, 30)]
                o["x90"] = o["r90"] - drifts[(c, s, 90)] if o["r90"] is not None and drifts[(c, s, 90)] is not None else None
                rows[s].append(o)
        d, cf = summarize(rows["DISCOVERY"]), summarize(rows["CONFIRM"])
        report[v] = {"DISCOVERY": d, "CONFIRM": cf, "status": verdict(d, cf)}
    return report


# ---------------------------------------------------------------------------
# data + CLI
# ---------------------------------------------------------------------------
def daily(db: str, coin: str, until: int = CONF_END) -> list[tuple]:
    """UTC daily bars from 5m (days with at least 200 of 288 bars), never past `until`."""
    import sqlite3

    con = sqlite3.connect(f"file:{os.path.expanduser(db)}?mode=ro", uri=True)
    try:
        cur = con.execute("SELECT event_unix, open, high, low, close, volume FROM bars WHERE instrument=? AND event_unix < ? "
                          "ORDER BY event_unix", (f"{coin}-USD-SPOT", until))
        out, day, acc = [], None, []
        for r in cur:
            d = r[0] // DAY
            if d != day:
                if len(acc) >= 200:
                    out.append((day * DAY, acc[0][1], max(x[2] for x in acc), min(x[3] for x in acc), acc[-1][4], sum(x[5] for x in acc)))
                day, acc = d, []
            acc.append(r)
        if len(acc) >= 200:
            out.append((day * DAY, acc[0][1], max(x[2] for x in acc), min(x[3] for x in acc), acc[-1][4], sum(x[5] for x in acc)))
        return out
    finally:
        con.close()


def cached_daily(db: str, coin: str, cache: Path, until: int) -> list[tuple]:
    p = cache / f"daily_{coin}_{until}.json"
    if p.exists():
        return [tuple(x) for x in json.loads(p.read_text())]
    D = daily(db, coin, until)
    cache.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(D))
    return D


def cases(D: dict[str, list[tuple]], days: dict[str, str]) -> dict:
    """Does the reader see what Madhav saw? For each of his buys: every read on that UTC day and the day before."""
    S, B = Series(D["SOL"]), Series(D["BTC"])
    out = {}
    for name, day in days.items():
        t = int(datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())
        rows = []
        for dt in (-1, 0, 1):
            i = S.at(t + dt * DAY)
            if i is None:
                continue
            for v in VARIANTS:
                r = READERS[v[:2]](S, i, B, v)
                if r:
                    rows.append({"day": datetime.fromtimestamp(S.t[i], timezone.utc).strftime("%Y-%m-%d"), "variant": v,
                                 "met": f"{sum(c['ok'] for c in r['conditions'])}/{len(r['conditions'])}", "fired": fired(r),
                                 "missing": [f"{c['name']}: {c['found']}" for c in r["conditions"] if not c["ok"]]})
        out[name] = rows
    return out


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", nargs="?", default="history", choices=["history", "cases"])
    ap.add_argument("--db", required=True)
    ap.add_argument("--out", default="~/ananta_runs/reads")
    ap.add_argument("--until", default=None, help="cases only: last day of data to load (YYYY-MM-DD)")
    a = ap.parse_args(argv)
    out = Path(os.path.expanduser(a.out))
    out.mkdir(parents=True, exist_ok=True)
    if a.mode == "history":
        D = {c: cached_daily(a.db, c, out, CONF_END) for c in COINS}
        print({c: len(v) for c, v in D.items()}, file=sys.stderr)
        rep = history(D)
        rep["_meta"] = {"run": datetime.now(timezone.utc).isoformat(timespec="seconds"), "pre_registration": "docs/repair_shop/REVIEW_5.md",
                        "days": {c: len(v) for c, v in D.items()}}
        (out / "review5_results.json").write_text(json.dumps(rep, indent=1))
        for v in VARIANTS:
            d, c = rep[v]["DISCOVERY"], rep[v]["CONFIRM"]
            print(f"{v:4} {rep[v]['status']:14} DISC ev {d.get('events', 0):3} ep {d.get('episodes', 0):3} x30 {d.get('mean_excess30_pct')} t {d.get('t_events')}"
                  f" | CONF ev {c.get('events', 0):3} ep {c.get('episodes', 0):3} x30 {c.get('mean_excess30_pct')}")
    else:
        until = int(datetime.strptime(a.until, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()) + DAY
        D = {c: cached_daily(a.db, c, out, until) for c in ("SOL", "BTC")}
        res = cases(D, {"C1": "2026-06-05", "C2": "2026-06-25", "C4": "2026-06-26", "C3": "2026-08-10"})
        (out / "review5_cases.json").write_text(json.dumps(res, indent=1))
        for k, rows in res.items():
            for r in rows:
                print(k, r["day"], r["variant"], r["met"], "FIRED" if r["fired"] else "", "; ".join(r["missing"])[:150])


if __name__ == "__main__":
    main()
