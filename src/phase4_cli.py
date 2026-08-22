"""Phase 4 CLI helpers: outcome link + wavea snapshot + KEEP/WATCH/CUT."""

WAVE_A_KEYS = ("hunter", "squeeze", "bollinger-mr")


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


def _last_human_calls(limit: int = 80) -> dict:
    """Most recent KEEP/WATCH/CUT per Wave A key."""
    out = {}
    try:
        from src.tools.decision_log import get_recent_decisions
        rows = get_recent_decisions(limit=limit)
    except Exception:
        return out
    for d in reversed(rows):
        action = str(d.get("action") or "").upper()
        if action not in ("KEEP", "WATCH", "CUT"):
            continue
        key = (d.get("strategy_key") or d.get("strategy") or "").lower()
        if key in WAVE_A_KEYS and key not in out:
            out[key] = {
                "action": action,
                "note": d.get("notes") or d.get("reason") or "",
                "time": str(d.get("timestamp") or "")[:19],
            }
    return out


def record_wavea_call(verdict: str, key: str, note: str = "") -> bool:
    """
    Record a human Wave A call: KEEP / WATCH / CUT.
    Suggestion from `wavea` is not a call until this is logged.
    """
    verdict = (verdict or "").upper().strip()
    key = (key or "").lower().strip()
    if verdict not in ("KEEP", "WATCH", "CUT"):
        print("Verdict must be: keep / watch / cut")
        return False
    if key not in WAVE_A_KEYS:
        print(f"Wave A keys: {', '.join(WAVE_A_KEYS)}")
        print(f"Got: {key}")
        return False
    note = (note or "").strip()
    if not note:
        note = f"Human {verdict} on {key} (no extra note)"

    try:
        from src.tools.decision_log import save_decision
        from src.tools.cycle_log import get_last_cycle_id, start_cycle, log_decision

        cycle_id = get_last_cycle_id() or start_cycle(notes=f"wavea_{verdict.lower()}")
        save_decision({
            "market": "crypto",
            "strategy": key,
            "strategy_key": key,
            "style": "WaveA",
            "reason": note,
            "notes": note,
            "user_selected": key,
            "user_confirmed": True,
            "user_enabled_strategy": False,
            "status": verdict.lower(),
            "expected_outcome": f"wavea_{verdict.lower()}",
            "action": verdict,
            "cycle_id": cycle_id,
        })
        log_decision(
            cycle_id,
            action=verdict,
            strategy=key,
            strategy_key=key,
            reason=note,
            user_confirmed=True,
            status=verdict.lower(),
        )
        print(f"→ Recorded {verdict} on {key}")
        print(f"  note: {note}")
        print(f"  cycle_id: {cycle_id}")
        print("  This is your call, not the snapshot suggestion.")
        return True
    except Exception as e:
        print(f"→ Failed to record: {e}")
        return False


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
                k = (s.get("key") or "").lower()
                live[k] = bool(s.get("enabled"))
    except Exception:
        pass

    snap = wave_a_snapshot()
    calls = _last_human_calls()
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
        call = calls.get(key)
        if call:
            print(f"                 Last human call: {call['action']}  {call['time']}  {call['note']}")
        else:
            print("                 Last human call: none yet")
    last = get_last_cycle_id()
    print("-" * 60)
    print(f"Wave A enabled: {on_count}/3")
    if last:
        print(f"Last cycle_id: {last}")
    print("=" * 60)
    print("Record a call:  keep hunter <note>")
    print("                watch squeeze <note>")
    print("                cut bollinger-mr <note>")
    print("Tip: mark SKIP/TAKE/WAIT in history so suggestions get smarter.")
