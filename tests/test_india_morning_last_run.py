"""india.morning reads only the last run's traceback from an error file with no run markers (review of 26 Oct 2026)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from india import morning  # noqa: E402

OLD = ["Traceback (most recent call last):",
       '  File "/x/india/sp1paper.py", line 1037, in <module>',
       "india.kite.NeedLogin: the Kite token expired at 6 am IST: open http://127.0.0.1:8100/kite/login on the Mac"]
NEW = ["Traceback (most recent call last):",
       '  File "/x/india/sp1paper.py", line 1037, in <module>',
       "IndexError: arrays used as indices must be of integer (or boolean) type"]


def test_unmarked_file_reads_last_traceback_only():
    errs, dead = morning._last_run_errors(OLD + OLD + NEW, marked=False)
    assert not dead
    assert errs == ["india.sp1paper: IndexError: arrays used as indices must be of integer (or boolean) type"]


def test_unmarked_file_token_dead_when_last_run_was():
    errs, dead = morning._last_run_errors(NEW + OLD, marked=False)
    assert dead and len(errs) == 1


def test_marked_file_keeps_every_error_since_the_marker():
    errs, dead = morning._last_run_errors(OLD + NEW, marked=True)
    assert dead and len(errs) == 2
