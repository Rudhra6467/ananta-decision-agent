# XO1: moving-average and MACD crossovers (registered 26 Oct 2026, before any run)

Madhav asked (India chat, 26 Oct): do crossovers, like the 50-day crossing the 200-day or the 20-day meeting the 50-day, give a good buy call?

- **What is tested:**
  - **Crossovers:** 50/200 golden and death crosses, 20/50 crosses, and MACD(12,26,9) signal-line crosses.
  - **Holding in the golden-cross state:** the index only, while the 50-day sits above the 200-day.
  - **Averages converging:** the 20, 50 and 200-day within 2% of each other; does a bigger move follow?
- **Where:** Nifty 50 and Nifty Bank (2003–2023), and the liquid-250 stocks (2000–2023). Development runs to 2017; validation is 2018–2023. Nothing from 2024 on is read.
- **How it is judged:**
  - **Index:** sessions with the signal against sessions without, block by block.
  - **Stocks:** each event against ordinary days in the same quarter (the random-entry yardstick), plus the trade's own return after costs.
  - **Trend split:** for the stocks, the 20/50 cross is also tested in uptrends and downtrends separately.
- **Bar:** 27 variants are listed in `xo1_v1.json`, a new family "technical", frozen at k = 27 (z about 3.1).
- **Expected:** index 50/200 crosses are rare (a few per decade), so those rows will likely read INCONCLUSIVE, and that stands.
- No paper rule changes because of this study.
