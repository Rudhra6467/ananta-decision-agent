"""The self-check nudge is not added when the answer already told the item (India morning review, 10 Nov 2026: the nightly replay's
"Is everything running?" listed the worker Mac outage and then got it again as "One thing that isn't right")."""
from jarvis import selfcheck

ANSWER = ("Yes, sir, the India side is running. Three things are not right. On the crypto side, the worker Mac was down for 78 minutes "
          "and then 31 minutes, and the brain's decision count has read 0 on the last 3 nightly cards.")


def test_an_outage_the_answer_told_is_not_nudged_again():
    items = [{"what": "a part was down at 9 Nov 17:56 Toronto (the worker Mac: 78 min)"},
             {"what": "a part was down at 9 Nov 19:33 Toronto (the worker Mac: 31 min)"}]
    assert selfcheck.already_said(items, ANSWER)


def test_an_item_the_answer_did_not_tell_is_still_nudged():
    items = [{"what": "the India Kite sign-in failed at 06:05 IST"}]
    assert not selfcheck.already_said(items, ANSWER)
    assert not selfcheck.already_said([{"what": "a part was down at 9 Nov 17:56 Toronto (the brain: 40 min)"}], "All is well, sir.")
