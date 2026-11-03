"""3 Nov 2026 (data audit step 6): the big-falls check sorts each unexplained fall by its evidence and never calls a fall true without a look."""
from india import fallcheck as fc


def test_ratios():
    assert fc.nearest_ratio(0.50)[0] == "1:2 split or 1:1 bonus"
    assert fc.nearest_ratio(0.101)[0] == "1:10 split"
    assert fc.nearest_ratio(0.37)[0] is None


def test_labels_follow_the_evidence():
    assert fc.classify(0.1, True, 12.0, True, True, False) == "known_action_not_applied"
    assert fc.classify(0.2, True, 5.0, False, False, False) == "likely_missed_action"        # a 1:5 ratio, stays down, five times the shares traded
    assert fc.classify(0.2, False, 5.0, False, False, False) == "no_evidence_found"          # bounced back: not a split
    assert fc.classify(0.43, True, 1.0, False, False, True) == "likely_demerger"
    assert fc.classify(0.37, True, 1.0, False, True, False) == "likely_missed_action"        # a filing names a bonus
    assert fc.classify(0.37, True, 1.0, False, False, False) == "no_evidence_found"
