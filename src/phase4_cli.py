"""Phase 4 CLI helpers: outcome link + wavea snapshot."""


def link_monitor_outcome(open_count: int, enabled_count: int, health: str, get_portfolio):
    """Best-effort outcome linkage after monitor. Fail soft."""
    try:
        from src.tools.cycle_log import get_last_cycle_id, log_outcome_link
        last_id = get_last_cycle_id()
        equity_val = None
        try:
            port = get_portfolio()
            if port.get("success") and port.get("data"):
                data = port["data"]
                equity_val = data.get("equity") or data.get("total_value") or data.get("balance")
        except Exception:
            pass
        if last_id:
            log_outcome_link(
                last_id,
                equity=equity_val,
                open_positions=open_count,
                note=f"monitor health={health} enabled={enabled_count}",
            )
            print(f"Outcome linked → cycle {last_id}")
    except Exception as e:
        print(f"(outcome link skipped: {e})")


def print_wavea_snapshot():
    from src.tools.cycle_log import wave_a_snapshot, get_last_cycle_id
    print("\nWAVE A POST-CYCLE SNAPSHOT (suggestion only)")
    print("=" * 60)
    print("Human still decides KEEP / WATCH / CUT. This is evidence support.")
    print("Set: hunter · squeeze · bollinger-mr   |  prefer 3 enabled, max 5")
    print("-" * 60)

    live = {}
    try:
        from src.tools.ananta_api import get_strategy_status
        st = get_strategy_status()
        if st.get("success"):
            for s in st.get("strategies", []):
                key = (s.get("key") or "").lower()
                live[key] = bool(s.get("enabled"))
    except Exception:
        pass

    snap = wave_a_snapshot()
    on_count = 0
    for key, info in snap.items():
        on = live.get(key)
        if on:
            on_count += 1
        flag = "● ON " if on else ("○ off" if on is False else "?    ")
        print(
            f"{key:<16} {flag}  → {info['suggestion']:<6}  "
            f"good={info['good']} bad={info['bad']} "
            f"neutral={info['neutral']} pending={info['pending']}"
        )
        print(f"                 {info['note']}")
    last = get_last_cycle_id()
    print("-" * 60)
    print(f"Wave A enabled: {on_count}/3")
    if last:
        print(f"Last cycle_id: {last}")
    print("=" * 60)
    print("Tip: mark SKIP/TAKE/WAIT in history so this snapshot gets smarter.")
