# Repair-shop review #23 (pre-registration): the outside world - US markets, the dollar, stress and crypto sentiment

Written 2026-10-05, before any of this data was downloaded or looked at (audit v1 U06 and U08, parked until now for lack of
data; Madhav's Aladdin-style goal of knowing how the wider world moves markets). Free sources: FRED (Nasdaq Composite
NASDAQCOM, broad US dollar index DTWEXBGS, 10-year Treasury yield DGS10, VIX VIXCLS) and the crypto Fear & Greed index
(alternative.me, daily since Feb 2018).

## No look-ahead
A crypto daily decision at the UTC close of day d uses each series' last value dated on or before d (US markets close before
the UTC midnight; the Fear & Greed value dated d is published at the start of d). Averages use earlier values only.

## Variants (5, all counted; nothing added after the run)
- **T3B-NQ:** T3-B, held only while the Nasdaq is above its 200-day average (US risk-on).
- **T3B-USD:** T3-B, held only while the US dollar index is below its 50-day average (a weakening dollar).
- **T3B-VIX:** T3-B, held only while VIX is under 25 (no market stress).
- **T3B-FG:** T3-B, not held while crypto Fear & Greed is 80 or higher (extreme greed).
- **H07-FG:** H07 signals only while Fear & Greed is 30 or lower (buying dips in fear).
The 10-year yield is downloaded and shown as context but not tested (no single direction is claimed for it).

## Tiers, splits, pass rules
As review #17: judged on TOP30, LAB10 and ALL reported; and, once review #22 has built it, the point-in-time top 30 reported.
Discovery before 2024-01-01 (Fear & Greed from Feb 2018), confirm 2024-01-01 to 2026-07-31, holdout not loaded. A T3 filter
must pass T3's rules and beat T3-B's MAR in both periods; H07-FG must pass H07's bar and beat plain H07 in both periods.

## Either way
These series join the lake and the agent pack as market context (shown, labelled with this review's verdict), so Ananta can
say what the wider world is doing; a failed variant is context, never a decision input.
