"""#140 (Madhav's yes, 3 Nov 2026): the GAVE_BACK finding counts only trades the protect rule could act on (entered from 24 Oct, best
price at +1.5 R or more, closed at a loss), so it no longer says the rule failed where it never applied."""
import json
import sqlite3
import types

from jarvis.service import reconstruct as X

T = X.PROTECT_SINCE + 86400


def _j(rows):
    db = sqlite3.connect(":memory:")
    db.execute("CREATE TABLE trade_reviews (id TEXT, t INTEGER, book TEXT, watch TEXT, coin TEXT, entry_t INTEGER, exit_t INTEGER, entry REAL, exit REAL, "
               "net_usd REAL, best_pct REAL, worst_pct REAL, after_pct REAL, tags TEXT, text TEXT, plan TEXT)")
    db.execute("CREATE TABLE evidence_trades (id TEXT, stop REAL, detail TEXT, entry_t INTEGER)")
    for k, (entry_t, entry, stop0, best, net) in enumerate(rows):
        db.execute("INSERT INTO trade_reviews (id, t, book, watch, entry, net_usd, best_pct, tags) VALUES (?,?,?,?,?,?,?,?)",
                   (f"ev:{k}", T + 5 * 86400, "evidence", "RBD-UB", entry, net, best, json.dumps(["GAVE_BACK"])))
        db.execute("INSERT INTO evidence_trades VALUES (?,?,?,?)", (str(k), stop0, json.dumps({"stop0": stop0}), entry_t))
    return types.SimpleNamespace(db=db)


def test_counts_only_trades_past_the_break_even_step():
    j = _j([(T, 100.0, 90.0, 16.0, -5.0),          # +1.6 R, lost: counts
            (T, 100.0, 90.0, 8.0, -5.0),           # +0.8 R (up 8%, stop 10% away): the rule never acted, not counted
            (T, 100.0, 96.0, 6.4, -2.0),           # +1.6 R on a tight stop: counts
            (T - 3 * 86400, 100.0, 90.0, 20.0, -5.0),  # entered before the rule: not counted
            (T, 100.0, 90.0, 20.0, 3.0)])          # ended up: not a loss
    assert X.gave_back_past_protect(j, T) == {"RBD-UB": 2}


def test_no_finding_below_three():
    j = _j([(T, 100.0, 90.0, 16.0, -5.0)] * 2)
    assert X.gave_back_past_protect(j, T) == {"RBD-UB": 2}
    assert not [f for f in X.findings(j, T + 6 * 86400, {}, {}, {}, {}) if f["kind"] == "GAVE_BACK"]
