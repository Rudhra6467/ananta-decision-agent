"""The new look's four surfaces for crypto (Madhav, 1 Nov 2026: "why no new look for crypto ananta?").

The same shapes the India service returns from jarvis/india/surfaces.py (today, money, proof, people), filled from the crypto
service's own sources: the $500 NDAX book, the dial, the officer's note, the setups scan, the weekly exam, the strategy register and
the reconstruction. Read-only: nothing here places, changes or decides anything. Rule B holds until 14 Dec 2026 (no new crypto
studies, no rule changes), so the screens say what is parked and when it returns, and never suggest a rule change.
The app reads these at /v3/surface/{today,money,proof,people}; India answers the same addresses (views.ROUTES aliases).

10 Nov 2026 (Madhav: "adding bitcoin, eth and sol in home square box in place of nifty 50 and bank nifty. Showing info in points (very
simple words). And other changes to other tabs as well ... do the necessary changes to crypto market Ananta as well"): the same shape the
India screens grew between 4 and 9 Nov. Today: a one-line headline with Details, a box of three live prices (Bitcoin, Ethereum, Solana)
and a box for the account, every card as short points. Proof: an explanation under each top card. Charts: /v3/surface/chart/{BTC,ETH,SOL,
PORTFOLIO} in the shape of India's /v3/chart. Display only: no rule, book or study is touched (Rule B).
"""
from __future__ import annotations

import datetime as dt
import json
import re
import time
from pathlib import Path
from zoneinfo import ZoneInfo

TOR = ZoneInfo("America/Toronto")
UTC = dt.timezone.utc
WINDOW_START = dt.date(2026, 10, 15)          # strategy_status evidence_window (Rule A/B, Madhav 14 Oct)
WINDOW_DAYS = 60
RULE_B_END = dt.date(2026, 12, 14)
REPO = Path(__file__).resolve().parents[2]


def _dw(d) -> str:
    try:
        x = d if isinstance(d, dt.date) else dt.date.fromisoformat(str(d)[:10])
        return x.strftime("%a %-d %b")
    except Exception:  # noqa: BLE001
        return str(d or "")


def _dm(d) -> str:
    """9 Nov: the short day for a chart's corner and its axis ends (the weekday wrapped that row on a phone)."""
    try:
        return dt.date.fromisoformat(str(d)[:10]).strftime("%-d %b")
    except ValueError:
        return str(d or "")


def _cad(v, nd: int = 2) -> str:
    if not isinstance(v, (int, float)):
        return "—"
    return ("−C$" if v < 0 else "C$") + f"{abs(v):,.{nd}f}"


def _pct(p, nd: int = 1) -> str:
    if not isinstance(p, (int, float)):
        return "—"
    return f"{'+' if p > 0 else '−' if p < 0 else ''}{abs(p):.{nd}f}%"


COINS = (("BTC", "Bitcoin"), ("ETH", "Ethereum"), ("SOL", "Solana"))      # the three in Today's first box, and the three charts
COIN_NAME = dict(COINS)


def _usd(v) -> str:
    """A coin's price in US dollars (the feed is Binance spot against USDT): no cents from a thousand up."""
    if not isinstance(v, (int, float)):
        return "—"
    return f"${v:,.0f}" if abs(v) >= 1000 else f"${v:,.2f}"


def _tone(x) -> str | None:
    return None if not isinstance(x, (int, float)) or abs(x) < 0.05 else ("good" if x > 0 else "bad")


def _clock(t: dt.datetime) -> str:
    """7 pm, 2:11 am."""
    return t.strftime("%-I:%M %p").replace(":00", "").lower()


def _start_cad() -> float:
    try:
        from src.research import book500 as B
        return float(B.START_CAD)
    except Exception:  # noqa: BLE001
        return 500.0


def _tidy(s: str) -> str:
    s = str(s or "").strip().rstrip(".").strip()
    return s[:1].upper() + s[1:] if s else s


def _sentences(text: str) -> list[str]:
    """A paragraph as its sentences, each one a point ("5.0%" and "C$439.49" are not sentence ends: a stop counts only before a space)."""
    return [x for x in (_tidy(p) for p in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9(\"“])", str(text or "").strip())) if x]


CODE_WORDS = {"H07": "short dip", "BRK": "breakout", "PULL": "pullback", "RBD": "rebound", "ZONE_TOUCH": "zone touch", "BOLD": "bold book",
              "JARVIS": "brain's book", "READS": "your setups", "M2a-G": "your setup M2", "M2a": "your setup M2"}


def _plain(s: str | None) -> str:
    """No codes on the screen (design principle 4): rule codes become their names, capitals become words."""
    s = str(s or "")
    s = re.sub(r"\b([A-Z0-9]{2,10}) (H07|BRK|PULL|RBD)\b", lambda m: f"{m.group(1)} ({CODE_WORDS[m.group(2)]})", s)
    s = re.sub(r"\((H07|BRK|PULL|RBD)\)", lambda m: f"({CODE_WORDS[m.group(1)]})", s)
    s = re.sub(r"\bThe (H07|BRK|RBD|ZONE_TOUCH) (losses|book|trades)\b", lambda m: f"The {CODE_WORDS[m.group(1)]} {m.group(2)}", s)
    s = re.sub(r"\b(H07|BRK|RBD|ZONE_TOUCH|M2a-G|M2a)\b", lambda m: CODE_WORDS[m.group(1)], s)
    s = s.replace("is still CLOSED", "is still closed").replace("is CLOSED", "is closed").replace("is OPEN", "is open").replace("BTC closed", "Bitcoin closed")
    return s


def _isodates(s: str) -> str:
    return re.sub(r"\b(20\d\d-\d\d-\d\d)\b", lambda m: _dw(m.group(1)), str(s or ""))


def _r1(x):
    return round(x, 1) if isinstance(x, (int, float)) else None


def _why(s) -> str:
    s = _plain(s).removeprefix("invalidation: ")
    return "the dial closed" if s == "dial closed" else s


def _safe(f, *a, default=None):
    try:
        return f(*a)
    except Exception:  # noqa: BLE001
        return default


def _window(today: dt.date | None = None) -> dict:
    today = today or dt.datetime.now(TOR).date()
    day = max(0, min(WINDOW_DAYS, (today - WINDOW_START).days + 1))
    return {"day": day, "of": WINDOW_DAYS, "ends": RULE_B_END.isoformat(),
            "words": f"Day {day} of {WINDOW_DAYS} · ends {_dw(RULE_B_END)}"}


def _next_close_words(now: dt.datetime) -> str:
    """Crypto's daily close is 00:00 UTC; say it in Toronto time."""
    nxt = (now.astimezone(UTC) + dt.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return nxt.astimezone(TOR).strftime("%-I:%M %p Toronto").replace(":00 ", " ").lower().replace("toronto", "Toronto")


def _book(j) -> dict:
    from jarvis.service import ndax_book
    return _safe(ndax_book.status, j, default={}) or {}


def _dial(j) -> dict:
    from jarvis.service import exposure
    return _safe(exposure.state, j, default={}) or {}


def _positions(b: dict) -> list[dict]:
    rows = []
    value = b.get("value_cad") or 0
    for coin, p in (b.get("positions") or {}).items():
        qty, last, paid = p.get("qty") or 0, p.get("last"), p.get("paid")
        v = qty * last if isinstance(last, (int, float)) else None
        pnl = (100 * (v / paid - 1)) if v and paid else None
        rows.append({"symbol": coin, "value": v, "value_words": _cad(v), "weight_pct": round(100 * v / value, 1) if v and value else None,
                     "weight_of": "of book", "pnl_pct": round(pnl, 1) if pnl is not None else None, "paid": paid, "since": p.get("day"),
                     "rule": p.get("rule"), "stop": p.get("stop_on_ndax"), "sleeve": (p.get("sleeve") or "").lower(),
                     "grade": None, "action": "hold", "chip": f"{CODE_WORDS.get(p.get('rule'), 'held')} · safety stop {_cad(p.get('stop_on_ndax'), 0 if (p.get('stop_on_ndax') or 0) >= 100 else 2)}"})
    rows.sort(key=lambda r: -(r["value"] or 0))
    return rows


def _brake(b: dict, now: dt.datetime) -> str | None:
    br = b.get("brakes") or {}
    until = br.get("block_until")
    if br.get("paused"):
        return "the book is paused"
    if isinstance(until, (int, float)) and until > now.timestamp():
        u = dt.datetime.fromtimestamp(until, TOR)
        when = u.strftime("%-I %p").lower() + (" today" if u.date() == now.date() else " tomorrow" if u.date() == now.date() + dt.timedelta(days=1) else u.strftime(", %a %-d %b"))
        return "a loss brake blocks new buys until " + when
    return None


def _officer_note(j) -> dict | None:
    from jarvis.service import officer
    notes = _safe(officer.latest, j, 1, default=[]) or []
    if not notes:
        return None
    n = notes[0]
    text = re.sub(r"^(Good (morning|evening|afternoon),\s*)?[Ss]ir,\s*", "", str(n.get("note") or "")).strip()  # the screen never says sir
    return {"day": n.get("day"), "text": text[:1].upper() + text[1:] if text else ""}


def _plan_parts(line: str) -> dict:
    """discipline.plan_line's one long line, cut at its own labels."""
    parts: dict[str, str] = {}
    keys = ["Account", "Bold", "Officer", "Setups", "Strongest", "Held back", "Touched", "View"]
    pat = re.compile(r"(?:^|(?<=\.)\s)(" + "|".join(re.escape(k) for k in keys) + r")\b:?\s*")
    hits = list(pat.finditer(line or ""))
    if hits:
        parts["dial"] = line[:hits[0].start()].strip()
    for i, m in enumerate(hits):
        end = hits[i + 1].start() if i + 1 < len(hits) else len(line)
        parts[m.group(1)] = (m.group(0).strip() + " " + line[m.end():end].strip()).strip() if m.group(1) in ("Strongest", "Held back", "Touched") else line[m.end():end].strip()
    return parts


def _dial_numbers(dial: dict) -> dict:
    """The dial's own three lines as numbers: Bitcoin's close and its two averages (exposure.state writes them as words)."""
    out: dict = {}
    for w in dial.get("why") or []:
        m = re.search(r"closed \S+ at ([\d,]+(?:\.\d+)?)", str(w))
        if m:
            out["close"] = float(m.group(1).replace(",", ""))
        m = re.search(r"(above|below) its (50|200)-day average \(([\d,]+(?:\.\d+)?)\)", str(w))
        if m:
            out["avg" + m.group(2)], out["side" + m.group(2)] = float(m.group(3).replace(",", "")), m.group(1)
    return out


def _last_close(dial: dict) -> tuple[str | None, dt.datetime | None]:
    """The day of the last daily candle and the moment it closed (00:00 UTC of the day after), in Toronto time."""
    try:
        d = dt.date.fromisoformat(str(dial.get("as_of_day"))[:10])
    except ValueError:
        return None, None
    return d.isoformat(), (dt.datetime(d.year, d.month, d.day, tzinfo=UTC) + dt.timedelta(days=1)).astimezone(TOR)


def _coin_pages(j, dial: dict, now: dt.datetime, closes: dict | None = None) -> list[dict]:
    """Today's first box: Bitcoin, Ethereum and Solana, one page each (swiped inside the box). The live price (at most 10 minutes old,
    feed.prices) with its move since the last daily close; with no live price, that close and its day. US dollars."""
    from jarvis.service import feed
    live = _safe(feed.prices, j, default={}) or {}
    pulled = getattr(live, "t", None) or {}
    closes = closes if closes is not None else (_safe(feed.last_closes, j, default={}) or {})
    day, close_at = _last_close(dial)
    since = ""
    if close_at:
        since = f"since {_clock(close_at)}" if (now - close_at) < dt.timedelta(hours=24, minutes=30) else f"since {_dw(day)}"
    pages = []
    for coin, name in COINS:
        px, last = live.get(coin), closes.get(coin)
        if isinstance(px, (int, float)) and px > 0:
            chg = 100 * (px / last - 1) if isinstance(last, (int, float)) and last > 0 else None
            at = dt.datetime.fromtimestamp(pulled[coin], TOR) if isinstance(pulled.get(coin), (int, float)) else now
            pages.append({"label": name, "value": _usd(px), "tone": _tone(chg), "focus": "dial", "coin": coin,
                          "sub": f"{_pct(chg)} {since}".strip() if chg is not None else "", "sub2": f"Live · {_clock(at)}"})
        elif isinstance(last, (int, float)) and last > 0:
            pages.append({"label": name, "value": _usd(last), "focus": "dial", "coin": coin,
                          "sub": f"{_dw(day)} close" if day else "last daily close", "sub2": "no live price now"})
        else:
            pages.append({"label": name, "value": "—", "focus": "dial", "coin": coin, "sub": "no price on file"})
    return pages


def _account_pages(b: dict, pos: list[dict]) -> list[dict]:
    """Today's second box: the account (its value and its change from the C$500 it began with), then the coins against the cash."""
    value, cash, ret = b.get("value_cad"), b.get("cash_cad"), b.get("return_pct")
    n = len(pos)
    coins = sum(p["value"] or 0 for p in pos)
    names = [p["symbol"] for p in pos]
    p1 = {"label": "Your account", "value": _cad(value, 0), "tone": _tone(ret), "focus": "holdings",
          "sub": f"{_pct(ret)} from {_cad(_start_cad(), 0)}" if isinstance(ret, (int, float)) else "starts at the next close",
          "sub2": ("All in cash" if not n else f"{n} coin{'s' if n != 1 else ''} · {_cad(cash, 0)} cash") if isinstance(value, (int, float)) else ""}
    p2 = {"label": "Coins held", "value": _cad(coins, 0), "focus": "holdings",
          "sub": "No coins held" if not n else (" and ".join(names) if n <= 2 else f"{n} coins"),
          "sub2": f"Cash {_cad(cash, 0)}" if isinstance(cash, (int, float)) else ""}
    return [p1, p2]


def book_gap(j, b: dict) -> list[dict]:
    """Coins the $500 book's own trade list says it bought and never sold, yet its holdings do not carry. Read-only: every fill against
    the holdings; nothing is changed. Found 10 Nov 2026 while building these screens: 0.008315 ETH bought on 26 Oct (an edge trade) left
    the holdings on 28 Oct when the core bought ETH (ndax_book's buy keeps one position a coin), so the book's value leaves it out. The
    repair is Madhav's decision (the file is pinned); until then every screen that shows the value says so."""
    net: dict[str, float] = {}
    buys: dict[str, list[tuple]] = {}
    for t, coin, side, qty, px, fee in j.db.execute("SELECT t, coin, side, qty, px, fee FROM book500_fills ORDER BY t"):
        net[coin] = net.get(coin, 0.0) + (qty if side == "BUY" else -qty)
        if side == "BUY":
            buys.setdefault(coin, []).append((t, qty, qty * px + (fee or 0)))
    held = {c: float(p.get("qty") or 0) for c, p in (b.get("positions") or {}).items()}
    out = []
    for coin, q in sorted(net.items()):
        miss = q - held.get(coin, 0.0)
        if miss <= 1e-9:
            continue
        same = [x for x in buys.get(coin, []) if abs(x[1] - miss) <= 1e-9]      # the one buy that is missing, when it is one buy
        row = {"coin": coin, "qty": miss, "day": None, "paid_cad": None}
        if same:
            row["day"] = dt.datetime.fromtimestamp(same[-1][0], UTC).strftime("%Y-%m-%d")
            row["paid_cad"] = round(same[-1][2], 2)
        out.append(row)
    return out


def gap_words(gap: list[dict]) -> str | None:
    if not gap:
        return None
    bits = [f"{g['qty']:.4g} {g['coin']}" + (f" bought on {_dw(g['day'])} for {_cad(g['paid_cad'])}" if g.get("day") else "") for g in gap]
    return "Under check: " + "; ".join(bits) + f" {'is' if len(gap) == 1 else 'are'} missing from the book's holdings, so the value shown is too low."


def _dial_points(dial: dict, closes: dict, now: dt.datetime) -> list[str]:
    n = _dial_numbers(dial)
    if not n.get("close"):
        return [_tidy(dial.get("note") or "The dial has no reading yet")]
    gap = lambda k: 100 * (n["close"] / n[k] - 1) if n.get(k) else None   # noqa: E731
    g50, g200 = gap("avg50"), gap("avg200")
    pts = [f"Bitcoin closed at {_usd(n['close'])} on {_dw(dial.get('as_of_day'))}"]
    if g50 is not None and g200 is not None:
        if (dial.get("dial") or 0) > 0:
            pts.append(f"That is {abs(g50):.1f}% above its 50-day average ({_usd(n['avg50'])}) and {abs(g200):.1f}% above its 200-day ({_usd(n['avg200'])}), so buying is on")
            pts.append("Buying turns off when Bitcoin closes below either average")
        elif g50 < 0 and g200 < 0:
            pts.append(f"That is {abs(g50):.1f}% below its 50-day average ({_usd(n['avg50'])}) and {abs(g200):.1f}% below its 200-day ({_usd(n['avg200'])}), so buying is off")
            pts.append("Buying turns on when Bitcoin closes above both averages")
        else:
            lo, hi = ("50", "200") if g50 < 0 else ("200", "50")
            g_hi = gap("avg" + hi)
            pts.append(f"That is {abs(gap('avg' + lo)):.1f}% below its {lo}-day average ({_usd(n['avg' + lo])}), so buying is off")
            pts.append(f"It is {abs(g_hi):.1f}% {'above' if g_hi >= 0 else 'below'} its {hi}-day average ({_usd(n['avg' + hi])})")
            pts.append("Buying turns on when Bitcoin closes above both averages")
    others = [(name, closes[c]) for c, name in COINS[1:] if isinstance(closes.get(c), (int, float))]
    if others:
        pts.append(" · ".join(f"{name} {'closed ' if i == 0 else ''}at {_usd(px)}" for i, (name, px) in enumerate(others)))
    pts.append(f"Next check at the daily close, {_next_close_words(now)}")
    pts.append("Prices are in US dollars; your account is in Canadian dollars")
    return pts


def _account_points(j, b: dict, pos: list[dict], brake: str | None, gap: list[dict]) -> list[str]:
    from jarvis.service import exposure
    value, cash, ret = b.get("value_cad"), b.get("cash_cad"), b.get("return_pct")
    if not isinstance(value, (int, float)):
        return ["The $500 book starts at the next daily close"]
    coins = sum(p["value"] or 0 for p in pos)
    pts = [f"{_cad(value)}, all in cash: no coins held" if not pos
           else f"{_cad(value)}: {_cad(coins)} in {len(pos)} coin{'s' if len(pos) != 1 else ''}, {_cad(cash)} in cash"]
    if gap:                                                 # said second, so it shows without "Show more": the value above is not the whole story
        pts.append(gap_words(gap).rstrip("."))
    if isinstance(ret, (int, float)):
        pts.append(f"{'Down' if ret < 0 else 'Up'} {abs(ret):.1f}% since it started with {_cad(_start_cad(), 0)} on {_dw(b.get('started'))}")
    for p in pos:
        stop = p.get("stop")
        pts.append(f"{COIN_NAME.get(p['symbol'], p['symbol'])}: {_cad(p['value'])}" + (f", {_pct(p['pnl_pct'])} on cost" if p.get("pnl_pct") is not None else "")
                   + (f" · stop at {_cad(stop, 0 if stop >= 100 else 2)}" if isinstance(stop, (int, float)) else ""))
    bk = {x.get("book"): x for x in ((_safe(exposure.books, j, default={}) or {}).get("books") or [])}
    hold, hurdle = (bk.get("HOLD") or {}).get("return_pct"), (bk.get("GATE50") or {}).get("return_pct")
    if isinstance(hold, (int, float)):
        pts.append(f"Bitcoin just held since {_dw(exposure.START)}: {_pct(hold)}"
                   + (f" · the hurdle to beat: {_pct(hurdle)}" if isinstance(hurdle, (int, float)) else ""))
    closed = b.get("closed") or []
    total = int((b.get("graduation") or {}).get("closed_trades") or len(closed))
    if total and total <= len(closed):
        won = sum(1 for c in closed if (c.get("pnl_cad") or 0) > 0)
        pts.append(f"{total} trade{'s' if total != 1 else ''} closed so far: {won} won, {total - won} lost")
    elif total:
        pts.append(f"{total} trades closed so far")
    if brake:
        pts.append(_tidy(brake))
    return pts


def _setup_points(parts: dict) -> list[str]:
    """The setups scan, in short points: how many coins, the best, what is held back, what touched its trigger, the strongest."""
    pts = []
    s = str(parts.get("Setups") or "")
    m = re.match(r"Scanned (\d+) coins: (\d+) setups? fired, (\d+) one step away\.?\s*", s)
    if m:
        pts.append(f"{m.group(1)} coins checked: {m.group(2)} show a buy setup, {m.group(3)} are one step away")
        s = s[m.end():]
    pts += [_plain(x) for x in _sentences(s)]
    hb = str(parts.get("Held back") or "")
    if hb.startswith("Held back by the closed dial") and ": " in hb:
        names = [re.sub(r"\s+(H07|BRK|PULL|RBD|ZONE_TOUCH)$", "", x.strip().rstrip(".")) for x in hb.rsplit(": ", 1)[-1].split(",")]
        pts.append("Held back while buying is off: " + ", ".join(x for x in names if x))
    elif hb:
        pts.append(_tidy(_plain(hb)))
    for k in ("Touched", "Strongest"):
        if parts.get(k):
            pts.append(_tidy(_plain(parts[k])))
    return [p for p in pts if p]


def _did_points(b: dict, since: dt.datetime | None) -> list[str]:
    """What the $500 book bought and sold at the last daily close (its fills since that close), each sale with its result."""
    if not since:
        return []
    day = since.astimezone(UTC).strftime("%Y-%m-%d")
    pnl = {c.get("coin"): c for c in (b.get("closed") or []) if c.get("out") == day}
    pts = []
    for f in sorted((x for x in (b.get("recent_fills") or []) if (x.get("t") or 0) >= since.timestamp()), key=lambda x: x.get("t") or 0):
        coin, amt = COIN_NAME.get(f.get("coin"), f.get("coin")), _cad((f.get("qty") or 0) * (f.get("px") or 0))
        if f.get("side") == "BUY":
            pts.append(f"Bought {coin} for {amt}")
        else:
            c = pnl.get(f.get("coin")) or {}
            pts.append(f"Sold {coin} for {amt} ({_why(f.get('why'))})" + (f": {_cad(c['pnl_cad'])}" if isinstance(c.get("pnl_cad"), (int, float)) else ""))
    return pts


def _running(h: dict) -> dict:
    """The status line, as India's: the 15-minute self-check first (a high item is said instead of "Everything is running"), then the
    2-minute health check with how long ago it last ran."""
    try:
        from jarvis import selfcheck
        c = selfcheck.check("crypto")
        top = [x for x in c.get("items") or [] if x.get("severity") == "high" and x.get("source") != "self-check"]
        if top and c.get("at"):
            what = selfcheck.spoken(str(top[0]["what"]))
            return {"ok": False, "words": what[:1].upper() + what[1:120] + ("…" if len(what) > 120 else ""),
                    "checked": f"checked {int((time.time() - float(c['at'])) // 60)} min ago", "more": len(top) - 1}
    except Exception:  # noqa: BLE001
        pass
    ago = h.get("last_check_s_ago")
    old = isinstance(ago, (int, float)) and ago > 3600
    down = len(h.get("down") or [])
    return {"ok": bool(h.get("all_ok")),
            "words": ("Everything was running at the last check" if old else "Everything is running") if h.get("all_ok") else f"{down} part{'s' if down != 1 else ''} down",
            "checked": (f"checked {int(ago // 60)} min ago" if ago >= 120 else "checked just now") if isinstance(ago, (int, float)) else "checked every 2 min"}


def headline(dial: dict, pos: list[dict], brake: str | None) -> str:
    """One line (India's "No change today"); the full sentence and where it came from open under Details."""
    if dial.get("dial") is None:
        return "No reading yet"
    n = len(pos)
    held = f"{n} coin{'s' if n != 1 else ''} held"
    if dial["dial"] <= 0:
        return f"No new buys, {held}" if n else "No new buys: all in cash"
    if brake:
        return "Buys paused by a loss brake"
    return f"Buying is on, {held}" if n else "Buying is on: all in cash"


def _decision(dial: dict, b: dict, pos: list[dict], brake: str | None) -> str:
    held = " and ".join(COIN_NAME.get(p["symbol"], p["symbol"]) for p in pos)
    if (dial.get("dial") or 0) <= 0:
        s = "Buying is off (the dial is closed), so nothing new is bought and the cash waits."
    else:
        s = "Buying is on (the dial is open): the book holds Bitcoin (40%) and Ethereum (20%) and may take small trades by the rules that passed."
        if brake:
            s += f" For now {brake}."
    if held:
        s += f" {held} {'stays' if len(pos) == 1 else 'stay'} held until {'its' if len(pos) == 1 else 'their'} own rule sells."
    return s


def today(j) -> dict:
    from jarvis.service import discipline, feed, health, waiting
    now = dt.datetime.now(TOR)
    b, dial = _book(j), _dial(j)
    pos = _positions(b)
    brake = _brake(b, now)
    plan = _safe(discipline.plan_line, j, default={}) or {}
    parts = _plan_parts(plan.get("line") or "")
    h = _safe(health.status, j, default={}) or {}
    w = _safe(waiting.collect, j, default={}) or {}
    why = dial.get("why") or []
    nums = _dial_numbers(dial)
    closes = _safe(feed.last_closes, j, default={}) or {}
    gap = _safe(book_gap, j, b, default=[]) or []
    is_open = (dial.get("dial") or 0) > 0
    # 10 Nov (Madhav): every card is short points in simple words; the screen shows two and "Show more" opens the rest. "text" stays for
    # older app builds. Each card's kind is unique: the app keys on it.
    cards = []
    pts = _dial_points(dial, closes, now)
    cards.append({"kind": "market", "label": "The market · buying is " + ("on" if is_open else "off"), "text": " ".join(p + "." for p in pts[:2]), "points": pts, "accent": True})
    pts = _account_points(j, b, pos, brake, gap)
    cards.append({"kind": "account", "label": "Your account · the $500 book", "text": " ".join(p + "." for p in pts[:2]), "points": pts})
    pts = _setup_points(parts)
    if pts:
        cards.append({"kind": "setups", "label": "Coins being watched", "text": " ".join(p + "." for p in pts[:2]), "points": pts,
                      "foot": "Held back means seen and noted. Nothing is bought while buying is off."})
    fails = [_tidy(c.get("words")) for c in (plan.get("checks") or []) if c.get("state") == "FAIL" and c.get("words")]
    if fails:
        cards.append({"kind": "checks", "label": "Checks that fail", "text": "; ".join(fails) + ".", "points": fails,
                      "foot": "Parked to the 14 Dec review (Rule B: no crypto rule changes before then)."})
    note = _officer_note(j)
    if note and note["text"]:
        pts = [_plain(x) for x in _sentences(note["text"])]
        late = [r for r in (_safe(_repairs, j, default=[]) or []) if str(r.get("day") or "") >= str(note["day"])]
        if late and isinstance(b.get("value_cad"), (int, float)):
            pts.insert(0, f"Corrected after this note was written: the account is {_cad(b['value_cad'])} ({_pct(b.get('return_pct'))}), not the figure in the note")
        cards.append({"kind": "note", "label": f"Ananta's nightly note · {_dw(note['day'])}", "text": _plain(note["text"]), "points": pts})
    day, close_at = _last_close(dial)
    did = _did_points(b, close_at)
    evening = {"label": f"What the $500 book did at the {_dw(day)} close", "text": "; ".join(did), "points": did} if did else None
    win = _window(now.date())
    tiles = [{"id": "market", "pages": _coin_pages(j, dial, now, closes)}, {"id": "account", "pages": _account_pages(b, pos)}]
    state = "open" if is_open else "closed"
    return {"ready": True, "market": "crypto", "now_words": now.strftime("%A %-d %b, %-I:%M %p Toronto").replace("AM", "am").replace("PM", "pm"),
            "when": f"next decision at the daily close, {_next_close_words(now)}",
            "headline": headline(dial, pos, brake),
            "decision": _decision(dial, b, pos, brake),
            "decision_source": f"From the daily close {_dw(dial.get('as_of_day'))} · " + ", ".join(why[1:3]) + (f" · {brake}" if brake else "") + " · nothing is placed, paper only",
            "tiles": tiles,
            # older app builds read two single numbers
            "numbers": [{"label": "Bitcoin · " + _dw(dial.get("as_of_day")), "value": f"{nums['close']:,.0f}" if nums.get("close") else "—", "focus": "dial",
                         "sub": "dial " + state},
                        {"label": "Your account", "value": _cad(b.get("value_cad"), 0), "focus": "holdings",
                         "sub": f"{_pct(b.get('return_pct'))} since {_dw(b.get('started'))} · {len(pos)} coin{'s' if len(pos) != 1 else ''}"}],
            "waiting": {"count": w.get("count") or 0, "words": w.get("line")},
            "running": _running(h),
            "cards": cards, "evening": evening, "clock": f"Evidence window: {win['words']}. Until then no new crypto strategy and no rule change without your yes (Rule B).",
            "suggested": ([f"Why is the dial {state}?", f"How are {' and '.join(p['symbol'] for p in pos)} doing?", "What happens on 14 Dec?"] if pos
                          else [f"Why is the dial {state}?", "What would reopen the dial?" if not is_open else "What would close the dial?", "What happens on 14 Dec?"]),
            "next_view": None, "paper": True}


_LFL: dict = {"t": 0.0, "words": ""}


def like_for_like(j) -> str:
    """One honest sentence beside the yardsticks (the outsider's review, 10 Nov 2026): Bitcoin bought with the whole C$500 at the book's own
    first Bitcoin price on NDAX (its ask, fee paid) and just held, valued at NDAX's bid now; and the share of the book that was in coins
    on an average recorded night. A second look, not a new yardstick: what counts as beating the hurdle is for the 14 Dec review.
    Kept 15 minutes; the NDAX quote gets 4 seconds and the sentence is left out when it does not come."""
    if time.time() - _LFL["t"] < 900:
        return _LFL["words"]
    import requests
    from jarvis.service import ndax_book
    from src.research import book500 as B
    words = ""
    first = j.db.execute("SELECT px FROM book500_fills WHERE coin='BTC' AND side='BUY' ORDER BY t LIMIT 1").fetchone()
    get = lambda url: requests.get(url, timeout=4).json()   # noqa: E731
    q = ndax_book.quote("BTC", ndax_book.instruments(get), get) if first else None
    if first and q:
        held = 100 * (q["bid"] / (first[0] * (1 + B.NDAX_FEE)) - 1)
        words = f"Like for like (Bitcoin bought at the book's first price on NDAX and just held, in Canadian dollars): {_pct(held)}. "
        share = []
        for (facts,) in j.db.execute("SELECT facts FROM officer_notes ORDER BY day"):
            try:
                a = (json.loads(facts or "{}").get("account") or {})
                if a.get("value_cad"):
                    share.append(1 - float(a.get("cash_cad") or 0) / float(a["value_cad"]))
            except (ValueError, TypeError):
                continue
        if share:
            words += f"The book had about {100 * sum(share) / len(share):.0f}% in coins on an average night. "
    _LFL.update(t=time.time(), words=words)
    return words


def money(j) -> dict:
    from jarvis.service import exposure
    now = dt.datetime.now(TOR)
    b, dial = _book(j), _dial(j)
    pos = _positions(b)
    coins = sum(p["value"] or 0 for p in pos)
    bk = {x.get("book"): x for x in ((_safe(exposure.books, j, default={}) or {}).get("books") or [])}
    win = _window(now.date())
    books = [{"id": "managed", "label": "The $500 book", "ret_pct": _r1(b.get("return_pct"))},
             {"id": "index", "label": "Bitcoin, just held", "ret_pct": _r1((bk.get("HOLD") or {}).get("return_pct"))},
             {"id": "twin", "label": "The dial's hurdle", "ret_pct": _r1((bk.get("GATE50") or {}).get("return_pct"))}]
    cp = b.get("core_plan") or {}
    closed_dial = (dial.get("dial") or 0) <= 0
    brake = _brake(b, now)
    brief = (("Buying is off. The core (the Bitcoin and Ethereum part) is in cash until Bitcoin closes above both its 50-day and 200-day averages."
              if closed_dial else f"Buying is on. The core (the Bitcoin and Ethereum part) aims for {cp.get('words') or 'its targets'}.")
             + (f" {brake[0].upper() + brake[1:]}." if brake else "")
             + (" The coins held stay until their own rules sell." if pos else ""))
    under = gap_words(_safe(book_gap, j, b, default=[]) or [])
    closed = [{"coin": c.get("coin"), "in": _dw(c.get("in")), "out": _dw(c.get("out")), "pnl_words": _cad(c.get("pnl_cad")), "pnl": c.get("pnl_cad"),
               "pct": c.get("pct"), "why": _why(c.get("why"))} for c in (b.get("closed") or [])][::-1]
    return {"ready": True, "paper": True, "market": "crypto", "ccy": "CAD",
            "value_cad": b.get("value_cad"), "value_words": _cad(b.get("value_cad")),
            "sub_words": f"NDAX bid · {_dw(now.date())} · {_cad(coins)} in coins · {_cad(b.get('cash_cad'))} cash · {_pct(b.get('return_pct'))} since {_dw(b.get('started'))}",
            "books_title": "The book and its yardsticks",
            "books": books, "clock": {"words": win["words"], "sessions": win["day"], "of": WINDOW_DAYS},
            "books_note": ("Bitcoin-held and the hurdle are paper books on Bitcoin's daily candles since 10 Oct, in US dollars, fully in Bitcoin; the $500 book began "
                           "11 Oct on NDAX in Canadian dollars. " + (_safe(like_for_like, j, default="") or "") + "Nothing is read into the gap before 14 Dec."),
            "books_ask": "Explain the book and its yardsticks in detail: what the $500 book holds and why, what 'Bitcoin, just held' and the dial's hurdle are, what the numbers mean today, what the 60-day evidence window is for, and what would tell us the book is working.",
            "plan": {"title": "At the next daily close", "tag": "dial closed" if closed_dial else "dial open", "brief": brief,
                     "asks": [{"label": "What would reopen it", "q": "What exactly would reopen the dial, and how close is Bitcoin to it?"},
                              {"label": "Ask about it", "q": "What will the $500 book do at the next daily close, and why?"}]},
            "managed": None,
            "holdings_title": "Your coins", "holdings_head": ["Coin · value · on cost", "Rule · safety stop"],
            "holdings": pos, "holdings_note": ("Paper, at real NDAX prices. Each small trade is sized for a loss of about 0.5% of the book; a real loss can be larger. "
                                              "The safety stop shown is a far line for real trading: on paper a trade ends by its own rule.") + (f" {under}" if under else ""),
            "under_check": under,
            "holdings_empty": "No coins held: the whole book is cash.",
            "dial_block": {"state": "closed" if closed_dial else "open", "words": _plain(str(dial.get("dial_words") or "").replace("CLOSED", "Closed").replace("OPEN", "Open")), "why": [_isodates(x) for x in dial.get("why") or []], "as_of": _dw(dial.get("as_of_day")),
                           "brake": brake, "rule": "Buying is allowed only while Bitcoin closes above both its 50-day and 200-day averages.",
                           "closed": closed, "graduation": None},
            "options_book": None}


FINDING_WORDS = {"MISS_PATTERN": ("repeated miss", "repeated misses"), "WAIT_ARRIVED": ("wait that came true (woke the brain)", "waits that came true (each woke the brain)"),   # 6 Nov: older cards only; new cards count wakes apart
                 "GAVE_BACK": ("gain given back", "gains given back"), "BLEED": ("book losing steadily", "books losing steadily"),
                 "SELECTION": ("selection slip", "selection slips")}


def _exam() -> dict | None:
    p = REPO / "docs" / "repair_shop" / "exam" / "latest.json"
    try:
        e = json.loads(p.read_text())
    except Exception:  # noqa: BLE001
        return None
    ok = all(e.get(k) for k in ("knows_pass", "unknowns_pass", "why_pass", "consistency_pass")) and e.get("numbers_pass", True)   # 10 Nov: the money questions count
    return {"grade": "Pass" if ok else "Fail", "day": e.get("day"),
            "words": f"{e.get('known')}/{e.get('known_of')} facts · {e.get('unknown')}/{e.get('unknown_of')} unknowns · {e.get('why')}/{e.get('why_of')} whys"
                     + (f" · {e.get('numbers')}/{e.get('numbers_of')} numbers" if e.get("numbers_of") else "") + f" · {_dw(e.get('day'))}"}


def _pace(done: int, need: int, started, today: dt.date) -> str:
    """When a count reaches its mark at the pace so far ("about Mar 2027 at this pace")."""
    try:
        days = (today - dt.date.fromisoformat(str(started)[:10])).days
    except ValueError:
        return ""
    if done <= 0 or days <= 0 or done >= need:
        return ""
    return "about " + (today + dt.timedelta(days=round((need - done) * days / done))).strftime("%b %Y") + " at this pace"


def proof(j) -> dict:
    from jarvis.service import missed, reconstruct, strategy_status
    now = dt.datetime.now(TOR)
    reg = _safe(strategy_status.load, default={}) or {}
    st = reg.get("strategies") or {}
    st = st if isinstance(st, dict) else {x.get("id"): x for x in st}
    count: dict[str, int] = {}
    for v in st.values():
        count[v.get("status") or "?"] = count.get(v.get("status") or "?", 0) + 1
    b = _book(j)
    g = b.get("graduation") or {}
    win = _window(now.date())
    clocks = [{"name": "The evidence window (Rule A and B)", "done": win["day"], "need": WINDOW_DAYS, "finish_words": _dw(RULE_B_END), "complete": win["day"] >= WINDOW_DAYS},
              {"name": "Round trips in the $500 book", "done": g.get("closed_trades") or 0, "need": 50, "finish_words": _pace(g.get("closed_trades") or 0, 50, b.get("started"), now.date()),
               "complete": (g.get("closed_trades") or 0) >= 50}]
    from jarvis.service import officer as _officer

    cn = _safe(_officer.clean_nights, j, default={}) or {}
    if cn:
        left = max(0, cn["need"] - cn["in_a_row"])
        brk = cn.get("last_break")
        clocks.append({"name": "Clean nights in a row (book, note and candle agree)", "done": cn["in_a_row"], "need": cn["need"],
                       "finish_words": ("done" if not left else f"{left} more to go; counted from {_dm(cn['since'])}"
                                        + (f". The count began again after {_dm(brk['day'])}" if brk else "")),
                       "complete": not left})
    m = _safe(missed.recent, j, 7, default={}) or {}
    c, moves = m.get("counts") or {}, m.get("moves") or []
    n_big = sum(c.get(k, 0) for k in ("CAUGHT", "SEEN", "MISSED"))
    on_purpose = sum(1 for x in moves if x.get("miss_class") == "INTENTIONAL")
    missed_words = (f"In 7 days your ten main coins made {n_big} big move{'s' if n_big != 1 else ''}. A paper book was in {c.get('CAUGHT', 0)} of them "
                    f"({c.get('CAUGHT_TRADE_OK', 0)} by a book allowed to trade, the rest by measuring books only); {c.get('SEEN', 0)} were seen and not traded; "
                    f"{c.get('MISSED', 0)} missed." + (f" {on_purpose} were held back on purpose while buying was off." if on_purpose else "")) if c else None
    r = _safe(reconstruct.latest, j, default={}) or {}
    kinds: dict[str, int] = {}
    for f in r.get("findings") or []:
        kinds[f.get("kind")] = kinds.get(f.get("kind"), 0) + 1
    found = ", ".join(f"{n} {FINDING_WORDS.get(k, (k.lower(), k.lower()))[0 if n == 1 else 1]}" for k, n in kinds.items())
    last_night = (f"{_dw(r.get('day'))}: {(r.get('market') or {}).get('dial_words') or ''}. "
                  + (f"Found {found}. Each is noted on the card; nothing changes a rule before the 14 Dec review." if found
                     else "Found nothing new. Nothing changes a rule before the 14 Dec review.")) if r else None
    return {"ready": True, "paper": True, "market": "crypto",
            "studies": {"label": "Strategies ›", "big": len(st), "run": len(st),
                        "sub": f"{count.get('ACTIVE', 0)} active · {count.get('PARKED', 0)} parked · {count.get('EVIDENCE', 0)} measured only",
                        "ask": STRAT_Q, "explain": _safe(strategies_explain, reg, win)},
            "exam": {**(_exam() or {"grade": None, "words": None}), "label": "Weekly exam ›",
                     "ask": EXAM_Q, "explain": _safe(exam_explain)},
            "clocks": clocks, "clocks_ask": "Explain every crypto clock in detail: the 60-day evidence window, the round trips the $500 book needs, the graduation gates, where each stands and what would count as a pass.",
            "missed": {"words": missed_words, "day": "last 7 days"} if missed_words else None,
            "last_night": {"words": last_night} if last_night else None,
            "links": [{"label": "The repair board", "route": "/flags"}, {"label": "What we missed", "route": "/missed"}, {"label": "The evidence, live", "route": "/reconstruction"}]}


def people(j, is_owner: bool = True) -> dict:
    rows = [{"id": "madhav", "name": "Madhav", "relation": "owner", "can": "decides everything", "voice": None}]
    if is_owner:
        pp = _safe(j.people, default={}) or {}
        vs = pp.get("visitors") or []
        for v in [x for x in vs if not x.get("expired")]:
            rows.append({"id": "v" + str(len(rows)), "name": v.get("name") or "Guest", "relation": "invited",
                         "can": "can ask; can't approve or change anything", "voice": None})
        gone = sum(1 for x in vs if x.get("expired"))
        if gone:
            rows.append({"id": "past", "name": "Past guests", "relation": f"{gone} invite{'s' if gone != 1 else ''} expired", "can": "no access now", "voice": None})
    return {"ready": True, "people": rows, "rule": "Only Madhav decides; everyone else can ask. A guest is greeted by name and never 'sir'.",
            "invite": "An invited person gets their own paper book and Ananta's tour in its own voice; they never see your account."}


# ------------------------------------------------------------------------------------------ 10 Nov 2026 (Madhav): explanations and charts
# The same two things India's Proof and Today got on 7 Nov: each top card of Proof opens an explanation written from the facts on file
# (so it changes when they do), with an Ask Ananta button; and each box on Today opens a chart.

STRAT_Q = ("Explain the strategies on record: which are active, which are parked and why, which are only measured, what the one measured "
           "edge is, and what Rule B means until 14 Dec.")
EXAM_Q = "Explain the weekly exam: what it asks, how it is graded, what it found this week, and what is still open."


def _short_name(name) -> str:
    """A strategy's name without its brackets and its code: 'Short dip trade (H07)' -> 'short dip trade'."""
    s = re.split(r"\s*[(:,]", str(name or ""), maxsplit=1)[0].strip()
    s = re.sub(r"^Madhav's\b", "your", s)
    return s if s.startswith(("The $", "your")) else s[:1].lower() + s[1:]


def _list(xs: list[str], n: int = 4) -> str:
    xs = [x for x in xs if x]
    if len(xs) > n:
        return ", ".join(xs[:n]) + f" and {len(xs) - n} more"
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1] if xs else ""


def strategies_explain(reg: dict, win: dict) -> dict:
    """The 'Strategies' card's explanation, from the strategy register (docs/knowledge/strategy_status.json): what a strategy is, how
    many are in each state, which trade, which are switched off, the one measured edge, and what Rule B holds still."""
    st = reg.get("strategies") or {}
    st = st if isinstance(st, dict) else {x.get("id"): x for x in st}
    by: dict[str, list[dict]] = {}
    for v in st.values():
        by.setdefault(v.get("status") or "?", []).append(v)
    n = lambda k: len(by.get(k) or [])   # noqa: E731
    counts = [f"{n('ACTIVE')} trade and count" if n("ACTIVE") else "", f"{n('UNDER_REVIEW')} {'is' if n('UNDER_REVIEW') == 1 else 'are'} under a review" if n("UNDER_REVIEW") else "",
              f"{n('EVIDENCE')} only measure in the background" if n("EVIDENCE") else "", f"{n('PARKED')} {'is' if n('PARKED') == 1 else 'are'} switched off" if n("PARKED") else "",
              f"{n('RETIRED')} {'is' if n('RETIRED') == 1 else 'are'} retired" if n("RETIRED") else ""]
    points = ["A strategy is one way of trading that holds or held paper money. Each has a status, and a status changes only with your yes.",
              f"{len(st)} are on record: " + ", ".join(c for c in counts if c) + "."]
    names = lambda k: _list([_short_name(v.get("name")) for v in by.get(k) or []])   # noqa: E731
    if n("ACTIVE"):
        points.append(f"Trading and counted: {names('ACTIVE')}." + (f" Under review: {names('UNDER_REVIEW')}." if n("UNDER_REVIEW") else ""))
    edge = next((v for v in st.values() if str(v.get("why") or "").startswith("The one measured edge")), None)
    if edge:
        pk = edge.get("parked") or {}
        s = f"The one measured edge is the {_short_name(edge.get('name'))}."
        if edge.get("status") == "EVIDENCE":
            s += " Its paper record is running again on big coins only; it does not trade for the account."
        if edge.get("status") == "PARKED":
            s += f" Its paper book is switched off{' since ' + _dw(pk.get('date')) if pk.get('date') else ''}"
            s += "; the research result stands." if "research verdict is unchanged" in str(pk.get("note") or "") else "."
        points.append(s)
    if n("PARKED"):
        points.append(f"Switched off: {names('PARKED')}.")
    if n("EVIDENCE"):
        points.append(f"Only measured, never held in your account: {names('EVIDENCE')}.")
    points.append(f"Until {_dw(RULE_B_END)} no new crypto strategy is added and no rule changes without your yes (Rule B). {win['words']}.")
    days = [str(reg.get("updated") or "")] + [str((v.get("parked") or {}).get("date") or "") for v in st.values()] + [str(v.get("since") or "") for v in st.values()]
    days = sorted(d for d in days if re.fullmatch(r"20\d\d-\d\d-\d\d", d))
    return {"title": "The strategies, explained", "points": points, "updated": _dw(days[-1]) if days else "", "source": "the strategy register", "ask": STRAT_Q}


def exam_explain(repo: Path | None = None) -> dict | None:
    """The 'Weekly exam' card's explanation: what it asks, the last result, what was marked wrong, how many exams passed so far."""
    d = (repo or REPO) / "docs" / "repair_shop" / "exam"
    try:
        e = json.loads((d / "latest.json").read_text())
    except (OSError, ValueError):
        return None
    passed = lambda x: all(x.get(k) for k in ("knows_pass", "unknowns_pass", "why_pass", "consistency_pass")) and x.get("numbers_pass", True)   # noqa: E731
    points = ["Every week Ananta sits an exam on its own crypto system: facts it must know, trick questions it must answer with 'I don't know', "
              "and reasons it must explain."]
    points.append(f"The last exam ({_dw(e.get('day'))}): knows {e.get('known')} of {e.get('known_of')}, says 'I don't know' when it should "
                  f"{e.get('unknown')} of {e.get('unknown_of')}, explains why {e.get('why')} of {e.get('why_of')}"
                  + (f", gives the same answer when asked twice {e.get('consistent')} of {e.get('consistent_of')}" if e.get("consistent_of") else "")
                  + (f", gets the money right {e.get('numbers')} of {e.get('numbers_of')}" if e.get("numbers_of") else "")
                  + f": {'pass' if passed(e) else 'fail'}.")
    wrong = [str(r.get("question") or "").strip() for r in e.get("rows") or [] if r.get("ok") is False and r.get("question")]
    if wrong:
        points.append("Marked wrong: " + "; ".join(f"“{q}”" for q in wrong[:3]) + (f" and {len(wrong) - 3} more" if len(wrong) > 3 else "") + ".")
    try:
        runs = [json.loads(x) for x in (d / "history.jsonl").read_text().splitlines() if x.strip()]
        runs = [x for x in runs if x.get("exam_pass") is not None]          # the runs that carry the exam's own verdict (exam.py)
        if runs:
            points.append(f"{sum(1 for x in runs if x['exam_pass'])} of {len(runs)} graded runs passed, since {_dw(runs[0].get('day'))}.")
    except (OSError, ValueError):
        pass
    points.append("A failed exam changes an answer, never a trade.")
    return {"title": "The weekly exam, explained", "points": points, "updated": _dw(e.get("day")) if e.get("day") else "", "source": "the weekly exam record", "ask": EXAM_Q}


CHART_ALIAS = {"BITCOIN": "BTC", "ETHEREUM": "ETH", "ETHER": "ETH", "SOLANA": "SOL"}
COIN_NOTE = {"BTC": "Buying is on only while Bitcoin closes above both lines.",
             "ETH": "The book's core Ethereum is sold on a daily close under Ethereum's own 50-day line, or when buying turns off.",
             "SOL": "Solana is not a core coin: the book holds it only on a small trade by a rule that passed."}


def coin_chart(j, coin: str, n: int = 120) -> dict:
    """One coin's last 120 daily closes with its 50-day and 200-day averages, in the shape of India's index chart. The averages are the
    dial's own (review25.ema over 50 days, review25.sma over 200), so the Bitcoin lines are the numbers the dial reads."""
    from jarvis.service import feed
    from src.research import review25 as R
    name = COIN_NAME[coin]
    note = ("Daily closes in US dollars (Binance). The 50-day line leans on recent days; the 200-day is a plain average. "
            + ("They are the averages the dial reads." if coin == "BTC" else "The dial reads the same two averages on Bitcoin."))
    D = feed.daily(j, coin)
    if len(D) < 2:
        return {"name": name, "kind": "index", "as_of": None, "chart": {"dates": [], "closes": [], "sma50": [], "sma200": [], "support": [], "resistance": []},
                "words": f"No daily candles for {name} on file yet.", "note": note}
    c = [float(b[4]) for b in D]
    e50, s200 = R.ema(c, 50), R.sma(c, 200)
    days = [dt.datetime.fromtimestamp(b[0], UTC).strftime("%Y-%m-%d") for b in D]
    last, a50, a200 = c[-1], e50[-1], s200[-1]
    words = f"{name} closed at {_usd(last)} on {_dw(days[-1])}."
    side = lambda a: f"{abs(100 * (last / a - 1)):.1f}% {'above' if last >= a else 'below'}"   # noqa: E731
    if a50 and a200:
        words += f" That is {side(a50)} its 50-day average ({_usd(a50)}) and {side(a200)} its 200-day ({_usd(a200)})."
    w = c[-n:]
    wd = days[-n:]
    if len(c) > 30:
        m30 = 100 * (last / c[-31] - 1)
        words += f" It is {'up' if m30 >= 0 else 'down'} {abs(m30):.1f}% over the last 30 days."
    hi, lo = max(range(len(w)), key=w.__getitem__), min(range(len(w)), key=w.__getitem__)
    words += f" In these {len(w)} days the highest close was {_usd(w[hi])} on {_dw(wd[hi])} and the lowest {_usd(w[lo])} on {_dw(wd[lo])}."
    words += " " + COIN_NOTE[coin]
    rnd = lambda x: None if x is None else round(x, 2)   # noqa: E731
    return {"name": name, "kind": "index", "coin": coin, "ccy": "USD", "as_of": _dm(days[-1]) + " close", "close": last,
            "chart": {"dates": wd, "closes": [rnd(x) for x in w], "sma50": [rnd(x) for x in e50[-n:]], "sma200": [rnd(x) for x in s200[-n:]], "support": [], "resistance": []},
            "x_labels": [_dm(wd[0]), _dm(wd[-1])], "words": words, "note": note}


def account_chart(j) -> dict:
    """The $500 book over time against its two yardsticks, in the shape of India's portfolio chart. The book's line is its value as the
    officer's nightly facts recorded it (officer_notes.facts.account.value_cad, written minutes after each daily close), one point a
    night; the yardsticks are exposure's own paper books (review25.run on Bitcoin's daily candles with NDAX costs) at the same closes,
    in the same dollars. Nothing is filled in: a night with no record is not drawn."""
    from jarvis.service import exposure, feed, officer
    from src.intelligence.explorer_engine import HALF_SPREAD, NDAX_FEE
    from src.research import review25 as R
    b = _book(j)
    start = _start_cad()
    officer._table(j)                                       # as officer.latest does: a service that has written no note yet has no table
    legend = {"yours": "the $500 book", "untouched": "Bitcoin, just held", "nifty500": "the hurdle to beat"}     # one line each on a phone
    lines = {"yours": "the book", "untouched": "Bitcoin held", "nifty500": "the hurdle"}
    note = "Paper only, in Canadian dollars. One point a night, as recorded after the daily close; the yardsticks count from Sat 10 Oct, the book from Sun 11 Oct."
    empty = {"name": "Your account on paper", "kind": "portfolio", "as_of": None, "chart": {"dates": [], "yours": [], "untouched": [], "nifty500": []},
             "legend": legend, "lines": lines, "words": "The account's record starts with the first nightly note; nothing to draw yet.", "note": note}
    rec: dict[str, float] = {}
    for day, facts in j.db.execute("SELECT day, facts FROM officer_notes ORDER BY day"):
        try:
            v = ((json.loads(facts or "{}") or {}).get("account") or {}).get("value_cad")
            close_day = (dt.date.fromisoformat(str(day)[:10]) - dt.timedelta(days=1)).isoformat()   # the note of day D follows the close of D-1
        except (ValueError, AttributeError):
            continue
        if isinstance(v, (int, float)):
            rec[close_day] = float(v)
    started = str(b.get("started") or "")[:10]
    if not rec or not re.fullmatch(r"20\d\d-\d\d-\d\d", started):
        return empty
    first = (dt.date.fromisoformat(started) - dt.timedelta(days=1)).isoformat()                     # the close before its first buy: C$500
    dates = [first] + sorted(d for d in rec if d > first)
    yours = [start] + [rec[d] for d in dates[1:]]
    D = [(t, o, h, lo, c) for t, o, h, lo, c, v in feed.daily(j, "BTC")]
    hold, hurdle = [None] * len(dates), [None] * len(dates)
    if len(D) >= 210:
        cost, t0 = NDAX_FEE + HALF_SPREAD["BTC"], R._t(exposure.START)
        w_hold, w_gate = R.targets(D, "HOLD"), R.targets(D, "GATE50")
        last_t = D[-1][0]
        for i, d in enumerate(dates):
            t1 = R._t(d)
            if t1 > last_t:                                                                        # a night newer than the candles on file
                continue
            hold[i] = round(start * (1 + R.run(D, w_hold, cost, t0, t1)["total_pct"] / 100), 2)
            hurdle[i] = round(start * (1 + R.run(D, w_gate, cost, t0, t1)["total_pct"] / 100), 2)
    pct = lambda v: _pct(100 * (v / start - 1)) if isinstance(v, (int, float)) else "—"   # noqa: E731
    fixes = [r for r in (_safe(_repairs, j, default=[]) or []) if str(r.get("day") or "") > dates[-1] or str(r.get("day") or "") in dates[-14:]]
    now_v = b.get("value_cad")
    lead = (f"The $500 book stands at {_cad(now_v)} now: {_pct(b.get('return_pct'))} since it started with {_cad(start, 0)} on {_dw(started)}. "
            f"The line's last nights were recorded before a correction, so it ends lower, at {_cad(yours[-1])}. " if fixes and isinstance(now_v, (int, float)) and abs(now_v - yours[-1]) > 0.5
            else f"The $500 book stood at {_cad(yours[-1])} at the {_dw(dates[-1])} close: {pct(yours[-1])} since it started with {_cad(start, 0)} on {_dw(started)}. ")
    words = (lead
             + (f"Over the same weeks Bitcoin just held is {pct(hold[-1])} and the hurdle (Bitcoin held only above its 50-day average) is {pct(hurdle[-1])}, "
                f"both counted from {_dw(exposure.START)}. " if hold[-1] is not None else "")
             + f"Drawn from {len(dates) - 1} recorded night{'s' if len(dates) != 2 else ''} and the start.")
    gap = _safe(book_gap, j, b, default=[]) or []
    if gap:
        words += " " + gap_words(gap)
    for r in fixes:                                          # a correction is said: the nights before it were recorded without that money
        words += (f" Corrected on {_dw(r.get('day'))}: {_cad(r.get('cash_added'))} from a trade whose sale had not been recorded; "
                  "the nights before that were recorded without it.")
    return {"name": "Your account on paper", "kind": "portfolio", "ccy": "CAD", "as_of": _dm(dates[-1]) + " close", "start_cad": start, "sessions": len(dates) - 1,
            "chart": {"dates": dates, "yours": yours, "untouched": hold, "nifty500": hurdle}, "legend": legend, "lines": lines,
            "x_labels": [_dm(dates[0]), _dm(dates[-1])], "words": words, "note": note}


def _repairs(j) -> list[dict]:
    """Corrections written into the $500 book's own state with Madhav's yes (each: day, what, cash_added)."""
    from jarvis.service import ndax_book
    return list((ndax_book._get(j, "state") or {}).get("repairs") or [])


def chart(j, name: str) -> dict:
    """/v3/surface/chart/{name}: BTC, ETH or SOL (a coin's closes and averages) or PORTFOLIO (the $500 book against its yardsticks)."""
    key = str(name or "").upper().strip()
    if key in ("PORTFOLIO", "ACCOUNT"):
        return account_chart(j)
    coin = CHART_ALIAS.get(key, key)
    if coin not in COIN_NAME:
        raise ValueError(f"no chart for {name}: the new look draws Bitcoin, Ethereum, Solana and the account")
    return coin_chart(j, coin)
