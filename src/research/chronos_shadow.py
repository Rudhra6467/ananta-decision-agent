"""Chronos shadow for crypto: a blind, append-only forward record of a Hugging Face forecaster (Madhav, 25 Oct 2026: "We can add both, if they
are helping Ananta in either crypto and Indian infrastructure").

What it is
- Once a day, after the daily candle closes, Amazon's free time-series model on Hugging Face (amazon/chronos-bolt-small, zero-shot, no fitting)
  forecasts BTC and ETH from their previous 300 daily closes: the next day and the next 5 days, as nine quantiles and the chance of up.
- Each forecast is appended to a hash-chained log OUTSIDE the repo: ~/ananta_runs/shadow_chronos/chronos_crypto.jsonl (prev_hash and
  hash = sha256(prev_hash + canonical JSON of the row without its hash), as the shadow lane and India's forecast ledger do). verify()
  recomputes the chain.

What it never does (the crypto lock's Rule B: a new study waits for the end of the evidence window; Madhav's word made this blind record the
exception, like OD-SHADOW-LANE)
- No outcome is computed or kept: append() refuses any row carrying an outcome field. results() raises Sealed before 2026-12-15 00:00 UTC;
  the scoring study (PW-HF-CHRONOS in docs/LOCK.md section 9) is registered and run after the window.
- Nothing in Ananta reads this log: no book, brain, gate, Ask, screen or brief (tests/test_chronos_shadow.py checks the repo).
- It opens the lake's daily file read-only (and, since 27 Oct, adds the finished days the weekly lake does not have yet from Binance spot's
  public daily candles, the lake's own source) and writes only under its own folder. It never touches a trade.
- One reader besides the run checker (Madhav's yes of 27 Oct 00:05): src/research/polymarket_shadow.py turns each forecast into a probability
  for Polymarket's crypto price questions; it is blind too (no score before 2026-12-15).

  python -m src.research.chronos_shadow run       one day's forecasts (runs in ~/ananta_venvs/hf; launchd com.ananta.chronosshadow 04:20 Toronto)
  python -m src.research.chronos_shadow verify    the chain
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

UTC = timezone.utc
DAY = 86400
SEALED_UNTIL = int(datetime(2026, 12, 15, tzinfo=UTC).timestamp())
MODEL_ID = "amazon/chronos-bolt-small"
REVISION = "772f3d25d38aec6d914c8949dab4462e2d46f5d8"
CONTEXT = 300
PRED_LEN = 5
HORIZONS = (1, 5)
QL = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
COINS = ("BTC", "ETH")
LOG, RUN_LOG = "chronos_crypto.jsonl", "run.log"
FORBIDDEN = frozenset({"outcome", "outcome_return", "actual", "actual_close", "hit", "hits", "ret", "return", "brier", "pnl", "net", "win",
                       "error", "abs_error", "covered", "inside_band", "score"})


class Sealed(RuntimeError):
    """A result was asked for before the end of the evidence window."""


def shadow_dir() -> Path:
    if os.getenv("ANANTA_CHRONOS_SHADOW_DIR"):
        return Path(os.environ["ANANTA_CHRONOS_SHADOW_DIR"]).expanduser()
    return Path(os.getenv("ANANTA_RUNS_DIR", str(Path.home() / "ananta_runs"))).expanduser() / "shadow_chronos"


def daily_db() -> Path:
    return Path(os.getenv("ANANTA_LAKE_DAILY", str(Path.home() / "ananta_lake" / "agent" / "daily.sqlite"))).expanduser()


def _canon(row: dict) -> str:
    return json.dumps({k: v for k, v in row.items() if k != "hash"}, sort_keys=True, separators=(",", ":"), default=str)


def _rows() -> list[dict]:
    p = shadow_dir() / LOG
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()] if p.exists() else []


def _keys(row: dict) -> set:
    out = set(row)
    for v in row.values():
        if isinstance(v, dict):
            out |= _keys(v)
    return out


def append(row: dict) -> dict:
    """Appends one row to the chain; refuses any outcome field anywhere in the row."""
    bad = _keys(row) & FORBIDDEN
    if bad:
        raise ValueError(f"the Chronos shadow keeps no outcome before the window ends; refused fields {sorted(bad)}")
    d = shadow_dir()
    d.mkdir(parents=True, exist_ok=True)
    rows = _rows()
    row = dict(row)
    row["prev_hash"] = rows[-1]["hash"] if rows else "genesis"
    row["hash"] = hashlib.sha256((row["prev_hash"] + _canon(row)).encode()).hexdigest()
    with (d / LOG).open("a") as fh:
        fh.write(json.dumps(row, default=str) + "\n")
    return row


def verify() -> dict:
    prev = "genesis"
    for i, r in enumerate(_rows(), 1):
        if r.get("prev_hash") != prev or hashlib.sha256((prev + _canon(r)).encode()).hexdigest() != r.get("hash"):
            return {"ok": False, "broken_at_line": i}
        prev = r["hash"]
    return {"ok": True, "rows": len(_rows())}


def results():
    """The only door to the rows for scoring: shut until 2026-12-15 00:00 UTC."""
    if time.time() < SEALED_UNTIL:
        raise Sealed("the Chronos shadow is sealed until 2026-12-15 00:00 UTC (CHECKPOINT-60); scoring is PW-HF-CHRONOS")
    return _rows()


BINANCE_DAILY = "https://data-api.binance.vision/api/v3/klines"   # Binance's public market-data mirror (no key); the lake's own source


def _api_daily(coin: str, after_t: int, now: float) -> list[tuple[int, float]]:
    """Complete UTC daily candles after after_t from Binance spot (COINUSDT), the same market the lake is built from (27 Oct: the lake's daily
    file is rebuilt only on Sundays, so on every other day the shadow skipped: 'the latest daily bar is ..., expected ...'; 0 rows written)."""
    import urllib.request

    url = f"{BINANCE_DAILY}?symbol={coin}USDT&interval=1d&startTime={(after_t + DAY) * 1000}&limit=10"
    req = urllib.request.Request(url, headers={"User-Agent": "Ananta chronos shadow (read-only)"})
    rows = json.loads(urllib.request.urlopen(req, timeout=30).read())
    return [(int(r[0]) // 1000, float(r[4])) for r in rows if int(r[6]) // 1000 < now]          # r[6] = close time: only finished days


def closes(coin: str, upto: str | None = None, now: float | None = None) -> tuple[list[int], np.ndarray]:
    """Daily bar times and closes from the lake's daily file, opened read-only. When the lake ends before `upto` (a UTC day), the missing
    finished days are added from Binance spot daily candles (_api_daily); a fetch failure leaves the lake's rows, and run() then skips as before."""
    con = sqlite3.connect(f"file:{daily_db()}?mode=ro", uri=True)
    try:
        rows = [(int(r[0]), float(r[1])) for r in con.execute("SELECT t, c FROM bars WHERE coin = ? ORDER BY t", (coin,)).fetchall()]
    finally:
        con.close()
    if rows and upto and datetime.fromtimestamp(rows[-1][0], UTC).strftime("%Y-%m-%d") < upto:
        try:
            rows += [x for x in _api_daily(coin, rows[-1][0], now or time.time()) if x[0] > rows[-1][0]]
        except Exception:  # noqa: BLE001  no network: the lake's rows only, and the day is skipped as stale
            pass
    return [r[0] for r in rows], np.array([r[1] for r in rows])


_PIPE = None


def predict(contexts: list[np.ndarray]) -> np.ndarray:
    """Quantiles, shape (n, PRED_LEN, 9). Torch and chronos load only here (venv ~/ananta_venvs/hf)."""
    global _PIPE
    import torch
    from chronos import BaseChronosPipeline

    if _PIPE is None:
        _PIPE = BaseChronosPipeline.from_pretrained(MODEL_ID, revision=REVISION, device_map="cpu", torch_dtype=torch.float32)
    q, _ = _PIPE.predict_quantiles([torch.tensor(np.asarray(c, dtype="float32")) for c in contexts], prediction_length=PRED_LEN, quantile_levels=QL)
    return q.detach().cpu().numpy()


def p_up(q: np.ndarray, last: float) -> float:
    q = np.maximum.accumulate(np.asarray(q, dtype=float))
    lv = np.asarray(QL)
    if last <= q[0]:
        return float(1 - min(0.99, max(0.01, lv[0] - (q[0] - last) * (lv[1] - lv[0]) / max(q[1] - q[0], 1e-12))))
    if last >= q[-1]:
        return float(1 - min(0.99, max(0.01, lv[-1] + (last - q[-1]) * (lv[-1] - lv[-2]) / max(q[-1] - q[-2], 1e-12))))
    return float(1 - np.interp(last, q, lv))


def run(now: float | None = None) -> dict:
    """One day: for each coin whose latest daily bar is yesterday's (UTC) and not yet forecast, append the forecast. A run line goes to run.log."""
    now = now or time.time()
    done = {(r.get("coin"), r.get("origin_day")) for r in _rows() if r.get("kind") == "forecast"}
    want = datetime.fromtimestamp(now - DAY, UTC).strftime("%Y-%m-%d")
    written, skipped = [], []
    todo = []
    for coin in COINS:
        ts, c = closes(coin, upto=want, now=now)
        if not ts:
            skipped.append(f"{coin}: no bars")
            continue
        day = datetime.fromtimestamp(ts[-1], UTC).strftime("%Y-%m-%d")
        if day != want:
            skipped.append(f"{coin}: the latest daily bar is {day}, expected {want}")
        elif (coin, day) in done:
            skipped.append(f"{coin}: already written for {day}")
        elif len(c) < CONTEXT:
            skipped.append(f"{coin}: only {len(c)} closes")
        else:
            todo.append((coin, day, c[-CONTEXT:]))
    if todo:
        q = predict([x[2] for x in todo])
        for k, (coin, day, ctx) in enumerate(todo):
            last = float(ctx[-1])
            row = {"kind": "forecast", "coin": coin, "origin_day": day, "origin_close": last, "made_at": datetime.fromtimestamp(now, UTC).isoformat(timespec="seconds"),
                   "model": MODEL_ID, "revision": REVISION, "context": CONTEXT,
                   "targets": "h1 = the close of the next daily candle after origin_day; h5 = the close 5 candles after it (forecast from closes through "
                              "origin_day only, written a few hours into the next candle: made_at says when)",
                   "forecast": {f"h{h}": {"quantiles": [round(float(x), 6) for x in q[k, h - 1]], "p_up": round(p_up(q[k, h - 1], last), 4)} for h in HORIZONS}}
            append(row)
            written.append(f"{coin} {day}")
    v = verify()
    status = "ok" if v["ok"] else f"CHAIN BROKEN at line {v.get('broken_at_line')}"
    d = shadow_dir()
    d.mkdir(parents=True, exist_ok=True)
    stamp = f"[{datetime.fromtimestamp(now, UTC):%Y-%m-%d %H:%M}]"
    with (d / RUN_LOG).open("a") as fh:                       # the run checker reads the 'daily rows=' line (runcheck_parts: chronos_shadow)
        fh.write(f"{stamp} daily rows={len(written)} status={status}\n" + (f"{stamp} skipped: {'; '.join(skipped)}\n" if skipped else ""))
    return {"written": written, "skipped": skipped, "chain": v}


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "verify"
    print(json.dumps(run() if cmd == "run" else verify(), indent=1))
