# Risk profiles — SAFE / MODERATE / AGGRESSIVE

**Locked:** 2026-08-23  
**Status:** Behavior parameters. **Not** three agents. **Not** three strategy codebases.

```text
Agent Ananta
   ↓  recommend (typed decision)
Risk profile (SAFE / MODERATE / AGGRESSIVE)
   ↓  cannot loosen hard gates
Hard safety (this package, deterministic)
   ↓  cannot override Ananta
Ananta execution authority
```

The agent can recommend aggressively. It cannot override Ananta.

| | SAFE | MODERATE | AGGRESSIVE |
|---|---|---|---|
| Max slots | 2 | 4 | 6 (charter abs 8) |
| Max enabled | 2 | 3 | 5 (charter max) |
| Notional cap (equity) | 5% | 15% | 30% |
| Autonomy | recommend only | constrained | higher, still gated |
| Weak evidence | WAIT | WAIT | SKIP |
| Uncertain regime TAKE | no | no | recommend only |
| Confirm TAKE | always | always | always while WATCH |
| Override Ananta | never | never | never |
| Promote Wave A | never | never | never |

Aggressive never means uncontrolled. Charter ceilings always win if a profile is looser — none are.

Default: **MODERATE**. Map user `Low/Medium/High` → SAFE/MODERATE/AGGRESSIVE.

Code: `src/intelligence/profiles.py`. CLI: `lab profile [SAFE|MODERATE|AGGRESSIVE]`.
