# Ananta backlog: everything still to do

The single list of remaining work, so nothing is forgotten between sessions. Kept in the repo (Ask Ananta reads it too).
Order = priority. Status: TODO / DOING / WAITING (on evidence or on Madhav) / DONE (moved to the bottom with the date).
Last updated 2026-10-03.

## A. Layers and connections (Madhav, 2026-10-03: "how well are they connected... divide them into layers and give priority")
1. DONE v1, 2026-10-03 (switch step: the Explorer does not read it yet) **Layer map the agent reads** (`docs/knowledge/layers.json`): every component with its layer (0 authority ... 8 interface),
   what it depends on, what it feeds, its status, its evidence, the market it works in (regime), and the file that implements it.
   Statuses become switches: code asks the map whether a component is allowed before using it.
2. TODO **Join the two brains**: the decision chain (how Ananta reasons) and the Explorer (what it paper-trades) share one
   decision record; every Explorer entry shows where it stood on the chain.
3. TODO **Credit tracking**: each decision and paper trade records which layers moved it; the learning layer scores each
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
5. TODO **Redo every study that ignored zones** (list and order in the program document, section 5).

## C. Teacher ideas not yet tested
1. TODO H07-H17 and P03 (RSI dips, relative strength, volume on breakouts, tight bases, pullbacks to the 50-day, first pullback after a
   breakout, false breaks, ATR stops, trailing stops, breadth, scaling in, book-level stop). Most become zone questions (B4).
2. TODO Resolve the conflict: Raunak's tight base with drying volume (H10) vs our dropped V14/V15, which were tested only on 5m-1h.
3. WAITING H06 (dip in an uptrend) PROMISING: needs a pre-registered test with costs and a paper shadow.

## D. Your setups (review #5)
1. WAITING Q5: 10 live fires recorded, then compare with random days and with history.
2. TODO Combine a read with V02 and T3 timing instead of the read alone (new counted test).
3. TODO Ask Madhav: phone alert for every fire, or only supported reads (current rule)?

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
- 2026-10-03 Domain livetrading247.com, guest practice mode, two Ask switches, MongoDB archive job.
- 2026-10-03 Knowledge layer (framework, hypotheses H01-H18), decision chain, teachers' channels analysed and first-look tested.
- 2026-10-03 Review #5 (your setups) and live "Your setups"; knowledge map, read_doc, notes folder.
