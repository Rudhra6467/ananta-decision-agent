"""Live path (flag 239, design: "Where it is built"): while LIVE_ORDERS is off, no code path reaches Kite's order or GTT endpoints, nor any
POST, PUT or DELETE other than the margin calculator; the only network call is orders._http, reached only through orders.send after the
gate; and nothing running imports the live path. Proven two ways: a scan of the code, and every public function called with a fake Kite."""
import ast
import datetime as dt
import inspect
from pathlib import Path

import pytest

from india import leakcheck, orders
from india.live import reconcile, rules, survival, switches
from india.live.rules import Plan
from live_fakes import FakeKite

ROOT = Path(__file__).resolve().parents[1]
LIVE_FILES = [ROOT / "india" / "orders.py", *sorted((ROOT / "india" / "live").glob("*.py"))]
NET_ATTRS = {"request", "post", "put", "delete", "patch", "urlopen", "send", "connect"}


def _calls(tree):
    return [n for n in ast.walk(tree) if isinstance(n, ast.Call)]


def test_no_network_library_in_the_live_path():
    for f in LIVE_FILES:
        tree = ast.parse(f.read_text())
        for n in ast.walk(tree):
            if isinstance(n, (ast.Import, ast.ImportFrom)):
                names = [a.name for a in n.names] + [getattr(n, "module", "") or ""]
                assert not any(x.split(".")[0] in ("requests", "urllib", "http", "socket", "httpx", "aiohttp") for x in names), f"{f.name}: {names}"


def test_the_one_network_call_is_in_http_behind_the_gate():
    found = []
    for f in LIVE_FILES:
        tree = ast.parse(f.read_text())
        funcs = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
        for c in _calls(tree):
            if isinstance(c.func, ast.Attribute) and c.func.attr in NET_ATTRS - {"send"}:
                owner = next((fn.name for fn in funcs if fn.lineno <= c.lineno <= fn.end_lineno), None)
                found.append((f.name, owner, ast.unparse(c.func)))
    assert found == [("orders.py", "_http", "kite.s.request")]
    tree = ast.parse((ROOT / "india" / "orders.py").read_text())
    fns = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    callers = {fn.name for fn in fns.values() for c in _calls(fn) if isinstance(c.func, ast.Name) and c.func.id == "_http"}
    assert callers == {"send"}
    first = fns["_http"].body[1] if isinstance(fns["_http"].body[0], ast.Expr) and isinstance(fns["_http"].body[0].value, ast.Constant) else fns["_http"].body[0]
    assert ast.unparse(first) == "switches.require_send()"
    gate = [c.lineno for c in _calls(fns["send"]) if ast.unparse(c.func) == "switches.require_send"]
    http = [c.lineno for c in _calls(fns["send"]) if ast.unparse(c.func) == "_http"]
    assert gate and http and min(gate) < min(http)


BN = Plan("2026-12-07", "BANKNIFTY", "D0", "NEXTOPEN", "BANKNIFTY26DEC63400CE", 30, 1000.0)
ST = Plan("2026-12-07", "BANKNIFTY", "D1", "ATRSTOP", "BANKNIFTY26DEC63400CE", 30, 1000.0,
          extra={"delta": 0.5, "index_entry": 63400.0, "index_stop": 63000.0})
DAYS = [{"date": "2026-12-01", "start": 100.0, "low": 90.0, "end": 95.0}]
SAMPLES = {
    "orders.limit_price": lambda k, p: orders.limit_price("BUY", 100.0),
    "orders.entry_request": lambda k, p: orders.entry_request(BN),
    "orders.exit_request": lambda k, p: orders.exit_request(BN, 1000.0, next_open=True),
    "orders.gtt_request": lambda k, p: orders.gtt_request(BN, 800.0, 1000.0),
    "orders.cancel_request": lambda k, p: orders.cancel_request("O1"),
    "orders.gtt_delete_request": lambda k, p: orders.gtt_delete_request(901),
    "orders.validate": lambda k, p: orders.validate(orders.entry_request(BN), BN),
    "orders.ledger_path": lambda k, p: orders.ledger_path(),
    "orders.read_ledger": lambda k, p: orders.read_ledger(),
    "orders.note": lambda k, p: orders.note(BN, "test", "test"),
    "orders.send": lambda k, p: pytest.raises(switches.OrdersOff, orders.send, k, orders.entry_request(BN), BN, "test"),
    "orders.amo_window_open": lambda k, p: orders.amo_window_open(dt.time(16, 0)),
    "orders.backstop_trigger": lambda k, p: orders.backstop_trigger(1000.0, 0.5, 63400.0, 63000.0),
    "orders.index_stop_hit": lambda k, p: orders.index_stop_hit("CE", 1.0, 2.0),
    "orders.exit_route": lambda k, p: orders.exit_route(ST),
    "orders.alert_step": lambda k, p: orders.alert_step(BN),
    "orders.enter": lambda k, p: orders.enter(k, BN, []),
    "orders.cancel_if_unfilled": lambda k, p: orders.cancel_if_unfilled(k, BN, "O1", 0.0, False, now=100.0),
    "orders.after_fill": lambda k, p: orders.after_fill(k, ST, 1000.0),
    "orders.exit_now": lambda k, p: orders.exit_now(k, BN, 1000.0, "test"),
    "orders.exit_next_open": lambda k, p: orders.exit_next_open(k, BN, 1000.0, dt.time(16, 0)),
    "orders.morning_check": lambda k, p: orders.morning_check(k, BN, "A1", False, dt.time(9, 21), new_ref=990.0),
    "rules.plan_from_decision": lambda k, p: rules.plan_from_decision({"kind": "decision", "choice": {}}),
    "rules.held_overnight": lambda k, p: rules.held_overnight(BN, [BN]),
    "rules.committed": lambda k, p: rules.committed(BN, [BN]),
    "rules.verdict": lambda k, p: rules.verdict(BN, []),
    "rules.walk": lambda k, p: rules.walk([BN, ST]),
    "rules.margin_order": lambda k, p: rules.margin_order(BN),
    "rules.margin_check": lambda k, p: rules.margin_check(k, BN, []),
    "reconcile.differences": lambda k, p: reconcile.differences([], [], {}, []),
    "reconcile.run": lambda k, p: reconcile.run(k, []),
    "survival.check": lambda k, p: survival.check(DAYS),
    "survival.actions": lambda k, p: survival.actions(survival.check(DAYS)),
    "survival.read_series": lambda k, p: survival.read_series(p),
    "survival.record": lambda k, p: survival.record(p),
    "switches.live_dir": lambda k, p: switches.live_dir(),
    "switches.kill_state": lambda k, p: switches.kill_state(),
    "switches.kill_on": lambda k, p: switches.kill_on(),
    "switches.turn_on": lambda k, p: (switches.turn_on("test"), switches.turn_off(by="Madhav")),
    "switches.turn_off": lambda k, p: switches.turn_off(by="Madhav"),
    "switches.note_failure": lambda k, p: switches.note_failure("test"),
    "switches.note_success": lambda k, p: switches.note_success(),
    "switches.may_send": lambda k, p: switches.may_send(),
    "switches.require_send": lambda k, p: pytest.raises(switches.OrdersOff, switches.require_send),
}


def _public(mod, name):
    return {f"{name}.{n}" for n, f in inspect.getmembers(mod, inspect.isfunction) if not n.startswith("_") and f.__module__ == mod.__name__}


def test_every_public_function_called_with_the_switch_off_sends_nothing(tmp_path, monkeypatch):
    monkeypatch.setenv("INDIA_LIVE_DIR", str(tmp_path / "live_india"))
    switches.turn_off(by="Madhav")                     # the worst case: the kill switch off; only LIVE_ORDERS (False) stands
    assert switches.LIVE_ORDERS is False
    public = set()
    for mod, name in ((orders, "orders"), (rules, "rules"), (reconcile, "reconcile"), (survival, "survival"), (switches, "switches")):
        public |= _public(mod, name)
    assert public == set(SAMPLES), f"a public function without a sample here: {sorted(public ^ set(SAMPLES))}"
    series = tmp_path / "book.jsonl"
    series.write_text('{"date": "2026-12-01", "start": 100, "low": 90, "end": 95}\n')
    k = FakeKite()
    for key in sorted(SAMPLES):
        SAMPLES[key](k, series)
    assert k.sent == [], f"reached an order or GTT endpoint with the switch off: {k.sent}"
    assert all(p in ("/trades", "/portfolio/positions", "/gtt/triggers", "/orders") for p in k.gets)


def test_nothing_running_imports_the_live_path():
    bad = []
    for f in ROOT.rglob("*.py"):
        rel = f.relative_to(ROOT).parts
        if rel[0] in ("tests", ".venv", "venv", "node_modules") or "site-packages" in rel or f in LIVE_FILES:
            continue
        src = f.read_text(errors="ignore")
        if "india.orders" in src or "india.live" in src or "from india import orders" in src or "import orders" in src:
            bad.append(str(f.relative_to(ROOT)))
    assert bad == []


def test_kite_client_stays_get_plus_the_calculator():
    assert leakcheck.check_kite_calls()[0]
    assert "orders import" not in (ROOT / "india" / "kite.py").read_text() and "india.live" not in (ROOT / "india" / "kite.py").read_text()
