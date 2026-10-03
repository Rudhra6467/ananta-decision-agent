"""Point-in-time news check (the "blunder guard"): before buying, a quick AI look at the news about the asset itself.

Madhav's rule: chart and value decide the buy; AI is the last look for a blunder he missed - like buying Yes Bank
while it was collapsing on its own bad news. So the check separates two kinds of bad news:
  DAMAGE  - bad news about the asset itself: hack/exploit, outage/halt, insolvency/default, fraud/charges/arrest,
            a regulator acting against it, delisting, insiders or a treasury dumping it  -> BLOCK (don't catch this knife)
  MARKET  - market-wide fear: liquidations, risk-off, macro, "everything is down"     -> not a reason to skip
  SUPPLY  - pressure that is not damage: token unlocks, ETF outflows, a fund trimming     -> CAUTION
  GOOD    - real positive news about the asset itself
Point in time: only headlines dated BEFORE the moment's day are used (Google News dates are day-level, so the buy's
own day could contain news from after the buy; those are listed separately, never used for the verdict).
Live use is the same call with the window ending now.

    python -m src.research.news_check --name Solana --at "2026-06-05 14:55" [--days 4] [--model gemma4:12b]
"""
from __future__ import annotations

import argparse
import email.utils
import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Toronto")
DAMAGE_WORDS = ("hack OR exploit OR outage OR halted OR lawsuit OR SEC OR regulator OR delist OR bankruptcy OR insolvency "
                "OR default OR fraud OR arrested OR investigation OR ban OR moratorium OR unlock OR dump OR sells")

SYSTEM = "You check news for a trader just before he buys. You are his last look for a blunder, not the reason to buy. Answer only JSON."

TASK = """Task: sort the headlines above that are about {name} the asset (skip anything else: a town with the same name, other tokens).
- DAMAGE: bad news about {name} itself that can hurt its value beyond the market mood: hack or exploit, network outage or halt,
  insolvency or default, fraud, charges or arrests of its leaders, a regulator or central bank acting against it, delisting,
  insiders or a big holder/treasury dumping it, a failed rescue or capital raise.
- SUPPLY: selling pressure that is not damage: token unlocks, ETF outflows, a fund trimming, emissions.
- MARKET: market-wide fear (crashes, liquidations, risk-off, macro). Price-drop headlines and bearish price predictions are MARKET, not DAMAGE.
- GOOD: real positive news about {name} itself (adoption, partnerships, upgrades, approvals). Price hype is not GOOD.
Verdict: BLOCK if any DAMAGE is serious and recent; CAUTION if DAMAGE is minor or SUPPLY is heavy; otherwise CLEAR.
Answer only this JSON, using the headline numbers:
{{"verdict":"BLOCK|CAUTION|CLEAR","why":"one or two plain sentences","damage":[{{"i":0,"note":"..."}}],"supply":[{{"i":0,"note":"..."}}],"market":[0],"good":[{{"i":0,"note":"..."}}]}}"""


def google_news(query: str, start: datetime, end: datetime) -> list[dict]:
    q = f"{query} after:{start:%Y-%m-%d} before:{(end + timedelta(days=1)):%Y-%m-%d}"
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode({"q": q, "hl": "en-US", "gl": "US", "ceid": "US:en"})
    raw = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=30).read()
    out = []
    for it in ET.fromstring(raw).findall("./channel/item"):
        d = email.utils.parsedate_to_datetime(it.findtext("pubDate"))
        title = re.sub(r"\s+-\s+[^-]+$", "", it.findtext("title") or "").strip()
        out.append({"day": d.strftime("%Y-%m-%d"), "title": title, "source": it.findtext("source") or ""})
    return out


def gather(name: str, at: datetime, days: int = 4, market: bool = True) -> dict:
    """Headlines dated before the moment's day (used) and on that day (shown only)."""
    start = at - timedelta(days=days)
    rows, seen = [], set()
    queries = [f'"{name}"', f'"{name}" ({DAMAGE_WORDS})'] + (["crypto market"] if market else [])
    for q in queries:
        try:
            got = google_news(q, start, at)
        except Exception as exc:  # noqa: BLE001
            got = []
            rows.append({"day": "", "title": f"(search failed: {exc})", "source": "", "query": q})
        for h in got:
            k = h["title"].lower()[:90]
            if k in seen:
                continue
            seen.add(k)
            rows.append(h | {"query": "market" if q == "crypto market" else ("damage" if "(" in q else "asset")})
    day = at.strftime("%Y-%m-%d")
    before = [r for r in rows if r["day"] and r["day"] < day]
    own = sorted([r for r in before if r["query"] != "market"], key=lambda r: r["day"])[-75:]       # the latest 75 about the asset
    mkt = sorted([r for r in before if r["query"] == "market"], key=lambda r: r["day"])[-15:]       # and 15 about the market
    used = sorted(own + mkt, key=lambda r: (r["day"], r["query"]))
    same = [r for r in rows if r["day"] == day]
    return {"used": used, "same_day_not_used": same}


def classify(name: str, at: datetime, headlines: list[dict], model: str = "gemma4:12b", url: str = "http://localhost:11434") -> dict:
    if not headlines:
        return {"verdict": "UNKNOWN", "why": "No dated headlines were found for this window (a data gap, not 'no bad news')."}
    lines = "\n".join(f"[{i}] {h['day']} | {h['title']} | {h['source']}" for i, h in enumerate(headlines[:90]))
    body = {"model": model, "stream": False, "format": "json", "think": False, "options": {"temperature": 0, "num_ctx": 16384},
            "messages": [{"role": "system", "content": SYSTEM},
                         {"role": "user", "content": f"Asset: {name}. Moment: {at:%Y-%m-%d %H:%M} Toronto. Headlines from the days before "
                                                     f"(day | title | source):\n{lines}\n\n" + TASK.format(name=name)}]}
    req = urllib.request.Request(f"{url}/api/chat", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    r = json.loads(urllib.request.urlopen(req, timeout=300).read())
    try:
        v = json.loads(r["message"]["content"])
    except Exception:  # noqa: BLE001
        return {"verdict": "UNKNOWN", "why": "The model's answer was not readable.", "raw": r.get("message", {}).get("content", "")[:500]}

    def pick(xs):
        out = []
        for x in xs or []:
            i = x.get("i") if isinstance(x, dict) else x
            if isinstance(i, int) and 0 <= i < len(headlines):
                out.append({"headline": f"{headlines[i]['day']} {headlines[i]['title']}", **({"note": x.get("note")} if isinstance(x, dict) else {})})
        return out

    return {"verdict": v.get("verdict", "UNKNOWN"), "why": v.get("why", ""), "damage": pick(v.get("damage")), "supply": pick(v.get("supply")),
            "good": pick(v.get("good")), "market_count": len(v.get("market") or []), "model": model}


def check(name: str, at_local: str, days: int = 4, model: str = "gemma4:12b", market: bool = True) -> dict:
    at = datetime.strptime(at_local, "%Y-%m-%d %H:%M").replace(tzinfo=TZ)
    g = gather(name, at, days, market)
    res = classify(name, at, g["used"], model)
    return {"asset": name, "moment": at_local, "window_days": days, "headlines_used": len(g["used"]),
            "same_day_not_used": [f"{h['day']} {h['title']}" for h in g["same_day_not_used"]][:15], **res}


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--at", required=True, help='Toronto time "YYYY-MM-DD HH:MM"')
    ap.add_argument("--days", type=int, default=4)
    ap.add_argument("--model", default="gemma4:12b")
    ap.add_argument("--no-market", action="store_true")
    a = ap.parse_args(argv)
    print(json.dumps(check(a.name, a.at, a.days, a.model, not a.no_market), indent=1))


if __name__ == "__main__":
    main()
