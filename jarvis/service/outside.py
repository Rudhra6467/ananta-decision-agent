"""Outside our system: live facts about ANY coin from CoinGecko (free public API, no key).

This is Ananta's first external connection. It is kept separate from Ananta's own data on purpose:
answers built on it are labelled "From AI · CoinGecko" so the owner always knows the number did not
come from our scans, trades or evidence. Nothing here is used for decisions or trading.
"""
from __future__ import annotations

import difflib
import re
import threading
import time

import requests

BASE = "https://api.coingecko.com/api/v3"
SOURCE = "CoinGecko (live market data)"
NOTE = "Outside our system: market facts from CoinGecko plus the AI's general knowledge, not from Ananta's scans, trades or evidence."
OUR_BASKET = {"BTC", "ETH", "SOL", "ADA", "DOGE", "AVAX", "BCH", "LINK", "LTC", "XRP"}

_cache: dict[str, tuple[float, object]] = {}
_lock = threading.Lock()


def _get(path: str, params: dict | None = None, ttl: int = 300, get=None):
    key = path + repr(sorted((params or {}).items()))
    with _lock:
        hit = _cache.get(key)
        if hit and hit[0] > time.time():
            return hit[1]
    if get:
        data = get(path, params or {})
    else:
        r = requests.get(BASE + path, params=params or {}, timeout=10, headers={"accept": "application/json"})
        if r.status_code == 429:
            raise RuntimeError("CoinGecko is rate-limiting us right now; try again in a minute")
        r.raise_for_status()
        data = r.json()
    with _lock:
        _cache[key] = (time.time() + ttl, data)
    return data


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def search(query: str, get=None) -> dict:
    """Find a coin by name or symbol. Exact name/symbol/id match wins; else best close match;
    else not found with a few similar names to pick from."""
    q = (query or "").strip()
    if not q:
        return {"found": False, "similar": [], "error": "no coin name given"}
    coins = (_get("/search", {"query": q}, ttl=3600, get=get) or {}).get("coins") or []
    nq = _norm(re.sub(r"\b(coin|token|crypto|price)\b", "", q, flags=re.I))
    exact = [c for c in coins if nq in (_norm(c.get("name")), _norm(c.get("symbol")), _norm(c.get("id")))]
    exact.sort(key=lambda c: c.get("market_cap_rank") or 10**9)
    if exact:
        return {"found": True, "id": exact[0]["id"], "name": exact[0]["name"], "symbol": exact[0]["symbol"].upper()}
    ranked = sorted([c for c in coins if c.get("market_cap_rank")], key=lambda c: c["market_cap_rank"])[:8] or coins[:8]
    if ranked and difflib.SequenceMatcher(None, nq, _norm(ranked[0]["name"])).ratio() >= 0.85:
        c = ranked[0]
        return {"found": True, "id": c["id"], "name": c["name"], "symbol": c["symbol"].upper(), "matched_from": q}
    similar = [f"{c['name']} ({c['symbol'].upper()})" for c in ranked[:4]]
    if not similar:                                   # misspelt ("etherium", "solanna"): closest well-known names
        similar = difflib.get_close_matches(q.title(), KNOWN, n=4, cutoff=0.5)
    return {"found": False, "similar": similar, "query": q}


def coin(query: str, get=None) -> dict:
    """Live facts about any coin: price, moves, size, rank, all-time high, what it is."""
    s = search(query, get=get)
    if not s.get("found"):
        return {**s, "source": SOURCE, "message": f"I couldn't find a coin called '{query}'."}
    d = _get(f"/coins/{s['id']}", {"localization": "false", "tickers": "false", "community_data": "false",
                                    "developer_data": "false", "sparkline": "false"}, get=get)
    md = d.get("market_data") or {}
    usd = lambda k: (md.get(k) or {}).get("usd")  # noqa: E731
    desc = re.sub(r"<[^>]+>", "", ((d.get("description") or {}).get("en") or "")).strip()
    desc = " ".join(re.split(r"(?<=[.!?])\s+", desc)[:2])[:400]
    sym = (d.get("symbol") or s["symbol"]).upper()
    return {
        "found": True, "name": d.get("name"), "symbol": sym, "in_our_basket": sym in OUR_BASKET,
        "price_usd": usd("current_price"), "change_24h_pct": md.get("price_change_percentage_24h"),
        "change_7d_pct": md.get("price_change_percentage_7d"), "change_30d_pct": md.get("price_change_percentage_30d"),
        "market_cap_usd": usd("market_cap"), "market_cap_rank": d.get("market_cap_rank"), "volume_24h_usd": usd("total_volume"),
        "high_24h": usd("high_24h"), "low_24h": usd("low_24h"), "all_time_high": usd("ath"), "ath_date": ((md.get("ath_date") or {}).get("usd") or "")[:10],
        "from_ath_pct": (md.get("ath_change_percentage") or {}).get("usd"),
        "categories": (d.get("categories") or [])[:4], "what_it_is": desc, "updated": md.get("last_updated"),
        "source": SOURCE, "source_url": f"https://www.coingecko.com/en/coins/{s['id']}",
        "label_rule": "Say this is from outside our system (CoinGecko + general AI knowledge). We do not trade or scan it" + ("" if sym in OUR_BASKET else ", it is not in our 10-coin basket") + ".",
    }


KNOWN = ["Bitcoin", "Ethereum", "Solana", "Cardano", "Dogecoin", "Avalanche", "Bitcoin Cash", "Chainlink", "Litecoin", "XRP", "Polkadot",
         "Polygon", "Shiba Inu", "Pepe", "Toncoin", "Tron", "Stellar", "Monero", "Uniswap", "Aave", "Near Protocol", "Sui", "Aptos",
         "Arbitrum", "Optimism", "Render", "Injective", "Kaspa", "Hedera", "Cosmos", "Filecoin", "Internet Computer", "Bonk", "Dogwifhat",
         "Tether", "USDC", "BNB", "Hyperliquid", "Ethena", "Celestia", "Sei", "Stacks", "Algorand", "Tezos", "Fantom", "Sonic"]
