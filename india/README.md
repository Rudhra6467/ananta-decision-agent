# Ananta India: the data lake (I-0 onward)

India is the first big market (Madhav, 16 Oct 2026). This folder holds the India data code; the data itself lives in
`~/ananta_data/india` (bronze, silver, gold, manifests, sealed, india.duckdb), moving to the external SSD when it arrives.
The plan: *Ananta — India First: Data Platform and Agent Plan* (16 Oct 2026). The registration: `registrations/I0_document.md`.

| Module | What it does |
| --- | --- |
| `paths.py` | Folders, the DEV / VAL / HOLDOUT split (2000–2017 / 2018–2023 / 2024-01-01 sealed), the isolation check that refuses a folder inside crypto or Canada |
| `nse.py` | NSE file patterns (old and UDiFF), the polite fetcher (browser headers, one request a second, backoff), bronze writes with a manifest line per day |
| `backfill.py` | `python -m india.backfill cm_bhavcopy 1994-11-03 2026-10-16` and the same for `fo_bhavcopy` and `delivery`; resumable |
| `kite.py` | Kite Connect read client (candles, instruments, holdings, positions, funds); GET only; raises NeedLogin and nudges the phone when the 6 am IST token has expired |
| `probe.py` | `python -m india.probe nse` (archive rate, first dates, index lists) and `python -m india.probe kite` (first 5-minute and daily candle per Nifty 50 name) |

Run everything with `~/ananta_venvs/lake/bin/python` from `~/code/ananta-records`. The Kite sign-in itself lives in the agent
repo (`src/india/kite_auth.py`, routes `/kite/login` and `/kite/callback` on the Jarvis service) and writes
`~/ananta_private/kite_token.json`, which is the only thing this folder reads from the service.

Rules that hold for every file here: bronze is never edited; every row carries its source and fetch time; nothing reads
`sealed/` except the sealed loader; nothing here places an order; nothing in any agent reads this folder until the database
gate (plan section 8) and Madhav's sentence.
