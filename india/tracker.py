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
    ("D03", "Corporate actions, two records", "READY", "", "1,870 events; applied only when both records agree or the price confirms within 15% (18 Oct rule); 75 ambiguous events left unapplied and skipped by the lab and the paper engine"),
    ("D04", "Stock 5-minute bars 2015-2026, Nifty 500", "READY", "", "1.54% of rows unscaled"),
    ("D05", "Security master by ISIN (from 2011)", "READY", "", "3,613 company entities"),
    ("D06", "Trading calendar", "READY", "", "7,904 trading days"),
    ("D07", "Universe table U_LIQ-IN (top N by 60-day turnover)", "READY", "", "gold/universe/u_liq_in.parquet: 6.99M stock-days, top 500 per day (built 18 Oct)"),
    ("D08", "Cost model v1 (brokerage, STT, exchange, SEBI, stamp, GST, spread, slippage) and tax model", "READY", "", "india/costs.py: Zerodha charges read 18 Oct 2026, spread estimate by turnover rank, STCG/LTCG; tax rates to confirm with the accountant"),
    ("D09", "Features table v1 (returns, ranges, volume ratios, momentum, delivery share, per stock-day)", "READY", "", "gold/features/daily.parquet: 3.44M rows, no forward columns (leak-checked)"),
    ("D10", "Index 5-minute and 1-minute history (Nifty 50, Bank Nifty, Fin Services, Midcap Select) and India VIX", "READY", "", "silver/kite_index: 53 indices daily from 2003, 8 indices 5-minute and 1-minute from 2015 (to 16 Oct 2026; 2024+ sealed)"),
    ("D11", "Index daily levels, sector indices, VIX daily", "READY", "", "index daily (53 incl. sector and broad indices) and India VIX in silver/kite_index/day; sector map from the Nifty 500 industry column (current constituents)"),
    ("D12", "F&O bhavcopy typed (silver), expiry calendar, lot sizes", "READY", "", "silver/fo_bhavcopy 2000-2026 (2024+ sealed); American-style stock options (CA/PA, to 2011) now kept with style A (18 Oct fix); lot sizes: UDiFF from 2024, estimated before"),
    ("D13", "Greeks and implied volatility from settlement prices", "READY", "", "silver/fo_greeks: Black-76 on the same-expiry future, weekly forward from put-call parity; 88-92% of rows priced; end-of-day estimates"),
    ("D14", "Option recorder, 1-minute live contracts", "WAIT_TIME", "accumulating", "auto: started 18 Oct 2026; milestones 4, 12, 26 weeks"),
    ("D15", "Nightly builds clean (gate counter)", "WAIT_TIME", "30 runs", "auto: counted from heartbeats"),
    ("D16", "Ledger snapshots (gate counter)", "WAIT_TIME", "30 snapshots", "auto: counted from bronze/ledger"),
    ("D17", "FII/DII flows history", "BUILD", "", "NSE provisional daily; how far back is free to be probed"),
    ("D18", "Announcements, board meetings, corporate-action text (PR zips, from ~2010)", "READY", "", "silver/pr: 7.0M announcements (categorised), 122k board meetings (to Oct 2025), 1.58M book-closure actions, 845k price-band hits, 2010-2026"),
    ("D19", "ASM/GSM surveillance lists and pledge/shareholding filings", "BUILD", "", "NSE archives and filings; coverage to probe"),
    ("D20", "Fundamentals dataset from filed results (NSE results API with filing timestamps and XBRL), point-in-time", "BUILD", "", "results index done (217,104 filings 2007-2024); 2025+ via the integrated-filing API (pulling); XBRL download running, liquid names first (53,654 files); parser india/fundamentals.py"),
    ("D29", "Sector indices and an industry/sector map for the liquid universe (sector relative strength, breadth by sector)", "READY", "", "sector and thematic indices daily (Kite) plus industry per Nifty 500 stock (current list, not point-in-time)"),
    ("D30", "Nifty valuation series (P/E, P/B, dividend yield) and index total-return history", "BUILD", "", "niftyindices endpoint no longer answers (18 Oct probe); another source needed; one hypothesis (OPT-H60)"),
    ("D20b", "Fundamentals before 2018 (old-format HTML result pages)", "DECISION", "", "parse the HTML pages, or start ratios from 2018; decide after D20 coverage report"),
    ("D21", "IPO dataset (issue price, subscription, listing, first 90 days)", "BUILD", "", "listing days come from the lake; issue data from NSE/BSE pages, to probe"),
    ("D22", "Macro (RBI, USDINR, crude, US yields)", "BUILD", "", "FRED pulled and typed (silver/macro: USDINR, Brent, WTI, US 10y/2y, S&P, Nasdaq, dollar index, US VIX, fed funds, India 10y monthly); RBI policy dates still to source"),
    ("D23", "hypothesis_map (3,870 teacher hypotheses mapped to data and status)", "READY", "", "gold/hypothesis_map: 137 register rows mapped (60 TWT, 60 OPT, 17 M); 18 Oct"),
    ("D24", "Calls ledger (1,001 dated calls + daily scored call)", "BUILD", "", "calls from 2024-01-01 stay unscored until unseal"),
    ("D25", "Madhav's trade history", "READY", "", "closed: not available; review starts from holdings, history builds from now"),
    ("D26", "Historical option bid-ask and intraday option prices before 18 Oct 2026", "DECISION", "", "not available free; stand-ins: synthetic from D13 plus a labelled spread estimate; paid source only if a study proves it matters"),
    ("D27", "External SSD and UPS", "WAIT_MADHAV", "", "data moves to the SSD when it arrives"),
    ("D28", "Residential-status answer (Zerodha, accountant)", "WAIT_MADHAV", "before live", "decides NRO conversion timing; not needed for research"),
]

# id, phase, family, question, needs, exit_focus, start
STUDIES = [
    ("S01", "P0", "Lab tools", "Features table v1", ["D01", "D02", "D04", "D06"], "", ""),
    ("S02", "P0", "Lab tools", "Universe table U_LIQ-IN", ["D01", "D06"], "", ""),
    ("S03", "P0", "Lab tools", "Cost model v1 and tax model v1", ["D01"], "", ""),
    ("S04", "P0", "Lab tools", "Null engine: no-trade, buy-and-hold, random entries at the same times (every study compares against these)", ["D01", "D04"], "", ""),
    ("S05", "P0", "Lab tools", "Exit-evaluation harness: one entry set, many exit policies, scored on expectancy in R, capture of the best price reached, giveback, worst loss", ["D01", "D04"], "yes", ""),
    ("S06", "P0", "Lab tools", "Registry and multiple-testing ledger (every test counted; thresholds rise with the count)", [], "", ""),
    ("S07", "P0", "Lab tools", "hypothesis_map build, Madhav review", ["D23"], "", ""),
    ("S08", "P0", "Lab tools", "Calls ledger and scoring", ["D24"], "", ""),
    ("E01", "P1", "Exits, stocks", "Stop space (M-06): how far a stop must sit to survive normal noise, by volatility bucket", ["D07", "D08", "D09"], "yes", ""),
    ("E02", "P1", "Exits, stocks", "Exit bake-off: fixed target, ATR trail, swing or level break, moving-average close, time stop, momentum fade, staged scale-outs", ["D07", "D08", "D09"], "yes", ""),
    ("E03", "P1", "Exits, stocks", "Turn warnings: which signals precede a turn (volume climax, momentum divergence, delivery collapse, range expansion, gap, distance from average), each tested as an exit trigger", ["D07", "D09", "D02"], "yes", ""),
    ("E04", "P1", "Exits, stocks", "Saturation after long runs and declines (M-03/04/13) as an exit and as a no-entry filter", ["D07", "D09"], "yes", ""),
    ("E05", "P1", "Exits, stocks", "Pullback depth and what a healthy pullback looks like (M-05) so Ananta holds through it", ["D07", "D09"], "yes", ""),
    ("E06", "P1", "Exits, stocks", "Ride and reposition versus simply holding, after costs, tax and missed upside (M-12)", ["D07", "D08", "D09"], "yes", ""),
    ("E07", "P1", "Exits, stocks", "Level-break exits: swing highs and lows, round numbers, volume-at-price, prior-day levels. Includes the crypto lesson that loose exits win in discovery years and lose in confirm years", ["D07", "D09"], "yes", ""),
    ("E08", "P1", "Exits, stocks", "Market gate on exits: Nifty above its 50-day average and breadth (the one crypto filter that passed)", ["D07", "D11"], "yes", ""),
    ("I01", "P2", "Opening and intraday", "First 30 minutes: what proves the day's direction, when 'wait longer' is right (M-01/02)", ["D10"], "", ""),
    ("I02", "P2", "Opening and intraday", "Intraday level-break exits for the index and F&O stocks: VWAP, opening range, prior-day high/low", ["D10", "D04"], "yes", ""),
    ("I03", "P2", "Opening and intraday", "Spot side of O-01 triangle breakout (1-minute)", ["D10"], "", ""),
    ("I04", "P2", "Opening and intraday", "Spot side of O-02: SuperTrend(10,2) + VWAP + VWMA(20) on 3-minute, with the 'bunched lines' filter made exact", ["D10"], "", ""),
    ("I05", "P2", "Opening and intraday", "Expiry-day spot behaviour after 1:30 pm: range, direction, level breaks (spot side of O-04)", ["D10", "D12"], "yes", ""),
    ("I06", "P2", "Opening and intraday", "Time-of-day map: volatility, volume and direction by minute of the session", ["D10", "D04"], "", ""),
    ("C01", "P3", "Context", "Market state map ported from the crypto work: volatility clustering, herding by volatility band, size-after-volatility", ["D04", "D10", "D11"], "", ""),
    ("C02", "P3", "Context", "Volume and momentum relationships (crypto H1/H2 port): does volume heat predict the next move's size and where it ends", ["D04", "D09"], "yes", ""),
    ("C03", "P3", "Context", "Index-stock-sector lead-lag and pairs checked side by side; effector groups (M-09)", ["D04", "D11"], "", ""),
    ("C04", "P3", "Context", "Buyers versus sellers dominance (M-10) from delivery share, turnover and up/down volume", ["D02", "D09"], "", ""),
    ("C05", "P3", "Context", "India VIX regimes and what they do to stops and exits", ["D11", "D09"], "yes", ""),
    ("C06", "P3", "Context", "FII/DII flows against the next days", ["D17"], "", ""),
    ("F01", "P4", "Futures and options (end of day)", "Expiry-day premium decay profiles by days to expiry; straddle decay (M-07/08)", ["D12", "D13"], "", ""),
    ("F02", "P4", "Futures and options (end of day)", "O-03 expiry-eve strangle, closing-price version: tail first (worst expiry, worst run, margin)", ["D12", "D13", "D08"], "", ""),
    ("F03", "P4", "Futures and options (end of day)", "OI, put-call ratio, max-pain and chain-shape hypotheses from the Optionables set", ["D12", "D13", "D23"], "", ""),
    ("F04", "P4", "Futures and options (end of day)", "Futures: basis, rollover, open interest versus price quadrants", ["D12"], "", ""),
    ("F05", "P4", "Futures and options (end of day)", "O-04 straddle, estimated version, to be calibrated against the recorder before it is trusted", ["D13", "D10", "D14"], "yes", ""),
    ("F06", "P4", "Futures and options (end of day)", "Hedging: Nifty puts and futures as portfolio protection, cost versus saved drawdown", ["D12", "D13", "D08"], "", ""),
    ("F07", "P4", "Futures and options (end of day)", "Paper book design (M-17): per-trade, daily and open-risk limits and the drawdown response, for Madhav's approval", ["D08", "D13"], "", ""),
    ("V01", "P5", "Events and fundamentals", "Behaviour around corporate actions, dividends and results dates", ["D18", "D03"], "", ""),
    ("V02", "P5", "Events and fundamentals", "Announcement reactions and post-event drift", ["D18"], "yes", ""),
    ("V03", "P5", "Events and fundamentals", "IPO listing and first 90 days (M-14)", ["D21"], "yes", ""),
    ("V04", "P5", "Events and fundamentals", "Red flags as a hard gate: surveillance lists, pledge, exchange actions", ["D19"], "", ""),
    ("V05", "P5", "Events and fundamentals", "Quality and mispricing, peer-relative (M-15); quality score and timing score kept apart", ["D20", "D07"], "", ""),
    ("V06", "P5", "Events and fundamentals", "Portfolio ranking, replacement finder and concentration (M-16); first run on the father's holdings, suggestions only", ["D16", "D20", "D19", "D08"], "", ""),
    ("R01", "P6", "Real intraday options", "Calibrate synthetic option prices against the recorder: how wrong are they", ["D14"], "", ""),
    ("R02", "P6", "Real intraday options", "O-01 option leg, O-02 option legs, O-04 real: first look at 12 weeks of recording, tail at 26", ["D14"], "yes", ""),
    ("K01", "P7", "Knowledge", "Teacher hypotheses run in batches by status (DAILY_NOW first, then OPTIONS, INTRADAY, EVENTS)", ["D23"], "", ""),
    ("K02", "P7", "Knowledge", "Daily scored call (M-11): bullish, bearish and neutral written before the open, scored at the checkpoint", ["D10", "D24"], "", ""),
    ("E09", "P1", "Entries and process", "Staged entries: 25/75 split at breakout and pullback, weekly instalments (TWT-H20/21), against one entry", ["D07", "D08", "D09"], "", ""),
    ("E10", "P1", "Exits, stocks", "Portfolio drawdown rule: review or exit everything when open drawdown reaches 7-8% (TWT-H25), on the paper book", ["D07", "D08"], "yes", ""),
    ("C07", "P3", "Context", "Sector relative strength, rotation and small/mid vs large ratio (TWT-H04-08, H13-14, H16, H29, H39)", ["D29", "D11"], "", ""),
    ("C08", "P3", "Context", "Breadth as a gate: share above the 200-day, swing-structure share, washouts (TWT-H01, H30-33)", ["D07", "D09"], "yes", ""),
    ("C09", "P3", "Context", "Intermarket: dollar, crude, S&P, rate cuts, Nifty valuation zones (TWT-H42-45, H47, OPT-H60)", ["D22", "D30"], "", ""),
    ("E11", "P1", "Exits, stocks", "Exit after a lower price-band hit (from V02)", ["D07", "D09", "D18"], "yes", ""),
    ("P01", "P1", "Entries and process", "Indicator-pattern entries (stochastic, Heikin Ashi, RSI divergence, Ichimoku, weekly outside bar, ADX): low priority, run after the exit work", ["D07", "D09"], "", ""),
    ("G01", "P8", "Synthesis and gate", "Relationship atlas v1 and the exit policy book: for each situation, the exit that held up out of sample", ["E01", "E02", "E03", "E07"], "yes", ""),
    ("G02", "P8", "Synthesis and gate", "Two families validated on development plus validation years; holdout opened once per family, and the gate sentence", ["G01", "D15", "D16"], "yes", ""),
]


PROGRESS = {
    "S01": "done: gold/features", "S02": "done: gold/universe", "S03": "done: india/costs.py", "S04": "done: india/exitlab.py (null engine, time-matched null)", "S05": "done: india/exitlab.py",
    "S06": "done: india/registry.py", "S07": "done: india/hypmap.py (137 rows)",
    "E01": "full run 18 Oct (all signals): no stop distance passes the bar; wider stops help PULL entries in dev only",
    "E02": "full run 18 Oct (22k BRK, 19k PULL, 154k ANY): no exit beats its time-matched null; ATR trails and the half-then-trail are significantly WORSE (OPPOSITE)",
    "E03": "full run 18 Oct: extra turn-warning exits cut giveback and holding time and cost return; three-down and giveback-50 OPPOSITE on PULL",
    "E07": "full run 18 Oct: prior-day-low exits OPPOSITE; 60-day hold + 20-day-low exit the only positive sign (not at the bar)",
    "E08": "full run 18 Oct: Nifty above its 50-day OPPOSITE in dev and validation for BRK, PULL and ANY (entries in weak markets earn 2-6% more)",
    "E04": "18 Oct: VALIDATED as a no-entry filter on ANY entries: more than 20% above the 50-day, or up more than 25% in 20 sessions, earn about 2-3% less over 20 days",
    "E05": "18 Oct: pullback-depth conditions INCONCLUSIVE or REJECTED (few quarters with both sides)",
    "E06": "18 Oct: stepping out and back in is WORSE than holding (OPPOSITE on PULL), but cuts the 5th-percentile loss from about -29% to -15%",
    "E09": "18 Oct: staged entries WORSE than one entry on PULL and ANY (OPPOSITE), smaller tail loss",
    "C05": "18 Oct: VIX above its 50-day CONDITIONAL for PULL entries (+3.8% dev, +1.5% val)",
    "C07": "18 Oct: small caps leading OPPOSITE (entries earn 2-6% less)",
    "C09": "18 Oct: rupee weakening OPPOSITE (entries earn 2.5-3.6% more); Nifty valuation part waits for D30",
    "F06": "18 Oct: monthly Nifty puts on the 10-slot books cost about 0.1-0.5% a quarter in validation and trim the worst quarter (ANY -34% to -24%), not significant; in dev the bleed outweighs the protection",
    "E11": "18 Oct: selling at the next open after a lower-band day is WORSE than holding on (OPPOSITE for BRK: -12.8% on the trades where it fired); the damage is in that open",
    "G01": "18 Oct first version (india/exitbook.py, descriptive): 10-slot books; per-trade means overstate what a slot-limited book earns (signals cluster in bull runs); val leaders hold60+low20, hold_60d, sma_close_50",
    "E10": "18 Oct: drawdown rule (flatten at -7/-8/-12%, pause 10/20) not significant on returns; cuts the book's worst drawdown (BRK dev -74% to -53%)",
    "V01": "18 Oct: results days move about 1.4x a normal day (VALIDATED); post-results drift not at the bar",
    "V02": "18 Oct: lower price-band hits keep falling (-7.6% dev, -3.1% val over 20 sessions vs Nifty, CONDITIONAL); announcement categories nothing at the bar",
    "F03": "18 Oct: PCR extremes nothing at the bar; max-pain pin OPPOSITE (the forward predicts settlement better)",
    "F01": "18 Oct: short ATM straddles to expiry: positive in validation for Bank Nifty weeklies, negative in dev; not validated; tails up to -Rs 98k per lot",
    "F02": "18 Oct: O-03 closing-price version: 84-87% wins, mean about Rs 120-140, worst about -Rs 14k, drawdowns -Rs 29k to -34k on a Rs 50,000 book",
    "I01": "18 Oct: opening 30/60 minutes do not predict the rest of the day",
    "I05": "18 Oct: expiry afternoons: the 13:00-13:29 range breaks 97-99% of days, no continuation after the break; median 13:30-15:15 move 0.24% (Nifty)",
    "C01": "18 Oct: shock days and high-volatility regimes: large positive leads (+4-8% after a 2% Nifty fall) but too few independent episodes: INCONCLUSIVE, also as declustered events",
    "F05": "18 Oct: synthetic reconstruction 2015-2023 (928 expiry days): O-04 loses about 1% of the Rs 50,000 book per expiry day; better than holding the straddle to 15:15 (CONDITIONAL); recorder calibration (R01) decides",
}


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
        studies.append({"progress": PROGRESS.get(sid, ""), "id": sid, "phase": ph, "family": fam, "question": q, "exit_focus": exit_focus, "planned_start": start,
                        "state": state, "waiting_on": "; ".join(pending)})
    return list(data.values()), studies


def build() -> dict:
    data, studies = evaluate()
    con = catalog.connect()
    con.execute("create or replace table data_needs (id varchar, item varchar, state varchar, eta varchar, note varchar, live varchar)")
    con.executemany("insert into data_needs values (?, ?, ?, ?, ?, ?)", [[d[k] for k in ("id", "item", "state", "eta", "note", "live")] for d in data])
    con.execute("create or replace table research_tracker (id varchar, phase varchar, family varchar, question varchar, exit_focus varchar, planned_start varchar, state varchar, waiting_on varchar, progress varchar)")
    con.executemany("insert into research_tracker values (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    [[s[k] for k in ("id", "phase", "family", "question", "exit_focus", "planned_start", "state", "waiting_on", "progress")] for s in studies])
    con.close()
    lines = ["# India research tracker (generated by `python -m india.tracker build`)", "", "## Data items", "", "| id | item | state | eta | live | note |", "|---|---|---|---|---|---|"]
    lines += [f"| {d['id']} | {d['item']} | {d['state']} | {d['eta']} | {d['live']} | {d['note']} |" for d in data]
    lines += ["", "## Studies", "", "| id | phase | family | question | exit focus | state | waiting on | progress |", "|---|---|---|---|---|---|---|---|"]
    lines += [f"| {s['id']} | {s['phase']} | {s['family']} | {s['question']} | {s['exit_focus']} | {s['state']} | {s['waiting_on']} | {s['progress']} |" for s in studies]
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
