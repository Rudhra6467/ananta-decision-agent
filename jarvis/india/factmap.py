"""The fact map (Madhav, 2 Nov 2026: "everything has to be audited and everything has to be mapped perfectly to the voice agent as well").

The 29 Oct "one map" covers every IDEA (study, rule, verdict). This covers every FACT: every file Ananta's India jobs write, checked by code
every night, so a new feature cannot ship without a route into what Ananta says, and Ananta can never be silently behind its own disk.

  1. Routes. Each file written in the last 8 days is found on disk and matched to a route:
       live     read by the India service at question time (jarvis/india/*.py), so the Ask, the voice and the screens see it at once
       nightly  read only by the read-model build (records india/readmodel.py and the morning-view build): Ananta sees it after the next build
       internal not meant to be spoken (ingest logs, ops checks, research workfiles), with the reason
     A file with no route FAILS: that is a feature that writes facts Ananta cannot say (2 Nov: the options line's trades).
  2. Behind. A nightly-routed file newer on disk than the read model Ananta answers from is listed with how far behind it is; one that
     changes during the Indian session and is nightly-only is a TODAY GAP (FAIL), because "what happened today" would miss it.
  3. Same number everywhere. The screens and the Ask are compared on the numbers both show (the Nifty now, the managed plan, the options
     line's trades, what waits for his yes). A difference FAILS (2 Nov: the Today tile showed Friday's Nifty while the voice said Monday's).

  python -m jarvis.india.factmap          writes docs/repair_shop/factmap/latest.json and .md; exit 1 on any FAIL
"""
from __future__ import annotations

import datetime as dt
import fnmatch
import json
import os
import re
import sys
import time
from pathlib import Path

DATA = Path(os.getenv("ANANTA_INDIA_DATA", os.path.expanduser("~/ananta_data/india")))
RECORDS = Path(os.getenv("ANANTA_RECORDS", os.path.expanduser("~/code/ananta-records")))
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "repair_shop" / "factmap"
WINDOW_DAYS = 8
LIVE_READERS = sorted(p for p in (ROOT / "jarvis" / "india").glob("*.py") if p.name not in ("factmap.py", "neveragain.py")) + [ROOT / "scripts" / "india_morningview.py"]
BUILD_READERS = [RECORDS / "india" / n for n in ("readmodel.py", "morningview.py", "dayplan.py", "report.py", "trials.py")]

# Not meant to be spoken, each with its reason. Anything else must be read by the service or the build.
INTERNAL = [
    ("manifests/*.jsonl", "an ingest or run log; the data it records reaches Ananta through the built tables"),
    ("manifests/*_build.json", "a build receipt"),
    ("manifests/quotebook_names.json", "the name list behind the quote book"),
    ("manifests/data_inventory.json", "ops: the data inventory (read by lineage and the morning review)"),
    ("manifests/datacheck.json", "ops: freshness check (morning review)"), ("manifests/firewall.json", "ops: sealed-data firewall"),
    ("manifests/integrity.json", "ops: integrity checks"), ("manifests/leakcheck.json", "ops: leak check"), ("manifests/lineage.json", "ops: lineage"),
    ("manifests/impact.json", "ops: lineage impact"), ("manifests/r2_verify.json", "ops: backup check"), ("manifests/nse_holidays.json", "the calendar (read through answerguide)"),
    ("manifests/lab*.json", "research results: reach the Ask through the registry and the one map (knowledgemap)"),
    ("manifests/gaplab_*.json", "research results: through the registry and the one map"), ("manifests/sensitivity_*.json", "research workfile"),
    ("manifests/holdout_candidates.json", "research workfile (sealed holdout list)"), ("manifests/settle_vs_tradable.json", "research workfile"),
    ("manifests/options_realism.json", "research workfile behind the options line's realistic fills"),
    ("manifests/big_falls.json", "data audit step 6 workfile; its counts reach the Ask through data_audit.json (the desk's data_we_have)"),
    ("manifests/w500.json", "research results: reach the Ask through the registry and the one map (and data_audit.json step 4)"),
    ("manifests/v02t.json", "research results: through the registry and the one map (and data_audit.json step 2)"),
    ("manifests/hfn1t.json", "research results: through the registry and the one map (and data_audit.json step 2)"),
    ("manifests/premarket_chain.json", "input to the morning view's build"), ("manifests/premarket_inputs.json", "input to the morning view's build"),
    ("manifests/hf_chronos_forward.json", "the forecast record, spoken through the morning view"), ("manifests/sp1_nightly_replay.json", "ops: the options line's replay check"),
    ("manifests/others_*.json", "the reference traders; reaches the Ask through the read model's learning section"),
    ("manifests/missed_*.json", "missed movers; reaches the Ask through the read model's learning section"),
    ("paper/*.parquet", "research book workfile"), ("paper/filter_slices.csv", "research book workfile"), ("paper/*/work/*", "workfile"),
    ("paper/teachers/live_signals.parquet", "teacher workfile"), ("paper/news_read/*", "the news model's daily read of movers: the record behind the news study"),
    ("paper/reconstruction/forwarded.jsonl", "the forwarding log (the repair board holds the items)"),
    ("paper/managed/ledger.jsonl", "the managed book's hash-chained ledger (its state and view are what is read)"),
    ("paper/managed/plans.jsonl", "the plan history (the latest plan is read through the managed view)"),
    ("paper/allocation_ledger.jsonl", "the allocator's ledger (its view is what is read)"),
    ("reports/*.md", "a written report for Madhav (the morning review page)"), ("reports/ask_guard.jsonl", "the answer guard's log (the morning review reads it)"),
    ("readmodel/*", "the read model itself"), ("paper/sp1/plans/*", "the options line's plan files (the decisions ledger is read live)"),
    # 3 Nov (Madhav: yes, the Map's change 4): the expiry-day book stopped and is no longer shown; its old file ages out of the window
    ("paper/options_trades.jsonl", "the expiry-day options book: stopped 3 Nov, kept on disk, not shown"),
]
# Inputs to another file that IS read: (pattern, the file it feeds, the job that turns one into the other)
FEEDS = [
    ("paper/account/benchmark.jsonl", "paper/account/view.json", "india.account run"), ("paper/account/frozen.json", "paper/account/view.json", "india.account run"),
    ("paper/others_history.jsonl", "manifests/others_DATE.json", "india.others"), ("paper/sp1/outcomes.jsonl", "paper/sp1/book.json", "india.sp1paper score"),
    ("paper/decisions/DATE.universe.json", "paper/decisions/DATE.json", "india.paper"), ("manifests/kite_fill.json", "the stock 5-minute candles", "india.kite_fill"),
    ("manifests/fii_dii_coverage.json", "manifests/market_context.json", "india.fiidii build"),
]
# Files read through a path built in code (a date, a loop), which a text search cannot see: (pattern, reader, a token the reader must contain)
READ_BY = [
    ("paper/dayplans/DATE.json", "jarvis/india/views.py", '"dayplans"'), ("paper/morningview/DATE.json", "jarvis/india/views.py", '"morningview"'),
    ("paper/reconstruction/DATE.json", "jarvis/india/ask.py", '"reconstruction"'), ("paper/reconstruction/netnotes/DATE.jsonl", "jarvis/india/ask.py", '"netnotes"'),
    ("paper/shadow/DATE.json", "jarvis/india/views.py", '"shadow"'), ("paper/teachers/forward_options.jsonl", "jarvis/india/views.py", "forward_options"),
    ("manifests/notable_results.json", "india/readmodel.py", "notable_results"),
    ("paper/sp1/book.json", "jarvis/india/views.py", "def sp1_live"), ("paper/sp1/decisions.jsonl", "jarvis/india/views.py", "def sp1_live"),
    # 5 Nov 2026: the 09:08 IST pre-open read, said by the today block (livesession.today -> preopen.today) until 10:30 IST
    ("paper/preopen/DATE.json", "jarvis/india/preopen.py", '"preopen"'),
]
# Study results whose findings are written into the Ask's words by hand (not read): a re-run must update the words. Reported, not failed.
COPIED = [
    ("manifests/xstudies_*.json", "jarvis/india/marketcontext.py", "XO1|FX1|FII1|SR1"), ("manifests/diistudy_dii1.json", "jarvis/india/marketcontext.py", "DII1"),
    ("manifests/hf_chronos_results.json", "india/morningview.py", "chronos"), ("manifests/hf_news_results.json", "jarvis/india/ask.py", "news"),
]
# Written during the Indian session (09:00-15:30 IST): these must be read live, never only by the nightly build
DAYTIME = ["paper/sp1/decisions.jsonl", "paper/sp1/book.json", "paper/morningview/*", "paper/account/*", "paper/allocation_view.json"]


def _dated(rel: str) -> str:
    return re.sub(r"\d{4}-\d{2}-\d{2}", "DATE", rel)


def producers(now: float | None = None) -> dict[str, dict]:
    """Every file pattern written in the window, with its newest write."""
    now = now or time.time()
    out: dict[str, dict] = {}
    for top in ("paper", "manifests", "readmodel", "reports"):
        for p in (DATA / top).rglob("*"):
            if not p.is_file() or "/ask/" in str(p):
                continue
            m = p.stat().st_mtime
            if now - m > WINDOW_DAYS * 86400:
                continue
            k = _dated(str(p.relative_to(DATA)))
            if k not in out or m > out[k]["mtime"]:
                out[k] = {"pattern": k, "mtime": m, "example": str(p.relative_to(DATA))}
    return out


def _tokens(pattern: str) -> list[str]:
    """What a reader's code would contain to read this file: 'sp1/decisions.jsonl' -> ['decisions.jsonl', 'sp1'] etc."""
    parts = pattern.split("/")
    name = parts[-1]
    toks = [name.replace("DATE", "")] if "DATE" not in name else [name.replace("DATE", "").lstrip("_-") or parts[-2]]
    return [t for t in toks if t and t not in (".json", ".jsonl", ".md")] + ([parts[-2]] if len(parts) > 2 else [])


def _read_corpus(files: list[Path]) -> list[str]:
    return [f.read_text(errors="ignore") for f in files if f.exists()]


def routes(prod: dict[str, dict]) -> list[dict]:
    live, build = _read_corpus(LIVE_READERS), _read_corpus(BUILD_READERS)
    rows = []
    for k, v in sorted(prod.items()):
        internal = next((why for pat, why in INTERNAL if fnmatch.fnmatch(k, pat)), None)
        toks = _tokens(k)
        name = toks[0] if toks else k
        folder = toks[1] if len(toks) > 1 else ""

        stem = re.sub(r"\.(json|jsonl|parquet|csv|md)$", "", name).strip("._-")

        def seen(corpus: str) -> bool:
            if not stem:
                return False
            tail = rf"[\"'/]{re.escape(stem)}\.(?:json|jsonl|parquet|csv)\b"
            generic = not folder or folder in ("manifests", "paper", "reports", "readmodel")
            # one reader file must name both the folder and the file (2 Nov: 'score.json' alone matched another book's score file)
            return any(re.search(tail, src) and (generic or re.search(rf"[\"'/]{re.escape(folder)}[\"'/]", src)) for src in corpus)
        feed = next((f"input to {to} ({job})" for pat, to, job in FEEDS if fnmatch.fnmatch(k, pat)), None)
        declared = next(((rd, tok) for pat, rd, tok in READ_BY if fnmatch.fnmatch(k, pat)), None)
        copied = next(((rd, tok) for pat, rd, tok in COPIED if fnmatch.fnmatch(k, pat)), None)
        route = "live" if seen(live) else None
        why = None
        if not route and declared:
            src = (ROOT / declared[0]) if declared[0].startswith("jarvis") else (RECORDS / declared[0])
            if src.exists() and re.search(declared[1], src.read_text(errors="ignore")):
                route, why = ("live" if declared[0].startswith("jarvis") else "nightly"), f"read by {declared[0]} (path built in code)"
        if not route and seen(build):
            route = "nightly"
        if not route and copied:
            src = (ROOT / copied[0]) if copied[0].startswith("jarvis") else (RECORDS / copied[0])
            if src.exists() and re.search(copied[1], src.read_text(errors="ignore")):
                route, why = "copied", f"its findings are written into {copied[0]} by hand: a re-run must update those words"
        if not route:
            route = "feeds" if feed else "internal" if internal else "NONE"
            why = feed if route == "feeds" else internal if route == "internal" else None
        rows.append({**v, "route": route, "why": why,
                     "daytime": any(fnmatch.fnmatch(k, d) for d in DAYTIME)})
    return rows


def behind(rows: list[dict], built_at: str | None) -> list[dict]:
    try:
        b = dt.datetime.fromisoformat(str(built_at)).timestamp()
    except Exception:  # noqa: BLE001
        return [{"check": "read model", "state": "FAIL", "words": f"the read model has no build time ({built_at})"}]
    out = []
    for r in rows:
        if r["route"] == "nightly" and r["daytime"]:
            out.append({"check": f"today gap: {r['pattern']}", "state": "FAIL",
                        "words": f"{r['pattern']} is written during the Indian session but Ananta reads it only after the nightly build"})
        elif r["route"] == "nightly" and r["mtime"] - b > 300:
            h = (r["mtime"] - b) / 3600
            out.append({"check": f"behind: {r['pattern']}", "state": "NOTE",
                        "words": f"{r['pattern']} is {h:.1f} h newer on disk than the read model Ananta answers from; it is seen after the next build"})
    return out


# Independent audit, 2 Nov: a route alone is not enough. The market summary was built at 12:38 Toronto and its inputs (futures positions, P/E, flows)
# landed at 12:47-12:50, so Ananta denied data it had for six hours; the route check passed. A summary must be newer than what it summarises.
SUMMARIES = [   # (summary file, the inputs it is built from)
    ("manifests/market_context.json", ["manifests/valuation.jsonl", "manifests/flows_participant_oi.jsonl", "manifests/fii_dii_cash.jsonl"]),
    ("manifests/quotebook.json", ["manifests/cm_bhavcopy.jsonl"]),
]


def stale_summaries(data: Path | None = None) -> list[dict]:
    data = data or DATA
    out = []
    for summ, inputs in SUMMARIES:
        try:
            built = (data / summ).stat().st_mtime
        except OSError:
            out.append({"check": f"fresh: {summ}", "state": "FAIL", "words": f"{summ} is missing"})
            continue
        newer = []
        for i in inputs:
            try:
                m = (data / i).stat().st_mtime
            except OSError:
                continue
            if m - built > 120:
                newer.append(f"{i} ({(m - built) / 60:.0f} min newer)")
        out.append({"check": f"fresh: {summ}", "state": "FAIL" if newer else "PASS",
                    "words": (f"{summ} was built before its inputs changed: {', '.join(newer)}; Ananta would deny data that is on disk" if newer
                              else f"{summ} is newer than all its inputs")})
    return out


def same_number() -> list[dict]:
    """The screens against the Ask's today-block, on the numbers both show."""
    from jarvis.india import livesession, surfaces, views
    rm = views.readmodel()
    t = livesession.today(rm)
    out = []

    def row(name, ok, words):
        out.append({"check": name, "state": "PASS" if ok else "FAIL", "words": words})
    # E1 the Nifty on the Today screen
    td = surfaces.today()
    tile = next((n for n in (td.get("numbers") or []) if str(n.get("label", "")).startswith("Nifty")), {})
    live = ((t.get("index_now") or {}).get("rows") or {}).get("NIFTY 50") or {}
    if live.get("last") is not None:
        shown = float(re.sub(r"[^0-9.]", "", str(tile.get("value") or "0")) or 0)
        ok = abs(shown - live["last"]) < 1.0
        row("Today screen Nifty = what Ananta says", ok, f"screen {tile.get('label')} {tile.get('value')}; Ananta {live['last']:,.2f} ({t['index_now'].get('kind')})")
    # E1b (4 Nov: the first box swipes up to Bank Nifty) the Bank Nifty page against what Ananta says
    bank = next((p for x in td.get("tiles") or [] for p in x.get("pages") or [] if p.get("label") == "Bank Nifty"), {})
    live_b = ((t.get("index_now") or {}).get("rows") or {}).get("NIFTY BANK") or {}
    if live_b.get("last") is not None and bank:
        shown = float(re.sub(r"[^0-9.]", "", str(bank.get("value") or "0")) or 0)
        row("Today screen Bank Nifty = what Ananta says", abs(shown - live_b["last"]) < 1.0,
            f"screen {bank.get('value')} ({bank.get('sub2')}); Ananta {live_b['last']:,.2f} ({t['index_now'].get('kind')})")
    # E2 the managed plan on Money against the today-block
    plan = (surfaces.money(full=True).get("plan") or {})
    scr = {b.get("symbol") for b in plan.get("buys") or []}
    said = set(re.findall(r"-> (\w+)", str((t.get("managed_today") or {}).get("pairs") or "")))
    if scr or said:
        row("Money screen managed buys = what Ananta says", scr == said or not said, f"screen {sorted(scr)}; Ananta {sorted(said)}")
    # E3 the options line's open positions on the screens against its ledger
    o = views.options()
    scr_open = {(x.get("index"), x.get("point")) for x in (o.get("decisions_today") or []) if str(x.get("exit") or "").upper() == "NEXTOPEN"}
    led = {(x.get("index"), x.get("point")) for x in ((t.get("options_today") or {}).get("taken") or []) if str(x.get("exit") or "").upper() == "NEXTOPEN"}
    if led or scr_open:
        row("options screen trades = the options ledger", scr_open == led, f"screen {sorted(scr_open)}; ledger ({t['options_today'].get('day')}) {sorted(led)}")
    return out


def run() -> dict:
    from jarvis.india import views
    prod = producers()
    rows = routes(prod)
    rm = views.readmodel()
    checks = [{"check": f"route: {r['pattern']}", "state": "FAIL", "words": f"{r['pattern']} (e.g. {r['example']}) is written by a job but nothing Ananta "
               "reads uses it and it is not marked internal: a fact Ananta cannot say"} for r in rows if r["route"] == "NONE"]
    checks += behind(rows, rm.get("built_at"))
    checks += stale_summaries()
    try:
        checks += same_number()
    except Exception as e:  # noqa: BLE001
        checks.append({"check": "same number", "state": "FAIL", "words": f"the comparison crashed: {type(e).__name__}: {str(e)[:160]}"})
    fails = [c for c in checks if c["state"] == "FAIL"]
    by = {k: sum(1 for r in rows if r["route"] == k) for k in ("live", "nightly", "feeds", "copied", "internal", "NONE")}
    rep = {"at": dt.datetime.now().isoformat(timespec="minutes"), "read_model_built": rm.get("built_at"), "files": len(rows), "routes": by,
           "fails": len(fails), "checks": checks, "rows": [{k: r[k] for k in ("pattern", "route", "daytime", "why")} | {"written": dt.datetime.fromtimestamp(r["mtime"]).isoformat(timespec="minutes")} for r in rows]}
    rep["words"] = (f"Fact map {rep['at']}: {len(rows)} kinds of file written in {WINDOW_DAYS} days; {by['live']} read live, {by['nightly']} after the nightly build, "
                    f"{by['feeds']} feed another file, {by['copied']} copied into words by hand, {by['internal']} internal, {by['NONE']} with no route. " + (f"{len(fails)} FAIL: " + "; ".join(c['check'] for c in fails[:6]) if fails else "No FAIL."))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "latest.json").write_text(json.dumps(rep, indent=1, ensure_ascii=False))
    md = [f"# Fact map {rep['at']}", "", rep["words"], "", "| check | state | words |", "|---|---|---|"]
    md += [f"| {c['check']} | {c['state']} | {c['words']} |" for c in checks]
    md += ["", "| file | route | written | why |", "|---|---|---|---|"] + [f"| {r['pattern']} | {r['route']}{' (daytime)' if r['daytime'] else ''} | {r['written']} | {r['why'] or ''} |" for r in rep["rows"]]
    (OUT / "latest.md").write_text("\n".join(md) + "\n")
    return rep


def main() -> int:
    rep = run()
    print(rep["words"])
    for c in rep["checks"]:
        if c["state"] != "PASS":
            print(f"  {c['state']}: {c['words']}")
    if rep["fails"] and "--push" in sys.argv:
        try:
            from jarvis.india import replay
            replay._ntfy("Ananta fact map", rep["words"][:480])
        except Exception as e:  # noqa: BLE001
            print(f"push skipped: {e}")
    return 1 if rep["fails"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
