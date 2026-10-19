"""The event registry (Market Brain layer 1): every market-moving event with the time it became public, what was known before, its sources,
its confounders and a verification status. News explains why; prices (the lake) show what happened: the two stay separately auditable.

  python -m india.events load            bronze/events/*.json (curated batches) -> silver/events/{events,sources}.parquet, with checks
  python -m india.events links           checks every source URL once (politely) and records reachable / blocked / dead
  python -m india.events report          registrations/event_registry.md: counts, coverage by year and category, open problems

Rules
- first_tradable_session is recomputed from the NSE trading calendar: public after 15:30 IST, or on a non-trading day -> the next session.
- Status: OFFICIAL (an official source), TWO_SOURCES (two independent tier A/B publishers), ONE_SOURCE (kept, excluded from studies),
  REJECTED (failed a check). Only OFFICIAL and TWO_SOURCES events enter studies.
- Era from first_tradable_session: dev (<2018), validation (2018-2023), holdout (2024+). Market reactions of holdout events are not computed
  until the one-time holdout run; the registry stores the event, never a reaction, for them.
- No reaction numbers from articles are stored anywhere: reactions come from the lake (india.eventresp).
- Same-day events are linked as confounders of each other automatically (in addition to those the curator named).
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd

from india import paths

CATEGORIES = {"world_macro", "commodity", "geopolitics_war", "terror_security", "civil_unrest", "india_policy", "rbi_policy", "union_budget", "election",
              "regulation_sebi", "credit_crisis", "banking", "corporate_governance", "corporate_event", "flows", "market_structure", "pandemic", "other"}
TIER_A = ("rbi.org.in", "pib.gov.in", "sebi.gov.in", "nseindia.com", "bseindia.com", "eci.gov.in", "federalreserve.gov", "who.int", "gov.uk", "whitehouse.gov",
          "ustr.gov", "indiabudget.gov.in", "finmin.nic.in", "mof.gov.in", "mea.gov.in", "pmindia.gov.in", "imf.org", "worldbank.org", "ecb.europa.eu", "iea.org", "un.org",
          "kremlin.ru", "archives.gov", "state.gov", "defense.gov", "businesswire.com", "prnewswire.com", "biontech.com", "pfizer.com", "nsearchives.nseindia.com",
          "archives.nseindia.com", "incometaxindia.gov.in", "gst.gov.in", "mha.gov.in", "eci.gov.in", "results.eci.gov.in")  # official bodies and issuers' own releases
TIER_B = ("reuters.com", "bloomberg.com", "business-standard.com", "livemint.com", "economictimes.indiatimes.com", "moneycontrol.com", "thehindubusinessline.com",
          "cnbc.com", "bbc.com", "bbc.co.uk", "ft.com", "wsj.com", "apnews.com", "aljazeera.com", "thehindu.com", "indianexpress.com", "hindustantimes.com",
          "ndtv.com", "timesofindia.indiatimes.com", "cnbctv18.com", "financialexpress.com", "nytimes.com", "theguardian.com", "washingtonpost.com",
          "businesstoday.in", "news18.com", "indiatoday.in", "france24.com", "dw.com", "npr.org", "axios.com", "politico.com", "marketwatch.com", "forbes.com",
          "deccanherald.com", "theprint.in", "thewire.in", "thequint.com", "outlookbusiness.com", "tribuneindia.com", "pbs.org", "bloombergquint.com", "ndtvprofit.com",
          "gulfnews.com", "arabnews.com", "think.ing.com", "moneylife.in", "thenewsminute.com", "businessinsider.in", "onmanorama.com", "theweek.in", "malaymail.com",
          "thejakartapost.com", "gulf-times.com", "dtnext.in", "boomlive.in", "etvbharat.com", "scroll.in", "firstpost.com", "telegraphindia.com", "deccanchronicle.com",
          "abc.net.au", "cbsnews.com", "nbcnews.com", "euronews.com", "japantimes.co.jp", "scmp.com", "straitstimes.com", "oxfordeconomics.com", "investing.com")
CLOSE = dt.time(15, 30)


def _tier(url: str) -> str:
    host = urlparse(url).netloc.lower()
    host = host[4:] if host.startswith("www.") else host
    if any(host == d or host.endswith("." + d) for d in TIER_A):
        return "A"
    if any(host == d or host.endswith("." + d) for d in TIER_B):
        return "B"
    return "C"


def _publisher_key(url: str) -> str:
    host = urlparse(url).netloc.lower()
    parts = host.split(".")
    return ".".join(parts[-3:]) if parts[-2:] in (["co", "uk"], ["gov", "in"], ["nic", "in"], ["org", "in"]) else ".".join(parts[-2:])


def _calendar() -> list[dt.date]:
    cal = pd.read_parquet(paths.data_dir() / "silver/calendar/calendar.parquet")
    return sorted(pd.to_datetime(cal.loc[cal["is_trading_day"], "date"]).dt.date)


def _first_session(d: dt.date, t: str | None, days: list[dt.date], period: str | None = None, curator: str | None = None) -> tuple[dt.date | None, str]:
    """The first session in which the event could be traded. An exact time decides; otherwise the sourced period (before_open / during /
    after_close); otherwise the curator's session with a flag; otherwise that day, flagged 'time unknown'."""
    import bisect
    note = ""
    after_close = False
    if t:
        try:
            hh, mm = map(int, t.split(":")[:2])
            after_close = dt.time(hh, mm) >= CLOSE
        except ValueError:
            note = "unparseable time"
    elif period in ("before_open", "during", "after_close"):
        after_close = period == "after_close"
        note = f"time unknown, period {period} (sourced)"
    elif curator:
        try:
            return dt.date.fromisoformat(curator), "time unknown; first session from the curator, unverified"
        except ValueError:
            note = "time unknown"
    else:
        note = "time unknown"
    i = bisect.bisect_left(days, d)
    if i < len(days) and days[i] == d and not after_close:
        return d, note
    j = bisect.bisect_right(days, d)
    if j >= len(days):
        return None, (note + "; beyond the calendar").strip("; ")
    return days[j], (note + ("; public after the close" if after_close else "; not a trading day")).strip("; ")


def _eid(e: dict) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", e["title"].lower()).strip("-")[:40]
    return f"EV-{e['event_date'].replace('-', '')}-{slug}"


def load() -> dict:
    paths.ensure()
    src_dir = paths.bronze("events")
    src_dir.mkdir(parents=True, exist_ok=True)
    days = _calendar()
    rows, srcs, problems = [], [], []
    seen = {}
    for f in sorted(src_dir.glob("*.json")):
        batch = json.loads(f.read_text())
        items = batch["events"] if isinstance(batch, dict) else batch
        for e in items:
            p = []
            try:
                d = dt.date.fromisoformat(e["event_date"])
            except Exception:
                problems.append(f"{f.name}: bad date in {e.get('title')}")
                continue
            if e.get("category") not in CATEGORIES:
                p.append(f"category {e.get('category')!r} not in the taxonomy")
            given = e.get("first_tradable_session")
            fts, tnote = _first_session(d, e.get("public_time_ist"), days, e.get("public_period"), given)
            if given and fts and given != fts.isoformat():
                p.append(f"curator's first session {given} differs from the calendar's {fts} ({tnote or 'trading day'})")
            eid = _eid(e)
            if eid in seen:
                p.append(f"duplicate of an event in {seen[eid]}")
                eid = eid + "-" + hashlib.sha1(f.name.encode()).hexdigest()[:4]
            seen[eid] = f.name
            tiers, pubs = [], set()
            for s in e.get("sources") or []:
                u = (s.get("url") or "").strip()
                if not u.startswith("http"):
                    p.append("a source without a URL")
                    continue
                t = _tier(u)
                tiers.append(t)
                if t in ("A", "B"):
                    pubs.add(_publisher_key(u))
                srcs.append({"event_id": eid, "url": u, "publisher": s.get("publisher"), "published": s.get("published"), "kind": s.get("kind"), "tier": t,
                             "batch": f.name})
            status = "OFFICIAL" if "A" in tiers else ("TWO_SOURCES" if len(pubs) >= 2 else "ONE_SOURCE")
            if fts is None:
                status = "REJECTED"
                p.append("no tradable session in the calendar")
            era = None if fts is None else ("dev" if fts.year < 2018 else ("validation" if fts.year < 2024 else "holdout"))
            rows.append({"event_id": eid, "title": e["title"], "category": e.get("category"), "subcategory": e.get("subcategory"), "scope": e.get("scope"),
                         "event_date": d, "public_time_ist": e.get("public_time_ist"), "public_period": e.get("public_period"), "first_tradable_session": fts, "timing_note": "; ".join(x for x in (e.get("timing_note"), tnote) if x),
                         "known_beforehand": e.get("known_beforehand"), "expectation": e.get("expectation"), "expectation_source": e.get("expectation_source"),
                         "what_happened": e.get("what_happened"), "reported_affected": json.dumps(e.get("reported_affected") or []),
                         "confounders": json.dumps(e.get("confounders") or []), "n_sources": len(tiers), "tiers": "".join(sorted(tiers)), "status": status,
                         "era": era, "problems": "; ".join(p), "batch": f.name, "notes": e.get("notes")})
    ev = pd.DataFrame(rows)
    if ev.empty:
        return {"events": 0, "problems": problems}
    # same-session events confound each other
    grp = ev.groupby("first_tradable_session")["event_id"].apply(list).to_dict()
    ev["same_session_events"] = ev.apply(lambda r: json.dumps([x for x in grp.get(r["first_tradable_session"], []) if x != r["event_id"]]), axis=1)
    out = paths.data_dir() / "silver" / "events"
    out.mkdir(parents=True, exist_ok=True)
    ev.to_parquet(out / "events.parquet")
    pd.DataFrame(srcs).to_parquet(out / "sources.parquet")
    summ = {"at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "events": len(ev), "by_status": ev["status"].value_counts().to_dict(),
            "by_era": ev["era"].value_counts().to_dict(), "by_category": ev["category"].value_counts().to_dict(),
            "with_problems": int((ev["problems"] != "").sum()), "time_known": int(ev["public_time_ist"].notna().sum()), "sources": len(srcs), "load_problems": problems}
    (paths.manifest_dir() / "events_load.json").write_text(json.dumps(summ, indent=1, default=str))
    return summ


def links(pause: float = 1.5) -> dict:
    """One polite request per source URL: 2xx/3xx reachable, 401/403/429 blocked-to-robots (unknown, not dead), 404/410 dead."""
    import requests
    p = paths.data_dir() / "silver/events/sources.parquet"
    s = pd.read_parquet(p)
    ua = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"}
    res = {}
    for u in s["url"].unique():
        try:
            r = requests.get(u, headers=ua, timeout=25, allow_redirects=True, stream=True)
            code = r.status_code
            r.close()
        except Exception as e:
            code = f"error:{type(e).__name__}"
        res[u] = code
        time.sleep(pause)
    s["link_status"] = s["url"].map(res).astype(str)
    s["link_class"] = s["link_status"].map(lambda c: "reachable" if c[:1] in "23" else ("dead" if c in ("404", "410") else "unknown"))
    s["link_checked_at"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    s.to_parquet(p)
    return s["link_class"].value_counts().to_dict()


def report() -> None:
    ev = pd.read_parquet(paths.data_dir() / "silver/events/events.parquet")
    s = pd.read_parquet(paths.data_dir() / "silver/events/sources.parquet")
    ev["year"] = pd.to_datetime(ev["first_tradable_session"]).dt.year
    L = ["# Event registry v1", "", f"Generated by `python -m india.events report` ({dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')}). "
         "Events and sources only: no market reactions are stored here (they come from the lake; holdout-era reactions stay sealed).", "",
         f"- Events: **{len(ev)}**; status: " + ", ".join(f"{k} {v}" for k, v in ev["status"].value_counts().items()),
         f"- Eras: " + ", ".join(f"{k} {v}" for k, v in ev["era"].value_counts().items()),
         f"- Public time known for {int(ev['public_time_ist'].notna().sum())} of {len(ev)}; events with a check problem: {int((ev['problems'] != '').sum())}",
         f"- Sources: {len(s)} ({', '.join(f'tier {k} {v}' for k, v in s['tier'].value_counts().sort_index().items())})"
         + (f"; links: {', '.join(f'{k} {v}' for k, v in s['link_class'].value_counts().items())}" if "link_class" in s else ""), "",
         "## By year and category", "", ev.pivot_table(index="year", columns="category", values="event_id", aggfunc="count", fill_value=0).to_markdown(), "",
         "## Problems to resolve", ""]
    for r in ev[ev["problems"] != ""].itertuples():
        L.append(f"- {r.event_id}: {r.problems}")
    L += ["", "## Events", "", "| first session | public time | category | title | status | known before | sources |", "|---|---|---|---|---|---|---|"]
    for r in ev.sort_values("first_tradable_session").itertuples():
        L.append(f"| {r.first_tradable_session} | {r.public_time_ist or '?'} | {r.category} | {r.title} | {r.status} | {r.known_beforehand or '?'} | {r.n_sources} ({r.tiers}) |")
    Path(__file__).resolve().parent.joinpath("registrations", "event_registry.md").write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "load"
    if cmd == "load":
        print(json.dumps(load(), indent=1, default=str))
    elif cmd == "links":
        print(links())
    else:
        report()
