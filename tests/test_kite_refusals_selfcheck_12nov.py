"""12 Nov 2026, the keen outside audit (G-54): a read Zerodha refused for a reason other than the sign-in left no trace. The Kite client
(the records checkout) now writes one line per refused read; the self-check reads them."""
import datetime as dt

from jarvis import selfcheck


def _line(ago_s, status="403", kind="PermissionException", path="/quote/ohlc", now=1_794_500_000.0):
    return f"{dt.datetime.fromtimestamp(now - ago_s, dt.timezone.utc).isoformat(timespec='seconds')} {status} {kind} {path}"


def test_no_log_or_only_old_lines_is_nothing(tmp_path):
    now = 1_794_500_000.0
    assert selfcheck._kite_refusals(now, tmp_path / "none.log") == []
    p = tmp_path / "r.log"
    p.write_text(_line(3 * 86400) + "\nnot a line\n")
    assert selfcheck._kite_refusals(now, p) == []


def test_a_refused_read_is_said_with_the_count_and_the_latest(tmp_path):
    now = 1_794_500_000.0
    p = tmp_path / "r.log"
    p.write_text(_line(7200) + "\n")
    one = selfcheck._kite_refusals(now, p)
    assert len(one) == 1 and one[0]["severity"] == "low" and one[0]["market"] == "india" and one[0]["source"] == "Zerodha reads"
    assert "refused 1 read in the last 24 hours" in one[0]["what"] and "403 PermissionException on /quote/ohlc" in one[0]["what"]
    p.write_text("\n".join([_line(7200), _line(3600, "500", "-", "/portfolio/holdings"), _line(60, "429", "-", "/quote/ohlc")]) + "\n")
    three = selfcheck._kite_refusals(now, p)
    assert three[0]["severity"] == "medium" and "refused 3 reads" in three[0]["what"] and "429 on /quote/ohlc" in three[0]["what"]


def test_it_is_one_of_the_named_checks():
    assert ("kite", "Zerodha refused no read for a reason other than the sign-in") in selfcheck.CHECKS
    assert selfcheck.SOURCE_CHECK["Zerodha reads"] == "kite"
    c = {"at_words": "now", "items": [{"market": "india", "severity": "low", "source": "Zerodha reads", "what": "x"}]}
    assert "Zerodha refused no read" not in selfcheck.fine(c)[0]
    assert "Zerodha refused no read" in selfcheck.fine({"at_words": "now", "items": []})[0]
