# Universe Rule v2 — the live universe (written 2026-10-09, before any result)

Madhav, 2026-10-09: "The ultimate goal is to make it watch whole universe like it was watching 10 in the prototype."
Decisions D1–D7 of the engine plan (Claude Doc "Ananta engine plan: watch the whole crypto universe"), all agreed.

This rule is pre-registered: it is written before any universe trade exists, so the universe cannot be picked to flatter a result.
Rule v1 (src/lake/universe.py, 2026-10-04) stays the research rule for the lake; v2 is the rule for what Ananta WATCHES live.

## 1. Who is in

Every Binance spot pair against USDT whose status is TRADING, read once a day (00:10 UTC) from Binance's public exchangeInfo.
Out, as in rule v1: stablecoins and fiat, leveraged tokens (UP/DOWN/BULL/BEAR), wrapped copies (`src.lake.universe.STABLE`,
`WRAPPED`, `LEVERAGED`), gold-backed tokens (XAUT, PAXG), tokenized shares (Binance tags them "bStocks": Apple, SPY, Nvidia and
about 90 more; they follow stock markets, not crypto), and names outside A–Z / 0–9 (a few new tokens are named in other
scripts; Binance's multi-coin price calls refuse them). Nothing else is taken out: small and new coins are in, in tier C.
On Oct 9, 2026 that left 393 coins: 24 in tier A, 133 in B, 236 in C.

## 2. Tiers (who is judged)

By the median daily traded value (quote volume, USDT) of the coin's last 30 closed days:

| Tier | Median daily trading | Judged? |
|---|---|---|
| A | $20M or more | yes |
| B | $1M to $20M | yes |
| C | under $1M, or fewer than 30 days of history | watched and scored, never judged or promoted (paper fills are not believable) |

Tiers are recomputed once a week (Monday 00:10 UTC) so coins do not flicker between tiers; a trade keeps the tier it was
opened in (the tier is part of its watch id, e.g. `H07-UB`). Membership (listed / delisted) is checked every day.

## 3. The 10 (LAB10) and the 29 (T30)

The 10 live coins and the 30-coin tier keep their own books exactly as before (D7: the control group). The universe books are
separate watch ids (suffix `-UA`, `-UB`, `-UC`), so evidence never mixes. The 10 and the 29 are also in the universe, in their tiers.

## 4. Can-buy flags

`ndax`: listed against CAD on NDAX (public GetInstruments). `kraken`: listed against USD on Kraken (public AssetPairs).
Read daily. A coin nobody in Canada can buy is still watched; it is flagged, never a live candidate.

## 5. Costs (each side, paper)

Fee: NDAX 0.20% when the coin is on NDAX, else 0.40% (Kraken taker).
Half spread: the 10 keep their measured NDAX half spreads; every other coin uses the larger of three times its measured Binance
half spread (bookTicker, daily) and its tier floor: A 0.20%, B 0.40%, C 0.80%.

## 6. Joining and leaving

A coin joins the day it appears TRADING. Rules that need history wait for it (60 days for daily rules, 210 for H07).
A coin that stops trading is marked DELISTED; its open paper trades close at its last close, reason "delisted".

## 7. What runs on every coin (D6)

The daily rules with the same code as the history tests (H07, M1a, M2a, M2a-G, M3a, M3b), the zone touch on live prices, and
random baselines per tier with the same horizons. The 15-minute Explorer setups run on the 10 only, as before; elsewhere they
would be shadows and never wake the brain. Hunter and Squeeze stay on the 10 (they live inside the old backend).

## 8. What earns promotion (D4)

A watch per tier, never one coin: beats its random baseline of the same tier and horizon after costs, over at least 10
independent market days (all trades closing on one day count once), in both market regimes. Promotion steps (shadow ->
evidence -> promoted -> live candidate) each need Madhav's sign-off.

## 9. The brain (D2)

A daily AI budget (BRAIN_DAILY_USD, $1.00) instead of a count; every wake is ranked first and the brain decides the best ones
while budget lasts. Wakes it never reviewed are logged and scored the same way. Raise the budget only after the brain beats its
random twins over 10 market days.
