# Live-money safety for the $500 NDAX book (D12)

Written 2026-10-11. **Nothing here moves real money.** The book is paper. This is what must be true, and rehearsed, before one
real dollar goes in. Wiring the guard into a real order path is a safety change, so it waits for Madhav's review.

## 1. The brakes (code, outside the AI)

| Brake | Limit on $500 | What happens |
|---|---|---|
| Day loss | 2% ($10) | no new buys the next day |
| Week loss | 4% ($20) | no new buys until Monday |
| Losing streak | 4 losing setup trades in a row | no new buys for 7 days |
| Fall from the peak | 15% ($75) | PAUSED: no new buys until Madhav presses Resume (`POST /v3/book500/resume`) |

- **Where they live:** `src/research/book500.py` (class `Brakes`). The paper book (`jarvis/service/ndax_book.py`) and the
  live guard (`jarvis/service/live_guard.py`) both use it. The AI cannot change or skip them: the brain only proposes buys, and
  the guard decides.
- **Brakes never block a sell.** Exits, the dial closing and the kill switch always run.
- **Backtest, 2018-2026 (docs/research/BOOK500.md):** the day brake fires often (97 times in 2018-2023), because 60% of the
  book is Bitcoin and Ethereum. Madhav may want the day and week brakes to apply only to the setup sleeves. That is his call.

## 2. Stops on NDAX itself

D12 asks for stops held by the exchange, so a dead Mac cannot leave a trade unprotected. Review #27 found that tight stops ruin
the dip trade. The backtest settles the distance:

| Resting stop on NDAX | Setup trades 2024-2026 | Book 2024-2026 |
|---|---|---|
| none | +4.5% a trade | +74% |
| 2 × ATR (the invalidation) | +1.9% | +67% |
| 4 × ATR | +4.2% | +73% |
| **6 × ATR (recommended)** | **+4.5% (never touched)** | **+74%** |

- **Plan:** every setup and judgment buy gets a resting stop at 6 × ATR(14) under the entry. That is outage insurance only, and
  the normal exits still run.
- **Worst case:** a 6 × ATR stop loses about 3 times the planned 0.5% risk, so about 1.5% of the book on one trade.
- **The core** (BTC + ETH) has no resting stop. The dial and the 15% pause protect it.
- **Before live:** check on NDAX, with the smallest possible order, that a stop order is accepted and shows under open orders.
  NDAX runs on AlphaPoint, which lists stop-market and stop-limit order types; the check proves it for our account.
- The paper book already records the stop each holding would carry (`stop_on_ndax`; `live_guard.stops_plan`).

## 3. The kill switch for NDAX

`live_guard.kill_plan()` shows the plan at any time (a dry run):

1. Cancel every open order on NDAX.
2. Sell every holding at the bid, back to CAD.
3. Check every balance except CAD is zero.
4. Disable the API key on the NDAX website.

The existing Hands kill switch (docs/RUNBOOK_SAFETY.md §1) stays as it is. The NDAX kill switch gets wired at go-live, after
review.

## 4. Incident runbook (what to do, in order)

| What you see | Do this |
|---|---|
| A trade or a balance you don't recognise | Kill switch (§3), then disable the API key on the NDAX website. Then ask Ananta "what did you do today". |
| The Mac is off or asleep | Nothing is at risk beyond the resting stops. Open the lid or wake it; the book catches up at the next daily close. |
| The phone says a brake fired | Nothing to do. Read why in Ananta: "did a brake fire". Resume only after the 15% pause, and only if you agree. |
| NDAX is down | Nothing new can be bought or sold. The resting stops sit on NDAX's side. Wait, then check the balances. |
| The API key may have leaked | Disable it on the NDAX website first, then make a new one (§5). |

## 5. API key and passwords (Madhav does these himself; never paste them into chat)

**The NDAX API key (only at go-live):**

1. Log in at ndax.io, open **Settings → API Keys**, and create a new key.
2. Tick **trade** only. Leave **withdraw** off: no software can take money out.
3. If NDAX offers an IP allowlist, add only your home internet address.
4. Open Terminal and type `open -e ~/code/ananta-agent-research/.env`. Add two lines yourself, `NDAX_API_KEY=` and
   `NDAX_API_SECRET=`, each followed by its value. Save and close.
5. Restart: `python3 ~/ananta_runs/restart_jarvis.py`.

**Rotate the development passwords (D12):**

1. Change the Hands login password in the Hands app's settings.
2. Open Terminal and type `open -e ~/code/ananta-agent-research/.env`. Find the line that holds the old Hands password,
   type the new one in its place, save, then restart with `python3 ~/ananta_runs/restart_jarvis.py`.
3. Change the Ananta app's owner password from the app's own settings screen.
4. Do the same for any password that was ever typed into a terminal during development (the email app password, the R2 keys).
   Create the new one on that service's website first, then replace it in `.env`.

## 6. Rehearsal checklist (monthly on paper, and once more on the day before going live)

- [ ] Pretend a 2% day loss in a test copy (`pytest tests/test_book500.py`): the next day's buy is refused
- [ ] Pretend a 15% fall: the book says PAUSED; Resume clears it
- [ ] `live_guard.kill_plan()` lists every holding and the CAD expected
- [ ] The Hands kill switch (RUNBOOK_SAFETY.md §1): on, check, off
- [ ] Every paper fill inside NDAX's bid and ask (Acceptance Gate: engine_execution)
- [ ] The sizing audit: 0 violations (Acceptance Gate: engine_sizing)
- [ ] Live only: one tiny stop order placed and cancelled on NDAX; the API key shows withdrawals off

## 7. What is wired and what waits

| Part | State |
|---|---|
| Brakes in the paper book | wired, runs every daily close |
| The live guard | written and tested; wired to nothing (needs Madhav's review) |
| The NDAX kill switch | plan only (dry run); wired at go-live after review |
| Resting stops on NDAX | recorded on paper; placed for real only at go-live |
