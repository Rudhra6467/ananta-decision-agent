"""The India research tracker: every study, every data item it waits on, and a live status you can ask for.

  python -m india.tracker build     rewrite catalog tables data_needs and research_tracker, and registrations/research_tracker.md
  python -m india.tracker status    what is ready, what is waiting on which data, what is waiting on Madhav
  python -m india.tracker waiting   only the blocked studies, grouped by the data they wait for
A study is READY when every data item it needs is READY; otherwise it is BLOCKED and the status line names the blocker. Data items marked
auto are checked from the catalog (nightly runs, ledger snapshots, recorder days); the rest are set here when the work lands.
Study ids: S = lab tools, E = exits on stocks, I = opening and intraday, C = context and relationships, F = futures and options,
V = events and fundamentals, R = real intraday options, K = knowledge pass, G = synthesis and gate.
"""
from __future__ import annotations

import json
import sys

from india import catalog, paths

# id, name, state (READY / BUILD / WAIT_DATA / WAIT_TIME / WAIT_MADHAV / DECISION), eta, note
DATA = [
    ("D01", "Daily cash prices 1994-2026, adjusted close", "READY", "", "cm, cm_adj; 299/300 delivery check, 299/300 BSE check"),
    ("D02", "Delivery report 2003-2026", "READY", "", "silver/delivery"),
    ("D03", "Corporate actions, two records", "READY", "", "99.1% agreement; 237 A_ONLY and 151 B_ONLY on a review list"),
    ("D04", "Stock 5-minute bars 2015-2026, Nifty 500", "READY", "", "1.54% of rows unscaled"),
    ("D05", "Security master by ISIN (from 2011)", "READY", "", "3,613 company entities"),
    ("D06", "Trading calendar", "READY", "", "7,904 trading days"),
    ("D07", "Universe table U_LIQ-IN (top N by 60-day turnover)", "BUILD", "Oct 21", "rule fixed in I0; table to build"),
    ("D08", "Cost model v1 (brokerage, STT, exchange, SEBI, stamp, GST, spread, slippage) and tax model", "BUILD", "Oct 24", "tax rates to confirm with the accountant"),
    ("D09", "Features table v1 (returns, ranges, volume ratios, momentum, delivery share, per stock-day)", "BUILD", "Oct 24", ""),
    ("D10", "Index 5-minute and 1-minute history (Nifty 50, Bank Nifty, Fin Services, Midcap Select) and India VIX", "BUILD", "Oct 21", "Kite pull, token needed; 1-minute reaches back only as far as Kite serves"),
    ("D11", "Index daily levels, sector indices, VIX daily", "BUILD", "Oct 22", "NSE index files, fetch plus typing"),
    ("D12", "F&O bhavcopy typed (silver), expiry calendar, lot sizes", "BUILD", "Oct 27", "bronze complete (6,499 files); lot-size history to confirm against NSE circulars"),
    ("D13", "Greeks and implied volatility from settlement prices", "WAIT_DATA", "Nov 3", "needs D12 and D11"),
    ("D14", "Option recorder, 1-minute live contracts", "WAIT_TIME", "accumulating", "auto: started 18 Oct 2026; milestones 4, 12, 26 weeks"),
    ("D15", "Nightly builds clean (gate counter)", "WAIT_TIME", "30 runs", "auto: counted from heartbeats"),
    ("D16", "Ledger snapshots (gate counter)", "WAIT_TIME", "30 snapshots", "auto: counted from bronze/ledger"),
    ("D17", "FII/DII flows history", "BUILD", "Oct 28", "NSE provisional daily; how far back is free to be probed"),
    ("D18", "Announcements, board meetings, corporate-action text (PR zips, from ~2010)", "BUILD", "Nov 3", "about 4,000 files at 1 per second; gate G-E"),
    ("D19", "ASM/GSM surveillance lists and pledge/shareholding filings", "BUILD", "Nov 10", "NSE archives and filings; coverage to probe"),
    ("D20", "Fundamentals dataset (statements, ratios), point-in-time", "DECISION", "", "gate G-U: source and licence not chosen; free sources may not allow product use"),
    ("D21", "IPO dataset (issue price, subscription, listing, first 90 days)", "BUILD", "Nov 10", "listing days come from the lake; issue data from NSE/BSE pages, to probe"),
    ("D22", "Macro (RBI, USDINR, crude, US yields)", "BUILD", "Nov 3", "FRED and RBI, open data"),
    ("D23", "hypothesis_map (3,870 teacher hypotheses mapped to data and status)", "BUILD", "Oct 31", "one automatic pass, about US$15; then Madhav reviews 50 sample rows plus every INTRADAY and EVENTS row"),
    ("D24", "Calls ledger (1,001 dated calls + daily scored call)", "BUILD", "Nov 7", "calls from 2024-01-01 stay unscored until unseal"),
    ("D25", "Madhav's trade history", "READY", "", "closed: not available; review starts from holdings, history builds from now"),
    ("D26", "Historical option bid-ask and intraday option prices before 18 Oct 2026", "DECISION", "", "not available free; stand-ins: synthetic from D13 plus a labelled spread estimate; paid source only if a study proves it matters"),
    ("D27", "External SSD and UPS", "WAIT_MADHAV", "this week", "data moves to the SSD when it arrives"),
    ("D28", "Residential-status answer (Zerodha, accountant)", "WAIT_MADHAV", "before live", "decides NRO conversion timing; not needed for research"),
]

# id, phase, family, question, needs, exit_focus, start
STUDIES = [
    ("S01", "P0", "Lab tools", "Features table v1", ["D01", "D02", "D04", "D06"], "", "Oct 21"),
    ("S02", "P0", "Lab tools", "Universe table U_LIQ-IN", ["D01", "D06"], "", "Oct 21"),
    ("S03", "P0", "Lab tools", "Cost model v1 and tax model v1", ["D01"], "", "Oct 22"),
    ("S04", "P0", "Lab tools", "Null engine: no-trade, buy-and-hold, random entries at the same times (every study compares against these)", ["D01", "D04"], "", "Oct 22"),
    ("S05", "P0", "Lab tools", "Exit-evaluation harness: one entry set, many exit policies, scored on expectancy in R, capture of the best price reached, giveback, worst loss", ["D01", "D04"], "yes", "Oct 24"),
    ("S06", "P0", "Lab tools", "Registry and multiple-testing ledger (every test counted; thresholds rise with the count)", [], "", "Oct 21"),
    ("S07", "P0", "Lab tools", "hypothesis_map build, Madhav review", ["D23"], "", "Oct 31"),
    ("S08", "P0", "Lab tools", "Calls ledger and scoring", ["D24"], "", "Nov 7"),
    ("E01", "P1", "Exits, stocks", "Stop space (M-06): how far a stop must sit to survive normal noise, by volatility bucket", ["D07", "D08", "D09"], "yes", "Oct 27"),
    ("E02", "P1", "Exits, stocks", "Exit bake-off: fixed target, ATR trail, swing or level break, moving-average close, time stop, momentum fade, staged scale-outs", ["D07", "D08", "D09"], "yes", "Oct 28"),
    ("E03", "P1", "Exits, stocks", "Turn warnings: which signals precede a turn (volume climax, momentum divergence, delivery collapse, range expansion, gap, distance from average), each tested as an exit trigger", ["D07", "D09", "D02"], "yes", "Nov 3"),
    ("E04", "P1", "Exits, stocks", "Saturation after long runs and declines (M-03/04/13) as an exit and as a no-entry filter", ["D07", "D09"], "yes", "Nov 5"),
    ("E05", "P1", "Exits, stocks", "Pullback depth and what a healthy pullback looks like (M-05) so Ananta holds through it", ["D07", "D09"], "yes", "Nov 5"),
    ("E06", "P1", "Exits, stocks", "Ride and reposition versus simply holding, after costs, tax and missed upside (M-12)", ["D07", "D08", "D09"], "yes", "Nov 10"),
    ("E07", "P1", "Exits, stocks", "Level-break exits: swing highs and lows, round numbers, volume-at-price, prior-day levels. Includes the crypto lesson that loose exits win in discovery years and lose in confirm years", ["D07", "D09"], "yes", "Nov 10"),
    ("E08", "P1", "Exits, stocks", "Market gate on exits: Nifty above its 50-day average and breadth (the one crypto filter that passed)", ["D07", "D11"], "yes", "Nov 12"),
    ("I01", "P2", "Opening and intraday", "First 30 minutes: what proves the day's direction, when 'wait longer' is right (M-01/02)", ["D10"], "", "Oct 28"),
    ("I02", "P2", "Opening and intraday", "Intraday level-break exits for the index and F&O stocks: VWAP, opening range, prior-day high/low", ["D10", "D04"], "yes", "Nov 3"),
    ("I03", "P2", "Opening and intraday", "Spot side of O-01 triangle breakout (1-minute)", ["D10"], "", "Nov 5"),
    ("I04", "P2", "Opening and intraday", "Spot side of O-02: SuperTrend(10,2) + VWAP + VWMA(20) on 3-minute, with the 'bunched lines' filter made exact", ["D10"], "", "Nov 5"),
    ("I05", "P2", "Opening and intraday", "Expiry-day spot behaviour after 1:30 pm: range, direction, level breaks (spot side of O-04)", ["D10", "D12"], "yes", "Nov 10"),
    ("I06", "P2", "Opening and intraday", "Time-of-day map: volatility, volume and direction by minute of the session", ["D10", "D04"], "", "Nov 3"),
    ("C01", "P3", "Context", "Market state map ported from the crypto work: volatility clustering, herding by volatility band, size-after-volatility", ["D04", "D10", "D11"], "", "Nov 5"),
    ("C02", "P3", "Context", "Volume and momentum relationships (crypto H1/H2 port): does volume heat predict the next move's size and where it ends", ["D04", "D09"], "yes", "Nov 5"),
    ("C03", "P3", "Context", "Index-stock-sector lead-lag and pairs checked side by side; effector groups (M-09)", ["D04", "D11"], "", "Nov 12"),
    ("C04", "P3", "Context", "Buyers versus sellers dominance (M-10) from delivery share, turnover and up/down volume", ["D02", "D09"], "", "Nov 12"),
    ("C05", "P3", "Context", "India VIX regimes and what they do to stops and exits", ["D11", "D09"], "yes", "Nov 12"),
    ("C06", "P3", "Context", "FII/DII flows against the next days", ["D17"], "", "Nov 17"),
    ("F01", "P4", "Futures and options (end of day)", "Expiry-day premium decay profiles by days to expiry; straddle decay (M-07/08)", ["D12", "D13"], "", "Nov 5"),
    ("F02", "P4", "Futures and options (end of day)", "O-03 expiry-eve strangle, closing-price version: tail first (worst expiry, worst run, margin)", ["D12", "D13", "D08"], "", "Nov 10"),
    ("F03", "P4", "Futures and options (end of day)", "OI, put-call ratio, max-pain and chain-shape hypotheses from the Optionables set", ["D12", "D13", "D23"], "", "Nov 17"),
    ("F04", "P4", "Futures and options (end of day)", "Futures: basis, rollover, open interest versus price quadrants", ["D12"], "", "Nov 5"),
    ("F05", "P4", "Futures and options (end of day)", "O-04 straddle, estimated version, to be calibrated against the recorder before it is trusted", ["D13", "D10", "D14"], "yes", "Nov 17"),
    ("F06", "P4", "Futures and options (end of day)", "Hedging: Nifty puts and futures as portfolio protection, cost versus saved drawdown", ["D12", "D13", "D08"], "", "Dec 1"),
    ("F07", "P4", "Futures and options (end of day)", "Paper book design (M-17): per-trade, daily and open-risk limits and the drawdown response, for Madhav's approval", ["D08", "D13"], "", "Dec 1"),
    ("V01", "P5", "Events and fundamentals", "Behaviour around corporate actions, dividends and results dates", ["D18", "D03"], "", "Nov 10"),
    ("V02", "P5", "Events and fundamentals", "Announcement reactions and post-event drift", ["D18"], "yes", "Nov 17"),
    ("V03", "P5", "Events and fundamentals", "IPO listing and first 90 days (M-14)", ["D21"], "yes", "Nov 24"),
    ("V04", "P5", "Events and fundamentals", "Red flags as a hard gate: surveillance lists, pledge, exchange actions", ["D19"], "", "Nov 24"),
    ("V05", "P5", "Events and fundamentals", "Quality and mispricing, peer-relative (M-15); quality score and timing score kept apart", ["D20", "D07"], "", "Dec 1"),
    ("V06", "P5", "Events and fundamentals", "Portfolio ranking, replacement finder and concentration (M-16); first run on the father's holdings, suggestions only", ["D16", "D20", "D19", "D08"], "", "Dec 8"),
    ("R01", "P6", "Real intraday options", "Calibrate synthetic option prices against the recorder: how wrong are they", ["D14"], "", "Nov 15 (4 weeks)"),
    ("R02", "P6", "Real intraday options", "O-01 option leg, O-02 option legs, O-04 real: first look at 12 weeks of recording, tail at 26", ["D14"], "yes", "Jan 10 (12 weeks)"),
    ("K01", "P7", "Knowledge", "Teacher hypotheses run in batches by status (DAILY_NOW first, then OPTIONS, INTRADAY, EVENTS)", ["D23"], "", "Nov 3"),
    ("K02", "P7", "Knowledge", "Daily scored call (M-11): bullish, bearish and neutral written before the open, scored at the checkpoint", ["D10", "D24"], "", "Nov 17"),
    ("G01", "P8", "Synthesis and gate", "Relationship atlas v1 and the exit policy book: for each situation, the exit that held up out of sample", ["E01", "E02", "E03", "E07"], "yes", "Dec 15"),
    ("G02", "P8", "Synthesis and gate", "Two families validated on development plus validation years; holdout opened once per family, and the gate sentence", ["G01", "D15", "D16"], "yes", "Jan 10"),
]


def _auto() -> dict[str, str]:
    import datetime as dt

    out = {}
    con = catalog.connect(read_only=True)
    try:
        n = con.execute("select count(*) from heartbeats where job = 'india.nightly' and ok").fetchone()[0]
        out["D15"] = f"{n} of 30 nightly runs"
        r = con.execute("select count(distinct cast(run_at as date)) from heartbeats where job = 'recorder.run' and ok").fetchone()[0]
        out["D14"] = f"{r} recorded evenings"
    except Exception:
        pass
    con.close()
    led = list(paths.bronze("ledger").glob("*.json")) if paths.bronze("ledger").exists() else []
    out["D16"] = f"{len(led)} of 30 snapshots"
    return out


def evaluate() -> tuple[list[dict], list[dict]]:
    auto = _auto()
    data = {d[0]: {"id": d[0], "item": d[1], "state": d[2], "eta": d[3], "note": d[4], "live": auto.get(d[0], "")} for d in DATA}
    studies = []
    done = {k for k, v in data.items() if v["state"] == "READY"}
    for sid, ph, fam, q, needs, exit_focus, start in STUDIES:
        blockers = [n for n in needs if n not in done and not (n.startswith(("E", "G")))]
        pending = [f"{n} ({data[n]['state'].lower()}, {data[n]['eta'] or 'no date'})" for n in blockers if n in data]
        pending += [f"study {n}" for n in needs if n.startswith(("E", "G"))]
        state = "READY" if not pending else "BLOCKED"
        studies.append({"id": sid, "phase": ph, "family": fam, "question": q, "exit_focus": exit_focus, "planned_start": start,
                        "state": state, "waiting_on": "; ".join(pending)})
    return list(data.values()), studies


def build() -> dict:
    data, studies = evaluate()
    con = catalog.connect()
    con.execute("create or replace table data_needs (id varchar, item varchar, state varchar, eta varchar, note varchar, live varchar)")
    con.executemany("insert into data_needs values (?, ?, ?, ?, ?, ?)", [[d[k] for k in ("id", "item", "state", "eta", "note", "live")] for d in data])
    con.execute("create or replace table research_tracker (id varchar, phase varchar, family varchar, question varchar, exit_focus varchar, planned_start varchar, state varchar, waiting_on varchar)")
    con.executemany("insert into research_tracker values (?, ?, ?, ?, ?, ?, ?, ?)",
                    [[s[k] for k in ("id", "phase", "family", "question", "exit_focus", "planned_start", "state", "waiting_on")] for s in studies])
    con.close()
    lines = ["# India research tracker (generated by `python -m india.tracker build`)", "", "## Data items", "", "| id | item | state | eta | live | note |", "|---|---|---|---|---|---|"]
    lines += [f"| {d['id']} | {d['item']} | {d['state']} | {d['eta']} | {d['live']} | {d['note']} |" for d in data]
    lines += ["", "## Studies", "", "| id | phase | family | question | exit focus | planned start | state | waiting on |", "|---|---|---|---|---|---|---|---|"]
    lines += [f"| {s['id']} | {s['phase']} | {s['family']} | {s['question']} | {s['exit_focus']} | {s['planned_start']} | {s['state']} | {s['waiting_on']} |" for s in studies]
    from pathlib import Path

    (Path(__file__).parent / "registrations" / "research_tracker.md").write_text("\n".join(lines) + "\n")
    return {"data_items": len(data), "studies": len(studies), "ready": sum(s["state"] == "READY" for s in studies)}


def status(only_waiting: bool = False) -> None:
    data, studies = evaluate()
    by = {}
    for s in studies:
        by.setdefault(s["state"], []).append(s)
    print(f"studies: {len(studies)} total, {len(by.get('READY', []))} ready, {len(by.get('BLOCKED', []))} blocked")
    if not only_waiting:
        print("\nREADY:")
        for s in by.get("READY", []):
            print(f"  {s['id']} {s['question'][:90]}")
    print("\nBLOCKED, grouped by what they wait for:")
    groups: dict[str, list[str]] = {}
    for s in by.get("BLOCKED", []):
        for w in s["waiting_on"].split("; "):
            groups.setdefault(w, []).append(s["id"])
    for w, ids in sorted(groups.items()):
        print(f"  {w}: {', '.join(ids)}")
    print("\nWAITING ON MADHAV:", "; ".join(f"{d['id']} {d['item']}" for d in data if d["state"] == "WAIT_MADHAV"))
    print("DECISIONS OPEN:", "; ".join(f"{d['id']} {d['item']}" for d in data if d["state"] == "DECISION"))
    print("LIVE COUNTERS:", "; ".join(f"{d['id']} {d['live']}" for d in data if d["live"]))


if __name__ == "__main__":
    paths.ensure()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "build":
        print(build())
    else:
        status(cmd == "waiting")
