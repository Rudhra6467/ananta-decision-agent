#!/usr/bin/env bash
# Log real user action (SKIP/TAKE/WAIT/ENABLE/CANCEL) on the cycle ledger.
# Run from repo root: bash scripts/fix_skip_action.sh
set -e
python3 << 'PY'
from pathlib import Path

p = Path("main.py")
t = p.read_text()

old_imp = "from src.tools.cycle_log import start_cycle, log_decision, log_opportunities"
new_imp = "from src.tools.cycle_log import start_cycle, log_decision, log_opportunities, infer_cycle_action"
if "infer_cycle_action" not in t:
    if old_imp not in t:
        raise SystemExit("import block not found")
    t = t.replace(old_imp, new_imp, 1)

old_act = '''        top = result.get("decision")
        action = "WAIT"
        if top and str(top).upper() in ("WAIT", "SKIP", "HOLD"):
            action = str(top).upper()
        log_opportunities(
            cycle_id,
            candidates,
            chosen_action=action,
            chosen_strategy=top,
            regime=result.get("market_regime"),
        )
        log_decision(
            cycle_id,
            action=action,
            strategy=top,
            confidence=result.get("confidence"),
            reason=result.get("reason"),
            top_recommendation=top,
            ranked_options=candidates,
            status="recommended",
        )'''

new_act = '''        top = result.get("decision")
        action = infer_cycle_action(result)
        chosen_strategy = "SKIP" if action == "SKIP" else top
        log_opportunities(
            cycle_id,
            candidates,
            chosen_action=action,
            chosen_strategy=chosen_strategy,
            regime=result.get("market_regime"),
        )
        log_decision(
            cycle_id,
            action=action,
            strategy=chosen_strategy,
            confidence=result.get("confidence") if action != "SKIP" else 0,
            reason=result.get("reason") if action != "SKIP" else "User skipped / no strategy selected",
            top_recommendation=top,
            ranked_options=candidates,
            user_confirmed=False if action in ("SKIP", "CANCEL") else None,
            status=str(result.get("execution_status") or action.lower()),
        )'''

if "chosen_strategy = \"SKIP\"" not in t and "chosen_strategy = 'SKIP'" not in t:
    if old_act not in t:
        print("WARN: action block already changed or layout unexpected")
    else:
        t = t.replace(old_act, new_act, 1)
        print("OK cycle action uses infer_cycle_action")
else:
    print("skip action block")

old_exec = '''    print("EXECUTION STATUS")
    print(f"  Status            : {result.get('execution_status', 'Not executed')}")
    if result.get("_cycle_id"):
        print(f"  Cycle ID          : {result.get('_cycle_id')}")'''

new_exec = '''    print("EXECUTION STATUS")
    print(f"  Status            : {result.get('execution_status', 'Not executed')}")
    try:
        from src.tools.cycle_log import infer_cycle_action
        ua = infer_cycle_action(result)
        print(f"  User action       : {ua}")
    except Exception:
        pass
    if result.get("_cycle_id"):
        print(f"  Cycle ID          : {result.get('_cycle_id')}")'''

if "User action" not in t:
    if old_exec not in t:
        print("WARN: execution status block not found")
    else:
        t = t.replace(old_exec, new_exec, 1)
        print("OK user action line")
else:
    print("skip user action print")

if "SKIP choices" not in t:
    t = t.replace(
        '                waits = sum(1 for d in decisions if str(d.get("strategy", "")).upper() == "WAIT")\n',
        '                waits = sum(1 for d in decisions if str(d.get("strategy", "")).upper() == "WAIT")\n'
        '                skips = sum(1 for d in decisions if str(d.get("strategy", "")).upper() == "SKIP")\n',
        1,
    )
    t = t.replace(
        '                print(f"  WAIT choices      : {waits}")\n',
        '                print(f"  SKIP choices      : {skips}")\n'
        '                print(f"  WAIT choices      : {waits}")\n',
        1,
    )
    print("OK skip stats")
else:
    print("skip stats")

p.write_text(t)

te = Path("src/agents/tool_execution_agent.py")
tt = te.read_text()
if 'state["_user_action"] = "SKIP"' not in tt:
    tt = tt.replace(
        '        state["execution_status"] = "No strategy selected"\n',
        '        state["execution_status"] = "No strategy selected"\n'
        '        state["_user_action"] = "SKIP"\n',
        1,
    )
    tt = tt.replace(
        '            state["execution_status"] = "WAIT confirmed — no new risk taken"\n',
        '            state["execution_status"] = "WAIT confirmed — no new risk taken"\n'
        '            state["_user_action"] = "WAIT"\n',
        1,
    )
    tt = tt.replace(
        '        print("→ Decision logged to memory (rich journal).")\n',
        '        print("→ Decision logged to memory (rich journal).")\n'
        '        if is_wait:\n'
        '            state["_user_action"] = "WAIT"\n'
        '        elif enabled_ok:\n'
        '            state["_user_action"] = "ENABLE"\n'
        '        else:\n'
        '            state["_user_action"] = "TAKE"\n',
        1,
    )
    tt = tt.replace(
        '        state["execution_status"] = "Cancelled by user"\n',
        '        state["execution_status"] = "Cancelled by user"\n'
        '        state["_user_action"] = "CANCEL"\n',
        1,
    )
    te.write_text(tt)
    print("OK tool_execution _user_action")
else:
    print("skip tool_execution")

st = Path("src/state/agent_state.py")
s = st.read_text()
if "_user_action" not in s:
    s = s.replace(
        "    _cycle_decision_logged: Optional[bool]\n",
        "    _cycle_decision_logged: Optional[bool]\n    _user_action: Optional[str]\n",
    )
    if "_user_action" not in s:
        s = s.replace(
            "    next_agent: Optional[str]\n",
            "    next_agent: Optional[str]\n    _user_action: Optional[str]\n",
        )
    st.write_text(s)
    print("OK AgentState _user_action")
else:
    print("skip AgentState")

import py_compile
for f in ["main.py", "src/agents/tool_execution_agent.py", "src/tools/cycle_log.py", "src/state/agent_state.py"]:
    py_compile.compile(f, doraise=True)
print("COMPILE_OK")
print("Done. Restart python main.py")
print("Test: run -> 0 Skip -> look for User action : SKIP then cycles")
PY
