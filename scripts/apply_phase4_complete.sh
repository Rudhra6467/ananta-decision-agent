#!/usr/bin/env bash
# Apply Phase 4 completion patches. Run from repo root:
#   bash scripts/apply_phase4_complete.sh
set -e
python3 << 'PY'
from pathlib import Path

p = Path("src/state/agent_state.py")
t = p.read_text()
if "_cycle_id" not in t:
    t = t.replace(
        "    # Control\n    next_agent: Optional[str]\n",
        "    # Control\n    next_agent: Optional[str]\n\n"
        "    # Phase 4 cycle provenance (carried through graph)\n"
        "    _cycle_id: Optional[str]\n"
        "    _cycle_decision_logged: Optional[bool]\n",
    )
    p.write_text(t)
    print("OK AgentState")
else:
    print("skip AgentState")

p = Path("src/agents/tool_execution_agent.py")
t = p.read_text()
if "_log_cycle_final" not in t:
    helper = (
        "def _log_cycle_final(state, action, strategy=None, strategy_key=None, "
        "confidence=None, reason=None, status=None, user_confirmed=None, user_override=None):\n"
        '    """Attach final user action to the open cycle (Phase 4). Fail soft."""\n'
        '    cycle_id = state.get("_cycle_id")\n'
        "    if not cycle_id:\n"
        "        return\n"
        "    try:\n"
        "        from src.tools.cycle_log import log_decision\n"
        "        log_decision(\n"
        "            cycle_id,\n"
        "            action=action,\n"
        "            strategy=strategy,\n"
        "            strategy_key=strategy_key,\n"
        "            confidence=confidence,\n"
        "            reason=reason,\n"
        '            top_recommendation=state.get("decision"),\n'
        "            user_confirmed=user_confirmed,\n"
        "            user_override=user_override,\n"
        "            status=status,\n"
        '            extra={"regime": state.get("market_regime")},\n'
        "        )\n"
        '        state["_cycle_decision_logged"] = True\n'
        "    except Exception:\n"
        "        pass\n\n\n"
    )
    idx = t.find("def ")
    t = t[:idx] + helper + t[idx:]

    old_skip = (
        '            print("\u2192 Skip logged to decision memory.")\n'
        "        except Exception:\n"
        "            pass\n\n"
        '        state["next_agent"] = "supervisor"\n'
        "        return state"
    )
    new_skip = (
        '            print("\u2192 Skip logged to decision memory.")\n'
        "        except Exception:\n"
        "            pass\n\n"
        "        _log_cycle_final(\n"
        "            state,\n"
        '            action="SKIP",\n'
        '            strategy="SKIP",\n'
        "            confidence=0,\n"
        '            reason="User selected 0 / do nothing",\n'
        '            status="skipped",\n'
        "            user_confirmed=False,\n"
        "            user_override=False,\n"
        "        )\n\n"
        '        state["next_agent"] = "supervisor"\n'
        "        return state"
    )
    if old_skip not in t:
        # try without unicode arrow
        old_skip = old_skip.replace("\u2192", "->")
        new_skip = new_skip.replace("\u2192", "->")
    if old_skip not in t:
        print("WARN skip block not found - check tool_execution manually")
    else:
        t = t.replace(old_skip, new_skip)

    old_rich = (
        '        print("\u2192 Decision logged to memory (rich journal).")\n'
        "    else:\n"
        '        print("\u2192 Cancelled.")'
    )
    new_rich = (
        '        print("\u2192 Decision logged to memory (rich journal).")\n\n'
        '        final_action = "WAIT" if is_wait else ("ENABLE" if enabled_ok else "TAKE")\n'
        "        _log_cycle_final(\n"
        "            state,\n"
        "            action=final_action,\n"
        "            strategy=selected_name,\n"
        "            strategy_key=strategy_key,\n"
        '            confidence=selected.get("confidence"),\n'
        '            reason=selected.get("reason"),\n'
        "            status=status,\n"
        "            user_confirmed=True,\n"
        "            user_override=user_override,\n"
        "        )\n"
        "    else:\n"
        '        print("\u2192 Cancelled.")'
    )
    if old_rich not in t:
        old_rich = old_rich.replace("\u2192", "->")
        new_rich = new_rich.replace("\u2192", "->")
    if old_rich not in t:
        print("WARN rich block not found")
    else:
        t = t.replace(old_rich, new_rich)

    old_cancel = (
        '            print("\u2192 Cancellation logged to decision memory.")\n'
        "        except Exception:\n"
        "            pass\n\n"
        '    state["next_agent"] = "supervisor"\n'
        "    return state\n"
    )
    new_cancel = (
        '            print("\u2192 Cancellation logged to decision memory.")\n'
        "        except Exception:\n"
        "            pass\n\n"
        "        _log_cycle_final(\n"
        "            state,\n"
        '            action="CANCEL",\n'
        "            strategy=selected_name,\n"
        "            strategy_key=preset_key,\n"
        '            confidence=selected.get("confidence"),\n'
        '            reason=selected.get("reason"),\n'
        '            status="cancelled",\n'
        "            user_confirmed=False,\n"
        '            user_override=str(selected_name).upper() != str(top_name).upper(),\n'
        "        )\n\n"
        '    state["next_agent"] = "supervisor"\n'
        "    return state\n"
    )
    if old_cancel not in t:
        old_cancel = old_cancel.replace("\u2192", "->")
        new_cancel = new_cancel.replace("\u2192", "->")
    if old_cancel not in t:
        print("WARN cancel block not found")
    else:
        t = t.replace(old_cancel, new_cancel)
    p.write_text(t)
    print("OK tool_execution")
else:
    print("skip tool_execution")

import subprocess
from pathlib import Path as P
if P("scripts/wire_phase4_main.sh").exists():
    subprocess.check_call(["bash", "scripts/wire_phase4_main.sh"])
else:
    print("wire_phase4_main.sh missing")

import py_compile
for f in ["main.py", "src/agents/tool_execution_agent.py", "src/state/agent_state.py"]:
    py_compile.compile(f, doraise=True)
print("COMPILE_OK")
print("Done. Run: python main.py")
print("Test: run -> choose 0 Skip -> cycles -> monitor -> wavea")
PY
