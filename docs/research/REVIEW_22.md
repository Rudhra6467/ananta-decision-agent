# Repair-shop review #22 (pre-registration): the survivorship check - T3-B and H07 on the point-in-time top 30

Written 2026-10-05, before the point-in-time membership was computed or any result seen. Why: the TOP30 tier of reviews #15,
#17, #20 is the top 30 by each coin's last 24 months, i.e. chosen with today's knowledge. Coins that were among the most traded
in 2020-22 and then collapsed but kept trading thinly (LUNA, FTT) are missing from it, which can flatter results. The fair
question: had Ananta traded "the 30 most-traded coins" at each moment, using only what it knew then, would T3-B and H07 still pass?

## The tier: PIT30 (src/lake/pit.py)
- For each month M, the 30 coins with the highest traded value (Binance spot USDT pairs, the eligible list of rule v1: no
  stablecoins, leveraged or wrapped tokens) summed over the 3 months before M. A coin needs all 3 of those months.
- Every coin ever in PIT30 that the lake does not hold is downloaded, built and quality-checked the same way (token-swap check
  included; a coin with an uncut swap is refused until checked).
- A coin may be held (T3-B) or bought (H07) only on days inside months in which it is a PIT30 member. When it leaves PIT30,
  T3-B sells it at the next open (as if its signal turned off); an open H07 trade runs to its own exit.

## Tests (the originals, unchanged)
- **T3-B on PIT30:** T3's rules in both periods (positive return, smaller worst fall than buy-and-hold of the same PIT30 coins,
  better MAR than that buy-and-hold).
- **H07 on PIT30:** H07's bar (discovery 30+ market events, mean excess over ordinary uptrend days of PIT30 coins > 0 with
  z >= 2.5; confirm > 0).
Splits as always (discovery before 2024-01-01, confirm to 2026-07-31, holdout not loaded); NDAX costs (0.40% half spread for
coins outside the lab 10). Two tests, nothing tuned.

## What follows
- Both pass: the 30-coin paper tier stands as built (its live coin list is today's top 30, which is what PIT30 is today).
- One fails: that idea's 30-coin result is reported as survivorship-flattered; its paper book keeps running as evidence, and its
  history verdict in the agent pack changes to the PIT30 result. Madhav decides whether to stop the book.
