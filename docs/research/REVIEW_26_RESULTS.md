# Review #26 results: the expected-value table

Run 2026-10-10 exactly as pre-registered (REVIEW_26.md): 6 daily rules on the lake's 120 coins (delisted included), 1,188 trades,
exits as live, tier costs, random entries of the same tier and market state as the bar. The full table: `review26.json`.

**One cell of 36 passes, strongly, in both periods: H07 (the short dip) on tier A coins while the exposure dial is CLOSED.**

| Cell | Period | Trades | Market days | Net per trade | Over random | z |
|---|---|---|---|---|---|---|
| H07, dial CLOSED, tier A | 2018–2023 | 92 | 48 | **+7.1%** | **+9.3%** | **5.0** |
| H07, dial CLOSED, tier A | 2024–2026 | 83 | 46 | **+5.3%** | **+6.3%** | **4.9** |
| H07, dial OPEN, tier A | 2018–2023 | 13 | 11 | +0.8% | −3.5% | −1.3 |
| H07, dial OPEN, tier A | 2024–2026 | 57 | 24 | +2.5% | +5.7% | 3.2 |
| H07, dial CLOSED, tier B | 2018–2023 | 31 | 26 | +1.4% | +1.3% | 0.6 |
| H07, dial CLOSED, tier B | 2024–2026 | 24 | 20 | +3.1% | +4.2% | 1.5 |

Its expected value (pooled excess, shrunk by n/(n+50)): **+5.1% per trade over random.** Every other cell is 0.

What it means, in plain words: a big, liquid coin that is still above its own 200-day average, dipping hard (RSI(10) under 30)
while Bitcoin itself is weak (under its 50-day or 200-day), has bounced well in both periods. It is a strong coin's dip in a weak
market, which is not the same thing as buying in a weak market. Everything else is not measurably better than random in this
table: your setups (M1a, M2a, M2a-G, M3a, M3b) are mixed between the periods, as reviews #5 and #8 found, and H07 in tier B or
with the dial open is not confirmed.

Cautions: 36 cells were tested; this one clears z 5 in each period separately, far past what luck across 36 tries produces. The
lake's 120 were chosen by traded value over their last 24 months, so a little survivorship remains; tiers are measured at each
signal's own date.

**What changes in the engine:** the exposure dial closes new buys EXCEPT moments with a measured edge in the closed state (today:
H07 on tier A). The brain's ranking uses these values in place of the hand-picked points for the daily rules.
