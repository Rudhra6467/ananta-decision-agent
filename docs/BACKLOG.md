# Ananta backlog: everything still to do

The single list of remaining work, so nothing is forgotten between sessions. Kept in the repo (Ask Ananta reads it too).
Order = priority. Status: TODO / DOING / WAITING (on evidence or on Madhav) / DONE (moved to the bottom with the date).
Last updated 2026-10-04.

## 0. Start of every work session: Madhav's requests
Read the OPEN and PLANNED requests first (on the Mac: `requests_log.list_(j, include_done=False)`, or GET /v3/requests), plan them,
and set each one's status with a short note when it moves (`requests_log.set_status(j, num, "PLANNED"|"DONE"|"WONT", note)`).
The phone note and Ananta's mention in the next conversation follow by themselves. Open on 2026-10-03: #2 first candle date per
coin (now answered by the prices lookup, what='coverage': mark DONE after deploy), #3 which timeframe built Hunter's support zone
(needs the Hunter log in Hands to record the zone's source and edges).

## I. Watches, evidence books and the eye (Madhav, 2026-10-03: "if every watch trades, only then we can measure it") - OK'd 2026-10-03
1. DONE in code 2026-10-03, LIVE AFTER MERGE: Hunter's book SD6 v3: one open trade per coin (up to 10) instead of one in total; a
   refused TAKE when full becomes a shadow. After Madhav merges: fast-forward the main checkout and restart the hourly watch
   (paper_watch), then check the heartbeat shows paper.exit.sd6.v3.
2. DONE 2026-10-03: evidence books (daily engine + Explorer would-be trades + SD6 shadows) and one scoreboard (Evidence page, Ask).
3. DONE 2026-10-03: the watch registry (knowledge/watches.json) with sections; the daily engine runs its daily watches.
4. DONE 2026-10-03: the eye (live Kraken prices every 10 s): your stops and alerts, Bitcoin shock, zone entries, zone-touch evidence trade.
   TODO later: move the Explorer and Hunter into the shared engine; add funding rates / open interest.
5. Portfolio book (the $500 rehearsal): picks among signals with real limits (a few open, 1% risk each, correlation budget).
6. Then: Madhav's 20-40 setups through the repair shop on history; the ones that pass get a registry slot and trade on paper.
7. Data for fast decisions: funding rates and open interest (free public feeds) first, order book later.

## J. Jarvis's brain, findings and self-checks (Madhav, 2026-10-04: "one intelligent agent ... not filters") - OK'd 2026-10-04
1. DONE in code 2026-10-04: the brain with its own paper book (JARVIS) and random twins, at most 20 decisions a day; passes
   scored; knowledge credit and confidence calibration (jarvis_book). WAITING: 10 independent events, then the verdict vs twins.
2. DONE 2026-10-04: the daily what-did-we-miss loop (missed_moves); repeated misses become requests and CANDIDATE patterns.
3. DONE 2026-10-04: health watchdog (inside, every 2 minutes) and the outside watchdog for Jarvis (launchd); market-shift
   alerts; self-flagging of gaps; a review of every closed trade; the evening self-review.
4. DONE 2026-10-04 (Madhav OK'd the mock): Home as mission control, Jarvis's book, one evidence trade, what we missed, four tabs
   (Home, Markets, Books, Ask Jarvis) and the Lab switch (the Evidence tab became the Lab page). Next: his feedback after using it.
5. WAITING (Madhav) the live rules and code-review guide: draft doc 2026-10-04 ("Going live: rules and code review"): T3 only, $250 in
   T3 + $250 cash, 20% shutdown. Decided 2026-10-04: NDAX (0.20% flat, minimum order $1-5 CAD); the other answers are the defaults
   (CAD 500, half in cash, 20% final stop, 25% disaster stop, approve weekly changes for 4 weeks, start when the checklist is done).
   TODO: test the lower-turnover T3 in the repair shop before live.
6. TODO when the brain has evidence: let it see funding rates and open interest; let a PROMOTED pattern from the misses become a
   registered watch.
7. LATER the big-data pipeline (100-120 coins, all history, tiers 10 traded / 30-50 paper / 100-120 research).

## V. Voice and Jarvis (Madhav, 2026-10-03: "smooth, light, a human touch"; "straight: ask me, confirm me, correct me")
1. DONE 2026-10-03: answer first, no stock openers, name once, spoken names not codes, rounded numbers, caveats once, a view when
   asked, corrects him with the data and never caves without checking; written -> spoken text; natural pauses (trimmed silence,
   longer after questions); normal pace by default; "one sec" while looking up; echo, "hmm" and noise never reach the model; a
   sentence cut off mid-way waits for the rest; the fastest Gemini first in voice.
2. DONE 2026-10-03: new abilities: price history (highs, lows, days, rankings), web lookup, news check, remember, numbered requests
   that report back, and cards (Face ID) for stops/targets on his own positions, kill switch, autopilot, portfolio approvals, alerts off, budget and voice settings.
3. TODO A better voice than Kokoro: options a cloud voice (OpenAI gpt-4o-mini-tts about 1.5 cents a minute: needs a real OpenAI
   key, the one in .env is a placeholder; or ElevenLabs), or a newer local model (try Marvis / CSM on the Mac).
4. TODO Our own app build (EAS development build / TestFlight, needs an Apple developer account): real Face ID, streaming voice
   (talk over it, answers start in under a second, like ChatGPT's voice), background audio. Expo Go cannot do these.
5. TODO Replay on request: "what would Hunter / the Explorer have done on BTC between these dates" (the engine can replay stored candles).
6. TODO Sell / exit signals for coins Madhav holds in his own book (the trend portfolio's ratings and the exit rules, said per coin).

## A. Layers and connections (Madhav, 2026-10-03: "how well are they connected... divide them into layers and give priority")
1. DONE v1, 2026-10-03 (switch step: the Explorer does not read it yet) **Layer map the agent reads** (`docs/knowledge/layers.json`): every component with its layer (0 authority ... 8 interface),
   what it depends on, what it feeds, its status, its evidence, the market it works in (regime), and the file that implements it.
   Statuses become switches: code asks the map whether a component is allowed before using it.
2. DONE v1 2026-10-03 (each paper trade shows what the reasoning layers said at the close before the buy; credit tracking joins them) **Join the two brains**: the decision chain (how Ananta reasons) and the Explorer (what it paper-trades) share one
   decision record; every Explorer entry shows where it stood on the chain.
3. DONE v1 2026-10-03 (records every coin at each close, scores 20 days later, joins Explorer trades; Evidence page and Ask) **Credit tracking**: each decision and paper trade records which layers moved it; the learning layer scores each
   component over time (which ones earn their keep, in which market).
4. TODO Unused evidence gets a consumer: V09/V10 (other traders' timing), reconstruction cases, the news check.

## B. Zones (Madhav: "it's always a zone; once we enter the zone we track it and start the lookout process")
1. DONE 2026-10-03 **Zone research program** (`docs/research/ZONES_PROGRAM.md`): what a zone is, how to measure its strength, and
   pre-registered review #6 (do strong zones hold more often than weak ones and than random prices?).
2. DONE 2026-10-03, review #6 run: zones hold a little more often than random; 200-day, confluence, new swing zones pass (`research/REVIEW_6_RESULTS.md`). **Zone engine** shared by history and live (one code path, lookahead-tested): static zones (swing clusters, 52-week
   extremes, round numbers), moving zones (20/50/200-day averages as bands), range zones (bases); multi-timeframe; strength score.
3. DONE 2026-10-03 (zone map, states, lookout, attention live; AI spending is not yet tied to attention: next) **Zone state and attention, live**: far / approaching / inside / held / broken / flipped per coin and zone. Entering a zone
   starts the lookout: chain, your setups, news check, what the knowledge says about this zone type, a plan (confirm / wrong / size).
   Outside zones Ananta stays quiet and cheap.
4. DONE 2026-10-03 **Review #7, the lookout**: only the market regime (BTC above its 50-day) separated held from broken (68% vs 50%); wick, close-back, volume, divergence, relative strength added nothing beyond arithmetic (`research/REVIEW_7_RESULTS.md`). Attention ranking (HIGH / WATCH / LOW) and the playbook (`knowledge/PLAYBOOK.md`) are live; every code file is on the layer map (test).
5. DONE 2026-10-03 **Redo every study that ignored zones**: done so far: your setups (review #8: retest with the market allowed most promising, insufficient), Explorer setups (review #9: zones do not help hours-long trades). Exits (review #10: a target at the next zone cuts winners; FAIL). Teacher ideas as zones (review #11: 50-day dip worse than average; breakouts on volume positive but not reliable; FAIL). Trailing stops vs T3 (review #12: T3's exit stays). Intraday atlas and other traders' reconstruction with zones: closed without a run, because review #9 showed daily zones do not change hours-long trades and both are hours-long. (list and order in the program document, section 5).

## C0. Consequence to fix
- DONE 2026-10-03 (Madhav's OK): LOCATION now asks for a zone history supports; the stop at a zone is a close 0.5 daily range under it.
  Was: the decision chain's LOCATION gate uses H11 (near the 20/50-day average, not stretched), which review #11 did not support.
  Proposal for Madhav: LOCATION = at a zone of a kind history supports (review #6), with the market gate first (review #7). Needs his OK
  because it changes how Ananta explains every coin.

## C. Teacher ideas not yet tested
1. DONE 2026-10-03 (reviews #11-#14: H07 promising and recorded live; H10, H11, H12, H13, H15, P03 not supported; H16 insufficient; H14, H17 untested: H14 is the chain's stop rule, H17 waits for entries worth staging) H07-H17 and P03 (RSI dips, relative strength, volume on breakouts, tight bases, pullbacks to the 50-day, first pullback after a
   breakout, false breaks, ATR stops, trailing stops, breadth, scaling in, book-level stop). Most become zone questions (B4).
2. DONE 2026-10-03 (daily bases tested in reviews #5, #6, #8: not supported, so the conflict resolves the same way on daily data) Resolve the conflict: Raunak's tight base with drying volume (H10) vs our dropped V14/V15, which were tested only on 5m-1h.
3. DOING H06/H07 (dip in an uptrend) PROMISING: review #14 found H07 beat a fair baseline in both periods but 5 events short; paper shadow running from 2026-10-03 (Madhav's OK), phone alert on each fire.

## D. Your setups (review #5)
1. WAITING Q5: 10 live fires recorded, then compare with random days and with history.
2. TODO Combine a read with V02 and T3 timing instead of the read alone (new counted test).
3. DONE 2026-10-03 Madhav: ring for the retest with the market allowed (M2a-G) and H07 too.

## E. News (the blunder guard)
1. DONE 2026-10-03 Point-in-time news recorder: one verdict per coin per day (Haiku, about 10 cents a day, HIGH-attention coins first), shown in the zone lookout and Ask.
2. TODO More known disasters and ordinary dips as controls (LUNA May 2022, FTX/FTT Nov 2022, chain outages).

## F. App and Jarvis
1. TODO Bug sweep (#50): bigger evals, highlight/speech checks, spot crawler, DB usage audit.
2. TODO Model bake-off in Test Lab; routing by scores (#55).
3. TODO Zones on the chart and a zone section on each coin page (after B3).
4. TODO Layers view in the app: what each layer contributed to a decision (after A3).

## G. Path to $500 live (unchanged order)
1. WAITING Q1 Explorer live vs replay (30 closed trades), Q2 T3 live tracking (6-8 rebalances), Q3 E5 probation, Q4 intraday atlas.
2. TODO SD6 hardening, Trust report as code, app push before live, monitoring and the incident runbook checked.
3. WAITING Madhav's code review pass, then his sentences for live; then $500.
4. TODO After this phase: Madhav rotates all dev passwords.

## H. Later (after $500 live proves the prototype)
- Big databases (crypto 150, India, Canada, US, options/futures), proper pipelines; Aladdin-style scenario layer; what carries
  forward is the layer map, the variables and the process, not the findings.

## Done
- 2026-10-03 Voice and abilities pass (V1, V2), the system map (`SYSTEM_MAP.md`), numbered requests that report back.
- 2026-10-03 Domain livetrading247.com, guest practice mode, two Ask switches, MongoDB archive job.
- 2026-10-03 Knowledge layer (framework, hypotheses H01-H18), decision chain, teachers' channels analysed and first-look tested.
- 2026-10-03 Review #5 (your setups) and live "Your setups"; knowledge map, read_doc, notes folder.
