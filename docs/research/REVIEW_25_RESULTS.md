# Review #25 results: the benchmark and the exposure dial

Run 2026-10-10 exactly as pre-registered (REVIEW_25.md). Bitcoin daily candles from the lake, NDAX costs (0.20% + 0.18% half
spread each side) on every change of position, positions changed at the next day's open. Raw numbers: `review25.json`.

| Variant | Period | Total | Per year | Worst fall | Return / fall | Sharpe | In market | Trades |
|---|---|---|---|---|---|---|---|---|
| HOLD (reference) | 2018–2023 | +207% | +20.9% | −81% | 0.26 | 0.63 | 100% | 1 |
| **GATE50 (benchmark)** | 2018–2023 | +339% | +28.3% | −65% | 0.44 | 0.76 | 50% | 141 |
| GATE50_200 | 2018–2023 | **+591%** | **+38.6%** | **−52%** | **0.74** | **1.01** | 37% | 81 |
| GATE50_VOL | 2018–2023 | +348% | +28.8% | −48% | 0.60 | 0.96 | 50% | 152 |
| HOLD (reference) | 2024–Oct 2026 | +100% | +28.5% | −53% | 0.54 | 0.77 | 100% | 1 |
| **GATE50 (benchmark)** | 2024–Oct 2026 | +73% | +21.9% | −34% | 0.64 | 0.76 | 54% | 67 |
| GATE50_200 | 2024–Oct 2026 | **+85%** | **+25.1%** | −30% | **0.83** | **0.88** | 45% | 47 |
| GATE50_VOL | 2024–Oct 2026 | +77% | +23.0% | −33% | 0.71 | 0.85 | 54% | 70 |

PAIR_GATE50 (half Bitcoin, half Ethereum, each gated): +735% in 2018–2023 (Ethereum's gated half +1,131%), +47% in 2024–2026
(Ethereum's half +20%, worst fall −51%): Ethereum helped in the first period and hurt in the second; not a candidate.

## Verdict

- **The benchmark (hurdle) is GATE50:** every Ananta strategy must beat Bitcoin-with-its-50-day-gate after costs, over the same days.
  In both periods it cut the worst fall a lot (−65% vs −81%, −34% vs −53%); it beat holding in 2018–2023 and trailed it in the
  2024–2026 bull market (+73% vs +100%), as a gate should.
- **GATE50_200: PASS.** Also requiring the 200-day average gave the best return per unit of fall in both periods (0.74 and 0.83),
  the highest returns, fewer trades, and the least time in the market. **It becomes the exposure dial's first version.**
- **GATE50_VOL: PASS** (0.60 and 0.71, both better than the benchmark), but behind GATE50_200 in both periods. Volatility sizing
  runs beside the dial on paper as its challenger; combining the two was not tested and is not assumed.
- Caution: one coin and two periods; the 200-day rule is one well-known idea, not a search over many, which keeps this honest.
