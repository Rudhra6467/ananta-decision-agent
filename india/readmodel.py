"""V0 India read model: one read-only JSON per session, built from the ledgers and manifests after the evening jobs.
  python -m india.readmodel build [YYYY-MM-DD]   -> <data dir>/readmodel/<day>.json and readmodel/latest.json, and registrations/india_readmodel.md
  python -m india.readmodel show                  prints the latest as plain text
Rules: derived numbers only (never a raw NSE or Kite row); every section names the file it came from, so each number traces to a ledger line;
nothing here reads sealed data, touches Kite, or writes to a ledger. The India app shell (V1), Ask (V2), voice (V3) and father mode read this
file and nothing else, so what is not here cannot be said. A section whose source is missing says so ("status": "missing") and never guesses.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from collections import Counter
from pathlib import Path

from india import paths

RULES = "readmodel-v0-2026-10-22"
REG = Path(__file__).parent / "registrations"
REF_POLICY = "hold_20d"       # the one exit shown per campaign in the stock-book summary (every policy stays in marks.jsonl)
CAMPAIGN_WORDS = {"BRK": "20-session breakout on volume", "PULL": "pullback in an uptrend", "REV": "oversold reversal (RSI under 30, P01)",
                  "CTL": "random control: no edge is claimed, it is the yardstick"}


def rm_dir() -> Path:
    d = paths.data_dir() / "readmodel"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _load(p: Path) -> dict | list | None:
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return None


def _jsonl(p: Path) -> list[dict]:
    try:
        return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
    except (OSError, ValueError):
        return []


def _missing(src: Path) -> dict:
    return {"status": "missing", "source": str(src)}


def _pct(x) -> str:
    return "n/a" if x is None else f"{x * 100:+.1f}%"


# ---------------------------------------------------------------------------------------------------------------- sections

def market(day: str) -> dict:
    src = paths.data_dir() / "paper" / "decisions" / f"{day}.json"
    j = _load(src)
    if not j or "context" not in j:
        return _missing(src)
    c = dict(j["context"])
    if c.get("nifty_close") is None:
        # 25 Oct: the decision was taken while the index download was down (Kite sign-in lost), so its context has no Nifty. Once the
        # index is fetched later, read the day's close and averages from it (sealed purpose paper_context, the same reader the engine uses)
        try:
            from india import sealed
            import datetime as _dt
            ix = sealed.read_index("paper_context", (_dt.date.fromisoformat(day) - _dt.timedelta(days=330)).isoformat(), ["NIFTY 50"])   # inside the 460-day cap
            ix = ix[ix["date"].astype(str).str[:10] <= day].sort_values("date")
            if len(ix) >= 200 and str(ix["date"].iloc[-1])[:10] == day:
                cl = ix["close"].astype(float)
                c["nifty_close"] = float(cl.iloc[-1])
                c["nifty_vs_sma50"] = float(cl.iloc[-1] / cl.tail(50).mean() - 1)
                c["nifty_vs_sma200"] = float(cl.iloc[-1] / cl.tail(200).mean() - 1)
        except Exception:  # noqa: BLE001  the section still says what it can
            pass
    if c.get("vix_close") is None:
        # 26 Oct: the same gap for the fear gauge: the decision recorded no VIX (stale: last row 22 Oct) and the morning view read 15.73 beside 16.86.
        # Fill the day's own close (and its distance from the 50-day average) from the index, the same reader the Nifty fill uses.
        try:
            from india import sealed
            import datetime as _dt
            ix = sealed.read_index("paper_context", (_dt.date.fromisoformat(day) - _dt.timedelta(days=330)).isoformat(), ["INDIA VIX"])
            ix = ix[ix["date"].astype(str).str[:10] <= day].sort_values("date")
            if len(ix) >= 50 and str(ix["date"].iloc[-1])[:10] == day:
                cl = ix["close"].astype(float)
                c["vix_close"] = float(cl.iloc[-1])
                c["vix_vs_sma50"] = float(cl.iloc[-1] / cl.tail(50).mean() - 1)
        except Exception:  # noqa: BLE001
            pass
    v50, v200 = c.get("nifty_vs_sma50"), c.get("nifty_vs_sma200")
    if v50 is None or v200 is None:
        state = "unknown"
    elif v50 > 0 and v200 > 0:
        state = "above_both"
    elif v50 < 0 and v200 < 0:
        state = "below_both"
    else:
        state = "mixed"
    words = {"above_both": "Nifty is above both its 50- and 200-day averages: an uptrend", "below_both": "Nifty is below both its 50- and 200-day averages: a downtrend",
             "mixed": "Nifty is between its 50- and 200-day averages: no clear trend", "unknown": "Nifty's trend could not be read"}[state]
    nc = newer_closes(day)
    return {"status": "ok", "source": str(src), "data_through": j.get("data_through", day), "nifty_close": c.get("nifty_close"), "nifty_vs_sma50": v50, "nifty_vs_sma200": v200,
            "trend_state": state, "vix_close": c.get("vix_close"), "vix_vs_sma50": c.get("vix_vs_sma50"),
            "breadth_200d_liquid": c.get("breadth200_liq"), "breadth_50d_liquid": c.get("breadth50_liq"),
            "newer_closes": nc,
            "words": f"{words}; {_pct(v50)} from the 50-day, {_pct(v200)} from the 200-day; {round((c.get('breadth200_liq') or 0) * 100)}% of the liquid 250 are above their 200-day"}


def newer_closes(day: str) -> dict:
    """26 Oct (Madhav's yes): the stock-book decision is written at 22:30 Toronto, but the day's index closes land at the 12:30 fetch. When the index
    is ahead of the decision day, say so with the newer closes (the decision-linked numbers above stay as decided: the allocator reads them).
    Same reader as the technicals panel (sealed purpose paper_context)."""
    try:
        from india import technicals
        fresh = technicals.latest_index(["NIFTY 50", "NIFTY BANK", "INDIA VIX"])
    except Exception:  # noqa: BLE001  no index files (or none newer): nothing to add
        return {}
    out = {n: {"date": f["date"], "close": f["close"], "d1": f["d1"]} for n, f in fresh.items() if str(f.get("date")) > day}
    if not out:
        return {}
    out["words"] = "; ".join(f"{n} {v['close']:,.2f} on {v['date']} ({_pct(v['d1'])})" for n, v in out.items() if isinstance(v, dict))
    out["meaning"] = f"the index data runs past the decision day {day}; the section above is as decided on {day}, these are the newer closes"
    return out


def call(day: str) -> dict:
    src = paths.data_dir() / "paper" / "calls.jsonl"
    rows = _jsonl(src)
    if not rows:
        return _missing(src)
    calls = [r for r in rows if r.get("kind") == "call"]
    scores = [r for r in rows if r.get("kind") == "score"]
    today = next((r for r in reversed(calls) if r.get("data_through") == day), calls[-1] if calls else None)
    hits = sum(1 for s in scores if s.get("score") == 1)
    null_hits = sum(1 for s in scores if s.get("null_score") == 1)
    return {"status": "ok", "source": str(src), "data_through": today.get("data_through") if today else None, "call": today.get("call") if today else None,
            "rule": today.get("rule") if today else None, "scored": len(scores), "hits": hits, "null_hits": null_hits,
            "words": (f"Daily call for the next session: {today.get('call')} (mechanical rule {today.get('rule')}); so far {hits} of {len(scores)} calls right "
                      f"against {null_hits} for the coin flip") if today else "no call written"}


def stock_book(day: str) -> dict:
    pdir = paths.data_dir() / "paper"
    st = _load(pdir / "state.json")
    if not st or "trades" not in st:
        return _missing(pdir / "state.json")
    open_ = {}
    closed = Counter()
    for t in st["trades"].values():
        if t.get("book") != "exec":
            continue
        if t.get("status") == "open":
            k = (t["campaign"], t["sid"])
            if t.get("policy") == REF_POLICY or k not in open_:
                e, l = t.get("entry_adj"), t.get("last_close_adj")
                open_[k] = {"symbol": t.get("symbol"), "campaign": t["campaign"], "entry_date": t.get("entry_date"), "entry": e, "last_close": l, "last_date": t.get("last_date"),
                            "pnl_pct": (l / e - 1) if e and l else None, "shown_policy": t.get("policy")}
        else:
            closed[t["campaign"]] += 1
    marks = _jsonl(pdir / "marks.jsonl")
    latest = {}
    for m in marks:
        if m.get("book") == "exec" and m.get("policy") == REF_POLICY:
            latest[m["campaign"]] = m
    by_campaign = {}
    for camp, m in latest.items():
        by_campaign[camp] = {"what": CAMPAIGN_WORDS.get(camp, camp), "open": m.get("open"), "closed": m.get("closed"), "realised_inr": m.get("realised_inr"),
                             "open_unrealised_inr": m.get("open_unrealised_inr"), "win_rate": m.get("win_rate"), "expectancy_R": m.get("expectancy_R"),
                             "marked_at": m.get("at"), "policy_shown": REF_POLICY}
    positions = sorted(open_.values(), key=lambda r: (r["campaign"], -(r["pnl_pct"] or 0)))
    try:   # flag 44 (26 Oct): closed and open counted apart, so a win rate over closed trades is never read as the whole book
        from india import bookstats

        cvo = bookstats.split(bookstats.trade_rows(st, REF_POLICY))
    except Exception as e:   # noqa: BLE001
        cvo = {"status": "unavailable", "why": f"{type(e).__name__}: {e}"[:160]}
    return {"status": "ok", "source": f"{pdir / 'state.json'} (exec book) and {pdir / 'marks.jsonl'} (policy {REF_POLICY})", "rules": st.get("version"),
            "open_positions": len(positions), "positions": positions[:40], "by_campaign": by_campaign, "closed_vs_open": cvo,
            "note": "the research book's scale unit is Rs 50,000 per trade (results in % and R); the real paper capital is Rs 60,000 and sits in the SP1 line"}


def decisions_today(day: str) -> dict:
    src = paths.data_dir() / "paper" / "decisions" / f"{day}.json"
    j = _load(src)
    if not j:
        return _missing(src)
    chosen = []
    for s in j.get("signals", []):
        camp = s.get("campaign")
        why = CAMPAIGN_WORDS.get(camp, camp)
        bits = []
        if s.get("vol_ratio20") is not None:
            bits.append(f"volume {s['vol_ratio20']:.1f}x its 20-day")
        if s.get("dist_sma20") is not None:
            bits.append(f"{_pct(s['dist_sma20'])} from the 20-day average")
        if s.get("dist_sma200") is not None:
            bits.append(f"{_pct(s['dist_sma200'])} from the 200-day")
        if s.get("liq_rank") is not None:
            bits.append(f"liquidity rank {s['liq_rank']}")
        chosen.append({"symbol": s.get("symbol"), "campaign": camp, "close": s.get("close"), "why": why + (": " + ", ".join(bits) if bits else ""),
                       "entry": "next session's open, Rs 50,000 notional, every registered exit tracked"})
    return {"status": "ok", "source": str(src), "rules": j.get("rules"), "decided_at": j.get("decided_at"), "data_through": j.get("data_through"),
            "universe": j.get("universe"), "candidates": j.get("candidates"), "chosen": chosen, "sha256": j.get("sha256"), "inputs": decision_inputs(j)}


def decision_inputs(j: dict) -> dict:
    """The stale-input mark (Madhav, 25 Oct 2026: marked, never stopped). Decisions from 25 Oct carry it; older decision files are never
    rewritten, so their mark is read from the context they recorded (the same index statuses)."""
    if j.get("inputs"):
        return j["inputs"]
    ctx = j.get("context") or {}
    stale = [f"{n}: {ctx.get(t + '_status')}" for t, n in (("nifty", "Nifty 50"), ("vix", "India VIX")) if ctx.get(t + "_status") not in (None, "ok")]
    if ctx.get("small_ratio_status"):
        stale.append(f"small-cap ratio: {ctx['small_ratio_status']}")
    if ctx.get("index_status"):
        stale.append(f"index file: {ctx['index_status']}")
    return {"stale": stale, "marked": bool(stale), "rule": "stale inputs are marked, never stopped or dropped (Madhav, 25 Oct 2026)", "derived": "from the recorded context"}


def stale_sessions() -> list[dict]:
    """Every decision day whose inputs were stale, for the evidence counts and the app."""
    out = []
    for p in sorted((paths.data_dir() / "paper" / "decisions").glob("20*.json")):
        if p.name.endswith("universe.json"):
            continue
        j = _load(p) or {}
        m = decision_inputs(j)
        if m["marked"]:
            out.append({"day": j.get("data_through") or p.stem, "stale": m["stale"]})
    return out


def sp1(day: str) -> dict:
    d = paths.data_dir() / "paper" / "sp1"
    allr = _jsonl(d / "decisions.jsonl")
    # 26 Oct: SP1 trades live in the morning, before the nightly data reaches `day`; the read model said "session lost" for 23 Oct while the
    # 26 Oct session had run and been scored. Show the newest SP1 session on or after `day`, always named by its date.
    newest = max([str(r.get("date")) for r in allr if r.get("date") and str(r.get("date")) >= day] or [day])
    rows = [r for r in allr if r.get("date") == newest]
    book = _load(d / "book.json") or {}
    errors = [r.get("error") for r in rows if r.get("kind") == "error"]
    decisions = [{"index": r.get("index"), "point": r.get("point"), "action": (r.get("choice") or {}).get("action"), "exit": (r.get("choice") or {}).get("exit"),
                  "situation": r.get("situation")} for r in rows if r.get("kind") == "decision"]
    status = "ok" if decisions else ("lost" if errors else ("no_rows" if (d / "decisions.jsonl").exists() else "missing"))
    try:
        x = dt.date.fromisoformat(newest)
        when = f"{x:%a} {x.day} {x:%b}"
    except ValueError:
        when = newest
    trades = [f"{q['index']} at {q.get('point')} ({'long' if (r.get('choice') or {}).get('dir', 1) > 0 else 'short'}, exit {q.get('exit')})"
              for q, r in zip(decisions, [r for r in rows if r.get("kind") == "decision"]) if q.get("action")]
    bi = book.get("by_index") or {}
    scored = "; ".join(f"{k}: {v.get('trades')} scored trade(s), index {v.get('index_proxy_sum_bps', 0):+.0f} bp, one option lot Rs {v.get('option_1lot_rs_realistic_fill', 0):,.0f} "
                       f"with realistic fills" for k, v in bi.items() if v.get("trades"))
    words = (f"{when}: session lost: " + errors[0]) if status == "lost" and errors else (
        f"{when}: {len(decisions)} index decisions recorded" + (f", traded {', '.join(trades)}" if trades else ", no trade") if decisions else f"{when}: no SP1 rows")
    if scored:
        words += f". Book over {book.get('sessions')} scored session(s): {scored}"
    return {"status": status, "date": newest, "source": f"{d / 'decisions.jsonl'} and {d / 'book.json'}", "decisions": decisions, "errors": errors[:3],
            "book": {"sessions": book.get("sessions"), "by_index": bi}, "capital_inr": 60000, "words": words}


def learning(day: str) -> dict:
    mdir = paths.manifest_dir()
    out = {}
    m = _load(mdir / f"missed_{day}.json")
    out["missed"] = ({"status": m.get("status"), "source": str(mdir / f"missed_{day}.json"), "summary": m.get("summary"), "line": m.get("md_line"), "drafts_written": m.get("drafts_written")}
                     if m else _missing(mdir / f"missed_{day}.json"))
    o = _load(mdir / f"others_{day}.json")
    if o:
        h1 = (o.get("by_h") or {}).get("1") or {}
        out["league"] = {"status": o.get("status"), "source": str(mdir / f"others_{day}.json"), "h1": {k: h1.get(k) for k in ("hindsight_mean", "market_mean", "ananta_mean", "ananta_n", "ananta_pct_vs_random", "coverage")},
                         "informed": o.get("informed"), "league": o.get("league"), "drafts_written": o.get("drafts_written")}
    else:
        out["league"] = _missing(mdir / f"others_{day}.json")
    drafts = _jsonl(REG / "missed_drafts.jsonl")
    out["drafts"] = {"source": str(REG / "missed_drafts.jsonl"), "total": len(drafts), "open": sum(1 for d in drafts if str(d.get("status", "DRAFT")).upper() in ("DRAFT", "OPEN"))}
    return out


def research() -> dict:
    from india import registry, tracker

    out = {"source": "india/tracker.py evaluate() and registrations/registry (ledger lines)"}
    try:
        data, studies = tracker.evaluate()
        out["studies"] = {"ready": sum(s["state"] == "READY" for s in studies), "blocked": sum(s["state"] == "BLOCKED" for s in studies), "with_results": sum(bool(s["progress"]) for s in studies)}
        out["gate_counters"] = {d["id"]: d["live"] for d in data if d["id"] in ("D15", "D16", "D32")}
        g02 = next((s for s in studies if s["id"] == "G02"), None)
        out["gate"] = {"state": g02["state"], "waiting_on": g02["waiting_on"]} if g02 else None
    except Exception as e:   # noqa: BLE001 - the read model must build even when the catalog is busy
        out["studies"] = {"status": "unavailable", "why": str(e)[:120]}
    try:   # 25 Oct audit: the India exam (india/exam.py), shown as a gate row and on the Evidence tracker
        from india import exam

        out["exam"] = exam.summary()
    except Exception as e:   # noqa: BLE001
        out["exam"] = {"words": f"unavailable: {str(e)[:80]}"}
    # audit 25 Oct: count each (study, version) once, at its latest result; the raw ledger also holds re-runs of the same version
    latest = {}
    for r in registry._rows():
        if r.get("kind") == "result" and r.get("verdict"):
            latest[(r["study"], r["variant"])] = r["verdict"]
    out["verdicts"] = dict(Counter(latest.values()))
    out["versions_tested"] = len(latest)
    out["ledger_result_rows"] = sum(1 for r in registry._rows() if r.get("kind") == "result")
    out["stale_input_sessions"] = stale_sessions()
    g01 = _load(paths.manifest_dir() / "g01_exit_book.json")
    out["exit_book"] = ({"source": str(paths.manifest_dir() / "g01_exit_book.json"), "chosen": {k: v.get("policy") for k, v in g01.get("chosen", {}).items()}} if g01
                        else _missing(paths.manifest_dir() / "g01_exit_book.json"))
    return out


def jobs() -> dict:
    from india import morning

    try:
        r = morning.build()
    except Exception as e:   # noqa: BLE001
        return {"status": "unavailable", "why": str(e)[:120]}
    return {"status": "ok", "source": "india/morning.py build() (launchd logs and proof-of-work files)", "signin": r.get("signin"),
            "jobs": [{"label": j["label"].replace("com.ananta.india.", ""), "ok": not j.get("problems") and not j.get("errors"), "problems": j.get("problems", [])[:2]} for j in r.get("jobs", [])],
            "lost": r.get("lost", [])[:6]}


def guardrails() -> dict:
    cfg = _load(Path(__file__).parent / "paper_config.json") or {}
    s = cfg.get("survival", {})
    return {"source": "india/paper_config.json survival", "daily_loss_limit_pct": s.get("daily_loss_limit_pct"), "pause_drawdown_pct": s.get("pause_drawdown_pct"),
            "state": "recorded, not enforced (paper); enforcement is W7 live-readiness work",
            "words": f"Stop for the day at a {s.get('daily_loss_limit_pct')}% loss; pause new entries when {s.get('pause_drawdown_pct')}% below the high-water mark until Madhav resumes"}


# ---------------------------------------------------------------------------------------------------------------- build and render

def latest_day() -> str:
    """The last session with a stock-book decision file (the 22:30 Toronto job writes it): the day the read model describes."""
    d = paths.data_dir() / "paper" / "decisions"
    days = sorted(p.stem for p in d.glob("????-??-??.json")) if d.exists() else []
    if not days:
        raise RuntimeError("no stock-book decision file yet; the read model has nothing to describe")
    return days[-1]


def reconstruction(day: str) -> dict:
    """RX-IN (india/reconstruct.py): the session card's headline, its findings and where every rule stands on the evidence staircase."""
    src = paths.data_dir() / "paper" / "reconstruction" / f"{day}.json"
    c = _load(src)
    if not c:
        return _missing(src)
    st = _load(REG / "evidence_staircase.json") or {}
    f = c.get("findings") or []
    rv = c.get("reviews") or {}
    return {"status": "ok", "source": str(src), "rules": c.get("rules"), "headline": c.get("headline"), "built_at": c.get("built_at"),
            "market_words": (c.get("market") or {}).get("words"), "people_words": (c.get("people") or {}).get("words"), "ananta_words": (c.get("ananta") or {}).get("words"),
            "not_done_words": (c.get("not_done") or {}).get("words"), "league_words": ((c.get("people") or {}).get("league") or {}).get("words"),
            "reviews": {"count": rv.get("count", 0), "tags": rv.get("tags") or {}, "exit_date": rv.get("reviewed_exit_date")},
            "findings": [{k: x.get(k) for k in ("type", "key", "lane", "state", "words", "day")} for x in f],
            "staircase": {"words": st.get("words"), "rules": {k: {"step": v.get("step"), "shadow_sessions": v.get("shadow_sessions"), "shadow_bar": v.get("shadow_bar"),
                                                                   "beats": v.get("independent_sessions_beating_random_and_market"), "beats_bar": v.get("independent_bar")} for k, v in (st.get("rules") or {}).items()},
                          "admitted": st.get("admitted") or [], "queue": st.get("queue") or {}},
            "meaning": "the nightly reconstruction: what the market and other participants did, what Ananta did and did not do, the trade reviews, the findings and their lane; "
                       "the staircase NOTED > DRAFT > REGISTERED > TESTED > SHADOW > ADMITTED > LIVE_ELIGIBLE says what the allocated capital may use (ADMITTED only)"}


def build(day: str | None = None) -> dict:
    from india import morning

    day = day or latest_day()
    hol = morning._holidays()
    nxt = morning.next_session(dt.date.fromisoformat(day) + dt.timedelta(days=1), hol).isoformat()   # morning's helper is "on or after"
    rm = {"rules": RULES, "built_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "data_through": day, "next_session": nxt,
          "market": market(day), "call": call(day), "stock_book": stock_book(day), "decisions_today": decisions_today(day), "sp1": sp1(day),
          "learning": learning(day), "research": research(), "jobs": jobs(), "guardrails": guardrails(), "reconstruction": reconstruction(day)}
    try:   # 26 Oct (Madhav: crossovers, RSI, MACD, support and resistance, volume): the technicals panel and what was ever tested about each
        from india import technicals

        rm["technicals"] = technicals.section()
        rm["indicator_knowledge"] = technicals.knowledge()
    except Exception as e:   # noqa: BLE001 - the read model must build even if the panel fails; the section says why
        rm["technicals"] = {"status": "unavailable", "why": f"{type(e).__name__}: {e}"[:160]}
    try:   # 26 Oct: the market-context feed (rupee, dollar, crude, US yields and indices, the fear gauges, institutions' flows): explanation only
        from india import marketcontext

        rm["market_context"] = marketcontext.section()
    except Exception as e:   # noqa: BLE001
        rm["market_context"] = {"status": "unavailable", "why": f"{type(e).__name__}: {e}"[:160]}
    try:   # 26 Oct (Madhav: yes to all): expectancy, Sharpe-like ratio, holdings correlation and slippage, each with its own "too few" words
        from india import bookstats

        rm["book_stats"] = bookstats.build()
    except Exception as e:   # noqa: BLE001
        rm["book_stats"] = {"status": "unavailable", "why": f"{type(e).__name__}: {e}"[:160]}
    rm["missing"] = [k for k, v in rm.items() if isinstance(v, dict) and v.get("status") == "missing"]
    rm["brief"] = brief(rm)
    body = json.dumps(rm, indent=1, default=str)
    (rm_dir() / f"{day}.json").write_text(body)
    (rm_dir() / "latest.json").write_text(body)
    (REG / "india_readmodel.md").write_text(markdown(rm))
    return rm


def brief(rm: dict) -> list[str]:
    """Three to five plain sentences, each from a section above: what the app's first screen and the morning voice say."""
    out = []
    m, c, sb, d, s, L = rm["market"], rm["call"], rm["stock_book"], rm["decisions_today"], rm["sp1"], rm["learning"]
    if m.get("status") == "ok":
        # request 85 (24-25 Oct): with the Kite sign-in lost there is no Nifty close for the day, and formatting None crashed the whole
        # read model (the app, the Ask and the voice then read a stale day). Say it is missing instead.
        close = f"Nifty {m['nifty_close']:,.0f}" if m.get("nifty_close") is not None else "no Nifty close for the day (the index download did not run)"
        out.append(f"Through {m['data_through']}: {close}. {m['words']}.")
    if c.get("status") == "ok":
        out.append(c["words"] + ".")
    if sb.get("status") == "ok":
        tot = sum((v.get("realised_inr") or 0) for v in sb["by_campaign"].values())
        out.append(f"Stock paper book: {sb['open_positions']} open positions; realised Rs {tot:+,.0f} on the {REF_POLICY} exits across campaigns.")
    if d.get("status") == "ok":
        by = Counter(x["campaign"] for x in d["chosen"])
        out.append("New for the next session: " + (", ".join(f"{n} {k}" for k, n in sorted(by.items())) or "nothing") + ".")
        if (d.get("inputs") or {}).get("marked"):
            out.append("Marked: these picks were made on stale inputs (" + "; ".join(d["inputs"]["stale"]) + ").")
    if s.get("status") in ("ok", "lost"):
        out.append("SP1 index line: " + s["words"] + ".")
    lg = L.get("league", {})
    if lg.get("status") == "ok" and lg.get("h1", {}).get("coverage"):
        cov = lg["h1"]["coverage"]
        out.append(f"Against the reference traders (1 session): Ananta held {cov.get('TAKEN', 0)} of the top 20 trips, passed on {cov.get('PASSED', 0)}, had no rule for {cov.get('NOT_COVERED', 0)}; "
                   f"its picks sat at the {round((lg['h1'].get('ananta_pct_vs_random') or 0) * 100)}th percentile of random.")
    if rm["missing"]:
        out.append("Not available for this session: " + ", ".join(rm["missing"]) + ".")
    return out


def markdown(rm: dict) -> str:
    L = [f"# India read model (V0) — data through {rm['data_through']}, built {rm['built_at']}", "", "Rules " + rm["rules"] + ". Every number below traces to the file named in its section of readmodel/latest.json; nothing here is typed by hand.", "",
         "## Brief", ""] + [f"- {s}" for s in rm["brief"]] + ["", "## Decisions for the next session", ""]
    d = rm["decisions_today"]
    if d.get("status") == "ok":
        L += ["| symbol | campaign | close | why |", "|---|---|---|---|"] + [f"| {x['symbol']} | {x['campaign']} | {x['close']} | {x['why']} |" for x in d["chosen"]]
    else:
        L.append("(no decision file)")
    L += ["", "## Stock paper book (exec, policy shown: " + REF_POLICY + ")", ""]
    sb = rm["stock_book"]
    if sb.get("status") == "ok":
        L += ["| campaign | what | open | closed | realised Rs | unrealised Rs | win rate | expectancy R |", "|---|---|---|---|---|---|---|---|"]
        L += [f"| {k} | {v['what']} | {v['open']} | {v['closed']} | {(v['realised_inr'] or 0):+,.0f} | {(v['open_unrealised_inr'] or 0):+,.0f} | {v['win_rate']} | {v['expectancy_R']} |" for k, v in sb["by_campaign"].items()]
    L += ["", "## SP1 index line", "", rm["sp1"].get("words", ""), "", "## Jobs", ""]
    j = rm["jobs"]
    if j.get("status") == "ok":
        L += [f"- {x['label']}: {'ok' if x['ok'] else 'PROBLEM ' + '; '.join(x['problems'])}" for x in j["jobs"]] + ["", f"Next sign-in: {j.get('signin')}"]
    r = rm["research"]
    L += ["", "## Research", "", f"- studies: {r.get('studies')}", f"- gate G02: {r.get('gate')} counters {r.get('gate_counters')}", f"- registry verdicts: {r.get('verdicts')}",
          f"- exit book (G01): {r.get('exit_book', {}).get('chosen')}", "", "## Guardrails", "", rm["guardrails"]["words"] + " — " + rm["guardrails"]["state"], ""]
    return "\n".join(L)


if __name__ == "__main__":
    paths.ensure()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "build"
    if cmd == "build":
        rm = build(sys.argv[2] if len(sys.argv) > 2 else None)
        print(f"read model built for {rm['data_through']}: missing {rm['missing'] or 'nothing'}")
        for s in rm["brief"]:
            print("  " + s)
    elif cmd == "show":
        rm = _load(rm_dir() / "latest.json")
        print(markdown(rm) if rm else "no read model yet")
    else:
        print("usage: python -m india.readmodel [build [YYYY-MM-DD]|show]")
        sys.exit(64)
