"""Three strategy rosters. They are not the same set. Not KEEP."""
from __future__ import annotations

from typing import Any, Dict, List

VERSION = "SWEEP-ROSTER-v0"

WAVE_A_WATCH = ("hunter", "squeeze", "bollinger-mr")
I2_SHADOW = ("donchian-breakout", "atr-breakout", "keltner-breakout")
UNIVERSE_OBS = WAVE_A_WATCH + ("continuation",) + I2_SHADOW
# Locked from health_sweep run ef32846f… 2026-08-31
DAILY_SWEEP = (
    "hunter",
    "squeeze",
    "continuation",
    "ema-cross",
    "supertrend",
    "rsi-momentum",
)
SWEEP_SYMBOLS = ("BTC/USD", "ETH/USD", "SOL/USD")
SWEEP_PERIOD = "3m"
SWEEP_MODE = "daily"

IN_SWEEP_NOT_OBS = tuple(s for s in DAILY_SWEEP if s not in UNIVERSE_OBS)
IN_OBS_NOT_SWEEP = tuple(s for s in UNIVERSE_OBS if s not in DAILY_SWEEP)

LAW = (
    "Daily health_sweep roster ≠ Wave A watch ≠ I2 hist shadows. "
    "ema-cross / supertrend / rsi-momentum on the sweep are STOCK Lab scores, "
    "not observation_v0 books and not live enable. Donchian is not on the sweep."
)


def print_roster() -> Dict[str, Any]:
    print(f"\nSWEEP ROSTER  {VERSION}")
    print("=" * 64)
    print(LAW)
    print("-" * 64)
    print(f"  Wave A WATCH     {list(WAVE_A_WATCH)}")
    print(f"  I2 hist shadow   {list(I2_SHADOW)}")
    print(f"  obs_v0 covered   {list(UNIVERSE_OBS)}")
    print(f"  daily sweep      {list(DAILY_SWEEP)}  {SWEEP_PERIOD} {SWEEP_SYMBOLS} mode={SWEEP_MODE}")
    print(f"  sweep but no obs {list(IN_SWEEP_NOT_OBS)}")
    print(f"  obs but no sweep {list(IN_OBS_NOT_SWEEP)}")
    print("-" * 64)
    print("  Do not enable ema/supertrend/rsi because they appear on the sweep.")
    print("  Do not score donchian-lb20 from this sweep. Donchian is absent.")
    print("  Sweep score ≠ after-cost vs sit-out. Sweep ≠ KEEP.")
    print("=" * 64)
    print()
    return {
        "ok": True,
        "version": VERSION,
        "wave_a": WAVE_A_WATCH,
        "i2": I2_SHADOW,
        "obs": UNIVERSE_OBS,
        "sweep": DAILY_SWEEP,
        "sweep_only": IN_SWEEP_NOT_OBS,
        "obs_only": IN_OBS_NOT_SWEEP,
        "keep": False,
    }
