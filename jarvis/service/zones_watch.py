"""Zones, live: the zone map around each coin's price (src/research/zones.py) and the lookout record.

    board(j)        every coin: the zones near its price, which one it is inside, and what history said about that kind of zone
    coin(j, c)      one coin's zones plus the lookout (decision chain row and your setups) when it is inside a zone
    watch(j)        every 15 minutes: record each new zone entry (price came down into a support band) and, as days pass, how it
                    ended (HELD / BROKEN / OPEN). These live entries are clean evidence for review #7 (the lookout).

Evidence for Madhav, never orders: no zone places a trade.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

PASSING_WORDS = {"PASS": "history supports this kind of zone (review #6)", "FAIL": "history did not support this kind of zone on its own"}
_CACHE: dict = {}


def _status(j) -> dict:
    from jarvis.service.core import docs_dir

    p = docs_dir(j.dir) / "research" / "zones_status.json"
    try:
        return {g: v["status"] for g, v in json.loads(p.read_text())["groups"].items()}
    except Exception:  # noqa: BLE001
        return {}


def _verdict(groups: list[str], st: dict) -> str:
    if any(st.get(g) == "PASS" for g in groups):
        return "SUPPORTED"
    return "NOT_SUPPORTED" if any(g in st for g in groups) else "UNTESTED"


def _lookout_status(j) -> dict:
    from jarvis.service.core import docs_dir

    try:
        return json.loads((docs_dir(j.dir) / "research" / "lookout_status.json").read_text())["reactions"]
    except Exception:  # noqa: BLE001
        return {}


def _reactions(D: list[tuple], btc: list[tuple], z: dict, ls: dict) -> list[dict]:
    """The seven lookout reactions on the last closed day, each with what review #7 said about it."""
    from src.research import reads as R
    from src.research import zones as Z

    S = R.Series(D)
    B = S if btc is D else R.Series(btc)
    f = Z.reactions(S, Z.Arr(S), B, len(D) - 1, {"top": z["top"], "bot": z["bot"], "kinds": set(z["kinds"]), "tier": z.get("tier")})
    return [{"id": k, "name": Z.REACTIONS[k], "present": bool(v), "history": ls.get(k, {}).get("status", "UNTESTED")} for k, v in f.items()]


def attention(row: dict, reads_row: dict | None) -> dict:
    """Where Ananta spends its attention (a design rule built from reviews #5-#7, not itself a tested signal).
    Points: in a zone 1, a zone kind history supports 2, came down into it within 5 days 1, market allowed 2,
    your setup showing 2 (one sign away 1). HIGH >= 6 = look now (worth AI time and the news check), WATCH >= 4, else LOW."""
    score, why = 0.0, []
    z = (row["inside"] or [None])[0] or row.get("tested")
    if z:
        score += 1                                       # price is almost always in some zone: on its own it is worth little
        why.append(f"price is {'inside' if row['inside'] else 'testing'} a zone ({'+'.join(z['kinds']).lower()})")
        if z.get("history") == "SUPPORTED":
            score += 2
            why.append("a kind of zone history supports (review #6)")
        rec = z.get("recent")
        if rec and row.get("day") and (datetime.strptime(row["day"], "%Y-%m-%d") - datetime.strptime(rec["entered"], "%Y-%m-%d")).days <= 5:
            score += 1
            why.append(f"it came down into it on {rec['entered']}")
    f6 = next((x for x in row.get("reactions") or [] if x["id"] == "F6"), None)
    if f6 and f6["present"]:
        score += 2
        why.append("the market is allowed (BTC above its 50-day): the one reaction history supports (review #7)")
    elif z:
        why.append("the market is not allowed (BTC under its 50-day): zones held about half the time then")
    for x in (reads_row or {}).get("reads", []):
        if x["state"] == "FIRED":
            score += 2
            why.append(f"your setup is showing: {x['name'].lower()}")
        elif x["state"] == "CLOSE":
            score += 1
            why.append(f"your setup is one sign away: {x['name'].lower()}")
    level = "HIGH" if score >= 6 else "WATCH" if score >= 4 else "LOW"
    return {"score": score, "level": level, "why": why}


def _coin_zones(j, c: str, st: dict) -> dict | None:
    from jarvis.service.reads_watch import _daily
    from src.research import zones as Z

    D = _daily(j, c)
    if len(D) < 260:
        return None
    z = Z.live_zones(D)
    for r in z["zones"]:
        r["history"] = _verdict(r["groups"], st)
    inside = [r for r in z["zones"] if r["state"] == "INSIDE"]
    tested = next((r for r in z["zones"] if r["state"] == "TESTED" and r["side"] == "support"), None)
    focus = inside[0] if inside else tested
    reactions = _reactions(D, D if c == "BTC" else _daily(j, "BTC"), focus, _lookout_status(j)) if focus else []
    below = [r for r in z["zones"] if r["side"] == "support"]
    above = [r for r in z["zones"] if r["side"] == "resistance"]
    nearest = lambda xs: min(xs, key=lambda r: abs(r["distance_atr"])) if xs else None      # noqa: E731
    return {"coin": c, **z, "inside": inside, "tested": tested, "reactions": reactions,
            "next_support": nearest(below), "next_resistance": nearest(above)}


def board(j) -> dict:
    from src.research import reads as R

    p = Path(j.dir) / "explorer_bars.sqlite"
    if not p.exists():
        return {"coins": [], "note": "The Explorer's candles are not available yet."}
    key = (str(p), p.stat().st_mtime // 900)
    if _CACHE.get("key") == key:
        return _CACHE["board"]
    st = _status(j)
    rows = [r for r in (_coin_zones(j, c, st) for c in R.COINS) if r]
    try:
        from jarvis.service import reads_watch

        rb = {r["coin"]: r for r in reads_watch.board(j).get("coins", [])}
    except Exception:  # noqa: BLE001
        rb = {}
    for r in rows:
        r["attention"] = attention(r, rb.get(r["coin"]))
    rows.sort(key=lambda r: (-r["attention"]["score"], min((abs(x["distance_atr"]) for x in r["zones"]), default=99)))
    out = {"day": rows[0]["day"] if rows else None, "coins": rows, "in_zone": [r["coin"] for r in rows if r["in_zone"]],
           "attention": [{"coin": r["coin"], **r["attention"]} for r in rows if r["attention"]["level"] != "LOW"],
           "groups": st, "recent": recent(j),
           "note": "Price is always in or near a zone (a band, not a line). Inside a zone Ananta starts its lookout. "
                   "History: zones hold a little more often than random bands, the 200-day average and overlapping zones the most "
                   "(review #6); inside a zone the market regime decides most (BTC above its 50-day: 68% held vs 50%); wicks, "
                   "volume and relative strength added nothing (review #7). Entering a zone is not a trade."}
    _CACHE.update(key=key, board=out)
    return out


def coin(j, c: str) -> dict | None:
    row = next((r for r in board(j)["coins"] if r["coin"] == c.upper()), None)
    if row is None:
        return None
    look = None
    if row["in_zone"] or row.get("tested"):             # the lookout: everything Ananta knows, gathered while price is in the zone
        look = {}
        try:
            from jarvis.service import chain

            ch = chain.board(j)
            look["chain"] = next((x for x in ch.get("coins", []) if x["coin"] == row["coin"]), None)
        except Exception:  # noqa: BLE001
            pass
        try:
            from jarvis.service import reads_watch

            rd = reads_watch.coin(j, row["coin"])
            look["your_setups"] = [{k: x.get(k) for k in ("variant", "name", "state", "met", "of", "history")} for x in (rd or {}).get("reads", [])]
        except Exception:  # noqa: BLE001
            pass
        look["plan"] = _plan(row)
        try:
            from jarvis.service import news_watch

            nl = news_watch.latest(j, row["coin"], 3)
            look["news"] = nl[0] if nl else None
        except Exception:  # noqa: BLE001
            look["news"] = None
        look["reactions"] = row.get("reactions")
        look["attention"] = row.get("attention")
    return {**row, "lookout": look, "visits": [v for v in recent(j, 120) if v["coin"] == row["coin"]]}


def _plan(row: dict) -> dict:
    """What would confirm the zone and where the idea is wrong (structure, not a fixed percent)."""
    z = (row["inside"] or [row.get("tested")])[0]
    atr = row["atr"]
    return {"zone": f"{z['bot']:.6g} - {z['top']:.6g}", "held_if": f"a rise above {z['top'] + 1.5 * atr:.6g} (1.5 daily ranges over the band)",
            "wrong_if": f"a daily close below {z['bot'] - 0.5 * atr:.6g} (0.5 daily range under the band)",
            "stop_pct": round(100 * ((z['bot'] - 0.5 * atr) / row["price"] - 1), 1)}


# ---------------------------------------------------------------------------
# the lookout record (live evidence for review #7)
# ---------------------------------------------------------------------------
def _table(j) -> None:
    j.db.execute("CREATE TABLE IF NOT EXISTS zone_visits (id TEXT PRIMARY KEY, t INTEGER, day TEXT, coin TEXT, bot REAL, top REAL, atr REAL, "
                 "groups TEXT, history TEXT, outcome TEXT, outcome_day TEXT)")


def recent(j, days: int = 60) -> list[dict]:
    try:
        _table(j)
        rows = j.db.execute("SELECT day, coin, bot, top, groups, history, outcome, outcome_day FROM zone_visits WHERE t >= ? ORDER BY t DESC",
                            (int(j.now()) - days * 86400,)).fetchall()
    except Exception:  # noqa: BLE001
        return []
    return [{"day": d, "coin": c, "bot": b, "top": t, "groups": json.loads(g or "[]"), "history": h, "outcome": o, "outcome_day": od}
            for d, c, b, t, g, h, o, od in rows]


def watch(j) -> dict:
    """Record new entries into support zones; settle open ones with the same rule as review #6."""
    from jarvis.service.reads_watch import _daily
    from src.research import reads as R
    from src.research import zones as Z

    b = board(j)
    _table(j)
    new, settled = [], []
    for r in b["coins"]:
        for z in r["zones"]:
            if z["state"] not in ("INSIDE", "TESTED") or z["side"] == "resistance" or not z.get("recent"):
                continue                                  # only entries from above (a support being tested), as in review #6
            day = z["recent"]["entered"]
            if j.db.execute("SELECT 1 FROM zone_visits WHERE coin=? AND day=? AND abs(bot-?) < 1e-9", (r["coin"], day, z["bot"])).fetchone():
                continue
            j.db.execute("INSERT INTO zone_visits VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                         (uuid.uuid4().hex, int(j.now()), day, r["coin"], z["bot"], z["top"], r["atr"], json.dumps(z["groups"]), z["history"], "OPEN", None))
            new.append({"coin": r["coin"], "day": day, "zone": [z["bot"], z["top"]], "history": z["history"]})
    for vid, c, day, bot, top, atr in j.db.execute("SELECT id, coin, day, bot, top, atr FROM zone_visits WHERE outcome='OPEN'").fetchall():
        D = _daily(j, c)
        S = R.Series(D)
        A = Z.Arr(S)
        k = next((i for i, x in enumerate(D) if datetime.fromtimestamp(x[0], timezone.utc).strftime("%Y-%m-%d") == day), None)
        if k is None:
            continue
        out = Z.touch_outcome(A, k, bot, top, atr, min(len(D), k + Z.OUTCOME_DAYS))
        if out != "OPEN" or len(D) - k >= Z.OUTCOME_DAYS:
            j.db.execute("UPDATE zone_visits SET outcome=?, outcome_day=? WHERE id=?",
                         (out, datetime.fromtimestamp(D[-1][0], timezone.utc).strftime("%Y-%m-%d"), vid))
            settled.append({"coin": c, "day": day, "outcome": out})
    j.db.commit()
    if new or settled:
        _CACHE.clear()
    return {"new": new, "settled": settled}
