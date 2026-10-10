# Go-live checklist (engine fix 5, Oct 10, 2026)

Nothing on this list moves real money by itself. Each stage needs every box ticked AND Madhav's sign-off. Paper only until then.

## The engine, in order (what changed on Oct 10)
1. **Exposure dial first** (`jarvis/service/exposure.py`, review #25). Bitcoin's daily close above its 50-day AND 200-day averages
   = OPEN, else CLOSED. While CLOSED there are no new buys, except moments with a measured edge in a closed market (today: H07 on tier A).
2. **Measured edge, not hand-picked points** (`jarvis/service/ev.py`, review #26). Each daily rule × market state × tier has the
   value history measured over random entries after costs, in both periods, shrunk toward zero. Anything that did not pass has 0.
   The brain ranks daily rules by this number, and the pack shows it.
3. **The brain picks, it does not design.** Its default is PASS. It chooses a stop and one of three tested exit plans
   (DIP, ZONE, TREND). It does not make up a hold time or a target.
4. **Risk-based sizing, results in R** (`universe_watch.would_be`). Each trade risks 0.5% of the account: size = risk / distance
   to its stop (8% when there is none), at most 20% of the account in one coin, and at most 6% open risk in total.
5. **The hurdle.** Every strategy must make money (positive R) AND beat the benchmark (Bitcoin above its 50-day average, GATE50)
   over the same days. Otherwise the benchmark itself is the better strategy.
6. **Fidelity** (`ev.fidelity`). Paper results must track the backtest within 3 points a trade over at least 10 trades. A cell that
   falls below goes to the repair shop.

## Stage 0: paper (now)
- [x] Dial live, benchmark books from Oct 10 (`/v3/exposure`, Ask: exposure, the Markets tab card)
- [x] Brain gated by the dial; daily rules ranked by measured edge
- [x] Would-be account in R, with the dial, the risk caps and the hurdle
- [ ] 60 market days of paper with the dial in force (both dial states seen at least once)

## Stage 1: tiny live (needs every box)
- [ ] The would-be account shows positive average R over at least 30 closed trades
- [ ] The would-be account beats the benchmark over the same days
- [ ] Fidelity: no cell with 10+ trades marked "BELOW BACKTEST"
- [ ] At least one rule × tier on the ladder at LIVE_CANDIDATE (Madhav's sign-off)
- [ ] Altcoin risks checked for each candidate coin: token unlocks in the next 30 days, sector cluster (no more than 2 open in one
      sector), and the spread on a down day (cost floor holds)
- [ ] Safety gates and the kill switch tested again (RUNBOOK_SAFETY.md)
- [ ] Madhav approves each order by hand; size 0.25% risk (half of paper)

## Stage 2: normal size
- [ ] 30 live trades at Stage 1, live results within 3 points a trade of paper
- [ ] Still beating the benchmark live
- [ ] Madhav's sign-off

## What sends it back a stage
- Live or paper falls under the benchmark over 60 market days
- Fidelity flags a live cell
- Any safety gate trips
