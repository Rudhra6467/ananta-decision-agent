from src.graph import agent_graph
from src.memory import get_last_user_profile
import os

def run_once():
    print("=" * 55)
    print("           Ananta Multi-Agent System")
    print("=" * 55)
    print()

    initial_state = {
        "messages": [],
        "user_goal": None,
        "risk_tolerance": None,
        "capital": None,
        "preferred_markets": None,
        "experience_level": None,
        "market_data": None,
        "market_regime": None,
        "decision": None,
        "reason": None,
        "confidence": None,
        "entry_idea": None,
        "stop_loss_idea": None,
        "take_profit_idea": None,
        "portfolio": None,
        "execution_status": None,
        "next_agent": None
    }

    result = agent_graph.invoke(initial_state)

    # Phase 4: cycle provenance (fail soft — never break CLI)
    cycle_id = None
    try:
        from src.tools.cycle_log import start_cycle, log_decision, log_opportunities
        from src.tools.ananta_api import get_strategy_status, get_portfolio

        market_data = result.get("market_data") or {}
        enabled_names = []
        enabled_count = None
        try:
            st = get_strategy_status()
            if st.get("success"):
                enabled_names = [
                    s.get("name") or s.get("key")
                    for s in st.get("strategies", [])
                    if s.get("enabled")
                ]
                enabled_count = len(enabled_names)
        except Exception:
            pass

        equity = None
        open_positions = None
        try:
            port = get_portfolio()
            if port.get("success") and port.get("data"):
                data = port["data"]
                equity = data.get("equity") or data.get("total_value") or data.get("balance")
                open_positions = data.get("slots_used") or data.get("open_positions")
        except Exception:
            pass
        if open_positions is None:
            open_positions = (result.get("portfolio") or {}).get("open_positions")

        load_level = None
        try:
            oc = int(open_positions or 0)
            ec = int(enabled_count or 0)
            if oc >= 10 or ec >= 8:
                load_level = "OVERLOADED"
            elif oc >= 7 or ec >= 5:
                load_level = "CAUTION"
            elif oc == 0 and ec == 0:
                load_level = "IDLE"
            else:
                load_level = "OK"
        except Exception:
            pass

        cycle_id = start_cycle(
            regime=result.get("market_regime"),
            symbol=market_data.get("symbol", "BTC"),
            price=market_data.get("price"),
            equity=equity,
            open_positions=open_positions,
            enabled_strategies=enabled_names,
            enabled_count=enabled_count,
            load_level=load_level,
        )
        result["_cycle_id"] = cycle_id

        options = result.get("strategy_options") or []
        candidates = [
            {
                "name": o.get("name"),
                "confidence": o.get("confidence"),
                "reason": o.get("reason"),
                "style": o.get("style"),
            }
            for o in options
        ]
        top = result.get("decision")
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
        )
    except Exception as e:
        print(f"(cycle log skipped: {e})")

    print("\n" + "=" * 55)
    print("           FINAL ANALYSIS RESULT")
    print("=" * 55)
    print()
    print("USER PROFILE")
    print(f"  Goal              : {result.get('user_goal')}")
    print(f"  Risk Tolerance    : {result.get('risk_tolerance')}")
    print(f"  Capital           : ${result.get('capital')}")
    print(f"  Preferred Markets : {result.get('preferred_markets')}")
    print(f"  Experience        : {result.get('experience_level')}")
    print()

    print("MARKET ANALYSIS")
    market_data = result.get("market_data") or {}
    print(f"  Symbol            : {market_data.get('symbol', 'BTC')}")
    print(f"  Current Price     : ${market_data.get('price', 'N/A')}")
    print(f"  24h Change        : {market_data.get('change_24h', 'N/A')}%")
    print(f"  Market Regime     : {result.get('market_regime')}")
    print()

    print("RECOMMENDATION")
    print(f"  Top Strategy      : {result.get('decision')}")
    print(f"  Confidence Score  : {result.get('confidence')}")
    print(f"  Reason            : {result.get('reason')}")
    print()
    print("  Suggested Plan:")
    print(f"    • Entry     : {result.get('entry_idea', 'N/A')}")
    print(f"    • Stop Loss : {result.get('stop_loss_idea', 'N/A')}")
    print(f"    • Take Profit: {result.get('take_profit_idea', 'N/A')}")
    print()
    if result.get("ranking_explanation"):
        print(f"  Ranking Logic   : {result.get('ranking_explanation')}")
        print()

    disable_suggestions = result.get("disable_suggestions") or []
    if disable_suggestions:
        print("CLEANUP SUGGESTIONS (reduce load)")
        print(f"  Load level        : {result.get('load_level', 'N/A')}")
        print(f"  Enabled now       : {result.get('enabled_count', 'N/A')}")
        print("  Run these one by one:")
        for key in disable_suggestions:
            print(f"    disable {key}")
        print()

    strategy_options = result.get("strategy_options")
    if strategy_options and len(strategy_options) > 1:
        print("RANKED STRATEGY OPTIONS")
        for i, opt in enumerate(strategy_options, 1):
            print(f"  {i}. {opt.get('name')} | Confidence: {opt.get('confidence')} | Style: {opt.get('style')}")
            print(f"     {opt.get('reason')}")
        print()
        print("Would you like to enable one of these strategies?")
        print("Type: enable <name>   (example: enable hunter)")
        print()

    portfolio = result.get("portfolio")
    if portfolio:
        print("PORTFOLIO ANALYSIS")
        print(f"  Total Value       : ${portfolio.get('total_value')}")
        print(f"  Cash              : ${portfolio.get('cash')}")
        print(f"  Invested          : ${portfolio.get('invested')}")
        print(f"  Open Positions    : {portfolio.get('open_positions')}")
        print(f"  Unrealized PnL    : ${portfolio.get('unrealized_pnl')}")
        print(f"  Risk Score        : {portfolio.get('risk_score')}")
        print(f"  Diversification   : {portfolio.get('diversification_score')}/10")
        print(f"  Notes             : {portfolio.get('notes')}")
        print()

    from src.tools.ananta_api import get_open_paper_trades
    trades_result = get_open_paper_trades()

    if trades_result.get("success") and trades_result.get("count", 0) > 0:
        open_trades = trades_result.get("open_trades", [])

        print("OPEN PAPER TRADES (from Ananta)")
        for i, trade in enumerate(open_trades[:5], 1):
            symbol = trade.get('symbol', 'N/A')
            side = trade.get('side', 'N/A')
            qty = round(trade.get('quantity', 0), 4)
            price = trade.get('price', 'N/A')
            print(f"  {i}. {symbol} | {side} | Qty: {qty} | Price: ${price}")

        print(f"  Total shown: {min(5, len(open_trades))} of {trades_result.get('count')} paper trades")
        print()

        buy_count = sum(1 for t in open_trades if str(t.get("side", "")).upper() == "BUY")
        sell_count = sum(1 for t in open_trades if str(t.get("side", "")).upper() == "SELL")

        print("  Exposure Summary:")
        print(f"    • Long positions  : {buy_count}")
        print(f"    • Short positions : {sell_count}")

        if buy_count > 5:
            print("  Note: Portfolio is heavily long. Consider reducing exposure or waiting for better setups.")
        elif sell_count > buy_count:
            print("  Note: More short positions than long. Bias is currently defensive.")
        elif buy_count == 0 and sell_count == 0:
            print("  Note: No open paper trades. Good time to look for new setups.")
        else:
            print("  Note: Exposure looks manageable.")
        print()

        if buy_count > sell_count + 2:
            print("    • Bias            : Currently net long")
        elif sell_count > buy_count + 2:
            print("    • Bias            : Currently net short")
        else:
            print("    • Bias            : Relatively balanced")
        print()

        open_count = trades_result.get("count", 0)
        if open_count >= 7:
            print("  Tip: type  cleanup  to reduce position load interactively.")
            print()

    print("EXECUTION STATUS")
    print(f"  Status            : {result.get('execution_status', 'Not executed')}")
    if result.get("_cycle_id"):
        print(f"  Cycle ID          : {result.get('_cycle_id')}")
    print("=" * 55)


def research_market():
    from src.tools.market_tools import get_market_data
    print("\nRESEARCH → MARKET")
    print("-" * 45)
    try:
        m = get_market_data()
        print(f"{'Metric':<18} {'Value'}")
        print("-" * 45)
        print(f"{'Symbol':<18} {m.get('symbol', 'BTC')}")
        print(f"{'Price':<18} ${m.get('price', 'N/A')}")
        print(f"{'24h Change':<18} {m.get('change_24h', 'N/A')}%")
        print(f"{'Regime':<18} {m.get('trend', 'N/A')}")
        print(f"{'RSI (approx)':<18} {m.get('rsi', 'N/A')}")
        print(f"{'Volatility':<18} {m.get('volatility', 'N/A')}")
        print("-" * 45)
        regime = str(m.get('trend', '')).upper()
        if regime == "COMPRESSION":
            print("Note: Compression — breakout / mean-reversion setups preferred.")
        elif "BULLISH" in regime or regime == "TREND_UP":
            print("Note: Bullish regime — momentum continuation favored.")
        elif "BEARISH" in regime or regime == "TREND_DOWN":
            print("Note: Bearish regime — short momentum / caution on longs.")
        else:
            print("Note: Neutral / mixed conditions.")
    except Exception as e:
        print(f"Could not fetch market data: {e}")
    print()


def research_strategies():
    from src.tools.ananta_api import get_strategy_status
    print("\nRESEARCH → STRATEGIES")
    print("-" * 55)
    result = get_strategy_status()
    if not result.get("success"):
        print(f"Could not fetch strategies: {result.get('error') or result}")
        print()
        return

    strategies = result.get("strategies", [])
    if not strategies:
        print("No strategies found.")
        print()
        return

    print(f"{'Strategy':<28} {'Key':<22} {'Status'}")
    print("-" * 55)
    enabled_count = 0
    for s in strategies:
        name = (s.get("name") or s.get("key") or "?")[:27]
        key = (s.get("key") or "?")[:21]
        enabled = s.get("enabled", False)
        status = "Enabled" if enabled else "Disabled"
        if enabled:
            enabled_count += 1
        mark = "●" if enabled else "○"
        print(f"{mark} {name:<26} {key:<22} {status}")
    print("-" * 55)
    print(f"Total: {len(strategies)} | Enabled: {enabled_count} | Disabled: {len(strategies) - enabled_count}")
    if enabled_count >= 5:
        print("Note: Many strategies enabled — watch for overlapping signals.")
    print()


def research_portfolio():
    from src.tools.ananta_api import get_portfolio, get_open_paper_trades, get_strategy_status
    print("\nRESEARCH → PORTFOLIO")
    print("-" * 45)

    equity = "N/A"
    slots = "N/A"
    try:
        port = get_portfolio()
        if port.get("success") and port.get("data"):
            data = port["data"]
            equity = data.get("equity") or data.get("total_value") or data.get("balance") or "N/A"
            slots = data.get("slots_used") or data.get("open_positions") or "N/A"
    except Exception:
        pass

    trades_result = get_open_paper_trades()
    open_count = trades_result.get("count", 0) if trades_result.get("success") else "N/A"

    enabled_count = 0
    status_result = get_strategy_status()
    if status_result.get("success"):
        enabled_count = sum(1 for s in status_result.get("strategies", []) if s.get("enabled"))

    try:
        oc = int(open_count) if open_count != "N/A" else 0
    except Exception:
        oc = 0
    if oc >= 10 or enabled_count >= 8:
        health = "OVERLOADED"
    elif oc >= 7 or enabled_count >= 5:
        health = "CAUTION"
    elif oc == 0 and enabled_count == 0:
        health = "IDLE"
    else:
        health = "OK"

    print(f"{'Metric':<22} {'Value'}")
    print("-" * 45)
    print(f"{'Equity':<22} ${equity}")
    print(f"{'Slots / Positions':<22} {slots}")
    print(f"{'Open Paper Trades':<22} {open_count}")
    print(f"{'Enabled Strategies':<22} {enabled_count}")
    print(f"{'Health':<22} {health}")
    print("-" * 45)

    if health == "OVERLOADED":
        print("⚠  Exposure is very high. Prefer WAIT / reduce size. Try: cleanup")
    elif health == "CAUTION":
        print("Note: Elevated exposure — be selective. Optional: cleanup")
    elif health == "IDLE":
        print("Note: Quiet book — good time to research setups.")
    else:
        print("Note: Portfolio health looks manageable.")
    print()


def research_menu():
    print("\nRESEARCH OPTIONS")
    print("-" * 40)
    print("  research market      → BTC regime & price table")
    print("  research strategies  → Strategy status table")
    print("  research portfolio   → Equity, trades, health")
    print("-" * 40)
    print("Tip: type the full command, e.g. research market")
    print()


def _log_strategy_toggle(action: str, key: str):
    """Write enable/disable actions into decision memory + cycle ledger."""
    try:
        from src.tools.decision_log import save_decision
        from src.tools.cycle_log import get_last_cycle_id, start_cycle, log_decision

        is_enable = action == "enable"
        cycle_id = get_last_cycle_id()
        if not cycle_id:
            cycle_id = start_cycle(notes=f"manual_{action}")
        save_decision({
            "market": "crypto",
            "strategy": key,
            "strategy_key": key,
            "style": "Manual",
            "reason": f"Manual {action.upper()} via Agent CLI: {key}",
            "user_selected": key,
            "user_confirmed": True,
            "user_enabled_strategy": is_enable,
            "status": "enabled" if is_enable else "disabled",
            "expected_outcome": f"manual_{action}",
            "notes": f"standalone {action} command",
            "action": action.upper(),
            "cycle_id": cycle_id,
        })
        log_decision(
            cycle_id,
            action=action.upper(),
            strategy=key,
            strategy_key=key,
            reason=f"Manual {action.upper()} via Agent CLI: {key}",
            user_confirmed=True,
            status="enabled" if is_enable else "disabled",
        )
        print("→ Logged to decision memory.")
        print(f"→ Linked to cycle {cycle_id}")
    except Exception as e:
        print(f"→ (memory log skipped: {e})")


def interactive_mode():
    print("=" * 55)
    print("     Ananta Agent - Interactive Mode")
    print("=" * 55)
    print("You can type:")
    print("  run / analyze / recommend  → Full analysis")
    print("  monitor / health           → Quick health check")
    print("  cleanup                    → Reduce open paper positions")
    print("  research                   → Research reports (tables)")
    print("  status                     → Strategy enabled/disabled list")
    print("  history                    → Decision memory journal")
    print("  cycles                     → Cycle + opportunity ledger")
    print("  wavea / postcycle          → Wave A KEEP/WATCH/CUT suggestions")
    print("  help                       → Show all commands")
    print("  exit                       → Quit")
    print("=" * 55)

    while True:
        user_input = input("\nYou: ").strip().lower()

        from src.cli_exec import handle_buy, handle_sell, handle_cycle, handle_cleanup
        if (
            handle_buy(user_input)
            or handle_sell(user_input)
            or handle_cycle(user_input)
            or handle_cleanup(user_input)
        ):
            continue

        if user_input in ["exit", "quit", "q"]:
            print("Goodbye.")
            break

        elif user_input in ["run", "analyze", "recommend", "start", "analysis"]:
            run_once()

        elif user_input in ["research"]:
            research_menu()

        elif user_input in ["research market", "research markets", "research btc"]:
            research_market()

        elif user_input in ["research strategies", "research strategy", "research strats"]:
            research_strategies()

        elif user_input in ["research portfolio", "research port", "research positions"]:
            research_portfolio()

        elif user_input.startswith("research "):
            print("Unknown research topic.")
            print("Use: research market | research strategies | research portfolio")

        elif user_input.startswith("mark "):
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
                            msg = f"→ Decision #{index} marked outcome='{outcome}'"
                            if quality:
                                msg += f", quality='{quality}'"
                            print(msg)
                        else:
                            print("Could not update decision. Check the number.")
                except Exception:
                    print("Usage: mark <number> <good/bad/neutral> [good_process/bad_process/unclear]")

        elif user_input in ["profile", "my profile", "show profile", "what is my profile"]:
            from src.memory import get_last_user_profile
            profile = get_last_user_profile()
            if profile:
                print("\nSaved Profile:")
                print(f"  Goal       : {profile.get('user_goal')}")
                print(f"  Risk       : {profile.get('risk_tolerance')}")
                print(f"  Capital    : ${profile.get('capital')}")
                print(f"  Experience : {profile.get('experience_level')}")
            else:
                print("No saved profile found.")

        elif user_input in ["clear", "clear memory", "reset"]:
            if os.path.exists("agent_memory.json"):
                os.remove("agent_memory.json")
                print("Profile memory cleared successfully.")
            else:
                print("No profile memory file found.")
            print("Note: decision_log.json (trading journal) was not deleted.")

        elif user_input in ["history", "decisions", "log"]:
            from src.tools.decision_log import get_recent_decisions
            decisions = get_recent_decisions(limit=8)

            if not decisions:
                print("No decisions logged yet.")
            else:
                print("\nDECISION MEMORY (recent)")
                print("-" * 65)
                for i, d in enumerate(reversed(decisions), 1):
                    outcome = d.get("outcome", "pending")
                    quality = d.get("decision_quality", "pending")
                    status = d.get("status", "?")
                    override = "yes" if d.get("user_override") else "no"
                    print(f"{i}. {d.get('strategy')} | Conf: {d.get('confidence')} | Outcome: {outcome}")
                    print(f"   Regime: {d.get('regime')} | Positions: {d.get('open_positions')} | Status: {status}")
                    print(f"   Top rec: {d.get('top_recommendation')} | Override: {override} | Quality: {quality}")
                    if d.get("price") is not None:
                        print(f"   Price: ${d.get('price')} | Equity: {d.get('portfolio_equity')}")
                    print(f"   Time: {str(d.get('timestamp', ''))[:19]}")
                    print()
                print("-" * 65)
                print("Tip: mark <num> good/bad/neutral")
                print("     mark <num> good good_process   (optional quality)")

        elif user_input in ["performance", "stats", "summary"]:
            from src.tools.decision_log import get_recent_decisions
            decisions = get_recent_decisions(limit=100)

            if not decisions:
                print("No decisions logged yet.")
            else:
                total = len(decisions)
                good = sum(1 for d in decisions if d.get("outcome") == "good")
                bad = sum(1 for d in decisions if d.get("outcome") == "bad")
                neutral = sum(1 for d in decisions if d.get("outcome") == "neutral")
                pending = sum(1 for d in decisions if d.get("outcome") == "pending")
                overrides = sum(1 for d in decisions if d.get("user_override"))
                enabled = sum(1 for d in decisions if d.get("user_enabled_strategy"))
                waits = sum(1 for d in decisions if str(d.get("strategy", "")).upper() == "WAIT")

                print("\nDecision Performance Summary")
                print("-" * 40)
                print(f"  Total decisions   : {total}")
                print(f"  Marked Good       : {good}")
                print(f"  Marked Bad        : {bad}")
                print(f"  Marked Neutral    : {neutral}")
                print(f"  Still Pending     : {pending}")
                print(f"  WAIT choices      : {waits}")
                print(f"  User overrides    : {overrides}")
                print(f"  Enabled in Ananta : {enabled}")

                if good + bad > 0:
                    win_rate = round((good / (good + bad)) * 100, 1)
                    print(f"  Outcome win rate  : {win_rate}%")
                print("-" * 40)

        elif user_input in ["cycles", "cycle log", "cycle history"]:
            from src.tools.cycle_log import read_recent_cycles, read_recent_opportunities
            cycles = read_recent_cycles(limit=12)
            if not cycles:
                print("No cycles logged yet. Run an analysis first.")
            else:
                print("\nCYCLE LOG (recent events)")
                print("-" * 65)
                for row in reversed(cycles[-30:]):
                    cid = str(row.get("cycle_id", ""))[:28]
                    ev = row.get("event", "?")
                    ts = str(row.get("timestamp", ""))[:19]
                    if ev == "cycle_start":
                        print(f"{ts}  START  {cid}  regime={row.get('regime')}  load={row.get('load_level')}  pos={row.get('open_positions')}")
                    elif ev == "decision":
                        print(f"{ts}  DECISION  action={row.get('action')}  strat={row.get('strategy')}  conf={row.get('confidence')}")
                    elif ev == "outcome_link":
                        print(f"{ts}  OUTCOME  equity={row.get('equity')}  pos={row.get('open_positions')}  {row.get('note','')}")
                    else:
                        print(f"{ts}  {ev}  {cid}")
                print("-" * 65)
            opps = read_recent_opportunities(limit=5)
            if opps:
                print("\nOPPORTUNITY LOG (recent)")
                print("-" * 65)
                for o in reversed(opps):
                    print(f"{str(o.get('timestamp',''))[:19]}  chose={o.get('chosen_action')}  strat={o.get('chosen_strategy')}  skipped={o.get('skipped')}")
                    cands = o.get("candidates") or []
                    for i, c in enumerate(cands[:3], 1):
                        print(f"   {i}. {c.get('name')} conf={c.get('confidence')}")
                print("-" * 65)

        elif user_input in ["wavea", "wave a", "postcycle", "post-cycle"]:
            from src.phase4_cli import print_wavea_snapshot
            print_wavea_snapshot()

        elif user_input in ["help", "commands", "?"]:
            print("\nAvailable commands:")
            print("  run / analyze / recommend  → Full market analysis")
            print("  monitor / health / check   → Quick portfolio & strategy health check")
            print("  cleanup / clean            → Guided position reduction (paper)")
            print("  cleanup list               → List aggregated positions only")
            print("  research                   → Show research options")
            print("  research market            → Market table (BTC, regime)")
            print("  research strategies        → Strategy status table")
            print("  research portfolio         → Portfolio health table")
            print("  status                     → Show all strategies + enabled status")
            print("  enable <name>              → Enable a strategy (with confirmation)")
            print("  disable <name>             → Disable a strategy (with confirmation)")
            print("  profile                    → Show your saved profile")
            print("  history                    → Decision memory journal")
            print("  cycles                     → Cycle + opportunity ledger")
            print("  wavea / postcycle          → Wave A KEEP/WATCH/CUT suggestions")
            print("  performance / stats        → Decision performance summary")
            print("  mark <num> good/bad/neutral→ Mark outcome")
            print("  mark <num> good good_process → Mark outcome + process quality")
            print("  clear                      → Clear saved profile memory")
            print("  buy <symbol> <usd>         → Real paper BUY (e.g. buy BTC 25)")
            print("  sell <symbol> <fraction>   → Real paper SELL (e.g. sell BTC 1.0)")
            print("  cycle [symbol]             → Run one Ananta evaluation cycle")
            print("  help                       → Show this message")
            print("  exit                       → Quit the agent")
            print()

        elif user_input.startswith("enable "):
            from src.tools.ananta_api import enable_strategy
            parts = user_input.split()
            if len(parts) < 2:
                print("Usage: enable <strategy_name>")
                print("Example: enable hunter")
                print("Example: enable mean reversion")
            else:
                strategy_name = " ".join(parts[1:]).strip().lower()
                print(f"You are about to ENABLE strategy: {strategy_name}")
                confirm = input("Are you sure? (yes/no): ").strip().lower()
                if confirm in ["yes", "y"]:
                    print(f"Enabling strategy: {strategy_name} ...")
                    result = enable_strategy(strategy_name, True)
                    if result.get("success"):
                        key = result.get("strategy_key", strategy_name)
                        print(f"→ Strategy '{key}' enabled successfully.")
                        _log_strategy_toggle("enable", key)

                        cycle_now = input(
                            "Strategy enabled. Run one evaluation cycle now? (yes/no): "
                        ).strip().lower()
                        if cycle_now in ["yes", "y"]:
                            from src.cli_exec import handle_cycle
                            handle_cycle("cycle")
                        else:
                            print("→ Skipped cycle. You can run it later with: cycle")
                    else:
                        print(f"→ Failed: {result.get('error') or result}")
                else:
                    print("Cancelled. Strategy was not enabled.")

        elif user_input.startswith("disable "):
            from src.tools.ananta_api import enable_strategy
            parts = user_input.split()
            if len(parts) < 2:
                print("Usage: disable <strategy_name>")
                print("Example: disable hunter")
                print("Example: disable mean reversion")
            else:
                strategy_name = " ".join(parts[1:]).strip().lower()
                print(f"You are about to DISABLE strategy: {strategy_name}")
                confirm = input("Are you sure? (yes/no): ").strip().lower()
                if confirm in ["yes", "y"]:
                    print(f"Disabling strategy: {strategy_name} ...")
                    result = enable_strategy(strategy_name, False)
                    if result.get("success"):
                        key = result.get("strategy_key", strategy_name)
                        print(f"→ Strategy '{key}' disabled successfully.")
                        _log_strategy_toggle("disable", key)
                    else:
                        print(f"→ Failed: {result.get('error') or result}")
                else:
                    print("Cancelled. Strategy was not disabled.")

        elif user_input in ["monitor", "health", "check"]:
            from src.tools.ananta_api import get_strategy_status, get_open_paper_trades, get_portfolio
            from src.tools.market_tools import get_market_data

            print("\nANANTA AGENT MONITOR")
            print("=" * 55)

            try:
                market = get_market_data()
                regime = market.get("trend", "N/A")
                price = market.get("price", "N/A")
                change = market.get("change_24h", "N/A")
                print(f"Market Regime      : {regime}")
                print(f"BTC Price          : ${price}  ({change}% 24h)")
            except Exception:
                print("Market Regime      : Could not fetch")

            try:
                port = get_portfolio()
                if port.get("success") and port.get("data"):
                    data = port["data"]
                    equity = data.get("equity") or data.get("total_value") or data.get("balance")
                    slots = data.get("slots_used") or data.get("open_positions")
                    if equity is not None:
                        print(f"Portfolio Equity   : ${equity}")
                    if slots is not None:
                        print(f"Slots / Positions  : {slots}")
            except Exception:
                pass

            status_result = get_strategy_status()
            enabled = []
            if status_result.get("success"):
                for s in status_result.get("strategies", []):
                    if s.get("enabled"):
                        enabled.append(s.get("name", s.get("key")))
                print(f"Enabled Strategies : {len(enabled)}")
                if enabled:
                    for name in enabled:
                        print(f"  • {name}")
                else:
                    print("  • None")
            else:
                print("Enabled Strategies : Could not fetch")

            trades_result = get_open_paper_trades()
            open_count = 0
            if trades_result.get("success"):
                open_count = trades_result.get("count", 0)
                print(f"Open Paper Trades  : {open_count}")
            else:
                print("Open Paper Trades  : Could not fetch")

            print()
            health = "OK"
            if open_count >= 10 or len(enabled) >= 8:
                health = "OVERLOADED"
            elif open_count >= 7 or len(enabled) >= 5:
                health = "CAUTION"
            elif open_count == 0 and len(enabled) == 0:
                health = "IDLE"

            print(f"Health Status      : {health}")

            if open_count >= 10:
                print("⚠  Very high open trades. Strongly consider: cleanup")
            elif open_count >= 7:
                print("⚠  Portfolio is heavily loaded. Try: cleanup")
            elif open_count >= 4:
                print("Note: Moderate exposure. Monitor closely.")
            elif open_count == 0:
                print("Note: No open trades. Good time to look for setups.")
            else:
                print("Note: Exposure looks manageable.")

            if len(enabled) >= 5:
                print("Note: Many strategies are enabled. Watch for overlapping signals.")

            print("=" * 55)
            from src.phase4_cli import link_monitor_outcome
            link_monitor_outcome(open_count, len(enabled), health, get_portfolio)

        elif user_input in ["status", "strategies", "strategy status"]:
            from src.tools.ananta_api import get_strategy_status
            print("Fetching strategy status from Ananta...")
            result = get_strategy_status()
            if result.get("success"):
                strategies = result.get("strategies", [])
                print("\nSTRATEGY STATUS")
                print("=" * 55)
                if not strategies:
                    print("No strategies found.")
                else:
                    enabled_count = 0
                    for s in strategies:
                        key = s.get("key", "unknown")
                        name = s.get("name", key)
                        status = s.get("status_label", "Unknown")
                        enabled = s.get("enabled", False)
                        if enabled:
                            enabled_count += 1
                            mark = "●"
                        else:
                            mark = "○"
                        print(f"{mark} {name} ({key})  →  {status}")
                    print()
                    print(f"Total: {len(strategies)} strategies | Enabled: {enabled_count}")
            else:
                print(f"Failed to get status: {result.get('error') or result}")

        else:
            print("Agent: I didn't understand that. Type 'help' to see available commands.")

if __name__ == "__main__":
    interactive_mode()
