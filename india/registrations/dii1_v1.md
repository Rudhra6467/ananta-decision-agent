# DII1 v1: domestic mutual fund flows and the Nifty (registered before the run, 26 Oct 2026)

**Asked by:** Madhav, 26 Oct 2026 12:19 Toronto, "lets fix everything. i say yes to your recommendations". The open item was that domestic institutions' (DII) flows had no history, so they were untested. FII1, the same day, found that foreign flows do not lead the Nifty.

**Data:** SEBI's Mutual Funds Trends, the official daily record of mutual funds' equity and debt buying and selling, compiled from custodians' reports. It is by trading date, filled from January 2005 by `india/fiidii.py mfhistory`, and each month is checked against the page's own total. Mutual funds are the largest part of DII and the only part with a free official daily history. Insurers, banks and pension funds are not covered.

**Timing:** a trading day's row is placed on the first Nifty session after that day, because SEBI publishes it a day or more later. The outcome then runs from the next session's close.

**Claims tested (10 versions; the strict bar for family "flows" with k = 22, z = 3.05):**
- After a sharp mutual-fund outflow (the bottom tenth of days, or of 5-session sums, against the last 756 sessions), the Nifty is weaker over the next 1, 5 and 20 sessions. That is 5 versions.
- After a sharp inflow (the top tenth), the Nifty is stronger. That is 3 versions.
- **The domestic cushion:** a day when mutual funds are in their top tenth while foreign investors are in their bottom tenth is followed by a stronger Nifty over 5 and 20 sessions. That is 2 versions.

**Periods:** development runs to 2017 (the first usable session is about 2007, after a 500-session warm-up) and validation covers 2018–2023. Nothing from 2024 on is used.

**Descriptive only (no verdict):** how the mutual-fund flow lines up, by year, with the previous, same and next session's Nifty return, and with the same session's foreign flow.

No paper rule changes from this study.
