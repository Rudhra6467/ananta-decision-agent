# SR1: support and resistance as an entry (registered 26 Oct 2026)

**Asked by:** Madhav, 26 Oct 2026 12:19 Toronto, "lets fix everything. i say yes to your recommendations". The recommendation was to test support and resistance as an ENTRY signal. Until now only swing-low exits (E02) and the retest cards were tested.

**Spec:** `sr1_v1.json` was written before any data was read; `run` registers it and then computes.
- Family: technical. The bar's k is frozen at 38 (XO1's 27 versions plus these 11), giving z 3.21.
- Periods: development 2000-2017, validation 2018-2023. Nothing from 2024 on is read.

**Levels:** the levels are the technicals panel's own (`india/technicals.py` swings).
- A swing low or high is a bar that is the lowest (highest) of the 5 bars on each side. It is known only 5 sessions later.
- Support is the highest swing low below yesterday's close, and resistance the lowest swing high above it, among swing bars in the last 20 or 60 sessions. The panel uses 60.
- A randomised check against `technicals.swings` matched on every day (0 mismatches).
- For the indices, closes stand in for highs and lows, as in the live panel.

**Versions (11):**
- Stocks, bounce off 20-session and 60-session support, measured against ordinary days; the 60-session bounce also as a trade after costs.
- Stocks, close above 20-session and 60-session resistance, measured against ordinary days; the 60-session breakout also after costs.
- Stocks, close below 60-session support (expected weaker).
- Nifty and Bank Nifty, bounce and breakout on 60-session levels.

The outcome is 20 sessions throughout. Stocks are bought at the next open and the return is net of costs; for the indices the return runs from the next close. There is one event per name per 10 sessions.

**Results:** `sr1_results_v1.md`.
