#!/usr/bin/env bash
# Flexible mark quality + paper-trade load CAUTION.
# Run from repo root after: git pull origin main
#   bash scripts/fix_mark_and_load.sh
set -e
python3 << 'PY'
from pathlib import Path

# --- main.py mark parser ---
p = Path("main.py")
t = p.read_text()
if "normalize_decision_quality" not in t:
    old = '''        elif user_input.startswith("mark "):
            from src.tools.decision_log import update_decision_outcome
            parts = user_input.split()

            if len(parts) < 3:
                print("Usage: mark <number> <good/bad/neutral> [good_process/bad_process/unclear]")
                print("Example: mark 1 good")
                print("Example: mark 1 bad bad_process")
            else:
                try:
                    index = int(parts[1])
                    outcome = parts[2].lower()
                    quality = parts[3].lower() if len(parts) >= 4 else None

                    if outcome not in ["good", "bad", "neutral"]:
                        print("Outcome must be: good / bad / neutral")
                    elif quality and quality not in ["good_process", "bad_process", "unclear"]:
                        print("Quality must be: good_process / bad_process / unclear")
                    else:
                        success = update_decision_outcome(index, outcome, decision_quality=quality)
                        if success:
                            msg = f"\u2192 Decision #{index} marked outcome='{outcome}'"
                            if quality:
                                msg += f", quality='{quality}'"
                            print(msg)
                        else:
                            print("Could not update decision. Check the number.")
                except Exception:
                    print("Usage: mark <number> <good/bad/neutral> [good_process/bad_process/unclear]")
'''
    new = '''        elif user_input.startswith("mark "):
            from src.tools.decision_log import update_decision_outcome, normalize_decision_quality
            parts = user_input.split()

            if len(parts) < 3:
                print("Usage: mark <number> <good/bad/neutral> [good_process/bad_process/unclear]")
                print("Example: mark 1 good")
                print("Example: mark 1 neutral good_process")
                print("Also ok: mark 1 neutral good process")
            else:
                try:
                    index = int(parts[1])
                    outcome = parts[2].lower()
                    quality_raw = " ".join(parts[3:]) if len(parts) >= 4 else None
                    quality = normalize_decision_quality(quality_raw) if quality_raw else None

                    if outcome not in ["good", "bad", "neutral"]:
                        print("Outcome must be: good / bad / neutral")
                    elif quality_raw and not quality:
                        print("Quality must be: good_process / bad_process / unclear")
                        print("(you can type: good process  or  good_process)")
                    else:
                        success = update_decision_outcome(index, outcome, decision_quality=quality)
                        if success:
                            msg = f"\u2192 Decision #{index} marked outcome='{outcome}'"
                            if quality:
                                msg += f", quality='{quality}'"
                            print(msg)
                        else:
                            print("Could not update decision. Check the number.")
                except Exception:
                    print("Usage: mark <number> <good/bad/neutral> [good_process/bad_process/unclear]")
'''
    if old not in t:
        raise SystemExit("mark block not found \u2014 main.py layout unexpected")
    t = t.replace(old, new, 1)
    p.write_text(t)
    print("OK mark parser")
else:
    print("skip mark parser")

# --- strategy paper load ---
sr = Path("src/agents/strategy_recommendation_agent.py")
st = sr.read_text()
if "get_open_paper_trades" not in st:
    st = st.replace(
        "from src.tools.ananta_api import get_portfolio, get_enabled_strategies, resolve_strategy_key",
        "from src.tools.ananta_api import get_portfolio, get_enabled_strategies, resolve_strategy_key, get_open_paper_trades",
        1,
    )
if "paper_trade_count" not in st:
    old = '''    print(f"   Load check \u2192 open positions: {open_positions} | enabled strategies: {enabled_count}")

    options = _build_ananta_options(regime, risk, enabled_list)

    # === RISK GUARDRAILS ===
    load_level = "OK"
    if open_positions >= 10 or enabled_count >= 9 or (open_positions >= 8 and enabled_count >= 6):
        load_level = "CRITICAL"
    elif open_positions >= 7 or enabled_count >= 7:
        load_level = "HIGH"
    elif open_positions >= 5 or enabled_count >= 5:
        load_level = "CAUTION"
'''
    new = '''    paper_trade_count = 0
    try:
        tr = get_open_paper_trades()
        if tr.get("success"):
            paper_trade_count = int(tr.get("count") or 0)
    except Exception:
        paper_trade_count = 0

    print(f"   Load check \u2192 open positions: {open_positions} | paper trades: {paper_trade_count} | enabled strategies: {enabled_count}")

    options = _build_ananta_options(regime, risk, enabled_list)

    # === RISK GUARDRAILS ===
    load_level = "OK"
    if open_positions >= 10 or enabled_count >= 9 or (open_positions >= 8 and enabled_count >= 6):
        load_level = "CRITICAL"
    elif open_positions >= 7 or enabled_count >= 7:
        load_level = "HIGH"
    elif open_positions >= 5 or enabled_count >= 5:
        load_level = "CAUTION"

    # Paper-trade list can be bloated vs slots; nudge OK \u2192 CAUTION only
    if paper_trade_count >= 20 and load_level == "OK":
        load_level = "CAUTION"
'''
    if old not in st:
        # try with arrow unicode already in file as actual char
        old2 = old.replace("\\u2192", "\u2192")
        new2 = new.replace("\\u2192", "\u2192")
        if old2 in st:
            st = st.replace(old2, new2, 1)
        else:
            raise SystemExit("load block not found")
    else:
        st = st.replace(old, new, 1)
    sr.write_text(st)
    print("OK paper trade load")
else:
    print("skip paper trade load")
    sr.write_text(st)

import py_compile
for f in ["main.py", "src/tools/decision_log.py", "src/agents/strategy_recommendation_agent.py"]:
    py_compile.compile(f, doraise=True)
print("COMPILE_OK")
print("Done. Restart: python main.py")
print("Then mark both SKIPs:")
print("  mark 1 neutral good_process")
print("  mark 2 neutral good_process")
PY
