# Ananta safety runbook: stop, flatten, roll back, resume

For the operator. Every command is copy-paste. Paste one block at a time into Terminal.
It works the same in paper today and live later; live-only steps are marked **LIVE**.

---

## 1. Something looks wrong: stop trading immediately (≈10 seconds)

**Hands kill switch.** Two effects, both immediate:
- Every new entry in the App is blocked (the cycle shows `BLOCKED / MANUAL_KILL`).
- **Every open Hands position is closed at market** by the position watcher. This is a flatten, not a pause.

It does not touch the Agent's own paper books (SD6, V0, V1); stop those with the watch command below.

```
cd ~/code/ananta-decision-agent
.venv/bin/python -c "from src.intelligence.circuit_breaker import engage_hands_kill_switch as k; print(k())"
```

You should see `{'status_code': 200, 'ok': True}`. The App's Settings page shows the kill switch as ON.

**Stop the Agent's hourly watch** (paper books and candidate runners):

```
pkill -f src.intelligence.paper_watch
```

---

## 2. Close a position now

Close one coin in Hands at market, for example BTC. Replace `BTC` with the coin:

```
cd ~/code/ananta-decision-agent
.venv/bin/python -c "
from src.tools import ananta_api as a; import requests
t=a.login()['token']
r=requests.post(a.BASE_URL+'/api/positions/BTC/close', headers=a.get_headers(t), timeout=30)
print(r.status_code, r.text[:300])"
```

**LIVE, last resort** if Hands itself is broken:
- Log in to the exchange website (Kraken or NDAX) and close the position there.
- Then **disable the API key** on the exchange website, so no software can trade.

---

## 3. Stop Hands completely

```
pkill -f "uvicorn server:app"
```

To start it again:

```
cd ~/code/Ananta/backend
nohup .venv/bin/python -m uvicorn server:app --host 127.0.0.1 --port 8001 --workers 1 >> hands.log 2>&1 &
```

---

## 4. Roll back a bad code change

See the recent versions (newest first):

```
cd ~/code/ananta-decision-agent && git log --oneline -8
```

Go back to a known-good version. Replace `abc1234` with its code from the list:

```
cd ~/code/ananta-decision-agent && git checkout abc1234
pkill -f src.intelligence.paper_watch
nohup caffeinate -i .venv/bin/python -u -m src.intelligence.paper_watch >> watch.log 2>&1 &
```

Same idea for Hands: use `~/code/Ananta`, then restart Hands as in section 3.
Return to the latest version later with `git checkout main && git pull`.

---

## 5. The circuit breaker tripped

It trips after **4 losses in a row**, or a **drawdown of 20% of starting capital**.
- New entries for that book stop.
- Open positions keep their stops and exits.
- You get an alert with the reason.
- **It never resumes by itself.**

See why:

```
cd ~/code/ananta-decision-agent && .venv/bin/python -m src.intelligence.circuit_breaker status
```

Before resuming, check:
- [ ] Were the losses normal stops, or a bug? Look at `watch.log` and the alert.
- [ ] Is the market in a regime the strategy is known to lose in (choppy / down)?
- [ ] Is data flowing? `python -m src.intelligence.paper_watch status` shows no gaps.

Resume, recording your name:

```
cd ~/code/ananta-decision-agent
.venv/bin/python -m src.intelligence.circuit_breaker resume --book candidate_v1_book.sqlite --by "Vamsi"
```

**LIVE:** a trip also turns on the Hands kill switch. Turn it off in the App's Settings only after this checklist.

---

## 6. Turn the Hands kill switch back off

Use the App's Settings page, or:

```
cd ~/code/ananta-decision-agent
.venv/bin/python -c "
from src.tools import ananta_api as a; import requests
t=a.login()['token']
print(requests.put(a.BASE_URL+'/api/settings', json={'manual_kill_switch': False}, headers=a.get_headers(t), timeout=20).status_code)"
```

---

## 7. Where to look

| What | Where |
|---|---|
| Hourly looks, gaps, book summaries | `cd ~/code/ananta-decision-agent && .venv/bin/python -m src.intelligence.paper_watch status` |
| Watch log / alerts | `~/code/ananta-decision-agent/watch.log`, `watch_alerts.jsonl` |
| Breaker state | `~/code/ananta-decision-agent/breaker_state.json` |
| Hands log | `~/code/Ananta/backend/hands.log` |

---

## 8. Before the first live dollar (checklist)

- [x] Rehearse sections 1 and 6 on paper. **Done 2026-09-30 ~08:54 UTC, passed:** engage → `manual_kill=True`, cycle 10/10 `BLOCKED / MANUAL_KILL`, 0 trades; off → `manual_kill=False`, `overall_safe=True`. (Hands had no open positions, so the flatten was not exercised.)
- [ ] Rehearse section 2 (close one position) on paper while Hands holds a paper position.
- [ ] Phone alerts: the ntfy test alert (section 9) arrives on the phone; the Ananta app push is set up.
- [ ] Exchange API key: **trade-only, withdrawals disabled**, IP-restricted if the exchange allows it.
- [ ] Live size fixed in writing, and the breaker limits confirmed for the live book.
- [ ] You know how to do section 2 on the exchange website without any software.

---

## 9. Phone alerts (ntfy)

Paper buys and exits, gaps, Hands being unreachable, errors and circuit-breaker trips are pushed to the phone.
Routine notes (INFO) stay in `watch_alerts.jsonl` only.

Send a test alert:

```
cd ~/code/ananta-decision-agent && .venv/bin/python -m src.intelligence.paper_watch test-alert
```

`phone push: sent` means the server took it. `off` means `ANANTA_NTFY_TOPIC` is missing from `.env`.
The topic name works like a password: anyone who knows it can read the alerts. It lives only in the laptop `.env`.
