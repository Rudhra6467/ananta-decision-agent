# Ananta Rulebook v0: the Explorer (paper only)

Status: **DRAFT for the operator's mark-up.** Nothing here is approved for live money.
Version id: `rulebook.v0` (every trade and decision records it).

## 0. Purpose and principles

- **Loose on purpose.** Paper exists to make mistakes cheaply. If any setup fires, the Explorer trades it. It never waits for a perfect signal.
- **Every rule has an ID** (S1, L2, E3, G2, X4 …). Every decision records every rule that fired and every value it looked at. When a trade loses, we can see which rule caused it.
- **Real costs on every paper trade.** NDAX: 0.20% fee per side, plus the coin's measured half-spread on market orders.
- **Rules change only by a new version** (v0 → v1 …), after a repair-shop review (section 11) and the operator's approval.
- **Hard limits that never loosen:**
  - paper only;
  - no live orders;
  - the Agent never writes Hands' database;
  - the kill switch and the daily trade cap always apply.

---

## 1. Universe and clock

| ID | Rule |
|---|---|
| U1 | Coins: BTC ETH SOL ADA DOGE AVAX BCH LINK LTC XRP. Candidates for more coins come from the fresh-coin sets later. |
| U2 | Scan every **15 minutes**, 1 minute after the 15m candle closes. Until Hands serves 15m/30m candles (section 13), scan hourly and skip the rules that need them. |
| U3 | Only **closed** candles. A forming candle is never used. |
| U4 | Stale data: if any candle a rule needs is more than 2 intervals old, that coin gets no new entries. Open trades are still managed. |

## 2. Market state: bull, bear, reversal

| ID | Name | Rule (1h unless stated) |
|---|---|---|
| S1 | Bias (solidness) | **BULL**: close > EMA50 and EMA50 higher than 5 candles ago. **BEAR**: close < EMA50 and EMA50 lower than 5 candles ago. Otherwise **NEUTRAL**. |
| S2 | Direction (current) | **UP**: close > EMA20 and EMA20 higher than 3 candles ago. **DOWN**: the mirror. Otherwise **FLAT**. EMA25 runs as a shadow variant (S2b) and is logged for comparison. |
| S3 | Reversal up (early) | 15m close crosses above the 15m EMA20 **and** that EMA turns up (higher than 3 candles ago). **Confirmed** if the 30m close is above the 30m EMA30 now or crossed it within the last 4 candles of 30m. Logged as S3_EARLY or S3_CONFIRMED. |
| S4 | Reversal down | The mirror of S3. Used only for exits, because we buy only. |
| S5 | Higher context (logged, not a gate) | 4h trend (close vs EMA50 and EMA20 vs EMA50), daily close vs daily EMA50, BTC's S1 and S2. Studies showed the BTC filter helps, so the repair shop checks it first. |

## 3. Levels: support and resistance

| ID | Rule |
|---|---|
| L1 | **Swing lows / highs** (1h, last 10 days): a low with 3 higher lows on each side is support; a high with 3 lower highs on each side is resistance. |
| L2 | **Yesterday's high and low**, and **today's open** (UTC day). |
| L3 | **Round numbers**: coin-specific steps (for example every $1,000 for BTC and $100 for ETH), logged only. |
| L4 | A **zone** is a level ± 0.25 × ATR14 (1h). Nearest support zone below the price; nearest resistance zone above it. |
| L5 | **Room** = distance to the nearest resistance zone, in % and in R (R = entry − stop). |

## 4. Indicators

| ID | Rule |
|---|---|
| I1 | RSI14 on 15m and 1h. |
| I2 | Momentum: 12-candle rate of change on 1h, plus its percentile over the last 200 candles. |
| I3 | **Contraction**, if either holds: Bollinger(20, 2) width at or below its 20th percentile over 100 candles (1h), or ATR14 below 0.8 × its 50-candle average. |
| I4 | Volume ratio: the candle's volume ÷ the average of the previous 20 candles (15m and 1h). |
| I5 | Database knowledge, logged as tags that feed the repair shop, not gates: green-run count on 5m (a run of 3 or more greens means "chasing, prefer a limit"), and hour of day. |

## 5. Setups (entry candidates)

Any setup that fires creates a candidate. **There is no minimum score in v0.**

| ID | Setup | Fires when | Entry plan |
|---|---|---|---|
| E1 | **Trend pullback** | S1 BULL, price touches the 1h EMA20 or a support zone, 1h RSI 35–55, then S3 (EARLY is enough) | Limit at the S3 candle close − 0.25 × ATR (15m) |
| E2 | **Breakout** | A 1h close above a resistance zone, volume ratio ≥ 1.5, and contraction (I3) at some point in the last 12 hours | Limit at the top of the broken level's zone (the retest) |
| E3 | **Bounce from support** (counter-trend) | Any bias, price in a support zone, 15m RSI < 35 and rising, then S3 | Limit at the S3 candle close − 0.25 × ATR (15m) |
| E4 | **Momentum continuation** | S1 BULL and S2 UP, momentum percentile ≥ 70, 1h RSI 55–70, a 15m pullback to its EMA20 that holds (close back above) | Limit at the 15m EMA20 |
| E5 | **Squeeze release** | Contraction (I3) on the previous candle, then a 1h close above the upper Bollinger band, S2 not DOWN | Limit at the release candle close − 0.25 × ATR (1h) |

| ID | Entry rule |
|---|---|
| N1 | **Limit orders only.** The green-run study showed they save about 0.26% per trade. |
| N2 | Limits rest for 1 hour (intraday) or 2 hours (the other types). If unfilled, the trade is logged as **MISSED** and followed anyway (section 10), so we learn what chasing would have done. |
| N3 | At most one open trade per coin per trade type. If two setups fire together, both are logged and the one with more room (L5) is taken. |
| N4 | Caps so a bug cannot run wild: at most 20 open trades, and at most 30 new entries per day. |

## 6. Trade type (the goal of the trade)

Assigned at entry and never changed. The **longest** type that qualifies wins.

| ID | Type | Qualifies when | Setups |
|---|---|---|---|
| G1 | **LONG_TERM** (days to weeks, cap 60 days) | S1 BULL, 4h trend up, daily close > daily EMA50 | E1, E4, E5 |
| G2 | **SHORT_TERM** (1–5 days) | S1 BULL or NEUTRAL, room (L5) ≥ 3% | Any |
| G3 | **INTRADAY** (≤ 8 hours) | Room 1.2–3%, or setup E3 in BEAR | Any |

- Anything else is logged as **NO_TYPE** and not traded. It is still followed (section 10).
- Intraday note: charges are large relative to intraday moves, so intraday entries **and** profit exits are resting limits set at entry. Coins whose half-spread is above 0.30% are tagged **EXPENSIVE**, so the repair shop can check them first.

## 7. Exits: the three bells for each type

Each open trade has a tracker. It checks the bells at every scan, in this order: **disaster → warning → profit.**

| ID | Bell | LONG_TERM | SHORT_TERM | INTRADAY |
|---|---|---|---|---|
| X1 | **Disaster stop** (resting) | entry − 3 × ATR (1h), or below the support zone used, whichever is lower | entry − 2 × ATR (1h) | entry − 1.2 × ATR (15m), at least 0.6% |
| X2 | **Disaster event** (all types) | Kill switch on; or BTC falls ≥ 4% within one 1h candle; or the coin falls ≥ 3 × ATR (1h) within one 15m candle. Exit at market. | same | same |
| X3 | **Warning bell** | Daily close < daily EMA20 → exit at the next open (the V1 exit) | 1h close < EMA50, or S4 on 30m while below +1R | S4 on 15m, or no progress (< +0.3R) after 4 hours |
| X4 | **Profit booking** | No fixed target. After +2R, trail the stop at 2.5 × ATR (4h) below the highest close. | Limit at the nearest resistance zone or +2R, whichever is closer | Limit at the nearest resistance zone or +1.5R, at least +1.2% |
| X5 | **Time cap** | 60 days | 5 days | 8 hours |

- A resting stop or target fills at its price. If a candle opens beyond the level (a gap), the fill is at the open.
- If one candle touches both the stop and the target, the **stop counts first** (the pessimistic rule our studies use).

## 8. Size and the paper account

| ID | Rule |
|---|---|
| Z1 | Explorer paper account: **$2,000**, with **$100 per trade** for every type. It is sized so the Explorer can hold many trades at once and doesn't sit idle. |
| Z2 | The circuit breaker is **logged, not enforced**, in the Explorer. It records when it *would* have tripped (4 losses in a row, or a 20% drawdown), so we learn whether its limits are right. The V1 book keeps its real breaker. |
| Z3 | Kelly and variable sizing are **off** until a setup has at least 100 closed trades with a measured edge. |

## 9. Reports back to the operator

| ID | Report | When | Where |
|---|---|---|---|
| P1 | Entry, exit and missed-entry alerts: coin, setup, type, price, bell, net P&L | as they happen | phone (ntfy), and later the Ananta app |
| P2 | **Daily status**: open trades with P&L; each trade's state (safe / warning close / near target); closed trades today; P&L by type and by setup | 21:00 Toronto | phone summary + `explorer_daily/DATE.md` |
| P3 | **Portfolio suggestions**: for each open trade, HOLD / TIGHTEN / EXIT-SOON, with the rule reasons (for example "X3 warning: 1h close under EMA50; S4 on 30m") | with P2 | same |
| P4 | **Weekly repair-shop report** (section 11) | Sunday | a PR in this repository, plus a phone summary |

## 10. Evidence: what is collected

Every scan writes one **decision record** for each coin, including coins where nothing happened. It contains:
- the rulebook version and the candle times used;
- every state value (S, L, I tags);
- every setup that fired;
- the trade type and why;
- candidates that were **rejected**, with the reason (caps, NO_TYPE, stale data).

Every trade writes:
- **Entry**: planned price, filled or missed, and the fill price, cost and time.
- **While open**: the bell states at every scan (so we can see *when* a warning first appeared); the best and worst price reached (MFE / MAE).
- **Exit**: which bell, price, cost, net P&L in $ and in R.
- **Shadows**, computed after the trade from the same candles:
  - what the **other two types' exits** would have made;
  - what a **random entry** on the same coin, at the same time, with the same type would have made;
  - for MISSED entries, what the trade would have done.

Storage:
- `explorer_book.sqlite` (trades), `explorer_decisions.jsonl` (decision records) and `explorer_shadow.sqlite` (shadow outcomes).
- Evidence class **PAPER_EXPLORER**: never counted toward a live decision on its own.

## 11. The repair shop: reconstruction, comparison, learning

**R1. Reconstruction (daily).**
- Rebuild every decision from the stored closed candles, and check that the rules produce the **same** decision.
- A mismatch is a **bug ticket**, not a strategy lesson. It usually means a data gap, a forming candle, or a code error.
- This is how we caught the forming-candle and floor-rounding bugs before.

**R2. Comparison (weekly).** For every rule ID, setup, type, bell and market state:
- trades, win rate, average net, expectancy in R, total $;
- versus the random-entry shadow (does the setup beat chance?);
- versus the other exits' shadows (does this exit beat the alternatives?);
- versus MISSED entries (should limits be closer, or looser?).
- **Out of our hands** is a separate column: losses from costs, gaps, or data. These are not strategy lessons.

**R3. History replay (weekly).**
- The same rulebook version runs over the 5m history: 2019–2023 for discovery, 2024–July 2026 for confirmation. The Aug–Sep 2026 holdout stays unused.
- This gives thousands of trades per rule in minutes. Paper tells us whether live behaviour matches history.

**R4. Learning → the next watches.** Each weekly review ends with at most **3 proposals**, for example "E3 in BEAR loses in both history and paper: allow E3 only in NEUTRAL/BULL". Each proposal:
1. is written down **before** its test is run;
2. is tested on history (discovery, then confirmation);
3. runs in paper as a **shadow variant** next to the current rule, logged and not traded, for at least 30 trades or 2 weeks;
4. is **promoted** only with the operator's approval, as a new version (v0 → v1).

Every rule has a status that the next watch reads:
- **ACTIVE**: trades.
- **PROBATION**: trades at half size and is flagged in reports.
- **SHADOW**: logged only.
- **RETIRED**: logged only, and re-checked monthly in case the market changes.

**R5. Forwarding.**
- **Explorer → the operator**: through the reports in section 9.
- **The operator → the Agent**: by approving a new rulebook version, a file in this repository that the Agent reads at startup and stamps on every record.
- **Explorer → live**: only rules that are ACTIVE, have ≥ 100 trades, a positive edge in both history and paper, and beat the random shadow can be written into the **strict live rulebook** for the $500 account. That rulebook is a separate document, reviewed before going live.

## 12. What the Explorer may not do

- Place live orders, touch exchange keys, or write Hands' database.
- Change a rule without a new version.
- Exceed the caps in N4, or ignore the kill switch.

## 13. Dependencies before the build

| Item | Status |
|---|---|
| Hands serves closed 15m and 30m candles to the Agent. Today it serves 1h/4h/1d only. | **Needed**: small App PR |
| NDAX half-spreads per coin | measured 2026-09-29; re-measured monthly |
| Phone alerts | ntfy live; Ananta app push before live |
| History replay engine for the rulebook | to build (reuses the green-run engine) |

---

## Questions for the operator's mark-up

1. Averages: EMA50 on 1h for bias and EMA20 for direction, with EMA25 as a shadow. Change these?
2. Paper account: $2,000 with $100 per trade, max 20 open, 30 new entries per day. OK?
3. Intraday: allow all 10 coins (the costs will teach), or only BTC/ETH?
4. Daily report at 21:00 Toronto time, weekly on Sunday. OK?
5. Anything to add to the three bells: a specific "disaster" you have in mind?
