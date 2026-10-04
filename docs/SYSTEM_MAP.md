# How Ananta is built: the system map

The plain-language map of the whole system: what runs, which database each part keeps, how a market scan becomes a paper
trade and then evidence, and how the repair shop and Madhav's requests close the loop. Ask Ananta reads this file to answer
"how is it built", "where does X live", "what happens after a setup fires". Last updated 2026-10-03.

## The running parts (all on Madhav's Mac)

| Part | Port / schedule | What it does | Its own storage |
|---|---|---|---|
| **Hands** (the App) | :8001 | Exchange side (paper today), Kraken candles, the account, the strategies Hunter / Squeeze / Bollinger, the kill switch | its own MongoDB. The Agent talks to Hands only over HTTP, never to its database |
| **15-minute Explorer** | every 15 min | Pulls closed candles from Hands, checks 10 coins for setups E1-E6, places $100 paper limit orders, manages stops / targets / warning bells on 5-minute bars, records shadows | `explorer_bars.sqlite` (candles), `explorer_book.sqlite` (orders, trades, shadows, events), `explorer_decisions.jsonl`, `explorer_state.pkl` |
| **Hourly watch** | 2 min after each hour | Asks Hands to run Hunter and Squeeze, stores each decision, opens paper trades in Hunter's book (SD6 exit manager) | `agent_decisions.sqlite`, `paper_book.sqlite` (Hunter's book), `watch_heartbeat.jsonl`, `watch_alerts.jsonl` |
| **Trend portfolio (T3)** | ratings each daily close, rebalance weekly | Holds coins in uptrends while Bitcoin is above its 50-day average; MAIN book (approve or autopilot) plus an automatic copy | `portfolio_book.sqlite` |
| **Jarvis service** | :8100 (api.livetrading247.com) | The phone app's server: reads every book above (read-only), runs Ask Ananta, alerts, briefs, the daily jobs | `jarvis.sqlite` (see below); each guest gets `jarvis_guest_<name>.sqlite` |
| **Voice** | :8200 (local only) | Whisper turns speech into text; Kokoro speaks the answer; both run on the Mac, free | none (audio is never stored) |
| **The app** | Expo Go, app.livetrading247.com | Home, Markets, Portfolio, Ananta (chat and voice), Evidence, Cockpit | settings on the phone |
| **Research** | on demand | 7 years of 5-minute history (Binance, 2017 to Sep 2026), the repair-shop studies | `docs/research`, `docs/repair_shop`, `docs/knowledge` |

What `jarvis.sqlite` holds: conversations (`ask_messages`), settings and AI spend, Madhav's own paper book (`manual_fills`,
`manual_orders`, `journal`), alerts and briefs, the mandate and cards waiting for his OK (`pending_actions`), your setups
(`read_fires`), zone visits, the daily news checks, credit records, the short dip shadow (`shadow_h07`), and his requests to
the repair shop (`owner_requests`).

## Our paper books (spoken names)

- **The Explorer**: its own $100 trades, started with $2,000. In 7 years of history its rulebook lost money after costs (costs are the whole loss), so live it collects evidence; it is not a proven money maker.
- **The trend portfolio (T3)**: started with $2,000. The one strategy that passed the repair shop (2024-26: +13% while buy-and-hold lost 22%, with half the drawdown).
- **Hunter's book (SD6)**: the hourly watch's trades; holds one trade at a time today.
- **Your own paper book**: orders Madhav asked for ($1,000 start); every order confirmed on screen.
- **The short dip shadow (H07)**: $100 per signal, its own exit; started 2026-10-03.

## From a market scan to evidence

1. **Scan.** Every 15 minutes (Explorer: E1-E6 on 10 coins), every hour (Hunter, Squeeze), every daily close (your setups, zones, the short dip trade, the trend portfolio's ratings, credit records, one AI news check per coin).
2. **Setup to decision.** A setup needs all its conditions, a trade type with room to a target, and a free slot. Then a limit order with 1-2 hours to fill. Anything blocked (slot taken, no trade type, missed fill) becomes a **shadow trade**, tracked with the same exits, so we still learn what it would have done. A share of scans also opens a **random entry** shadow: the baseline every setup must beat after costs.
3. **Tracking.** Fills, stops, trails and warning bells on 5-minute bars; phone notes for fills and exits; the Home feed; a value snapshot every 15 minutes; a nightly rebuild that recomputes every decision from raw candles and checks it matches the live log.
4. **Performance.** The Evidence page: collected (what was seen and traded), forwarded (questions for the repair shop), in use (what passed). Results are counted by market events, not trades: our 10 coins move together, so ten trades in one drop are one bet.
5. **Repair shop.** A question is written down first, tested on 2017-2023, confirmed on 2024-2026, with the last two months sealed for a final check. 14 reviews so far: the trend portfolio passed, the short dip trade (H07) is promising, most short-term ideas failed on costs.
6. **Evidence use.** The layer map (`knowledge/layers.json`) says which parts may act. Acting today: the market regime (the Bitcoin 50-day rule), coin trend, costs, the trend portfolio, the Explorer rulebook (paper), exits, safety. Shown but not acting: zones, your setups, the decision chain, news, credit, teacher ideas.

## How Ananta (chat and voice) works

- Each question goes to a model with live briefs of our books and the market (the fast path) plus lookups over all the data above. Facts only from those; codes and exact numbers go on screen, the spoken answer is short and rounded.
- **It can do right away:** answer from the data, price history from our stored candles (highs, lows, days, rankings), a web lookup for things outside our data (stocks, news, the economy; labelled "from the web"), the AI news check on a coin, save a note Madhav asks it to remember (his notes folder), flag a request for the repair shop, start a reconstruction, move the screen and walk him through it.
- **It can prepare (a card he confirms with Face ID, or the phone passcode in Expo Go):** paper orders in his own book (buy, sell, close), a stop or target on his own position, alerts and switching one off, mandate changes, the kill switch, the trend portfolio's autopilot, approving or rejecting the trend portfolio's suggestions, the AI budget and voice settings.
- **It cannot:** place real orders (no exchange connected; live needs Madhav's written rules), or hand-edit the Explorer's or the trend portfolio's own trades (they are evidence).
- **Voice:** what reaches the model is a real question: the mic's echo of Ananta's own voice, "hmm" / "okay" and noise are dropped; a sentence cut off in the middle ("I want to know...") waits for the rest. When an answer takes more than about 1.5 seconds Ananta says "one sec" in the same voice.

## Madhav's requests (the repair-shop loop)

"Flag this", "add it to the repair shop", "that was wrong" -> a numbered request (data, feature, bug, idea) -> the Evidence page
and the Home feed -> the next work session reads the open ones first (docs/BACKLOG.md) -> its status changes (planned, fixed,
closed) -> a phone note, and Ananta mentions it once in the next conversation.

## Watches, evidence books, the scoreboard and the eye (built 2026-10-03, Madhav's OK)

- **The watch registry** (`knowledge/watches.json`): every watch declared once, in sections (market weather, coin structure and zones, setups, risk and exits, news and events, baselines), with its candle, trigger, where it runs, entry, exit, size, evidence book and status. Writing a rule there before it trades is its pre-registration.
- **Evidence books**: every signal is a $100 paper trade with its own exit. The daily engine (`watch_engine`, after each daily close) runs your setups (M1a, M2a, M2a-G, M3a, M3b), the short dip trade (H07) and three random baselines (one coin a day held 10, 20 or 30 days), with the same entry and exits the history tests used; one trade at a time per watch and coin. The Explorer's blocked signals count as its would-be trades. Hunter's book (SD6 v3) opens one trade per coin and keeps shadows when full (live after Madhav's merge and a restart of the hourly watch).
- **The scoreboard** (`/v3/scoreboard`, Evidence page, the scoreboard lookup): every trading watch with the same columns against the random baseline with the same holding time, counted by independent events and split by market regime. A watch needs 10 events before it can be called ahead of random.
- **The eye** (`eye`, inside Jarvis): Kraken's live prices every 10 seconds against your stops and targets (sold at the live price), your price alerts, a sudden Bitcoin drop (2% in 15 minutes), and price entering a support zone (feed; phone when attention is HIGH). A supported zone touched while the market is allowed opens the zone-touch evidence trade (stop half a daily range under the zone, else 20 days). Bar-close rules stay on their closes; the Explorer keeps its 5-minute execution so live and replay stay one engine.

## Proposed next

- **A portfolio book (the $500 rehearsal)** that picks among signals with real limits; this is what goes live later.
- Move the Explorer setups and Hunter into the shared engine once their books are stable; funding rates and open interest for the eye.
