"""Strategy configuration research — one-page spec. Not KEEP. Not a miner."""
from __future__ import annotations

from typing import Any, Dict

VERSION = "CFG-SPEC-v0"

LAW = (
    "Budgeted configs. In-sample search only. Held-out never tunes. "
    "Win = after costs. Family ≠ one config. Shadow ≠ live TAKE."
)

# --- record ---
RECORD_FIELDS = (
    "exp_id",             # EXP-nnn
    "family",             # donchian-breakout
    "config_id",          # donchian-lb20-v1
    "params",             # {lookback: 20}
    "asset", "timeframe", "state",
    "split",              # IN_SAMPLE | HELD_OUT | LIVE_SHADOW
    "period_from", "period_to",
    "strategy_version", "regime_def_version", "cost_version",
    "n_setups", "n_take_eq",
    "wins_after_cost", "win_rate_after_cost",
    "expectancy_after_cost",
    "avg_win", "avg_loss", "payoff",
    "mfe", "mae",
    "vs_sitout",          # WASH | TAKE_HURT | EDGE | INSUFFICIENT | NO_TAKE
    "depth",              # NONE | ANECDOTE | THIN | ADEQUATE
    "promote",            # always False until graduation
    "keep",               # always False here
)

# --- how configs are generated ---
GENERATION = {
    "method": "CLOSED_BUDGET",
    "not": "unlimited random search",
    "rule": "Family lists at most N named configs before any run. No extra knobs mid-test.",
    "donchian_v1_budget": ["lb20", "lb30", "lb40", "lb55", "lb80"],
    "max_configs_per_family_v0": 5,
    "in_sample_fraction": 0.70,
    "held_out_fraction": 0.30,
    "held_out_touches_search": False,
}

# --- win after costs ---
COST = {
    "version": "cost-v0",
    "default_round_trip_pct": 0.08,  # placeholder; replace with venue schedule
    "win_definition": (
        "A TAKE-eq is a WIN iff forward horizon return - round_trip_cost > 0. "
        "Win rate = wins / n_take_eq. n_take_eq=0 → NO_TAKE, not 0% win rate."
    ),
    "horizon_primary": "+1h",
    "horizons_kept": ["+15m", "+1h", "+4h"],
    "hist_15m_unusable_on_1h_books": True,
}

# --- episodes ---
EPISODE = {
    "definition": (
        "A contiguous window where a named fingerprint/regime persists, "
        "or a labeled pull (e.g. TREND_UP run of ≥ N bars). "
        "Episode is evidence, not proof the family is universally good."
    ),
    "stored_as": "episode_id + period + state + which configs rode it after cost",
    "not": "this pull made Donchian good forever",
}

# --- graduation ---
GRADUATION = [
    "RESEARCH — in-sample only; promote=False",
    "CANDIDATE — held-out vs sit-out after cost is EDGE or not HURT; n depth ≥ THIN",
    "SHADOW — live tape logs shadow TAKE-eq; Wave A still WATCH",
    "PAPER — I5 human gate only",
    "CAPITAL — I6 after paper DQ",
]
GRADUATION_BLOCKED_IF = [
    "held-out used to pick params",
    "n ANECDOTE",
    "TAKE_HURT on held-out",
    "win_rate high but expectancy after cost ≤ 0",
    "Wave A mutation / TREND_UP enable",
]

BOARDS = {
    "HIT_RATE": "rank by win_rate_after_cost among ADEQUATE",
    "EXPECTANCY": "rank by expectancy_after_cost among ADEQUATE",
    "rule": "DI may read both. No blended score. No polarity.",
}


def spec() -> Dict[str, Any]:
    return {
        "ok": True,
        "version": VERSION,
        "keep": False,
        "law": LAW,
        "record_fields": list(RECORD_FIELDS),
        "generation": dict(GENERATION),
        "cost": dict(COST),
        "episode": dict(EPISODE),
        "graduation": list(GRADUATION),
        "blocked_if": list(GRADUATION_BLOCKED_IF),
        "boards": dict(BOARDS),
        "needs_ananta": (
            "Replay with param override OR local PIT evaluator. "
            "Until then catalog exists; scores stay PENDING."
        ),
    }


def print_spec() -> Dict[str, Any]:
    r = spec()
    print(f"\nCFG SPEC  {r['version']}")
    print("=" * 64)
    print(r["law"])
    print("-" * 64)
    print("  GENERATE:", r["generation"]["donchian_v1_budget"],
          "max", r["generation"]["max_configs_per_family_v0"])
    print("  SPLIT: 70/30  held-out touches search =",
          r["generation"]["held_out_touches_search"])
    print("  WIN:", r["cost"]["win_definition"][:88], "...")
    print("  COST model:", r["cost"]["version"],
          "rt%", r["cost"]["default_round_trip_pct"])
    print("  GRADUATE:")
    for g in r["graduation"]:
        print("   ", g)
    print("-" * 64)
    print("  Scores PENDING until Ananta can replay a config_id.")
    print("  keep=False")
    print("=" * 64)
    print()
    return r
