# HFN1 · Does a news model's reading of NSE announcements tell us where the stock goes next? (pre-registration, 25 Oct 2026)

Written and frozen before any rating or outcome was computed. The full spec is `hf_news_v1.json`.

- **Why:** Madhav, 25 Oct: "We can add both, if they are helping Ananta in either crypto and Indian infrastructure ... see where hugging face fits for us".
- **The model:** `ProsusAI/finbert` from Hugging Face (revision 0bc2ac10), a BERT model trained on financial news, run on the Mac with no fitting.
  It reads each announcement and gives positive, negative and neutral chances.
- **The data:** NSE company announcements from the PR zips, 2010-2023 only, on days the stock was among the lab's 500 most liquid; fund NAVs and
  share-certificate notices left out. 319,430 announcements on 234,386 stock-days (counts only).
- **The timing:** the file of day d is known after its close; the outcome runs from the close of d to the close of d+5 and d+20, minus the Nifty.
- **The questions (8 rows):** positive days drift up, negative days drift down (5 and 20 sessions), positive minus negative, the same inside each
  announcement category (does the reading add anything beyond the category V02 already uses?), and the rank correlation of tone with the 20-day drift.
- **The bar:** quarter blocks; development 2010-2017, validation 2018-2023; the events family's 24 rows plus these 8 = k 32, z 3.16, frozen.
- **What a pass means:** the reading carries information. It is not a trade: the drifts are before costs, and a paper rule would need its own test
  and Madhav's yes.
- **Forward:** from 26 Oct every evening's announcements are rated (`paper/news_read/<day>.json`); the reconstruction card shows the counts as a
  note. Nothing trades on it.
