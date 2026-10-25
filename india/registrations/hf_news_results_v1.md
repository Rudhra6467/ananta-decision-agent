# HFN1 results · a news model reading NSE announcements (2010-2023), 25 Oct 2026

Spec: `hf_news_v1.json` (frozen before any rating or outcome). Model: `ProsusAI/finbert` at revision 0bc2ac10, run on the Mac, zero-shot.
Code: `india/hf_news.py`. Ledger: study HFN1, family news_tone, bar k 32 (z 3.16). Manifest: `manifests/hf_news_results.json`.

## In plain words

**No. The model's reading of company announcements did not tell us where the stock went next.** Seven of the eight registered rows were
REJECTED and one was INCONCLUSIVE; none came near the bar. Positive announcements were followed by about the same 20-session drift as negative
ones once the market is taken out (+0.03% against 0.00% across all stock-days), and inside the same kind of announcement the reading added
nothing (t 0.6 and 0.3).

Two reasons, both visible in the data:
- **Most filings say nothing a tone model can read.** 212,047 of 234,386 stock-days (90%) read neutral: "has informed the Exchange regarding
  credit rating" carries no tone. The rating itself, the order size, the result numbers are in the attachments, not in the text we have.
- **Where the tone is clear, the category already says it.** 61% of order wins read positive and 15% of management changes read negative; the
  V02 study already measures those categories.

## The rows (drift = close of the announcement day to the close 5 or 20 sessions later, minus the Nifty; before costs)

| row | dev mean | dev t | dev quarters | val mean | val t | val quarters | verdict |
|---|---|---|---|---|---|---|---|
| pos|drift5 | -0.09% | -0.99 | 31 | +0.01% | +0.08 | 22 | REJECTED |
| pos|drift20 | +0.18% | +0.52 | 31 | +0.24% | +0.49 | 22 | REJECTED |
| neg|drift5 | -0.09% | -0.60 | 31 | +0.24% | +1.15 | 22 | REJECTED |
| neg|drift20 | -0.33% | -0.88 | 31 | -0.30% | -0.49 | 22 | REJECTED |
| spread|drift5 | +0.01% | +0.04 | 31 | -0.23% | -1.22 | 22 | REJECTED |
| spread|drift20 | +0.51% | +2.06 | 31 | +0.54% | +1.50 | 22 | INCONCLUSIVE |
| within_cat|drift20 | +0.44% | +0.57 | 31 | +0.39% | +0.30 | 22 | REJECTED |
| rank|drift20 | +0.006 | +1.30 | 31 | +0.010 | +1.33 | 22 | REJECTED |

The one row with the expected sign in both periods (positive minus negative over 20 sessions, about +0.5%) is a third of a round trip's cost
(0.3-0.5%) and stays far from the bar (t 2.1 and 1.5 against 3.16). It is recorded, not acted on.

## What the model saw

- 319,430 announcements on 234,386 stock-days of the 500 most liquid stocks; 249,893 distinct texts rated (about an hour on the Mac's GPU).
- Stock-days: neutral 212,047, positive 13,975, negative 8,172, mixed 192.
- Share read positive / negative by category: order win 61% / 1%; fund raising 7% / 0%; rating 10% / 2%; bonus and split 5% / 1%;
  management 3% / 15%; legal 2% / 11%; results 0% / 1%; other 10% / 4%.

## What happens now

- **Forward, as a note only:** every evening's announcements are rated after the 19:00 fetch (`paper/news_read/<day>.json`) and the
  reconstruction card's "what people did" line shows "the news read (FinBERT): N positive, M negative". The live sessions of 16-23 Oct are
  already rated (each about 2-4% positive and 2-4% negative). No book, rule, score or Ask reads it to decide anything.
- **No paper rule.** A rule from this would need its own registered test and Madhav's yes; this result gives no reason to write one.
- **What might work better (not run):** reading the attachments (the actual result numbers, the order size), which is a different study.
