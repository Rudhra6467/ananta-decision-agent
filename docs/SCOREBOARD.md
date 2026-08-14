# Ananta Strategy Scoreboard

**Update after every lab session (or at least every wave).**  
Status must be one of: `TEST` | `WATCH` | `CORE` | `CUT` | `PARK`

---

## Active book snapshot

| Field | Value | Updated |
|--------|--------|---------|
| Max enabled (charter) | 5 | 2026-08-14 |
| Max slots preferred / absolute | 6 / 8 | 2026-08-14 |
| Current enabled count | _fill_ | |
| Current slots | _fill_ | |
| Active wave | _none / A / B / C / D_ | |
| Last lab date | | |

---

## Strategy table

| Key | Name | Status | Days on (approx) | Regimes seen | Notes / evidence | Last review |
|-----|------|--------|------------------|--------------|-------------------------------|
| hunter | Hunter | PARK | | | Selective core candidate | 2026-08-14 |
| squeeze | Volatility Squeeze | PARK | | | Wave A candidate | 2026-08-14 |
| bollinger-mr | Bollinger Mean Reversion | PARK | | | Wave A candidate | 2026-08-14 |
| vwap-mr | VWAP Mean Reversion | PARK | | | Wave A candidate | 2026-08-14 |
| ema-cross | EMA Cross | PARK | | | Wave B candidate | 2026-08-14 |
| continuation | Continuation | PARK | | | Wave B candidate | 2026-08-14 |
| supertrend | Supertrend | PARK | | | Wave B candidate | 2026-08-14 |
| donchian-breakout | Donchian Breakout | PARK | | | Wave C candidate | 2026-08-14 |
| atr-breakout | ATR Breakout | PARK | | | Wave C candidate | 2026-08-14 |
| keltner-breakout | Keltner Breakout | PARK | | | Wave C candidate | 2026-08-14 |
| time-series-momentum | Time Series Momentum | PARK | | | | 2026-08-14 |
| stochastic-momentum | Stochastic Momentum | PARK | | | | 2026-08-14 |
| rsi-momentum | RSI Momentum | PARK | | | | 2026-08-14 |
| macd-trend | MACD Trend | PARK | | | | 2026-08-14 |
| turtle | Turtle Trading | PARK | | | | 2026-08-14 |
| aggressive-movement-cf1358 | Aggressive movement | PARK | | | Prefer last in queue | 2026-08-14 |

---

## How to update

1. Run `status` in the agent → set **Current enabled count**.
2. Run `monitor` → set **Current slots**.
3. For each enabled strategy, bump **Days on** if it was on today.
4. Add regime from `run` / market agent (NEUTRAL, TREND_UP, …).
5. After marks or obvious results, write one line in **Notes**.
6. Change **Status** only using Laboratory Charter rules.

---

## Decision log link

Agent memory: `decision_log.json` (local) + `history` / `mark` commands.

Weekly habit: copy 3–5 important marks into Notes for CORE/WATCH candidates.
