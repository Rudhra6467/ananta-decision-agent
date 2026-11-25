# NC1: after news, does a confirmed move continue or fade? (design, frozen 25 Nov 2026, before any outcome)

Madhav, 25 Nov 2026: "Ananta can predict the live happening, which was let's say 5 minutes or 10 minutes or 15 minutes later ... we don't have to hurry in finding the moves. The proved moves are good enough ... what are the most effective news for the Indian market ... the main influencing keywords, sometimes for market gainers or market losers". Then: "let's proceed and complete it ... we are treating the study as, that is the thing we are doing, right?"

**A study, never a trading rule.** It marks which kinds of company news move Indian stocks, and whether a move that is confirmed after the news goes on or fades. What it finds becomes what Ananta knows and can explain. A rule from it would need its own registered forward test against random, and Madhav's yes.

## The question

- **Part A, overnight news.** News made public after the 15:30 close or before 09:00. The move is confirmed at the open: the open is at least 2% away from the previous close, beyond the Nifty's own gap. Does the stock keep going the same way until the close? Compared with gaps of the same size on days with no news at all.
- **Part B, news during the session.** News made public between 09:20 and 15:00. The move is confirmed about 15 minutes later: at least 1% beyond the Nifty, on 5-minute bars. Does it keep going until the close? Compared with no-news moves of the same size, in the same direction, at the same time of day.

## The kinds of news (fixed before looking, `india/newskinds.py`)

The 17 kinds are: results, order wins, a USFDA warning or observations, a USFDA approval, a rating cut, a rating raise, raising equity, mergers and acquisitions, insider and promoter holding changes, a senior exit, pledges and defaults, penalties, searches and court matters, buybacks, dividends, bonus and split, a new plant or launch, a fire, shutdown or strike, and analyst meetings (the routine control). There is also "all news": every announcement that is not a routine notice. Routine notices (lost share certificates, trading-window closures, newspaper copies, record dates, the exchange's own questions about a price move) never count as news. The run refuses to start if the dictionary file changes.

## What is measured

- 72 rows are tested: for each part and each kind, "cont" (the move went on) and "edge" (it went on further than a no-news move). The bar is z 3.55: 130 rows across the events, news-tone and news-confirm families, two-sided.
- Splits: Part A uses 2010-2017 to look and 2018-2023 to check. Part B uses 2015-2018 and 2019-2023, because the 5-minute bars start in 2015.
- Not tested, only described:
  - which kinds of news move stocks most often, by how much, and how fast;
  - which kinds come with the day's 25 biggest gainers and losers (the lift);
  - the move over the next five sessions.

## Counts before any outcome (no price read)

879,659 announcements in 2010-2023. 241,388 are routine. Of the 638,271 news announcements, 405,933 were made public overnight and 232,338 in session. By kind (announcements): results 94,475, analyst meetings 91,287, holding changes 61,336, dividends, bonus and split 25,596, mergers and acquisitions 20,769, a new plant or launch 7,104, raising equity 6,200, pledges and defaults 5,711, penalties and court matters 5,412, order wins 3,834, buybacks 3,315, senior exits 3,258, disruptions 2,724, USFDA approvals 1,121, rating raises 715, rating cuts 209, USFDA warnings 138. The rare kinds may not fill 16 quarters; then their rows read INCONCLUSIVE, which is the honest answer.

Moves are before costs; a round trip costs about 0.3-0.5%. Full design: `nc1_v1.json`.
