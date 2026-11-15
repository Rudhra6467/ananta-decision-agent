"""15 Nov 2026, audit repair 6 (open-list flag 122), G-48: ten coin-days sat in the missed-moves table twice with different labels (AVAX on
9 Nov: caught in the ten lab coins, seen in the wide list). Counted once, a coin-day takes the best label any list gave it. The rows stay one
per list: pre-registered review #38 reads each list's rows."""
import time

from tests.test_universe_live import J


def test_a_coin_day_counted_once_takes_its_best_label(tmp_path):
    from jarvis.service import missed

    j = J(tmp_path)
    missed._table(j)
    day = time.strftime("%Y-%m-%d", time.gmtime(j.now() - 86400))
    base = {"day": day, "coin": "AVAX", "move_pct": 7.0, "move_atr": 1.4, "kind": "breakout", "pattern": "breakout|no zone|?", "miss_class": None}
    missed._insert(j, {**base, "id": f"{day}:AVAX", "tier": "LIVE10", "label": "SEEN", "miss_class": "DECISION"})
    missed._insert(j, {**base, "id": f"{day}:UNIV:AVAX", "tier": "UNIV", "label": "CAUGHT", "caught_allowed": 1})
    missed._insert(j, {**base, "id": f"{day}:UNIV:SOL", "coin": "SOL", "tier": "UNIV", "label": "MISSED", "miss_class": "DETECTION"})
    j.db.commit()
    r = missed.recent(j, 7)
    assert r["catches"]["all_tiers"]["CAUGHT_TRADE_OK"] == 1                  # it was 0: the lab list's "seen" came first
    assert r["catches"]["lists_disagree"] == {f"{day} AVAX": {"LIVE10": "SEEN", "UNIV": "CAUGHT"}}
    assert r["classes"]["DECISION"] == 0 and r["classes"]["DETECTION"] == 1   # AVAX was caught, so it is no decision miss
    assert r["counts"]["SEEN"] == 1 and r["universe"]["counts"]["CAUGHT"] == 1  # each list keeps its own row and its own count
    assert j.db.execute("SELECT COUNT(*) FROM missed_moves").fetchone()[0] == 3
