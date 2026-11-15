# What runs on the Mac, and why (15 Nov 2026)

One page for "what is running, when, and what is it for". 42 launchd jobs: 9 always on, 33 on a clock (the watchdog every 5 minutes). Times are Toronto winter
time; the India jobs keep Indian time across clock changes (`jarvis/india/schedule.py`). Every job that runs by itself, with what proves
it ran and did its work, is in `jarvis/service/runcheck_parts.py` (the lost-runs check reads it); this page is the plain map.

## 1. Always on (services)
| job | what |
|---|---|
| jarvis | the crypto service and the app's server (:8100); its 15-minute loop runs watches, the brain, books, reviews, the self-check |
| india.web | the India Ask, voice and pages (:8110) |
| hands | the crypto App backend (orders, risk; paper) |
| explorer | the 15-minute crypto market scan |
| voice, speaker | the voice server and speaker recognition |
| website, tunnel | livetrading247.com and its Cloudflare tunnel |
| awake | keeps the Mac from sleeping |
| watchdog (every 5 min) | the outside check: is Jarvis answering, are the sites up; heals a stuck service once an hour at most |

## 2. Is it running? (five checks, each a different job, not copies)
- **Health** (inside Jarvis, every 2 min): each part alive (Explorer, eye, jobs, candles, voice, Hands, tunnel, disk). Phone at once when a part goes quiet or comes back.
- **Watchdog** (outside, every 5 min): Jarvis itself and the public sites. Phone at once.
- **Lost runs** (`runcheck`, read by the self-check): did every scheduled part run AND do its work.
- **Self-check** (every 15 min): what is not right right now, across both markets; a HIGH item reaches the phone once a day.
- **Clock check** (`india.schedulecheck`, 3 a day): moves India jobs after a clock change; silent unless it changes one.

## 3. India: data, decisions, paper (the one job until spring: the portfolio on paper)
| when (Toronto) | job | what |
|---|---|---|
| 05:20 Mon-Fri | india.postclose | index bars, chart readings, first market summary |
| 07:00 | india.sp1paper.score | the options line scored (shadow) |
| 07:20 | india.morning | morning checks, read model |
| 12:30 Mon-Fri | india.recorder_noon | option minutes, ledger snapshot |
| 12:45 Mon-Fri, 02:30 | india.nightly | the official day file, technicals, quote book, desk; 02:30 is the heal run |
| 19:35-20:40 | india.autologin | Zerodha sign-in |
| 20:00 | india.evening_zerodha | account snapshot, recorder, SP1 replay check |
| 20:20 | india.evening | flows, deals, filings, evidence and leak checks, the allocator, **the managed book** (fills, plan, score, audit), the account twin, SF1 |
| 20:35 | india.studies | trials' clocks, tilt book, write-ups, knowledge map, data audit |
| 21:00 | india.sp1paper | the options line's plan (shadow) |
| 21:30 | india.paper | practice book, RX1 and RS trials, missed movers, reference traders, reconstruction, read model |
| 21:35 Mon-Fri | india.spreads | spread samples |
| 22:00 | india.morningview | the India morning view |
| 22:06 | india.shadowtrader | shadow trader |
| 22:39 Mon-Fri | india.preopen | the pre-open read |
| 23:50 | india.openingview | the opening update (goes to the phone at once) |
| 00:30, 05:40, 13:35 | india.factmap | the fact map at three moments |
| Sat 10:00 | india.kitefill | the week's minute bars |

## 4. Are the answers right?
- **Every night 23:20** (`india.replay`): the day's real India questions asked again against today's code, plus the never-again bank. The 30-question India exam runs from the same job once a week (`--if-due`).
- **Every night** (crypto, after the officer's note): the crypto night test.
- **Sundays 07:10** (`exam`): the weekly crypto agent exam.

## 5. Crypto (trading parked since 13 Nov; recorders kept, forward data cannot be recreated)
chronosshadow (every 4 h), hfnews.shadow (05:10), othersdaily (04:30), polymarketshadow (04:45), workerpull (from the 2017 Mac),
plus the service loop's watches, tier30, brain, stance, reviews, officer's note.

## 6. What reaches the phone
- **At once:** warnings and errors, outages and recoveries, the self-check, a new flag, a flag that needs your yes or failed, the India opening update, the Kite sign-in, price alerts, anything not on the routine list.
- **Morning digest 09:30** (`digest.morning`) and **night digest 22:42** (`digest.night`, 09:12 India time, before the open): the briefs, the officer's note, the day in review, the night tests (failures first), the India morning view and pre-open, the Planned and Fixed flag notes. Each note kept in full in `~/ananta_runs/digest_queue.jsonl` and `~/ananta_runs/digests/`; never held more than 16 hours (`src/intelligence/digest.py`).

## 7. Backups and records
backup (03:40, the databases), mongoarchive (03:20), lake (Sundays 02:15, R2), records (06:50, commits the day's records).

## Changed on 15 Nov 2026
- Routine notes now come in two digests (section 6).
- The RX1 and RS trials run once a night (in india.paper), not twice.
- 15 old work folders moved to `~/code/_archive-2026-11-15`; old job backups to `~/Library/LaunchAgents/archive-2026-11-15`. Nothing deleted.
- SF1 (does strength flip in a falling market?) records one shadow row every evening.

## Looked at and kept as they are
- The five "is it running" checks each do a different job (section 2).
- The data checks (inventory, lineage, selection, data audit) take seconds, send nothing, and feed the read model.
- The India exam was already weekly.
