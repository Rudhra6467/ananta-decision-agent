# Repair-shop review #30 (pre-registration): the survivorship check for the live 10 - T3-B on the point-in-time top 10

Written 2026-10-15, before the point-in-time top 10 was computed or any result seen (`reports/pit_top10.json` does not
exist yet). Queue item Q9, raised by review #22.

## Why
The live 10 (the lab 10) were chosen by each coin's last 24 months, i.e. with today's knowledge. Review #22 showed what that
can do: on 30 coins, T3-B made +26.1% in 2024 - Jul 2026 on today's top 30 but lost 22.5% on the coins that really were the
30 most traded at each moment. On the lab 10, T3-B made +15.1% in the same period (review #20). The fair question: had
Ananta run T3-B on "the 10 most-traded coins" at each moment, using only what it knew then, would it still pass?

## The tier: PIT10 (src/lake/pit.py, `membership(10)`)
- For each month M, the 10 coins with the highest traded value (Binance spot USDT pairs, rule v1's eligible list: no
  stablecoins, leveraged or wrapped tokens) summed over the 3 months before M. A coin needs all 3 of those months.
- PIT10 is a subset of PIT30, so every member is already in the lake and was checked in review #22 (LUNA's re-use cut stays
  as in `ENDS`; no coin is fetched for this review).
- A coin may be held only on days inside months in which it is a PIT10 member. When it leaves PIT10, T3-B sells it at the
  next open (as if its signal turned off).

## The test (the original, unchanged)
- **T3-B on PIT10:** T3's rules in both periods: a positive return, a smaller worst fall than buy-and-hold of the same PIT10
  coins, and a better MAR than that buy-and-hold.
- Splits as always: discovery before 2024-01-01, confirm 2024-01-01 to 2026-07-31, holdout not loaded. NDAX costs (each lab
  coin's own cost; 0.40% half spread for coins outside the lab 10). One test, nothing tuned.
- Reported beside it, not tested: T3-B on today's lab 10 over the same days (review #20's figures), the PIT10 members per day,
  and the coins that were in PIT10 but are not in today's 10.

## What follows (decided now)
- **PASS:** the live 10's T3-B result is not survivorship-flattered. Gate: `data_survivorship` becomes PASS (both trading
  tiers re-tested: 30 in #22, 10 here); `strategy_survivorship` passes for the 10, and its overall status follows the scope
  decision below. T3's history verdict in the agent pack adds "passes point-in-time on the 10 (#30)".
- **FAIL:** T3-B's history verdict in the agent pack changes to the PIT10 result ("on the 10 most-traded coins at each
  moment, T3-B loses less in slides but did not make money in 2024-26"). The T3 books keep running as paper evidence (Q2);
  no promotion on history; Madhav decides whether to stop a book (recommendation in the results file). `data_survivorship`
  still becomes PASS (the check was done); `strategy_survivorship` stays FAIL with both reasons.
- Either way: Rule A is unchanged (no real money until 60 market days, both dial states, execution within 3 points), and the
  30-coin tier stays as review #22 left it (evidence only, not promoted).

## One decision for Madhav before the run (so the result cannot bend it)
The gate's `strategy_survivorship` check today counts the 30-coin tier, which failed in #22 and is already evidence-only.
- **(a)** It counts every tier that has a paper book: it stays FAIL while the 30-coin books run, whatever #30 shows.
- **(b)** It counts only the tiers that could ever trade real money (the live 10); the 30-coin books are labelled
  "evidence only" wherever they are shown.

Recommendation: **(b)**. Review #22 already ruled the 30-coin tier out of promotion, and the gate exists to decide what may
trade real money. Whichever he picks is written here before the run.

**Madhav's decision (Oct 15, 09:10 Toronto, before the run): "30 yes b".** Run review #30 as written; scope **(b)**: the gate's
`strategy_survivorship` counts only the tiers that could ever trade real money (the live 10), and the 30-coin books are
labelled "evidence only" wherever they are shown.
