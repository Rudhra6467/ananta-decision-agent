"""5 Nov 2026: a test question (source="eval": outsider rounds, the Sunday exam, acceptance) reads everything and saves nothing.

The 1 Nov outsider round's "buy me some solana now" had left a real $100 Solana card in Madhav's approvals, worded
"Madhav asked to buy Solana now", and the crypto Ask offered it to him for four days.
"""
from jarvis.service import ask
from tests.test_ask_ananta import _jarvis


def _count(j, table: str) -> int:
    try:
        return j.db.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
    except Exception:  # noqa: BLE001 - a table that was never created holds nothing
        return 0


def test_test_questions_leave_nothing_behind():
    j, ex = _jarvis()
    coin = next(iter(ex.st["engines"]))
    tables = ("pending_actions", "owner_requests", "account_watches")
    before = {t: _count(j, t) for t in tables}
    L = ask.Lookups(j, "evalthread", test=True)
    r = L.call("propose_paper_order", {"side": "buy", "coin": coin, "usd": 100})
    assert r.get("test_run") and r["prepared"]["status"] == "TEST", r
    assert L.created and L.created[0]["test"] and "$100" in L.created[0]["summary"]
    for name, args in [("propose_alert", {"kind": "price_above", "coin": coin, "value": 1.0}),
                       ("log_request", {"kind": "data", "text": "a test note"}),
                       ("remember", {"text": "a test memory"}),
                       ("propose_setting", {"key": "daily_budget_usd", "value": "3"}),
                       ("watch", {"coins": [coin]}),
                       ("start_research", {"kind": "reconstruction"})]:
        out = L.call(name, args)
        assert out.get("test_run"), (name, out)
    assert {t: _count(j, t) for t in tables} == before


def test_real_questions_still_prepare_cards():
    j, ex = _jarvis()
    coin = next(iter(ex.st["engines"]))
    L = ask.Lookups(j, "realthread")
    r = L.call("propose_paper_order", {"side": "buy", "coin": coin, "usd": 100})
    assert r["prepared"]["status"] == "PENDING", r
    assert j.db.execute("SELECT count(*) FROM pending_actions WHERE status='PENDING'").fetchone()[0] == 1


def test_every_ask_path_passes_the_test_flag():
    src = open(ask.__file__).read()
    assert src.count("Lookups(self.j, thread, _ht,") == src.count('test=source == "eval")')
