# Ananta Agent — Lab Docs

Observability and operating docs for the paper-trading laboratory.

| Doc | Purpose |
|-----|---------|
| [ROADMAP.md](./ROADMAP.md) | Locked product roadmap + 2026-08-20 operating-mode addendum |
| [LOCAL_LOOP.md](./LOCAL_LOOP.md) | Backend-first lab loop — **no website required** |
| [AGENT_CONTRACT_V0.md](./AGENT_CONTRACT_V0.md) | Shared truth language with Ananta |
| [LABORATORY_CHARTER.md](./LABORATORY_CHARTER.md) | Hard rules: limits, ritual, kill/promotion criteria |
| [SCOREBOARD.md](./SCOREBOARD.md) | Strategy status TEST/WATCH/CORE/CUT/PARK |
| [experiments/JOURNAL.md](./experiments/JOURNAL.md) | Session-by-session log |

## Start of every lab day

1. Confirm Ananta **backend** is reachable (`ANANTA_BASE_URL`). Do not wait on the website.
2. Read charter limits (slots ≤ 6 preferred, enabled ≤ 5).
3. `git pull` + run agent.
4. `monitor` → `status`.
5. Follow daily ritual in the charter.
6. Update JOURNAL + SCOREBOARD before closing the laptop.

If login fails, the backend is down or `ANANTA_BASE_URL` still points at the expired Emergent host. Fix the API, not the UI. See [LOCAL_LOOP.md](./LOCAL_LOOP.md).

## Roadmap phase map (short)

- **Phase 1–2:** Agent foundation + lab operability — done / nearly done
- **Phase 3:** Wave A discovery — current, needs a live API
- **Phase 3.5:** Contract v0
- **Phase 3.6:** Backend independence (local Ananta API) — **current unblocking work**
- **Phase 4:** Decision / cycle / opportunity ledgers + outcome links
- **Phase 5+:** Evaluation, Trust Report, cockpit, India — gated

Do not start extra agents, fancy UI, autonomy, or India until Wave A + Contract + ledgers can produce an auditable dataset.
