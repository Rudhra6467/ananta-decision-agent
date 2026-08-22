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


def print_audit_pack():
    """
    Phase 4 evidence pack: one screen that answers
    what was decided, skipped, why, and what happened after.
    """
    from src.tools.cycle_log import (
        read_recent_cycles,
        read_recent_opportunities,
        get_last_cycle_id,
        wave_a_snapshot,
    )
    from src.tools.decision_log import get_recent_decisions

    print("\nAGENT ANANTA AUDIT PACK")
    print("=" * 64)
    print("What was decided, skipped, marked, and called (Wave A).")
    print("-" * 64)

    live = {}
    equity = None
    slots = None
    try:
        from src.tools.ananta_api import get_strategy_status, get_portfolio
        st = get_strategy_status()
        if st.get("success"):
            for s in st.get("strategies", []):
                live[(s.get("key") or "").lower()] = bool(s.get("enabled"))
        port = get_portfolio()
        if port.get("success") and port.get("data"):
            data = port["data"]
            equity = data.get("equity") or data.get("total_value") or data.get("balance")
            slots = data.get("slots_used") or data.get("open_positions")
    except Exception:
        pass

    print("BOOK")
    print(f"  Equity     : {equity}")
    print(f"  Positions  : {slots}")
    on = [k for k in WAVE_A_KEYS if live.get(k)]
    extra = [k for k, v in live.items() if v and k not in WAVE_A_KEYS]
    print(f"  Wave A ON  : {', '.join(on) or 'none'}  ({len(on)}/3)")
    if extra:
        print(f"  Extra ON   : {', '.join(extra)}  (not Wave A)")
    print()

    print("WAVE A CALLS (human)")
    calls = _last_human_calls()
    snap = wave_a_snapshot()
    for key in WAVE_A_KEYS:
        info = snap.get(key) or {}
        call = calls.get(key)
        flag = "ON" if live.get(key) else "off"
        if call:
            print(f"  {key:<14} {flag:<3}  suggest={info.get('suggestion')}  call={call['action']}  {call['note']}")
        else:
            print(f"  {key:<14} {flag:<3}  suggest={info.get('suggestion')}  call=NONE")
    print()

    decisions = get_recent_decisions(limit=40)
    skip_n = sum(1 for d in decisions if str(d.get("action") or d.get("status") or "").upper() in ("SKIP", "WAIT", "SKIPPED") or str(d.get("strategy") or "").upper() == "SKIP")
    take_n = sum(1 for d in decisions if str(d.get("action") or "").upper() == "TAKE" or str(d.get("status") or "").lower() == "filled")
    _TRADE_ACTIONS = {"SKIP", "WAIT", "TAKE", "HOLD", "SKIPPED"}
    marked = [
        d for d in decisions
        if d.get("outcome") in ("good", "bad", "neutral")
        and (
            str(d.get("action") or "").upper() in _TRADE_ACTIONS
            or str(d.get("status") or "").lower() in ("skipped", "filled")
            or str(d.get("strategy") or "").upper() == "SKIP"
        )
    ]
    pending = sum(1 for d in decisions if d.get("outcome") == "pending")

    print("DECISION MEMORY (recent 40)")
    print(f"  SKIP/WAIT  : {skip_n}")
    print(f"  TAKE/fill  : {take_n}")
    print(f"  Marked     : {len(marked)}   pending={pending}")
    if marked:
        print("  Last marks:")
        for d in reversed(marked[-5:]):
            print(
                f"    {str(d.get('timestamp', ''))[:19]}  "
                f"{d.get('action') or d.get('status')}  {d.get('strategy')}  "
                f"outcome={d.get('outcome')}  quality={d.get('decision_quality')}"
            )
    print()

    print("LAST 8 LEDGER EVENTS")
    cycles = read_recent_cycles(limit=40)
    shown = 0
    for row in reversed(cycles):
        if shown >= 8:
            break
        ev = row.get("event")
        ts = str(row.get("timestamp", ""))[:19]
        cid = str(row.get("cycle_id") or "")[:28]
        if ev == "cycle_start":
            print(f"  {ts}  START    {cid}  pos={row.get('open_positions')}  {row.get('notes') or ''}")
        elif ev == "decision":
            print(f"  {ts}  {str(row.get('action') or 'DECISION'):<8} {row.get('strategy') or '-'}  {str(row.get('reason') or '')[:50]}")
        elif ev == "outcome_link":
            print(f"  {ts}  OUTCOME  equity={row.get('equity')} pos={row.get('open_positions')}  {row.get('note', '')}")
        else:
            continue
        shown += 1
    print()

    opps = read_recent_opportunities(limit=4)
    print("RECENT OPPORTUNITIES")
    if not opps:
        print("  (none)")
    else:
        for o in reversed(opps):
            print(
                f"  {str(o.get('timestamp', ''))[:19]}  "
                f"chose={o.get('chosen_action')}  skipped={o.get('skipped')}  "
                f"strat={o.get('chosen_strategy')}"
            )
    last = get_last_cycle_id()
    print("-" * 64)
    if last:
        print(f"Last cycle_id: {last}")
    print("Files: decision_log.json  cycle_log.jsonl  opportunity_log.jsonl")
    print("=" * 64)


_TRADE_ACTIONS = {"SKIP", "WAIT", "TAKE", "HOLD", "SKIPPED"}


def _is_trade_decision(d: dict) -> bool:
    action = str(d.get("action") or "").upper()
    status = str(d.get("status") or "").lower()
    strategy = str(d.get("strategy") or "").upper()
    return (
        action in _TRADE_ACTIONS
        or status in ("skipped", "filled")
        or strategy == "SKIP"
    )


def _evidence_label(good: int, bad: int, marked: int, *, take_marked: int = 0) -> str:
    """Contract evidence lifecycle: UNKNOWN → WEAK → PROMISING → SUPPORTED → VALIDATED.

    WAIT/NO_SETUP process marks alone cannot reach SUPPORTED/VALIDATED.
    Promotion-grade labels require TAKE outcome evidence.
    """
    if marked == 0:
        return "UNKNOWN"
    if take_marked == 0:
        # Process-only (WAIT/SKIP) dataset
        if marked < 3:
            return "WEAK"
        return "INSUFFICIENT_EVIDENCE"
    if take_marked < 3:
        return "WEAK"
    if good >= 5 and bad == 0 and take_marked >= 5:
        return "VALIDATED"
    if good >= 3 and good > bad and take_marked >= 3:
        return "SUPPORTED"
    if good > bad:
        return "PROMISING"
    return "WEAK"


def print_decision_eval():
    """Phase 5: score Agent decisions (process vs outcome), not strategy PnL."""
    from src.tools.decision_log import get_recent_decisions
    from src.tools.cycle_log import read_recent_opportunities, get_last_cycle_id

    rows = get_recent_decisions(limit=80)
    trades = [d for d in rows if _is_trade_decision(d)]
    skips = [
        d for d in trades
        if str(d.get("action") or d.get("status") or d.get("strategy") or "").upper()
        in ("SKIP", "WAIT", "HOLD", "SKIPPED")
        or str(d.get("strategy") or "").upper() == "SKIP"
    ]
    takes = [
        d for d in trades
        if str(d.get("action") or "").upper() == "TAKE"
        or str(d.get("status") or "").lower() == "filled"
    ]

    def _count(ds, field, value):
        return sum(1 for d in ds if d.get(field) == value)

    skip_good = _count(skips, "outcome", "good")
    skip_bad = _count(skips, "outcome", "bad")
    skip_neu = _count(skips, "outcome", "neutral")
    skip_pend = _count(skips, "outcome", "pending")
    take_good = _count(takes, "outcome", "good")
    take_bad = _count(takes, "outcome", "bad")
    take_neu = _count(takes, "outcome", "neutral")
    take_pend = _count(takes, "outcome", "pending")
    gp = sum(1 for d in trades if d.get("decision_quality") == "good_process")
    bp = sum(1 for d in trades if d.get("decision_quality") == "bad_process")

    marked = skip_good + skip_bad + skip_neu + take_good + take_bad + take_neu
    take_marked = take_good + take_bad + take_neu
    # Promotion evidence uses TAKE outcomes; WAIT/SKIP are process-only.
    evidence = _evidence_label(
        take_good, take_bad, marked, take_marked=take_marked,
    )

    opps = read_recent_opportunities(limit=20)
    skipped_opps = sum(1 for o in opps if o.get("skipped"))

    print("\nAGENT DECISION EVALUATION (Phase 5)")
    print("=" * 60)
    print("Scores the Agent's choices, not Ananta PnL.")
    print("Process ≠ outcome. SKIP is first-class. WAIT ≠ strategy success.")
    print("-" * 60)
    print("SKIP / WAIT  (process — not promotion evidence)")
    print(f"  n={len(skips)}  good={skip_good}  bad={skip_bad}  neutral={skip_neu}  pending={skip_pend}")
    print("TAKE  (promotion evidence)")
    print(f"  n={len(takes)}  good={take_good}  bad={take_bad}  neutral={take_neu}  pending={take_pend}")
    print("PROCESS QUALITY (trade rows)")
    print(f"  good_process={gp}  bad_process={bp}")
    print(f"Opportunity SKIPs (recent 20): {skipped_opps}")
    print("-" * 60)
    print(f"Evidence strength : {evidence}")
    if evidence == "UNKNOWN":
        print("  No marked SKIP/TAKE yet. Run cycles, then mark.")
    elif evidence == "INSUFFICIENT_EVIDENCE":
        print("  WAIT/SKIP process marks only. Need TAKE outcomes for KEEP/SUPPORTED.")
        print("  Stay on WATCH. INSUFFICIENT EVIDENCE is a valid result.")
    elif evidence == "WEAK":
        print("  Too few TAKE marks to KEEP or CUT. Stay on WATCH.")
    elif evidence == "PROMISING":
        print("  Early positive TAKE tilt. Do not promote yet.")
    elif evidence == "SUPPORTED":
        print("  Enough supportive TAKE marks to consider KEEP (still human-gated).")
    else:
        print("  Strong TAKE marks. KEEP is defensible; still human-gated.")
    last = get_last_cycle_id()
    if last:
        print(f"Last cycle_id    : {last}")
    print("=" * 60)
    print("Next: cycle → mark SKIP/TAKE → evaluate. Do not enable more strategies.")


