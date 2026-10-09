"""The live universe registry: every coin Ananta watches, one list every part reads (Universe Rule v2, docs/UNIVERSE_RULE_V2.md;
engine plan U1, Madhav 2026-10-09: "watch whole crypto universe").

Membership: every Binance spot pair against USDT that is TRADING, minus stablecoins / fiat / leveraged / wrapped (rule v1's lists).
Tiers by the median daily traded value of the last 30 closed days: A >= $20M, B >= $1M, C below (or under 30 days of history).
Tiers are recomputed once a week (Monday, UTC); membership and can-buy flags (NDAX vs CAD, Kraken vs USD) every day.

Groups that keep their own books (D7, the control group): LAB10 (the 10 live coins) and T30 (the 30-coin tier).

  build(j, get=None)     refresh membership, flags, spreads (daily) and tiers (weekly); writes universe_live.json in the agent folder
  load(j)                the registry as a dict (cached by file time)
  members(j, tier=None)  coins, optionally of one tier ("A", "B", "C" or "AB")
  tier_of(j, coin)       "A" / "B" / "C" / None
  cost(coin)             paper cost per side (fee + half spread) under rule v2
  lab10() / t30()        the two control groups
Read-only public data; nothing here trades.
"""
from __future__ import annotations

import json
import statistics
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

FILE = "universe_live.json"
TIER_A, TIER_B = 20e6, 1e6
FLOOR = {"A": 0.0020, "B": 0.0040, "C": 0.0080}
NDAX_FEE, KRAKEN_FEE = 0.0020, 0.0040
BINANCE = "https://api.binance.com"
KRAKEN_ALIAS = {"XBT": "BTC", "XDG": "DOGE"}
PEGGED = {"XAUT", "PAXG"}                     # gold-backed tokens track gold, not the crypto market (PAXG is also in rule v1's list)
_CACHE: dict = {"m": None, "reg": None, "path": None}


def _get(url: str, timeout: int = 30):
    req = urllib.request.Request(url, headers={"User-Agent": "ananta-registry/1"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def lab10() -> list[str]:
    from src.research import reads as R

    return list(R.COINS)


def t30() -> list[str]:
    from jarvis.service import tier30

    return list(tier30.COINS)


def _excluded(base: str) -> bool:
    from src.lake.universe import LEVERAGED, STABLE, WRAPPED

    import re

    # also out: names outside A-Z / 0-9 (a few new Binance tokens use other scripts; Binance's multi-symbol calls refuse them)
    return (not base) or base in STABLE or base in WRAPPED or base in PEGGED or bool(LEVERAGED.search(base)) or not re.fullmatch(r"[A-Z0-9]+", base)


def _path(j) -> Path:
    return Path(j.dir) / FILE


def load(j) -> dict:
    p = _path(j)
    if not p.exists():
        return {"coins": {}, "built_at": None}
    m = p.stat().st_mtime
    if _CACHE["m"] != m or _CACHE["path"] != str(p):
        _CACHE.update(m=m, path=str(p), reg=json.loads(p.read_text()))
    return _CACHE["reg"]


def members(j, tier: str | None = None, listed: bool = True) -> list[str]:
    coins = load(j).get("coins", {})
    out = []
    for c, k in coins.items():
        if listed and k.get("status") != "LISTED":
            continue
        if tier and (k.get("tier") or "C") not in tier:
            continue
        out.append(c)
    return sorted(out, key=lambda c: -(coins[c].get("median_usd_30d") or 0))


def tier_of(j, coin: str) -> str | None:
    k = load(j).get("coins", {}).get((coin or "").upper())
    return (k or {}).get("tier")


def card(j, coin: str) -> dict | None:
    k = load(j).get("coins", {}).get((coin or "").upper())
    return dict(k, coin=coin.upper()) if k else None


def cost(coin: str, reg: dict | None = None) -> float:
    """Paper cost per side under rule v2 (the 10 keep their measured NDAX costs)."""
    from src.intelligence.explorer_engine import HALF_SPREAD

    c = (coin or "").upper()
    if c in HALF_SPREAD:
        return NDAX_FEE + HALF_SPREAD[c]
    reg = reg or _CACHE.get("reg") or {}
    k = reg.get("coins", {}).get(c) or {}
    tier = k.get("tier") or "C"
    hs = max(3 * (k.get("binance_half_spread") or 0.0), FLOOR[tier])
    return (NDAX_FEE if k.get("ndax") else KRAKEN_FEE) + hs


def _ndax(get) -> set[str]:
    ins = get("https://api.ndax.io:8443/AP/GetInstruments?OMSId=1")
    return {i.get("Product1Symbol") for i in ins if i.get("Product2Symbol") == "CAD" and not i.get("IsDisable")}


def _kraken(get) -> set[str]:
    res = get("https://api.kraken.com/0/public/AssetPairs")["result"]
    out = set()
    for v in res.values():
        ws = v.get("wsname") or ""
        if ws.endswith("/USD"):
            b = ws.split("/")[0]
            out.add(KRAKEN_ALIAS.get(b, b))
    return out


def _week(t: float) -> str:
    y, w, _ = datetime.fromtimestamp(t, timezone.utc).isocalendar()
    return f"{y}-W{w:02d}"


def build(j, get=None, daily_qv=None, now: float | None = None, force_tiers: bool = False) -> dict:
    """Refresh the registry. daily_qv(coin) -> list of (t, quote_volume) closed days (the feed's daily candles)."""
    get = get or _get
    now = now or time.time()
    old = load(j)
    info = get(f"{BINANCE}/api/v3/exchangeInfo?permissions=SPOT")
    names, stocks = {}, set(old.get("stock_tokens") or [])
    try:                                                  # names and tags; tokenized shares ('bStocks') are not crypto: out
        for x in get("https://www.binance.com/bapi/asset/v2/public/asset-service/product/get-products?includeEtf=true")["data"]:
            if x.get("q") == "USDT" or x.get("pm") == "USDT":
                names[x["b"]] = x.get("an")
                if "bStocks" in (x.get("tags") or []) or "(bStocks)" in (x.get("an") or ""):
                    stocks.add(x["b"])
    except Exception:  # noqa: BLE001  the product list is down: keep the stock list we had
        pass
    live = {}
    for s in info["symbols"]:
        if s.get("quoteAsset") == "USDT" and s.get("status") == "TRADING" and not _excluded(s["baseAsset"]) and s["baseAsset"] not in stocks:
            live[s["baseAsset"]] = s["symbol"]
    flags = {}
    for name, fn in (("ndax", _ndax), ("kraken", _kraken)):
        try:
            flags[name] = fn(get)
        except Exception:  # noqa: BLE001  a venue down keeps yesterday's flags
            flags[name] = None
    try:
        book = {b["symbol"]: b for b in get(f"{BINANCE}/api/v3/ticker/bookTicker")}
    except Exception:  # noqa: BLE001
        book = {}
    coins = {}
    prev = old.get("coins", {})
    for base, sym in live.items():
        k = dict(prev.get(base) or {})
        k.update(symbol=sym, status="LISTED", last_seen=int(now))
        if names.get(base):
            k["name"] = names[base]
        k.setdefault("first_seen", int(now))
        for name in ("ndax", "kraken"):
            if flags[name] is not None:
                k[name] = base in flags[name]
        b = book.get(sym)
        try:
            bid, ask = float(b["bidPrice"]), float(b["askPrice"])
            if bid > 0 and ask > 0:
                k["binance_half_spread"] = round((ask - bid) / (ask + bid), 6)
        except Exception:  # noqa: BLE001
            pass
        coins[base] = k
    for base, k in prev.items():                          # gone from the list = delisted (kept, with the day it went)
        if base in stocks or _excluded(base):
            continue
        if base not in coins:
            k = dict(k)
            if k.get("status") == "LISTED":
                k.update(status="DELISTED", delisted_at=int(now))
            coins[base] = k
    week = _week(now)
    redo = force_tiers or old.get("tiers_week") != week or any("tier" not in k for k in coins.values() if k["status"] == "LISTED")
    if redo and daily_qv:
        for base, k in coins.items():
            if k["status"] != "LISTED":
                continue
            rows = [qv for t, qv in (daily_qv(base) or [])[-30:] if qv is not None]
            med = statistics.median(rows) if rows else 0.0
            k["median_usd_30d"] = round(med)
            k["days_of_history"] = len(daily_qv(base) or [])
            k["tier"] = "C" if len(rows) < 30 else "A" if med >= TIER_A else "B" if med >= TIER_B else "C"
        tiers_week = week
    else:
        tiers_week = old.get("tiers_week")
    labs, tiers30 = set(lab10()), set(t30())
    for base, k in coins.items():
        k["groups"] = [g for g, s in (("LAB10", labs), ("T30", tiers30)) if base in s]
    reg = {"rule": "v2 (docs/UNIVERSE_RULE_V2.md)", "built_at": int(now), "tiers_week": tiers_week, "coins": coins,
           "stock_tokens": sorted(stocks),
           "counts": {"listed": sum(k["status"] == "LISTED" for k in coins.values()),
                      **{t: sum(k["status"] == "LISTED" and k.get("tier") == t for k in coins.values()) for t in "ABC"},
                      "delisted": sum(k["status"] == "DELISTED" for k in coins.values()),
                      "ndax": sum(bool(k.get("ndax")) for k in coins.values() if k["status"] == "LISTED"),
                      "kraken": sum(bool(k.get("kraken")) for k in coins.values() if k["status"] == "LISTED")}}
    p = _path(j)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(reg, indent=1))
    tmp.replace(p)
    _CACHE.update(m=None)
    return {"built_at": reg["built_at"], "counts": reg["counts"], "tiers_recomputed": bool(redo and daily_qv)}
