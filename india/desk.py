"""The trader's desk (3 Nov 2026, Madhav's chat at 08:46-09:01 Toronto and the outside trader-grader's report).

Madhav asked Ananta what it would watch tomorrow, why his MARICO jumped 10%, and whether "our data" was enough; Ananta said it had no
announcement dates and no per-stock results, which was wrong (the announcements are fetched every evening; results filings are indexed),
and it could not name a stock to watch or say why one moved. This module is the one owner of those facts for the Ask:

  news            the company announcements of the last 7 fetched days, per symbol (results, board meetings, the rest), newest first
  results_ahead   board meetings for results in the next sessions, read from the meetings' own intimation text
  movers          the biggest one-day moves of the liquid stocks in the latest quote book, each with its news (or "no filing found")
  feeds           each data source's last day and when it was fetched, so "check the link" is answered feed by feed
  inventory       what data Ananta has, its years and size, and where it is thin (from manifests/data_inventory.json and the tracker's data rows)

build() is read-only on files already fetched (bronze announcements of the live window, manifests); no Kite, no order. Run as a job
(the postclose and nightly chains) it first fetches the last few days' announcements again (announce.fetch_recent, 9 Nov 2026) and
rebuilds the one calendar (calendar_ahead).

  python -m india.desk build        writes manifests/desk.json
"""
from __future__ import annotations

import datetime as dt
import gzip
import json
import re
import sys
from pathlib import Path

from india import dayplan, paths

DAYS_NEWS = 7
PER_SYMBOL = 6
MOVERS = 12
MIN_TURNOVER_CR = 5.0           # liquid: at least Rs 5 crore traded a day on average over 20 sessions
MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def _man() -> Path:
    return paths.manifest_dir()


def _json(p: Path, default=None):
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return default


def _last_line(p: Path) -> dict:
    try:
        with p.open("rb") as fh:
            fh.seek(0, 2)
            size = fh.tell()
            fh.seek(max(0, size - 8192))
            lines = [x for x in fh.read().decode("utf-8", "replace").splitlines() if x.strip()]
        return json.loads(lines[-1]) if lines else {}
    except (OSError, ValueError):
        return {}


def kind_of(desc: str, text: str) -> str:
    low = (text or "").lower()
    d = (desc or "").lower()
    if "financial result" in low and ("outcome" in d or "outcome" in low or "approved" in low or "enclos" in low):
        return "results"
    if "board meeting" in d or ("board" in low and ("will be held" in low or "scheduled" in low or "to be held" in low or "intimat" in low)):
        return "board_meeting"
    if "con. call" in d or "analyst" in d or "earnings conference call" in low or "earnings call" in low:
        return "analyst_call"
    if any(w in low for w in ("order", "contract worth", "letter of award", "bagged", "secured")):
        return "order"
    if any(w in d for w in ("dividend", "bonus", "split", "buyback", "rights")):
        return "corporate_action"
    if "credit rating" in low or "rating" in d:
        return "rating"
    if any(w in d for w in ("acquisition", "amalgamation", "merger", "scheme")):
        return "deal"
    return "other"


def dates_in(text: str) -> set[dt.date]:
    """Dates written in an intimation ('November 4, 2026', '04-11-2026', '4th November 2026', '04/11/2026')."""
    out = set()
    t = (text or "").lower()
    for d, mo, y in re.findall(r"\b(\d{1,2})(?:st|nd|rd|th)?[\s,-]+([a-z]{3,9})[\s,.-]+(20\d\d)\b", t):
        if mo[:3] in MONTHS:
            try:
                out.add(dt.date(int(y), MONTHS[mo[:3]], int(d)))
            except ValueError:
                pass
    for mo, d, y in re.findall(r"\b([a-z]{3,9})\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(20\d\d)\b", t):
        if mo[:3] in MONTHS:
            try:
                out.add(dt.date(int(y), MONTHS[mo[:3]], int(d)))
            except ValueError:
                pass
    for d, mo, y in re.findall(r"\b(\d{1,2})[/.-](\d{1,2})[/.-](20\d\d)\b", t):
        try:
            out.add(dt.date(int(y), int(mo), int(d)))
        except ValueError:
            pass
    return out


def _announce_files(n: int = DAYS_NEWS) -> list[Path]:
    root = paths.data_dir() / "bronze" / "announce_api"
    files = sorted(root.glob("20[2-9][0-9]/*.json.gz"))
    return files[-n:]


def news(files: list[Path] | None = None) -> tuple[dict, dict]:
    """({symbol: [items newest first]}, {symbol: [dates of results board meetings ahead]})."""
    by_sym: dict[str, list] = {}
    meets: dict[str, set] = {}
    for f in files if files is not None else _announce_files():
        try:
            rows = json.loads(gzip.open(f).read())
        except (OSError, ValueError, EOFError):
            continue
        for x in rows if isinstance(rows, list) else []:
            sym = str(x.get("symbol") or "").upper()
            if not sym:
                continue
            desc, text = str(x.get("desc") or ""), str(x.get("attchmntText") or "")
            k = kind_of(desc, text)
            when = str(x.get("an_dt") or "")
            try:
                when = dt.datetime.strptime(when, "%d-%b-%Y %H:%M:%S").strftime("%Y-%m-%d %H:%M")
            except ValueError:
                when = when[:16]
            by_sym.setdefault(sym, []).append({"at": when, "kind": k, "what": desc, "text": re.sub(r"\s+", " ", text)[:240]})
            low = text.lower()
            if "result" in low and any(w in low for w in ("scheduled", "will be held", "to be held", "is to consider", "to consider and approve")) \
                    and "held today" not in low and "outcome" not in desc.lower():
                filed = when[:10]
                meets.setdefault(sym, set()).update(d for d in dates_in(text) if d.isoformat() >= filed)   # not the quarter's end date
    for sym, items in by_sym.items():
        items.sort(key=lambda i: i["at"], reverse=True)
        keep = [i for i in items if i["kind"] != "other"][:PER_SYMBOL]
        by_sym[sym] = keep or items[:2]
    return by_sym, {s: sorted(d.isoformat() for d in v) for s, v in meets.items()}


def feeds() -> list[dict]:
    """Each source's last day on file and when it was fetched (the 'check the link' answer, feed by feed)."""
    m = _man()
    rows = []
    for name, f, day_key in [("NSE cash day file (every stock's close)", "cm_bhavcopy.jsonl", "date"), ("NSE F&O day file (open interest)", "fo_bhavcopy.jsonl", "date"),
                             ("FII/DII cash flows", "fii_dii_cash.jsonl", "date"), ("participant open interest (FII/DII/pro futures)", "flows_participant_oi.jsonl", "date"),
                             ("company announcements", "announce_api.jsonl", "date"), ("bulk and block deals", "deals_snapshot.jsonl", "date"),
                             ("US close (QQQ, SPY)", "us_close.jsonl", "end"), ("options recorder (1-minute)", "kite_1m_fo.jsonl", "end"),
                             ("results filings index", "results_index_integrated_v2.jsonl", "to")]:
        x = _last_line(m / f)
        rows.append({"feed": name, "last_day": x.get(day_key), "fetched_at": x.get("fetched_at"), "status": x.get("status")})
    for name, f, key in [("market summary", "market_context.json", "built_at"), ("stock quote book", "quotebook.json", "built_at"),
                         ("option chain levels (OI walls)", "premarket_chain.json", "built_at"), ("F&O ban list", "fo_ban.json", "fetched_at")]:
        x = _json(m / f, {}) or {}
        rows.append({"feed": name, "last_day": x.get("as_of") or x.get("day"), "fetched_at": x.get(key), "status": x.get("status") if isinstance(x.get("status"), (str, int)) else "ok"})
    return rows


def inventory() -> dict:
    """What data Ananta has (years, size, where it is thin): the data inventory manifest plus the tracker's data rows, in one place."""
    inv = _json(_man() / "data_inventory.json", {}) or {}
    try:
        from india import tracker
        items = [{"id": r[0], "item": r[1], "state": r[2], "note": r[4]} for r in tracker.DATA]
    except Exception:  # noqa: BLE001
        items = []
    ds = {k: {"rows": v.get("rows"), "research_years": f"{(v.get('first') or '')[:4]}-{(v.get('last') or '')[:4]}" if v.get("first") else None,
              "live_to": v.get("sealed_last")} for k, v in (inv.get("datasets") or {}).items() if v.get("rows")}
    ann = inv.get("announcements") or {}
    intr = (inv.get("intraday_stocks") or {}).get("by_year") or {}
    last_year = max(intr) if intr else None
    return {"at": inv.get("at"), "datasets": ds, "tracker_rows": items,
            "announcements": {"research_rows": ann.get("rows_ex_nav"), "from": ann.get("first"), "categories": ann.get("categories"),
                              "live": "every evening from NSE's announcements feed (bronze/announce_api)", "time_of_day": ann.get("time_of_day")},
            "intraday_stocks": {"latest_year": last_year, **(intr.get(last_year) or {})} if last_year else None,
            "results_index_files": (inv.get("results_index") or {}).get("files")}


def movers(qb: dict, by_sym: dict, n: int = MOVERS) -> dict:
    q = qb.get("quotes") or {}
    liquid = [x for x in q.values() if x.get("kind") != "etf" and (x.get("avg_turnover_20d_cr") or 0) >= MIN_TURNOVER_CR and x.get("chg_1d") is not None]
    def row(x):
        items = by_sym.get(str(x.get("symbol")).upper()) or []
        return {"symbol": x.get("symbol"), "name": x.get("name"), "industry": x.get("industry"), "chg_1d_pct": round(100 * x["chg_1d"], 2),
                "close": x.get("close"), "vs_sma50_pct": round(100 * x["vs_sma50"], 1) if x.get("vs_sma50") is not None else None,
                "news": items[:2], "why": (items[0]["what"] + ": " + items[0]["text"][:160]) if items else "no company filing found in the last 7 fetched days"}
    up = sorted(liquid, key=lambda x: x["chg_1d"], reverse=True)[:n]
    dn = sorted(liquid, key=lambda x: x["chg_1d"])[:n]
    return {"as_of": qb.get("as_of"), "liquid_names": len(liquid), "up": [row(x) for x in up], "down": [row(x) for x in dn]}


SAY_KINDS = {"results": "results", "order": "an order or contract", "corporate_action": "a dividend, bonus, split or buyback", "deal": "an acquisition or merger",
             "rating": "a credit rating", "board_meeting": "a board meeting notice"}


def _dw(day: str) -> str:
    try:
        d = dt.date.fromisoformat(str(day)[:10])
        return f"{d:%a} {d.day} {d:%b}"
    except ValueError:
        return str(day)


def holdings_news(since: str | None = None, held: list[str] | None = None, by_sym: dict | None = None, ahead: dict | None = None, qb: dict | None = None) -> dict:
    """One line for each stock in the account that has filed something since the last session's close, the day's move of each, and the
    results meetings ahead (9 Nov 2026; Madhav: "yes, lets complete", the readiness review's fix 3: holdings first). The morning view opens
    with this. What was filed is NSE's own heading and the first words of the filing; the figures inside a results filing are not read here.
    since: 'YYYY-MM-DD HH:MM' in India (default: the 15:30 close of the read model's last session)."""
    rm = _json(paths.data_dir() / "readmodel" / "latest.json", {}) or {}
    qb = qb if qb is not None else (_json(_man() / "quotebook.json", {}) or {})
    # the last session with a close on file: the quote book is built the same night, the read model the next morning; the newer one decides,
    # and each stock's move is labelled with the quote book's own day
    through = max([str(x) for x in (rm.get("data_through"), qb.get("as_of")) if x] or [""]) or None
    moved_on = qb.get("as_of") or through
    since = since or (f"{through} 15:30" if through else "0000")
    if held is None:
        held = sorted((_json(paths.data_dir() / "paper" / "account" / "state.json", {}) or {}).get("positions") or {})
    if by_sym is None:
        by_sym, _ = news(_announce_files(DAYS_NEWS + 3))
    if ahead is None:
        ahead = (_json(_man() / "desk.json", {}) or {}).get("results_ahead") or {}
    q = qb.get("quotes") or {}
    rows, quiet = [], []
    for sym in held:
        new = [i for i in by_sym.get(sym, []) if str(i.get("at") or "") >= since]
        said = [i for i in new if i["kind"] in SAY_KINDS]
        mv = (q.get(sym) or {}).get("chg_1d")
        move = round(100 * mv, 1) if isinstance(mv, (int, float)) else None
        if not said:                       # nothing, or only routine filings (newspaper copies, allotments, call schedules)
            quiet.append(sym)
            continue
        bits, seen = [], {}
        for i in sorted(said, key=lambda i: i["at"]):
            seen.setdefault((i["kind"], i["what"]), []).append(i)
        for (kind, what), items in list(seen.items())[:3]:
            last = items[-1]
            label = SAY_KINDS[kind]
            if kind == "results":
                board = "board meeting" in what.lower()
                per = re.search(r"(?:quarter|half[- ]year|period|year)(?: and [a-z -]{3,20})? ended[^.;,]{0,30}", str(last.get("text") or ""), re.I)
                label = ("its results" + (f" for the {re.sub(chr(92) + 's+', ' ', per.group(0)).strip()}" if per else "")) if board else "a results call or presentation"
            bits.append(f"{label} ({what}, {_dw(last['at'])} {str(last['at'])[11:16]} IST" + (f", {len(items)} filings" if len(items) > 1 else "") + ")")
        line = f"{sym}: filed " + "; ".join(bits) + (f". It closed {move:+.1f}% on {_dw(moved_on)}." if move is not None and moved_on else ".")
        rows.append({"symbol": sym, "kinds": sorted({i["kind"] for i in said}), "items": said[:4], "move_pct": move, "line": line})
    rows.sort(key=lambda r: (0 if "results" in r["kinds"] else 1, r["symbol"]))
    due = sorted((d, s) for d, syms in ahead.items() for s in syms if s in set(held))
    movers = sorted(((round(100 * (q.get(s) or {}).get("chg_1d"), 1), s) for s in quiet if isinstance((q.get(s) or {}).get("chg_1d"), (int, float))
                     and abs((q.get(s) or {}).get("chg_1d")) >= 0.02), reverse=True)
    lines = [r["line"] for r in rows]
    if quiet:
        lines.append((f"No results, order, deal or dividend filing since {_dw(since)}'s close from the other {len(quiet)}: " if rows
                      else f"None of your {len(held)} stocks has filed results, an order, a deal or a dividend since {_dw(since)}'s close: ") + ", ".join(quiet) + ".")
    if movers:
        lines.append(f"Moved 2% or more on {_dw(moved_on)} with no filing: " + ", ".join(f"{s} {m:+.1f}%" for m, s in movers) + ".")
    if due:
        lines.append("Results meetings ahead for your stocks: " + ", ".join(f"{s} on {_dw(d)}" for d, s in due) + ".")
    return {"since": since, "through": through, "held": len(held), "rows": rows, "quiet": quiet, "ahead": [{"symbol": s, "date": d} for d, s in due], "lines": lines,
            "note": "what was filed is NSE's heading and the filing's first words; the figures inside a results filing are not read here"}


def build(write: bool = True) -> dict:
    by_sym, _ = news()
    _, meets = news(_announce_files(25))          # a results meeting is intimated a week or more ahead: read 25 fetched days for the dates
    hol = dayplan.holidays(refresh=False)
    today = dt.date.today()
    ahead, d = [], today
    while len(ahead) < 3:
        d += dt.timedelta(days=1)
        if d.weekday() < 5 and d not in hol:
            ahead.append(d)
    due = {a.isoformat(): sorted(s for s, ds in meets.items() if a.isoformat() in ds) for a in ahead}
    # 3 Nov 2026 (audit step 3): NSE's own board-meetings calendar, fetched each night, joined to what the filings name
    try:
        from india import boardmeetings
        nse_due, snap = boardmeetings.results_ahead(ahead)
    except Exception:  # noqa: BLE001 - the filings list still stands on its own
        nse_due, snap = {}, None
    for k, syms in nse_due.items():
        due[k] = sorted(set(due.get(k, [])) | set(syms))
    qb = _json(_man() / "quotebook.json", {}) or {}
    files = _announce_files()
    out = {"built_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "rules": "desk-v1-2026-11-03",
           "news_days": [f.name[:8] for f in files], "news": by_sym, "results_ahead": due,
           "results_ahead_note": (f"NSE's board-meetings calendar (fetched {snap}) joined to the meeting dates named in company filings" if snap else
                                  "read from the company announcements feed only (a meeting date named in the filing); NSE's own board-meetings "
                                  "calendar has not been fetched yet, so this list is incomplete"),
           "movers": movers(qb, by_sym),
           "holdings_news": holdings_news(by_sym=news(_announce_files(DAYS_NEWS + 3))[0], ahead=due, qb=qb),
           "feeds": feeds(), "inventory": inventory()}
    if write:
        (_man() / "desk.json").write_text(json.dumps(out, indent=1, default=str, ensure_ascii=False))
    return out


if __name__ == "__main__":
    paths.ensure()
    # 9 Nov 2026: the announcements of the last few days (weekends and today so far) are fetched again first, so the desk after the close
    # and at night holds what companies filed that evening; build() itself still reads only what is on disk
    try:
        from india import announce, calendar_ahead
        print(announce.fetch_recent()["words"])
        calendar_ahead.build()
    except Exception as e:  # noqa: BLE001 - the desk still builds from what is on disk
        print(f"announcements not refreshed: {type(e).__name__}: {str(e)[:120]}")
    r = build()
    print(json.dumps({"news_symbols": len(r["news"]), "news_days": r["news_days"], "results_ahead": {k: len(v) for k, v in r["results_ahead"].items()},
                      "movers_as_of": r["movers"]["as_of"], "feeds": len(r["feeds"])}, indent=1))
    sys.exit(0)
