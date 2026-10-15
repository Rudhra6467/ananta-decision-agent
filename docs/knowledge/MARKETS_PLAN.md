# Ananta's markets plan: crypto today; American, Indian and Canadian market agents next

Written 2026-10-11 for Madhav, his family and the people testing the app.

- **What exists today:** crypto, on paper.
- **What follows:** a plan, not a promise of dates or returns. The order is Madhav's call.
- **Rules and costs below:** as of mid-2026. Each agent re-checks them with a web lookup before it is built.

## What every market agent reuses (already built for crypto)

1. **Data:** years of daily and intraday prices in a research lake, quality-checked.
2. **Pre-registered reviews.** An idea is written down before it is tested. It must pass in two separate periods, after
   real costs, against random entries. Most ideas fail, and that is the point: only what survives may trade.
3. **The exposure dial:** how much may be in the market, decided by the market's own trend before any setup.
4. **Paper books with real prices and real costs**, judged against a simple benchmark (the hurdle).
5. **Brakes in code, outside the AI:** daily and weekly loss limits, a losing-streak pause, a kill switch, and stops held by the
   broker.
6. **The go-live gate:** 27 checks, then tiny live money with each order approved by hand, then normal size.
7. **Ask Ananta, by voice or typing:** every answer comes from the evidence.

## Crypto (live on paper today)

- **What it does:**
  - Watches about 390 coins, every day and night.
  - Pre-registered reviews #1-#30 (#28 was a change review, not a study).
  - One measured daily edge: dip buys on the biggest coins while the market trend is down (review #26, confirmed point in time by #29).
- **The $500 NDAX book:**
  - Started Oct 11, in Canadian dollars, at NDAX's real prices.
  - Its 2018-2026 backtest fell about half as far as its benchmark.
- **The second Mac** records NDAX's real buy and sell prices every minute.

## Indian market agent (NSE / BSE)

- **The market:**
  - Hours: 9:15 am - 3:30 pm IST, Monday to Friday.
  - Indices: Nifty 50, Bank Nifty, Sensex. Regulator: SEBI. Settlement: T+1.
- **Futures and options (F&O):**
  - The world's busiest index-options market.
  - SEBI's own study found about 9 in 10 individual F&O traders lost money (FY22-FY24).
  - Since late 2024 there is only one weekly index expiry per exchange, and contracts are bigger.
- **Brokers with trading APIs:** Zerodha (Kite Connect), Upstox, Angel One (SmartAPI), Dhan.
- **Costs to model:** brokerage, STT, exchange and SEBI fees, stamp duty, GST.
  - Short-term gains on listed shares are taxed at 20% and long-term at 12.5% above ₹1.25 lakh (from the July 2024 budget).
- **Plan:**
  1. Nifty 500 daily history.
  2. The same reviews as crypto: trend, dips in uptrends, zones.
  3. A paper book in rupees against a Nifty 50 benchmark.
  4. F&O only after cash stocks pass, and only defined-risk.
- **Knowledge of how Indian traders actually work is the most valuable input here.** Madhav's family includes an experienced Indian-market trader.
- **Accounts:** a resident's account and an NRI's account follow different rules, so whose account it would run in matters.

## American market agent (NYSE / Nasdaq)

- **The market:**
  - Hours: 9:30 am - 4:00 pm ET, plus pre- and after-market. Settlement: T+1 since May 2024.
  - The deepest stock and ETF market, with the most free history.
- **Brokers with APIs:** Alpaca (built-in paper trading), Interactive Brokers.
- **The pattern-day-trader rule** has applied to margin accounts under $25,000 making frequent day trades. Check the current
  rule before building.
- **Plan:**
  1. S&P 500 and sector ETFs daily.
  2. The trend dial against the S&P 500.
  3. Paper on Alpaca, then the gate.

## Canadian market agent (TSX / TSX-V)

- **The market:**
  - Hours: 9:30 am - 4:00 pm ET. Settlement: T+1 since May 2024.
  - Banks, energy and mining dominate.
- **Brokers with APIs:** Questrade, Interactive Brokers. Wealthsimple has no official public trading API.
- **TFSA and RRSP:** frequent trading inside a TFSA can be taxed as business income.
- **Plan:**
  1. TSX 60 / TSX Composite daily.
  2. The same dial and reviews.
  3. Paper first.
  4. It shares the CAD tooling built for the NDAX book.

## Proposed order (Madhav decides)

1. Finish crypto: 60 market days on paper, then the gate, then tiny live.
2. **American:** the best free data, and paper trading built into the broker.
3. **Indian:** with a family member who trades Indian markets as the domain expert.
4. **Canadian:** smallest step, because the CAD tooling already exists.

Each agent goes through the same evidence process. No market goes live without passing the gate and Madhav's sign-off.
