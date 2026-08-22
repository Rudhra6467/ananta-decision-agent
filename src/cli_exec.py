"""CLI helpers for real Ananta paper execution (buy/sell/cycle/cleanup)."""


def _book_snapshot():
    """Best-effort enabled/equity snapshot for ledgers. Fail soft."""
    enabled_names, enabled_count, equity, open_positions = [], 0, None, None
    try:
        from src.tools.ananta_api import get_strategy_status, get_portfolio

        st = get_strategy_status()
        if st.get("success"):
            enabled_names = [
                s.get("name") or s.get("key")
                for s in st.get("strategies", [])
                if s.get("enabled")
            ]
            enabled_count = len(enabled_names)
        port = get_portfolio()
        if port.get("success") and port.get("data"):
            data = port["data"]
            equity = data.get("equity") or data.get("total_value") or data.get("balance")
            open_positions = data.get("slots_used") or data.get("open_positions")
    except Exception:
        pass
    return enabled_names, enabled_count, equity, open_positions


def _log_manual_order(side: str, symbol: str, result: dict, extra: dict = None):
    """Write a decision-memory record for a manual paper order + cycle ledger TAKE."""
    try:
        from src.tools.decision_log import save_decision
        from src.tools.cycle_log import (
            get_last_cycle_id,
            start_cycle,
            log_decision,
            log_outcome_link,
        )

        trade = (result.get("data") or {}).get("trade") or {}
        names, count, equity, pos = _book_snapshot()
        cycle_id = get_last_cycle_id()
        if not cycle_id:
            cycle_id = start_cycle(
                symbol=trade.get("symbol") or symbol,
                price=trade.get("price"),
                equity=equity,
                open_positions=pos,
                enabled_strategies=names,
                enabled_count=count,
                notes="manual_paper_order",
            )
        payload = {
            "market": "crypto",
            "symbol": trade.get("symbol") or symbol,
            "price": trade.get("price"),
            "strategy": "manual",
            "strategy_key": "manual",
            "confidence": 0,
            "style": "Manual",
            "reason": f"Manual paper {side} via Agent CLI",
            "entry_idea": f"{side} {symbol}",
            "user_selected": f"manual_{side.lower()}",
            "user_confirmed": True,
            "user_enabled_strategy": False,
            "user_override": False,
            "status": "filled" if result.get("success") else "failed",
            "expected_outcome": "manual_order",
            "notes": f"trade_id={trade.get('id')} notional={trade.get('notional')} qty={trade.get('quantity')}",
            "action": "TAKE",
            "cycle_id": cycle_id,
            "portfolio_equity": equity,
            "open_positions": pos or 0,
        }
        if extra:
            payload.update(extra)
        save_decision(payload)
        log_decision(
            cycle_id,
            action="TAKE",
            strategy="manual",
            strategy_key="manual",
            reason=f"Manual paper {side} {symbol}",
            user_confirmed=True,
            status=payload["status"],
            extra={
                "side": side,
                "symbol": trade.get("symbol") or symbol,
                "trade_id": trade.get("id"),
                "notional": trade.get("notional"),
            },
        )
        log_outcome_link(
            cycle_id,
            equity=equity,
            open_positions=pos,
            note=f"manual {side} {symbol}",
        )
        print("→ Logged to decision memory.")
        print(f"→ Linked to cycle {cycle_id}")
    except Exception as e:
        print(f"→ (memory log skipped: {e})")


def handle_buy(user_input: str) -> bool:
    if not user_input.startswith("buy "):
        return False
    from src.tools.ananta_api import place_manual_paper_order
    parts = user_input.split()
    if len(parts) < 3:
        print("Usage: buy <symbol> <usd_amount>")
        print("Example: buy BTC 25")
        return True
    symbol = parts[1].upper()
    try:
        usd = float(parts[2])
    except Exception:
        print("USD amount must be a number")
        return True
    print(f"You are about to PAPER BUY ${usd} of {symbol}")
    confirm = input("Confirm real paper order on Ananta? (yes/no): ").strip().lower()
    if confirm not in ["yes", "y"]:
        print("Cancelled.")
        return True
    result = place_manual_paper_order(symbol=symbol, side="BUY", notional_usd=usd)
    if result.get("success"):
        trade = (result.get("data") or {}).get("trade") or {}
        print("→ Paper BUY filled on Ananta.")
        print(f"  Symbol   : {trade.get('symbol', symbol)}")
        print(f"  Qty      : {trade.get('quantity')}")
        print(f"  Price    : {trade.get('price')}")
        print(f"  Notional : {trade.get('notional')}")
        print(f"  Trade id : {trade.get('id')}")
        _log_manual_order("BUY", symbol, result, {"capital": usd})
    else:
        print(f"→ Failed: {result.get('error') or result}")
    return True


def handle_sell(user_input: str) -> bool:
    if not user_input.startswith("sell "):
        return False
    from src.tools.ananta_api import place_manual_paper_order
    parts = user_input.split()
    if len(parts) < 3:
        print("Usage: sell <symbol> <fraction>")
        print("Example: sell BTC 1.0")
        return True
    symbol = parts[1].upper()
    try:
        frac = float(parts[2])
    except Exception:
        print("Fraction must be a number between 0 and 1")
        return True
    print(f"You are about to PAPER SELL fraction={frac} of {symbol}")
    confirm = input("Confirm real paper order on Ananta? (yes/no): ").strip().lower()
    if confirm not in ["yes", "y"]:
        print("Cancelled.")
        return True
    result = place_manual_paper_order(symbol=symbol, side="SELL", fraction=frac)
    if result.get("success"):
        print("→ Paper SELL submitted on Ananta.")
        print(f"  Response: {str(result.get('data'))[:300]}")
        _log_manual_order("SELL", symbol, result, {"notes": f"fraction={frac}"})
    else:
        print(f"→ Failed: {result.get('error') or result}")
    return True


def handle_cycle(user_input: str) -> bool:
    if user_input != "cycle" and not user_input.startswith("cycle "):
        return False
    from src.tools.ananta_api import run_evaluation_cycle
    parts = user_input.split()
    symbol = parts[1].upper() if len(parts) >= 2 else None
    print("Running one Ananta evaluation cycle" + (f" for {symbol}" if symbol else "") + " ...")
    result = run_evaluation_cycle(symbol=symbol)
    if result.get("success"):
        data = result.get("data") or {}
        print("→ Cycle completed.")
        print(f"  ran_at : {data.get('ran_at')}")
        results = data.get("results") or []
        print(f"  symbols processed: {len(results)}")
        for item in results[:5]:
            sym = item.get("symbol")
            macro = item.get("macro") or {}
            print(f"  • {sym}: bias={macro.get('bias')} conf={macro.get('confidence')} | {str(macro.get('reason', ''))[:80]}")
        if len(results) > 5:
            print(f"  ... and {len(results) - 5} more")
        try:
            from src.tools.cycle_log import start_cycle, log_decision, log_opportunities, log_outcome_link

            names, count, equity, pos = _book_snapshot()
            cid = start_cycle(
                regime=None,
                symbol=symbol or "MULTI",
                equity=equity,
                open_positions=pos,
                enabled_strategies=names,
                enabled_count=count,
                load_level="OK" if (pos or 0) < 7 else "CAUTION",
                notes="ananta_eval_cycle",
            )
            log_decision(
                cid,
                action="CYCLE",
                reason=f"Ananta evaluation ran_at={data.get('ran_at')} symbols={len(results)}",
                status="completed",
                extra={"ananta_ran_at": data.get("ran_at"), "symbol_count": len(results)},
            )
            cands = []
            for item in results[:12]:
                macro = item.get("macro") or {}
                cands.append({
                    "name": item.get("symbol"),
                    "confidence": macro.get("confidence"),
                    "reason": str(macro.get("reason", ""))[:160],
                    "style": macro.get("bias"),
                })
            log_opportunities(
                cid,
                cands,
                chosen_action="WAIT",
                chosen_strategy=None,
                regime=None,
            )
            log_outcome_link(
                cid,
                equity=equity,
                open_positions=pos,
                note="after ananta evaluation cycle",
            )
            print(f"  cycle_id: {cid}")
            print("  → Written to cycle + opportunity ledgers.")
            try:
                from src.tools.decision_log import save_decision

                reasons = [
                    str((item.get("macro") or {}).get("reason") or "")
                    for item in results
                ]
                no_setup = bool(results) and all(
                    "no qualifying setup" in r.lower() or not r.strip()
                    for r in reasons
                )
                wait_reason = (
                    f"Ananta cycle: no qualifying setup on {len(results)} symbols"
                    if no_setup
                    else f"Ananta cycle completed on {len(results)} symbols; no Agent TAKE"
                )
                save_decision({
                    "market": "crypto",
                    "symbol": symbol or "MULTI",
                    "strategy": "WAIT",
                    "strategy_key": "hunter" if no_setup else None,
                    "action": "WAIT",
                    "status": "skipped",
                    "reason": wait_reason,
                    "notes": wait_reason,
                    "top_recommendation": "WAIT",
                    "user_confirmed": True,
                    "user_enabled_strategy": False,
                    "cycle_id": cid,
                    "portfolio_equity": equity,
                    "open_positions": pos or 0,
                    "expected_outcome": "ananta_cycle_wait",
                })
                print("  → Markable WAIT added to history (use: history then mark 1 ...)")
            except Exception as e:
                print(f"  (decision memory skipped: {e})")
        except Exception as e:
            print(f"  (cycle ledger skipped: {e})")
    else:
        print(f"→ Failed: {result.get('error') or result}")
    return True


def _base_symbol(sym: str) -> str:
    s = (sym or "").upper().replace(" ", "")
    if "/" in s:
        s = s.split("/")[0]
    return s


def _aggregate_positions(trades: list) -> list:
    """
    Aggregate filled paper trades by base symbol + side.
    Returns list of dicts sorted by cleanup priority (highest first).
    """
    buckets = {}
    for t in trades:
        base = _base_symbol(t.get("symbol"))
        side = str(t.get("side", "")).upper()
        if not base or side not in ("BUY", "SELL"):
            continue
        key = (base, side)
        b = buckets.setdefault(
            key,
            {
                "symbol": base,
                "side": side,
                "quantity": 0.0,
                "notional": 0.0,
                "fills": 0,
                "avg_price": 0.0,
                "_px_sum": 0.0,
            },
        )
        qty = float(t.get("quantity") or 0)
        px = float(t.get("price") or 0)
        notion = t.get("notional")
        try:
            notion = float(notion) if notion is not None else abs(qty * px)
        except Exception:
            notion = abs(qty * px)
        b["quantity"] += qty
        b["notional"] += abs(notion)
        b["fills"] += 1
        b["_px_sum"] += px * qty if qty else px

    positions = []
    for b in buckets.values():
        if b["quantity"]:
            b["avg_price"] = b["_px_sum"] / b["quantity"]
        else:
            b["avg_price"] = 0.0
        del b["_px_sum"]

        # Priority score: prefer closing duplicates, dust, large shorts
        score = 0.0
        if b["fills"] >= 2:
            score += 40 + 10 * (b["fills"] - 1)  # duplicates
        if b["symbol"] == "BTC" and b["notional"] < 50:
            score += 35  # dust BTC lots
        if b["side"] == "SELL" and b["notional"] > 200:
            score += 25  # large short exposure
        if b["notional"] < 30:
            score += 15  # tiny residual
        if b["symbol"] in ("ARB", "AAVE") and b["fills"] >= 2:
            score += 20
        b["priority"] = score
        b["suggest_fraction"] = 1.0 if (b["fills"] >= 2 or b["notional"] < 50) else 0.5
        positions.append(b)

    positions.sort(key=lambda x: (x["priority"], x["notional"]), reverse=True)
    return positions


def handle_cleanup(user_input: str) -> bool:
    """
    Guided position cleanup:
      cleanup           → list + interactive reduce
      cleanup list      → list only
    """
    if user_input not in ("cleanup", "clean", "cleanup list", "clean list"):
        return False

    from src.tools.ananta_api import get_paper_trades, place_manual_paper_order

    list_only = user_input.endswith("list")

    print("\nPOSITION CLEANUP ASSISTANT")
    print("=" * 60)
    print("Fetching paper trades from Ananta...")

    result = get_paper_trades(limit=100)
    if not result.get("success"):
        print(f"→ Failed to fetch trades: {result.get('message') or result}")
        return True

    data = result.get("data") or {}
    items = data.get("items", []) if isinstance(data, dict) else []
    paper_fills = [
        t for t in items
        if str(t.get("status", "")).upper() == "FILLED"
        and str(t.get("mode", "")).upper() == "PAPER"
    ]

    if not paper_fills:
        print("No filled paper trades found.")
        print("=" * 60)
        return True

    positions = _aggregate_positions(paper_fills)
    if not positions:
        print("No aggregatable positions found.")
        print("=" * 60)
        return True

    print(f"Aggregated positions: {len(positions)}  (from {len(paper_fills)} paper fills)")
    print("-" * 60)
    print(f"{'#':<3} {'Symbol':<8} {'Side':<6} {'Fills':<6} {'Qty':>12} {'Notional~$':>12} {'Priority'}")
    print("-" * 60)
    for i, p in enumerate(positions, 1):
        flag = "← suggest" if p["priority"] >= 30 else ""
        print(
            f"{i:<3} {p['symbol']:<8} {p['side']:<6} {p['fills']:<6} "
            f"{p['quantity']:>12.4f} {p['notional']:>12.2f} {p['priority']:>6.0f} {flag}"
        )
    print("-" * 60)
    print("Priority = duplicates / dust / large shorts (higher = better to reduce first)")
    print()

    suggested = [p for p in positions if p["priority"] >= 30][:5]
    if suggested:
        print("Suggested reductions:")
        for p in suggested:
            frac = p["suggest_fraction"]
            # SELL closes a long (BUY side aggregate); BUY covers a short (SELL side aggregate)
            if p["side"] == "BUY":
                action = f"sell {p['symbol']} {frac}"
                meaning = "close long"
            else:
                action = f"buy {p['symbol']} <usd>"
                meaning = "cover short (use buy with $ size)"
            print(f"  • {p['symbol']} {p['side']} ×{p['fills']} fills → {action}  ({meaning})")
        print()

    if list_only:
        print("List only. To reduce interactively: cleanup")
        print("Or direct: sell ARB 1.0   |   sell BTC 1.0")
        print("=" * 60)
        return True

    print("Options:")
    print("  • Enter a number to reduce that LONG (BUY side) with a SELL fraction")
    print("  • For SHORTS (SELL side): cover via  buy <symbol> <usd>")
    print("  • 0 = exit cleanup")
    print()

    choice = input("Select position # to reduce (longs only via sell): ").strip()
    try:
        num = int(choice)
    except Exception:
        print("Cancelled.")
        return True

    if num == 0 or num < 1 or num > len(positions):
        print("Exited cleanup.")
        return True

    pos = positions[num - 1]
    if pos["side"] != "BUY":
        print(f"→ {pos['symbol']} is a SHORT aggregate (side=SELL).")
        print("  Covering shorts needs BUY size in USD, e.g.:")
        approx = max(25.0, min(500.0, pos["notional"] * 0.5))
        print(f"    buy {pos['symbol']} {approx:.0f}")
        print("  Run that command from the main prompt after cleanup.")
        return True

    default_frac = pos["suggest_fraction"]
    frac_raw = input(f"Fraction to SELL of {pos['symbol']} [default {default_frac}]: ").strip()
    if not frac_raw:
        frac = default_frac
    else:
        try:
            frac = float(frac_raw)
        except Exception:
            print("Invalid fraction.")
            return True

    if frac <= 0 or frac > 1:
        print("Fraction must be between 0 and 1.")
        return True

    print(f"\nYou are about to PAPER SELL fraction={frac} of {pos['symbol']}")
    print(f"  Approx notional in aggregate: ~${pos['notional']:.2f} across {pos['fills']} fills")
    confirm = input("Confirm real paper order on Ananta? (yes/no): ").strip().lower()
    if confirm not in ["yes", "y"]:
        print("Cancelled.")
        return True

    result = place_manual_paper_order(symbol=pos["symbol"], side="SELL", fraction=frac)
    if result.get("success"):
        print("→ Paper SELL submitted on Ananta.")
        print(f"  Response: {str(result.get('data'))[:300]}")
        _log_manual_order(
            "SELL",
            pos["symbol"],
            result,
            {"notes": f"cleanup fraction={frac} fills={pos['fills']} notional~{pos['notional']:.2f}"},
        )
        print("Tip: run  cleanup list  or  monitor  to see updated exposure.")
    else:
        print(f"→ Failed: {result.get('error') or result}")
        print("  If Ananta rejects, try cockpit close or: sell SYMBOL 1.0")

    print("=" * 60)
    return True
