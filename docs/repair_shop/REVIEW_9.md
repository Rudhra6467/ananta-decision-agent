# Repair-shop review #9: the Explorer's setups with zones (pre-registration)

Written 2026-10-03, before any run. The Explorer (rulebook v0) looks for "support" as recent 1-hour swing lows; Madhav: it is always
a zone. Question: do the Explorer's own entries do better when they are made **at a zone** (and with the market allowed)?
No new replay: the existing history replay of rulebook v0 (`~/ananta_runs/explorer_v0/trades_*.pkl`, 2017 to July 2026, the same
engine the live Explorer runs, NDAX costs, $100 per trade) is split by the daily context at each entry. Random entries made by the
same replay (shadow RANDOM, same exits) are the baseline.

- **Context at entry**, from daily bars that closed before the entry's day only (`src/research/zones.py`):
  - **Z**: the entry price is inside a support zone of a kind review #6 passed (AVERAGE-200, CONFLUENCE, SWING-NEW) or at most
    0.5 daily range above its top;
  - **Zany**: the same with any zone kind;
  - **G**: BTC's previous daily close above its 50-day average (V02).
- **Groups:** real trades (no shadow) and RANDOM shadows, each split Z / not Z, Zany / not, G / not G, Z and G / not.
- **Measure:** mean net $ per $100 trade (ACTUAL_net), Welch t.
- **Pass (per split):** DISCOVERY (entries before 2024-01-01): real trades in the context (1) have a mean net > $0, (2) beat RANDOM
  entries in the same context by t >= 2, and (3) beat real trades outside the context by t >= 2. CONFIRM (2024 to July 2026):
  real in the context beat real outside it. Four splits tested; all reported.
- **If a split passes:** it becomes a candidate filter for the Explorer, run as a paper shadow first; it changes nothing by itself.
