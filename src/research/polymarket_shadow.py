"""Polymarket shadow for crypto: the crowd's probability beside Ananta's, a blind forward record (Madhav, 27 Oct 2026 00:05 Toronto, "yes", to:
"Polymarket's crypto markets ('Bitcoin above $X by Friday') give a crowd probability we could compare against Ananta's own crypto forecasts.
That would be a record-only shadow: read the prices, never bet").

What it does
- Once a day, right after the Chronos shadow writes its forecast (com.ananta.chronosshadow 04:20 Toronto), it reads Polymarket's PUBLIC market
  list (gamma-api.polymarket.com, no key, no account, no wallet) for the simple price questions "Will the price of Bitcoin / Ethereum be above
  $K on <date>?" (resolved on Binance's BTCUSDT / ETHUSDT 1-minute candle at 12:00 ET of that date).
- For each question it records the crowd's YES price (its probability) and, when the question settles 1 or 5 days after the Chronos forecast's
  origin day, Ananta's probability from that forecast's nine quantiles (P(close above K), interpolated as chronos_shadow.p_up does). Chronos'
  targets are the daily closes (00:00 UTC), 8 hours after the 12:00 ET resolution: the row says so (gap_hours). Any other date gets
  'no forecast'; nothing is extrapolated.
- Rows go to a hash-chained log OUTSIDE the repo: ~/ananta_runs/shadow_polymarket/polymarket_crypto.jsonl. settle() later records each
  question's public resolution (and checks it against Binance's own 1-minute candle) in polymarket_settled.jsonl.

What it never does
- It never bets, signs in, holds money or sends an order; nothing in a book, the brain, the gate or a trade reads it.
- It scores nothing before 2026-12-15 00:00 UTC: results() is sealed like the Chronos shadow (its probabilities are Chronos' forecasts, and the
  Chronos study PW-HF-CHRONOS runs after the window). Before then only counts are shown (status()): "record-only shadow, not evidence until 30+
  settled". After the window: Brier score for the crowd and for Ananta on the same settled questions.

  python -m src.research.polymarket_shadow record     today's questions (launchd com.ananta.polymarketshadow 04:45 Toronto, after Chronos)
  python -m src.research.polymarket_shadow settle     resolutions of questions whose date has passed
  python -m src.research.polymarket_shadow status     counts only
  python -m src.research.polymarket_shadow verify     the chain
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.research import chronos_shadow as C

UTC = timezone.utc
SEALED_UNTIL = C.SEALED_UNTIL
GAMMA = "https://gamma-api.polymarket.com"
BINANCE_1M = "https://data-api.binance.vision/api/v3/klines"
LOG, SETTLED, RUN_LOG = "polymarket_crypto.jsonl", "polymarket_settled.jsonl", "run.log"
COIN_OF = {"bitcoin": "BTC", "ethereum": "ETH"}                 # the Chronos shadow forecasts BTC and ETH only
EVENT_RX = re.compile(r"^(Bitcoin|Ethereum) above ___ on (.+?)\??$", re.I)
Q_RX = re.compile(r"^Will the price of (Bitcoin|Ethereum) be above \$([\d,]+(?:\.\d+)?) on ([A-Za-z]+ \d{1,2})\?$", re.I)
PAUSE = 1.5                                                     # seconds between requests: gentle
MIN_SETTLED = 30


class Sealed(RuntimeError):
    """A score was asked for before the end of the evidence window."""


def shadow_dir() -> Path:
    if os.getenv("ANANTA_POLYMARKET_SHADOW_DIR"):
        return Path(os.environ["ANANTA_POLYMARKET_SHADOW_DIR"]).expanduser()
    return Path(os.getenv("ANANTA_RUNS_DIR", str(Path.home() / "ananta_runs"))).expanduser() / "shadow_polymarket"


def _get(url: str) -> object:
    req = urllib.request.Request(url, headers={"User-Agent": "Ananta read-only shadow (no trading)"})
    return json.loads(urllib.request.urlopen(req, timeout=30).read())


def _canon(row: dict) -> str:
    return json.dumps({k: v for k, v in row.items() if k != "hash"}, sort_keys=True, separators=(",", ":"))


def _rows(name: str = LOG) -> list[dict]:
    p = shadow_dir() / name
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()] if p.exists() else []


def _append(row: dict, name: str = LOG) -> dict:
    d = shadow_dir()
    d.mkdir(parents=True, exist_ok=True)
    rows = _rows(name)
    row = {**row, "prev_hash": rows[-1]["hash"] if rows else "0" * 64}
    row["hash"] = hashlib.sha256((row["prev_hash"] + _canon(row)).encode()).hexdigest()
    with (d / name).open("a") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")
    return row


def verify(name: str = LOG) -> dict:
    prev = "0" * 64
    rows = _rows(name)
    for i, r in enumerate(rows, 1):
        if r.get("prev_hash") != prev or hashlib.sha256((prev + _canon(r)).encode()).hexdigest() != r.get("hash"):
            return {"ok": False, "rows": len(rows), "broken_at_line": i}
        prev = r["hash"]
    return {"ok": True, "rows": len(rows)}


# ------------------------------------------------------------------------------------------------------------------------------ parsing

def parse_question(q: str, end_date: str) -> dict | None:
    """'Will the price of Bitcoin be above $78,000 on October 28?' with its endDate -> coin, threshold, resolution time (UTC). Others: None."""
    m = Q_RX.match((q or "").strip())
    if not m or not end_date:
        return None
    try:
        res = datetime.fromisoformat(end_date.replace("Z", "+00:00")).astimezone(UTC)
    except ValueError:
        return None
    return {"coin": COIN_OF[m.group(1).lower()], "threshold": float(m.group(2).replace(",", "")), "direction": "above",
            "resolves_at": res.isoformat(timespec="seconds"), "date": res.strftime("%Y-%m-%d")}


def crowd_p(m: dict) -> dict:
    """The YES price: the mid of the best bid and ask when both exist, else the listed outcome price."""
    out = {}
    try:
        prices = json.loads(m.get("outcomePrices") or "null")
        outcomes = json.loads(m.get("outcomes") or "null")
        if prices and outcomes and str(outcomes[0]).lower() == "yes":
            out["listed"] = float(prices[0])
    except (TypeError, ValueError):
        pass
    bb, ba = m.get("bestBid"), m.get("bestAsk")
    if bb is not None and ba is not None and float(ba) >= float(bb) > 0:
        out["mid"] = round((float(bb) + float(ba)) / 2, 4)
    out["p"] = out.get("mid", out.get("listed"))
    return out


def fetch_questions() -> list[dict]:
    """Open 'Bitcoin / Ethereum above ___ on <date>?' events from the public list, two pages at most."""
    found = []
    for offset in (0, 100):
        evs = _get(f"{GAMMA}/events?" + urllib.parse.urlencode({"tag_slug": "crypto", "active": "true", "closed": "false", "limit": 100,
                                                                "offset": offset, "order": "volume24hr", "ascending": "false"}))
        time.sleep(PAUSE)
        for e in evs or []:
            if not EVENT_RX.match(str(e.get("title") or "")):
                continue
            for m in e.get("markets") or []:
                p = parse_question(m.get("question"), m.get("endDate") or e.get("endDate"))
                if p and not m.get("closed"):
                    found.append({**p, "market_id": str(m.get("id")), "question": m.get("question"), "slug": m.get("slug"),
                                  "crowd": crowd_p(m), "volume": _num(m.get("volume")), "liquidity": _num(m.get("liquidity")),
                                  "resolution_source": (m.get("resolutionSource") or "")[:200]})
        if len(evs or []) < 100:
            break
    return found


def _num(x) -> float | None:
    try:
        return round(float(x), 2)
    except (TypeError, ValueError):
        return None


# ------------------------------------------------------------------------------------------------------------------------------ Ananta's side

def latest_forecasts() -> dict:
    """The newest Chronos forecast per coin (read-only)."""
    out = {}
    for r in C._rows():
        if r.get("kind") == "forecast":
            out[r["coin"]] = r
    return out


def ananta_p(q: dict, fc: dict | None) -> dict:
    """P(close above K) from the Chronos quantiles when the question's date is 1 or 5 days after the forecast's origin day; else 'no forecast'."""
    if not fc:
        return {"status": "no forecast", "why": "no Chronos forecast for this coin yet"}
    origin = datetime.strptime(fc["origin_day"], "%Y-%m-%d").replace(tzinfo=UTC)
    res = datetime.fromisoformat(q["resolves_at"])
    h = (res.date() - origin.date()).days
    if h not in C.HORIZONS:
        return {"status": "no forecast", "why": f"the question settles {h} days after the forecast's origin day; Chronos forecasts 1 and 5 days"}
    target = origin + timedelta(days=h + 1)                                   # the close of day origin+h = 00:00 UTC of the next day
    quant = fc["forecast"][f"h{h}"]["quantiles"]
    return {"status": "ok", "p": round(C.p_up(quant, q["threshold"]), 4), "horizon_days": h, "origin_day": fc["origin_day"],
            "forecast_made_at": fc.get("made_at"), "target": f"the daily close of {(origin + timedelta(days=h)):%Y-%m-%d} (00:00 UTC)",
            "gap_hours": round((target - res).total_seconds() / 3600, 1)}


def record(now: float | None = None, questions: list[dict] | None = None) -> dict:
    """One row per question per Chronos origin day (a re-run the same day writes nothing new)."""
    now = now or time.time()
    qs = fetch_questions() if questions is None else questions
    fcs = latest_forecasts()
    done = {(r.get("market_id"), (r.get("ananta") or {}).get("origin_day") or r.get("recorded_day")) for r in _rows()}
    day = datetime.fromtimestamp(now, UTC).strftime("%Y-%m-%d")
    written = with_p = 0
    for q in qs:
        if q.get("crowd", {}).get("p") is None or datetime.fromisoformat(q["resolves_at"]).timestamp() <= now:
            continue
        a = ananta_p(q, fcs.get(q["coin"]))
        key = (q["market_id"], a.get("origin_day") or day)
        if key in done:
            continue
        _append({"kind": "record", "recorded_at": datetime.fromtimestamp(now, UTC).isoformat(timespec="seconds"), "recorded_day": day, **q, "ananta": a})
        done.add(key)
        written += 1
        with_p += a["status"] == "ok"
    v = verify()
    d = shadow_dir()
    d.mkdir(parents=True, exist_ok=True)
    with (d / RUN_LOG).open("a") as fh:
        stamp = f"[{datetime.fromtimestamp(now, UTC):%Y-%m-%d %H:%M}]"     # the run checker reads the 'daily rows=' line (runcheck_parts: polymarket_shadow)
        fh.write(f"{stamp} daily rows={written} status={'ok' if v['ok'] else 'CHAIN BROKEN at line ' + str(v.get('broken_at_line'))}\n"
                 f"{stamp} detail: with_ananta={with_p} found={len(qs)}\n")
    return {"found": len(qs), "written": written, "with_ananta_p": with_p, "chain": v}


# ------------------------------------------------------------------------------------------------------------------------------ settlement

def _binance_close_at(coin: str, at: datetime) -> float | None:
    """The close of Binance spot's 1-minute candle that opens at `at` (the question's resolution minute)."""
    t = int(at.timestamp()) * 1000
    rows = _get(f"{BINANCE_1M}?symbol={coin}USDT&interval=1m&startTime={t}&limit=1")
    return float(rows[0][4]) if rows and int(rows[0][0]) == t else None


def settle(now: float | None = None) -> dict:
    """For each recorded question whose resolution time has passed and that is not settled: Polymarket's public resolution (closed market,
    outcome prices 1/0) and the Binance 1-minute check. The outcome lives in its own log; nothing is scored here."""
    now = now or time.time()
    settled = {r["market_id"] for r in _rows(SETTLED)}
    todo = {}
    for r in _rows():
        if r["market_id"] not in settled and datetime.fromisoformat(r["resolves_at"]).timestamp() < now - 3600:
            todo[r["market_id"]] = r
    n = 0
    for mid, r in todo.items():
        try:
            m = _get(f"{GAMMA}/markets/{mid}")
            time.sleep(PAUSE)
        except Exception:  # noqa: BLE001  try again tomorrow
            continue
        if not m.get("closed"):
            continue
        try:
            prices = [float(x) for x in json.loads(m.get("outcomePrices") or "[]")]
        except (TypeError, ValueError):
            continue
        if len(prices) < 2 or sorted(prices) != [0.0, 1.0]:
            continue
        yes = int(prices[0] == 1.0)
        check = None
        try:
            px = _binance_close_at(r["coin"], datetime.fromisoformat(r["resolves_at"]))
            time.sleep(PAUSE)
            if px is not None:
                check = {"binance_close": px, "above": px > r["threshold"], "agrees": (px > r["threshold"]) == bool(yes)}
        except Exception:  # noqa: BLE001
            pass
        _append({"kind": "settled", "settled_at": datetime.fromtimestamp(now, UTC).isoformat(timespec="seconds"), "market_id": mid,
                 "question": r["question"], "resolves_at": r["resolves_at"], "yes": yes, "binance_check": check}, SETTLED)
        n += 1
    return {"settled_now": n, "chain": verify(SETTLED)}


# ------------------------------------------------------------------------------------------------------------------------------ counts and the sealed score

def status() -> dict:
    """Counts only (what Ask and the run checker may show before the window ends)."""
    rows, st = _rows(), _rows(SETTLED)
    qs = {r["market_id"] for r in rows}
    both = {r["market_id"] for r in rows if (r.get("ananta") or {}).get("status") == "ok"}
    done = {r["market_id"] for r in st}
    n_both = len(both & done)
    return {"questions": len(qs), "with_ananta_p": len(both), "settled": len(done & qs), "settled_with_both": n_both,
            "first": rows[0]["recorded_day"] if rows else None, "sealed_until": "2026-12-15",
            "words": (f"Polymarket shadow (record-only shadow, not evidence until {MIN_SETTLED}+ settled): {len(qs)} crypto price questions recorded"
                      + (f" since {rows[0]['recorded_day']}" if rows else "") + f", {len(both)} with Ananta's own probability, "
                      f"{n_both} settled with both; no score is shown before 15 Dec (the Chronos forecasts behind Ananta's side are sealed until then).")}


def results(now: float | None = None) -> dict:
    """Brier score for the crowd and for Ananta on the same settled questions (first record per question). Sealed until 2026-12-15 00:00 UTC."""
    if (now or time.time()) < SEALED_UNTIL:
        raise Sealed("the Polymarket shadow is sealed until 2026-12-15 00:00 UTC (its Ananta side is the Chronos shadow; PW-HF-CHRONOS)")
    yes = {r["market_id"]: r["yes"] for r in _rows(SETTLED)}
    first = {}
    for r in _rows():
        if (r.get("ananta") or {}).get("status") == "ok" and r["market_id"] in yes and r["market_id"] not in first:
            first[r["market_id"]] = r
    pairs = [(r["crowd"]["p"], r["ananta"]["p"], yes[m]) for m, r in first.items()]
    n = len(pairs)
    bc = sum((c - y) ** 2 for c, _, y in pairs) / n if n else None
    ba = sum((a - y) ** 2 for _, a, y in pairs) / n if n else None
    return {"n": n, "crowd_brier": bc and round(bc, 4), "ananta_brier": ba and round(ba, 4),
            "words": f"{n} settled: crowd Brier {bc:.3f}, Ananta {ba:.3f} (lower is better)" + ("; needs 30+ to mean anything" if n < MIN_SETTLED else "")
            if n else "nothing settled with both probabilities"}


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    fn = {"record": record, "settle": settle, "status": status, "verify": verify}.get(cmd)
    print(json.dumps(fn() if fn else {"usage": "record | settle | status | verify"}, indent=1, default=str))
