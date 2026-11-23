"""23 Nov 2026 (the audit re-check): the practice book's trial line reads the book, not a sentence written on 29 Oct."""
from india import trials


def _t(status, reason, ret, bars=21):
    return {"book": "exec", "policy": trials.__dict__.get("REF", "hold_20d"), "status": status, "exit_reason": reason, "net_ret": ret,
            "entry_adj": 100, "last_close_adj": 100 * (1 + ret), "campaign": "BRK", "bars_seen": bars}


def test_the_line_counts_stops_and_time_exits(monkeypatch):
    from india import bookstats
    st = {"trades": {"a": _t("closed", "stop", -0.05), "b": _t("closed", "time", 0.04), "c": _t("open", None, 0.02)}}
    for t in st["trades"].values():
        t["policy"] = bookstats.REF_POLICY
    w = trials.practice_words(st)
    assert "2 closed so far (1 by stop-loss, 1 by time or target): 1 won" in w and "1 still open, 1 of them up" in w
    assert "no trade has reached its hold yet" not in w


def test_an_empty_book():
    assert trials.practice_words({}) == "no trade has closed yet"
