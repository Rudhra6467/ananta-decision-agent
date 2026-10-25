# India voice agent timing, app separation, and pre-live account readiness (20 Oct 2026)

Madhav's questions, 20 Oct 08:36 Toronto:
- (4) When is the best time to start an Ananta India voice agent like the crypto one? Keep it completely separate. In the app, pressing "Indian market" reloads the whole app with Indian data and no link to crypto.
- (5) In future, one voice with all the knowledge, and one app showing every market separately, each clearly different in design, architecture, voice and feel.
- Residency: Indian-born, recently moved to Canada, applying for PR, and will always stay Indian. Ananta manages his father's account until live, then adds his own account after live. He is ready to do the paperwork before live, and none is needed while Ananta is a prototype.

Part B is factual background from public broker pages, gathered so the paperwork is ready before live. It is **not legal or tax advice**. Each item ends with who should confirm it.

---

## A. The India voice agent

### A1. When to start: after the India brain has something true to say every day

A voice is only as good as what it reads. The crypto voice works because behind it sit a live paper book, a ledger, a "why" for every decision, and a map of the app it can point at. Today the India side has the first two only partly:
- The stock paper engine runs.
- SP1 index paper starts Wed 21 Oct.
- The "why" layer and a read model the app can serve do not exist yet.

The crypto voice also needed about three weeks of fixes, and two of those fixes are still in review (say-vs-show and mic timing). The India voice should start from the fixed engine, not the old one.

| Step | Start when | What it is | Done when |
|---|---|---|---|
| V0. India read model (no voice) | Now, alongside SP1 paper | A read-only summary built each evening on the Mac from the ledgers and manifests: the book, today's decisions and their reasons, the tracker, and the research registry. Derived numbers only, never raw NSE or Kite rows. | Builds every evening for 10 sessions in a row, and every number in it traces to a ledger row. |
| V1. India app shell (screens, no voice) | After 10 clean SP1 paper sessions (about 4 Nov) and once the crypto voice fixes have run a week | The "Indian market" button opens a separate India app that reads only the V0 summary. | Madhav uses it for a week, and nothing on it touches crypto (checked automatically). |
| V2. India Ask (typed questions) | After V1 | Typed questions about the India book, answered only from the V0 summary, with the same honesty checks as crypto (say-vs-show map, "I don't know" when the summary has no answer). | A 30-question India exam passes. |
| V3. India voice | After V2 (target: late Nov to early Dec) | The fixed crypto voice engine, with its own voice, its own wake words, and India terms (₹, IST, NSE session times, lots, expiries). | The same voice checks crypto passes, run on India screens. |

The order matters. Voice comes last because every voice problem Madhav flagged in crypto traced back to the layers underneath: what it reads, and what the screen map lets it show.

### A2. Complete separation (his item 4)

| Layer | Crypto (today) | India (planned) | Rule that keeps them apart |
|---|---|---|---|
| Data | `jarvis.sqlite` and the crypto lake | `india/` lake, ledgers and the V0 summary | Separate files and processes; neither service can open the other's paths (a check like leakcheck, run in tests). |
| Service | `com.ananta.jarvis` | A separate `com.ananta.india.app` service on its own port | Separate launchd job, logs, sign-in token and voice files. |
| Web address | livetrading247.com | A separate address on the same tunnel (e.g. `india.` subdomain) | Different cookies and storage, so nothing carries over between them. |
| App | Crypto screens | India screens under their own root | Pressing "Indian market" does a full reload, not a tab switch: the web app loads a fresh page, and the phone app remounts a separate root, so no crypto state survives in memory. |
| Voice | Kokoro voice A, crypto wake words | A different Kokoro voice, India words | Separate voice IDs and separate say-vs-show maps. |
| Look | Crypto palette | Its own palette and type | Unmistakable at a glance which market is open. |

The data-use rule holds as before. NSE and Kite data are for personal use, so the India app shows only derived numbers (book, P&L, decisions, reasons), behind Madhav's sign-in. Raw rows never leave the Mac.

### A3. Later: one voice across markets (his item 5)

One voice that knows everything, without ever mixing the books:
- A thin front voice that only routes. It decides which market a question is about and hands it to that market's own brain. When a question spans markets ("how did everything do this week?"), it asks each brain separately and reads each answer under its own name.
- Each brain keeps its own numbers, rules and evidence bar. The router never computes anything itself.
- The app shows every market side by side, each in its own design, so the difference is visible.

Build this only after both voices have each stood on their own for a few weeks.

---

## B. Pre-live account readiness (factual background, not legal or tax advice)

**Prototype stage needs nothing.** Ananta's Kite module only reads data and never places, changes or cancels an order. Its single write call is Kite's margin calculator, approved on 19 Oct. Zerodha says market data and the read calls work from any IP address. The rules below start to matter only on the day Ananta places a real order.

### B1. Father's account (resident; Zerodha ID kept in ~/ananta_private): before Ananta places any order

1. **Static IP for API orders.** Zerodha requires a static IP for API order placement from 1 April 2026, under the NSE/SEBI retail-algo rules. You may register up to two IPs, and change them at most once a week. One IP can be shared only with "immediate family", which Zerodha names as spouse, dependent children and dependent parents.
   - Decide before live which machine places orders (the Mac in Canada, or a small server in India), and get a static IP for it.
   - Confirm with Zerodha that your father's account fits their family rule, or whether the API app should be in his name.
2. **Your father's written consent** for Ananta trading his account, and Zerodha's view on a family member running the account through the API. Confirm with Zerodha.
3. **Registration threshold.** Algos sending 10 orders per second or fewer do not need exchange registration, but broker risk controls still apply. Ananta's order rate will be a few orders a day, far below that. Confirm Zerodha's order-tagging requirements at that point.
4. **Tax on his account** is his. F&O gains are usually treated as non-speculative business income in India, which affects his return form and audit thresholds. Confirm with his CA.

### B2. Your own account (after live)

1. **Residency.** Indian rules use two different tests:
   - FEMA (banking and investment accounts) mainly looks at why and for how long you are living abroad.
   - The Income Tax Act counts days in India.

   Applying for PR does not by itself change either. Zerodha converts a resident account only to NRO (not NRE), and only after your status on the income tax portal shows non-resident. Confirm your own status with a CA in India. This matters for any resident bank or demat accounts you already hold, separately from Ananta.
2. **What an NRI can trade at Zerodha:**

   | Activity | NRO non-PIS | NRE-PIS |
   |---|---|---|
   | Equity delivery | yes | yes |
   | Intraday equity | yes | no |
   | F&O | yes | no |
   | BTST | yes | no |
   | Pledge for F&O margin | yes | no |
   | MTF | no | no |
   | Currency | no | no |
   | Commodity | no | no |

   US and Canada residents also cannot buy mutual funds through Zerodha Coin. **So your account is an NRO non-PIS account. The currency and commodity paper tracks stay research-only for it.**
3. **Costs are higher for NRIs**, and Ananta must model them before your account's numbers mean anything. Zerodha NRI F&O brokerage is ₹50 per executed order (₹20 for residents), plus clearing charges of ₹150 per crore a month on futures and ₹1,500 per crore a month on options. **Ananta task:** add an "NRI" cost profile to the paper engine.
4. **Custodian (CP) code for NRI F&O.** Some brokers require one. Zerodha's pages I could read did not say. Confirm at account opening.
5. **Tax across two countries** (confirm with a CA in India and a Canadian accountant):
   - India taxes Indian-source gains, and tax is usually deducted at source on NRI accounts.
   - Canada taxes its residents on worldwide income, with credit for Indian tax under the India–Canada tax treaty.
   - Canada's T1135 foreign-property form applies once the total cost of specified foreign property exceeds C$100,000.
   - Moving money out of an NRO account usually needs the bank's 15CA/15CB forms, within an annual limit.

### B3. What Ananta's side must have ready before the first real order

All of this is engineering, none is paperwork:
- A separate, reviewed order module. Order calls are forbidden in code today, and leakcheck enforces it.
- The order machine and its static IP.
- A cost profile per account (resident for your father's, NRI for yours).
- A per-account ledger, so the two books never mix.
- The survival rules (5% in a day, the 22% pause) switched from "record only" to "enforced".

---

Sources:
- [Zerodha: segments NRIs can trade](https://support.zerodha.com/category/account-opening/nri-account-opening/trading/articles/segments-in-which-nris-are-allowed-to-trade)
- [Zerodha: can an NRI trade F&O](https://support.zerodha.com/category/account-opening/nri-account-opening/trading/articles/can-a-nri-trade-in-futures-options)
- [Zerodha: NRI charges](https://support.zerodha.com/category/account-opening/nri-account-opening/articles/what-are-the-charges-for-nri-accounts)
- [Zerodha: converting a resident account to NRI](https://support.zerodha.com/category/account-opening/nri-account-opening/articles/convert-resident-account-to-nri-account)
- [Zerodha: static IP for Kite Connect](https://support.zerodha.com/category/trading-and-markets/general-kite/kite-api/articles/static-ip)
- [Marketcalls: NSE retail algo rules](https://www.marketcalls.in/market-regulations/new-nse-rules-for-retail-algo-trading-what-retail-traders-algo-platforms-and-brokers-must-now-do.html)
