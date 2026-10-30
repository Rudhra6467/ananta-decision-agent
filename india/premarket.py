"""The pre-market inputs (Phase 4.1 of the 29 Oct 2026 plan): what a trader's morning routine needs, what Ananta has, what is free to add,
what has no free source; and the two free inputs added here.

  python -m india.premarket chain [day]     the index option chain's end-of-day shape for the last session: put-call ratio, max pain, the biggest
                                            open-interest strikes (the "walls") of the nearest expiry -> manifests/premarket_chain.json
  python -m india.premarket ban             the F&O ban list for the next session from NSE (free) -> bronze/fo_secban/<date>.csv, manifests/fo_ban.json
  python -m india.premarket gaps            the input gap table -> manifests/premarket_inputs.json and registrations/premarket_inputs.md
  python -m india.premarket all             the three, in that order (the evening chain)

The chain read goes through india.sealed.read_chain (purpose chain_brief, one live day, nothing scored). Free sources only (Madhav, 29 Oct).
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

from india import paths

REG_DIR = Path(__file__).resolve().parent / "registrations"
BAN_URL = "https://nsearchives.nseindia.com/content/fo/fo_secban.csv"


def _man() -> Path:
    p = paths.manifest_dir()
    p.mkdir(parents=True, exist_ok=True)
    return p


def _last_session() -> str | None:
    rm = paths.data_dir() / "readmodel" / "latest.json"
    try:
        return json.loads(rm.read_text()).get("data_through")
    except (OSError, ValueError):
        return None


def chain(day: str | None = None) -> dict:
    from india import sealed
    import pandas as pd
    day = day or _last_session()
    out = {"day": day, "built_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "indices": {}}
    if not day:
        out["status"] = "no last session"
        return out
    try:
        df = sealed.read_chain("chain_brief", day)
    except Exception as e:  # noqa: BLE001
        out["status"] = f"unavailable: {type(e).__name__}: {str(e)[:120]}"
        (_man() / "premarket_chain.json").write_text(json.dumps(out, indent=1, default=str))
        return out
    if not len(df):
        out["status"] = "no rows"
        (_man() / "premarket_chain.json").write_text(json.dumps(out, indent=1, default=str))
        return out
    df["expiry"] = pd.to_datetime(df["expiry"]).dt.date
    for sym, g in df.groupby("symbol"):
        exps = sorted(e for e in g["expiry"].unique() if e >= dt.date.fromisoformat(day))
        if not exps:
            continue
        near = g[g["expiry"] == exps[0]]
        ce, pe = near[near["opt_type"] == "CE"], near[near["opt_type"] == "PE"]
        oi_c, oi_p = float(ce["open_interest"].sum()), float(pe["open_interest"].sum())
        pcr = oi_p / oi_c if oi_c > 0 else None
        spot = float(near["underlying"].dropna().iloc[0]) if near["underlying"].notna().any() else None
        # max pain: the strike where the total intrinsic value of all open options is smallest
        strikes = sorted(near["strike"].unique())
        pain = {}
        c_oi = ce.groupby("strike")["open_interest"].sum()
        p_oi = pe.groupby("strike")["open_interest"].sum()
        for k in strikes:
            pain[k] = sum(max(k - s, 0) * c_oi.get(s, 0) for s in c_oi.index) + sum(max(s - k, 0) * p_oi.get(s, 0) for s in p_oi.index)
        max_pain = min(pain, key=pain.get) if pain else None
        walls_c = c_oi.sort_values(ascending=False).head(3)
        walls_p = p_oi.sort_values(ascending=False).head(3)
        out["indices"][sym] = {"nearest_expiry": str(exps[0]), "spot_underlying": spot, "pcr_oi": round(pcr, 3) if pcr else None, "max_pain": max_pain,
                               "call_walls": [{"strike": float(k), "oi": int(v)} for k, v in walls_c.items()], "put_walls": [{"strike": float(k), "oi": int(v)} for k, v in walls_p.items()],
                               "total_oi": {"calls": int(oi_c), "puts": int(oi_p)},
                               "words": (f"{sym}: nearest expiry {exps[0]}; put-call ratio {pcr:.2f} ({'more puts than calls open' if pcr and pcr > 1 else 'more calls than puts open'}); "
                                         f"max pain {max_pain:,.0f}; biggest call wall {walls_c.index[0]:,.0f}, biggest put wall {walls_p.index[0]:,.0f}" if pcr else f"{sym}: no open interest read")}
    out["status"] = "ok"
    out["note"] = ("end-of-day open interest of the last session; F03 found PCR extremes and the max-pain pin had no edge (OPPOSITE / REJECTED), so these "
                   "are context, never a signal")
    (_man() / "premarket_chain.json").write_text(json.dumps(out, indent=1, default=str))
    return out


def ban() -> dict:
    from india import nse
    f = nse.Fetcher(rate_s=1.0)
    status, body, _secs = f.get(BAN_URL)
    out = {"fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "status": status, "source": BAN_URL}
    if status != 200 or not body:
        out["symbols"], out["words"] = None, f"the F&O ban list could not be fetched (HTTP {status})"
        (_man() / "fo_ban.json").write_text(json.dumps(out, indent=1))
        return out
    text = body.decode("utf-8", errors="replace")
    today = dt.datetime.now(dt.timezone(dt.timedelta(hours=5, minutes=30))).date().isoformat()
    d = paths.bronze("fo_secban")
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{today}.csv").write_text(text)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    syms = []
    for ln in lines[1:]:   # first line is a header like "Securities in Ban For Trade Date 30-OCT-2026"
        parts = [x.strip() for x in ln.split(",")]
        sym = parts[-1] if parts else ""
        if sym and sym.upper() == sym and not sym.startswith("SYMBOL"):
            syms.append(sym)
    out["header"] = lines[0] if lines else ""
    out["symbols"] = syms
    out["words"] = (f"F&O ban list ({out['header'][-11:] if out['header'] else today}): " + ", ".join(syms)) if syms else "no stock in the F&O ban list"
    (_man() / "fo_ban.json").write_text(json.dumps(out, indent=1))
    return out


def gaps() -> dict:
    """The routine against the inputs Ananta has, read from the manifests as they stand."""
    dc = {}
    try:
        dc = json.loads((_man() / "datacheck.json").read_text())
    except (OSError, ValueError):
        pass
    fresh = {r.get("input"): r for r in (dc.get("freshness") or [])}
    ch = {}
    try:
        ch = json.loads((_man() / "premarket_chain.json").read_text())
    except (OSError, ValueError):
        pass
    bn = {}
    try:
        bn = json.loads((_man() / "fo_ban.json").read_text())
    except (OSError, ValueError):
        pass

    def st(name: str) -> str:
        r = fresh.get(name) or {}
        return f"{'fresh' if r.get('ok') else 'stale'} ({r.get('as_of')})" if r else "not checked"

    rows = [
        {"input": "US close (S&P 500, Nasdaq, 10-year yield)", "have": "yes", "source": "FRED / us_close, nightly", "status": st("market context: SP500"), "decision": "in the brief"},
        {"input": "Asian markets at 08:30 IST (Nikkei, Hang Seng, Kospi)", "have": "no", "source": "no free intraday feed; previous closes only (stooq)", "status": "-", "decision": "left out: a stale close adds little; revisit if a free feed appears"},
        {"input": "GIFT Nifty", "have": "no", "source": "no free source", "status": "-", "decision": "left out; the opening update at 10:20 IST says what the open did"},
        {"input": "Crude and the dollar", "have": "yes, lagged", "source": "FRED (Brent 2 days, dollar index and rupee about 6 days)", "status": st("market context: DCOILBRENTEU"), "decision": "in the context with its lag said; same-day rupee from the RBI reference rate"},
        {"input": "Institutions' flows (FII/DII)", "have": "yes", "source": "NSE daily, evening", "status": st("market context: flows"), "decision": "in the brief"},
        {"input": "India VIX", "have": "yes", "source": "Kite index day file, evening", "status": st("market context: india_vix"), "decision": "in the brief"},
        {"input": "Option chain: PCR, max pain, OI walls", "have": "yes (added 30 Oct)", "source": "NSE F&O file, end of the last session, through the sealed firewall (chain_brief)", "status": ch.get("status", "not built"), "decision": "in the brief as context only (F03: no edge in PCR extremes or the pin)"},
        {"input": "Live option chain before the open", "have": "no", "source": "Kite quotes exist only from 09:15 (the recorder)", "status": "-", "decision": "left out before the open; the options line reads live quotes from 09:15"},
        {"input": "Results calendar and announcements", "have": "partly", "source": "NSE announcements (bronze daily, table built evening); board-meeting dates in the PR file", "status": st("announcements"), "decision": "the announcements table is in the Ask; a per-stock 'results today' flag is Phase 4 follow-up"},
        {"input": "F&O ban list", "have": "yes (added 30 Oct)", "source": "NSE fo_secban.csv, free, each evening for the next session", "status": (bn.get("words") or "not fetched")[:80], "decision": "in the brief; the paper book should not enter a banned name's F&O (it trades cash only, so a note)"},
        {"input": "Pre-open indicative (09:00-09:08 IST)", "have": "no", "source": "NSE site only; Kite stock quotes in pre-open possible, the index indicative is not", "status": "-", "decision": "left out; the opening update covers the open"},
        {"input": "Yesterday's practice book and the scorecard", "have": "yes", "source": "marks, forecasts ledger, daily call", "status": "ok", "decision": "in the brief ('our chances, honestly')"},
        {"input": "The holdings' grades and the allocation", "have": "yes", "source": "allocation ledger (autonomous)", "status": "ok", "decision": "in the brief"},
        {"input": "Which findings apply today", "have": "partly", "source": "the read model's indicator knowledge and the one map", "status": "ok", "decision": "the brief names the filters in force; per-pick 'which rule' is the decision journal"},
    ]
    out = {"built_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "rows": rows,
           "summary": {"have": sum(1 for r in rows if r["have"].startswith("yes")), "partly": sum(1 for r in rows if r["have"] == "partly"), "missing": sum(1 for r in rows if r["have"] == "no")}}
    (_man() / "premarket_inputs.json").write_text(json.dumps(out, indent=1))
    L = ["# The pre-market inputs: the routine against what Ananta has (Phase 4.1, generated by india.premarket)", "",
         f"As of {out['built_at'][:16]}Z. Free sources and proxies only (Madhav, 29 Oct 2026). Have {out['summary']['have']}, partly {out['summary']['partly']}, missing {out['summary']['missing']}.", "",
         "| input | have | source | status | decision |", "|---|---|---|---|---|"]
    L += [f"| {r['input']} | {r['have']} | {r['source']} | {r['status']} | {r['decision']} |" for r in rows]
    (REG_DIR / "premarket_inputs.md").write_text("\n".join(L) + "\n")
    return out


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "gaps"
    if cmd == "chain":
        print(json.dumps(chain(sys.argv[2] if len(sys.argv) > 2 else None), indent=1, default=str))
    elif cmd == "ban":
        print(json.dumps(ban(), indent=1))
    elif cmd == "gaps":
        print(json.dumps(gaps()["summary"], indent=1))
    elif cmd == "all":
        for fn in (chain, ban, gaps):
            try:
                r = fn()
                print(fn.__name__, (r.get("status") or r.get("words") or r.get("summary")))
            except Exception as e:  # noqa: BLE001
                print(fn.__name__, "failed:", type(e).__name__, str(e)[:120])
