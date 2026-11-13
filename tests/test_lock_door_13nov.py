"""13 Nov 2026 (Madhav: "these locks are there for just the proof ... when we are working on the lock itself, the lock should not stop
it"; his "Yes to all" of 07:06, "let's solve this issue for once" of 07:59, and "simplest method possible" of 10:01). A change to a
pinned thing goes through one of two doors (scripts/lock_door.py; docs/knowledge/LOCKS.md): a repair that changes no decision, or a
change of decision on his own yes. These checks keep the doors and the lock file in step, so a later change cannot leave the lock
in a bad state."""
import copy
import importlib.util
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("lock_door", ROOT / "scripts" / "lock_door.py")
D = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(D)

PATH, MODULE = D.find_lock(ROOT)
LIVE = json.loads(PATH.read_text())
NOW = D.current_hashes(MODULE, ROOT)
PIN = sorted(LIVE["pins"])[0]
WHAT = "the words of the dial's line were corrected"


def _passes_the_lock_test(lock: dict, now: dict) -> None:
    """What the lock's own test asks of every pin (the stricter of the two lock tests)."""
    for name, pin in lock["pins"].items():
        for h in pin["history"]:
            assert h["approved_by"].startswith("Madhav") and len(h["note"]) >= 20 and re.fullmatch(r"\d{4}-\d{2}-\d{2}", h["date"])
        new = [h for h in pin["history"] if h.get("door")]
        assert all(h["approved_by"] == "Madhav (in chat)" and '"' in h["note"] for h in new)
        assert pin["sha256"] == pin["history"][-1]["sha256"] == now[name]


def _changed(to: str = "f"):
    lock, now = copy.deepcopy(LIVE), dict(NOW)
    now[PIN] = to * 64                                                  # as if a pinned thing had just been edited
    return lock, now


def test_the_live_lock_file_carries_the_repair_door_and_every_pin_has_an_end_day():
    assert LIVE["repair_door"]["since"] == "2026-11-13" and '"Yes to all"' in LIVE["repair_door"]["approved"]
    assert [r["pin"] for r in D.status(LIVE, NOW, "2026-11-13") if not r["ends"]] == []
    assert all(r["state"] == "as pinned" for r in D.status(LIVE, NOW, "2026-11-13"))   # the tool reads the same hashes as the lock test
    book = ROOT / "docs" / "knowledge" / "LOCKS.md"
    if book.exists():                                                   # the lock book sits in the app's checkout
        text = book.read_text()
        assert "## The repair door" in text and "## Strict locks" in text and "## Test locks" in text and PATH.name in text
        assert "scripts/lock_door.py" in text and "cannot tell whether a change alters a decision" in text


def test_no_door_opens_when_nothing_changed_or_for_a_thing_that_is_not_a_pin():
    with pytest.raises(D.Refused, match="nothing in .* changed"):
        D.open_door(copy.deepcopy(LIVE), dict(NOW), PIN, "repair", WHAT)
    lock, now = _changed()
    with pytest.raises(D.Refused, match="no pin named"):                # a strict lock has no door
        D.open_door(lock, now, "real_money", "repair", "anything at all, said in a full sentence")
    with pytest.raises(D.Refused, match="the doors are repair and change"):
        D.open_door(lock, now, PIN, "side_door", "anything at all, said in a full sentence")
    with pytest.raises(D.Refused, match="full sentence"):
        D.open_door(lock, now, PIN, "repair", "fixed it")
    assert lock == LIVE                                                 # a refusal leaves the lock as it was


def test_a_repair_is_recorded_at_once_under_the_standing_yes():
    lock, now = _changed()
    e = D.open_door(lock, now, PIN, "repair", WHAT, commit="abc1234", today="2026-11-14")
    assert e["door"] == "repair" and e["note"].startswith("Repair, no rule change: ") and '"Yes to all"' in e["note"]
    assert e["commit"] == "abc1234" and e["date"] == "2026-11-14"
    assert lock["pins"][PIN]["sha256"] == now[PIN] and len(lock["pins"][PIN]["history"]) == len(LIVE["pins"][PIN]["history"]) + 1
    _passes_the_lock_test(lock, now)


def test_a_change_of_decision_needs_his_own_yes_and_its_day_is_the_split_day():
    lock, now = _changed()
    for yes, when in ((None, None), ("yes", None), (None, "14 Nov 2026 09:00 Toronto"), ("", "")):
        with pytest.raises(D.Refused, match="Madhav's own yes"):        # the standing yes never covers a change of decision
            D.open_door(lock, now, PIN, "change", "a sale with no quote is now skipped, not priced at zero", yes=yes, when=when)
    assert lock == LIVE
    e = D.open_door(lock, now, PIN, "change", "a sale with no quote is now skipped, not priced at zero", yes="Yes",
                    when="14 Nov 2026 09:00 Toronto", today="2026-11-14")
    assert e["door"] == "change" and 'Madhav, 14 Nov 2026 09:00 Toronto: "Yes"' in e["note"] and "Yes to all" not in e["note"]
    assert "the record is split at this day" in e["note"] and e["date"] == "2026-11-14"
    _passes_the_lock_test(lock, now)


def test_two_changes_to_one_pin_both_stand_in_its_history_in_order():
    lock, now = _changed("e")
    D.open_door(lock, now, PIN, "repair", WHAT, today="2026-11-14")
    now[PIN] = "d" * 64                                                 # a later change, after performance
    D.open_door(lock, now, PIN, "change", "the dial opens one step sooner after a deep drop", yes="go ahead", when="15 Dec 2026 10:00 Toronto",
                today="2026-12-15")
    last = lock["pins"][PIN]["history"][-2:]
    assert [h["door"] for h in last] == ["repair", "change"] and [h["sha256"] for h in last] == ["e" * 64, "d" * 64]
    assert [h["date"] for h in last] == ["2026-11-14", "2026-12-15"] and lock["pins"][PIN]["history"][:-2] == LIVE["pins"][PIN]["history"]
    _passes_the_lock_test(lock, now)


def test_a_lock_past_its_end_day_is_said_and_stops_nothing():
    rows = D.status(LIVE, NOW, "2099-01-01")
    assert any(r["lapsed"] for r in rows) and not any(r["lapsed"] for r in D.status(LIVE, NOW, "2026-11-13"))   # an end that is an event has no day
    lock, now = _changed()
    D.open_door(lock, now, PIN, "repair", WHAT, today="2099-01-01")    # the door still opens; an end day is a note to Madhav, not a wall
    _passes_the_lock_test(lock, now)


def test_the_command_line_writes_only_on_a_real_door_and_names_the_commit(tmp_path, monkeypatch, capsys):
    before = PATH.read_bytes()
    assert D.main(["status"], ROOT) == 0 and "as pinned" in capsys.readouterr().out
    assert D.main(["repair", "real_money", "--what", WHAT], ROOT) == 1 and "refused: nothing in" not in capsys.readouterr().out
    assert D.main(["repair", PIN, "--what", WHAT], ROOT) == 1 and "refused: nothing in" in capsys.readouterr().out   # nothing changed
    assert PATH.read_bytes() == before
    copy_of = tmp_path / PATH.name                                      # from here on the tool works on a copy, as if a pin had changed
    copy_of.write_bytes(before)
    now = dict(NOW, **{PIN: "c" * 64})
    monkeypatch.setattr(D, "find_lock", lambda root=ROOT: (copy_of, MODULE))
    monkeypatch.setattr(D, "current_hashes", lambda module, root=ROOT: now)
    monkeypatch.setattr(D, "committed_at", lambda root, lock_path: "abc1234")
    assert D.main(["repair", PIN, "--what", WHAT, "--dry"], ROOT) == 0 and copy_of.read_bytes() == before
    assert D.main(["change", PIN, "--what", WHAT], ROOT) == 1 and copy_of.read_bytes() == before            # no yes, no change
    assert D.main(["repair", PIN, "--what", WHAT], ROOT) == 0
    written = json.loads(copy_of.read_text())
    assert written["pins"][PIN]["history"][-1]["commit"] == "abc1234" and PATH.read_bytes() == before
    _passes_the_lock_test(written, now)
    assert json.dumps(written, indent=1, ensure_ascii=False) + "\n" == copy_of.read_text()                    # the file keeps its layout


def test_a_door_opens_only_on_committed_work(tmp_path):
    import subprocess

    def git(*a):
        return subprocess.run(["git", "-C", str(tmp_path), "-c", "user.name=t", "-c", "user.email=none", *a], capture_output=True, text=True, check=True)
    git("init", "-q")
    (tmp_path / "rule.py").write_text("x = 1\n")
    (tmp_path / "the_lock.json").write_text("{}\n")
    git("add", "rule.py", "the_lock.json")
    git("commit", "-q", "-m", "first")
    head = D.committed_at(tmp_path, tmp_path / "the_lock.json")
    assert re.fullmatch(r"[0-9a-f]{7,12}", head)
    (tmp_path / "the_lock.json").write_text('{"a": 1}\n')              # the lock file itself may be mid-change (two pins, two doors)
    assert D.committed_at(tmp_path, tmp_path / "the_lock.json") == head
    (tmp_path / "rule.py").write_text("x = 2\n")                       # a loose edit to anything else: commit it first
    with pytest.raises(D.Refused, match="commit the change first"):
        D.committed_at(tmp_path, tmp_path / "the_lock.json")
