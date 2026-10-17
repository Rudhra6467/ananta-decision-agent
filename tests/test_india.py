"""India lake, I-0: URL patterns, polite fetching into bronze with a manifest, the isolation rule, and a read-only Kite client."""
from __future__ import annotations

import datetime as dt
import inspect
import json
import zipfile
import io

import pytest

from india import backfill, kite, nse, paths


def test_cm_urls_old_and_udiff():
    old = nse.cm_urls(dt.date(2024, 7, 5))
    assert old[0] == "https://nsearchives.nseindia.com/content/historical/EQUITIES/2024/JUL/cm05JUL2024bhav.csv.zip"
    new = nse.cm_urls(dt.date(2024, 7, 8))
    assert new[0] == "https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_20240708_F_0000.csv.zip"
    assert new[1] == "https://nsearchives.nseindia.com/content/historical/EQUITIES/2024/JUL/cm08JUL2024bhav.csv.zip"
    assert nse.fo_urls(dt.date(2010, 1, 4))[0].endswith("/DERIVATIVES/2010/JAN/fo04JAN2010bhav.csv.zip")
    assert nse.delivery_urls(dt.date(2026, 10, 15))[0].endswith("/sec_bhavdata_full_15102026.csv")


def test_weekdays_skip_weekends():
    days = list(nse.weekdays(dt.date(2026, 10, 16), dt.date(2026, 10, 20)))   # Fri .. Tue
    assert [d.isoformat() for d in days] == ["2026-10-16", "2026-10-19", "2026-10-20"]


@pytest.fixture
def lake(tmp_path, monkeypatch):
    monkeypatch.setenv("INDIA_DATA_DIR", str(tmp_path / "india"))
    paths.ensure()
    return tmp_path / "india"


def _zip(name: str, text: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(name, text)
    return buf.getvalue()


def test_fetch_day_writes_bronze_and_manifest(lake, monkeypatch):
    body = _zip("cm16OCT2026bhav.csv", "SYMBOL,SERIES,OPEN\nINFY,EQ,1500\n")
    answers = {"cm16OCT2026bhav.csv.zip": (200, body), "BhavCopy_NSE_CM_0_0_0_20261017_F_0000.csv.zip": (404, b""),
               "cm17OCT2026bhav.csv.zip": (404, b""), "BhavCopy_NSE_CM_0_0_0_20261016_F_0000.csv.zip": (200, b"<html>not a file</html>")}

    def fake_get(self, url):
        st, b = answers[url.rsplit("/", 1)[1]]
        return st, b, 0.01

    monkeypatch.setattr(nse.Fetcher, "get", fake_get)
    f = nse.Fetcher(rate_s=0)
    row = nse.fetch_day(f, "cm_bhavcopy", dt.date(2026, 10, 16))
    assert row["status"] == 200 and row["bytes"] == len(body)
    assert (lake / "bronze" / "cm_bhavcopy" / "2026" / "cm_bhavcopy_20261016.csv.zip").read_bytes() == body
    miss = nse.fetch_day(f, "cm_bhavcopy", dt.date(2026, 10, 17))
    assert miss["status"] == 404 and "path" not in miss
    rows = nse.manifest_rows("cm_bhavcopy")
    assert set(rows) == {"2026-10-16", "2026-10-17"} and rows["2026-10-16"]["sha256"]


def test_html_with_200_is_not_a_file(lake, monkeypatch):
    monkeypatch.setattr(nse.Fetcher, "get", lambda self, url: (200, b"<html><body>Access Denied</body></html>", 0.01))
    row = nse.fetch_day(nse.Fetcher(rate_s=0), "cm_bhavcopy", dt.date(2026, 10, 16))
    assert row["status"] == 204 and not list((lake / "bronze" / "cm_bhavcopy").rglob("*.zip"))


def test_backfill_resumes(lake, monkeypatch):
    calls = []

    def fake_get(self, url):
        calls.append(url)
        return (200, _zip("x.csv", "a,b\n1,2\n"), 0.0) if "cm" in url else (404, b"", 0.0)

    monkeypatch.setattr(nse.Fetcher, "get", fake_get)
    out = backfill.run("cm_bhavcopy", dt.date(2026, 10, 12), dt.date(2026, 10, 16), rate_s=0)
    assert out["files"] == 5 and out["fetched"] == 5
    out2 = backfill.run("cm_bhavcopy", dt.date(2026, 10, 12), dt.date(2026, 10, 16), rate_s=0)
    assert out2["fetched"] == 0


def test_isolation_refuses_crypto_and_canada_folders(monkeypatch, tmp_path):
    monkeypatch.setenv("INDIA_DATA_DIR", str(tmp_path / "ok"))
    assert paths.check_isolated()
    for bad in ("~/ananta_lake/india", "~/ananta_data/canada/india", "~/code/ananta-agent-research/india_data"):
        monkeypatch.setenv("INDIA_DATA_DIR", bad)
        with pytest.raises(RuntimeError, match="refused"):
            paths.check_isolated()


def test_kite_client_is_read_only():
    src = inspect.getsource(kite)
    for verb in (".post(", ".put(", ".delete(", "/orders/regular", "/gtt"):
        assert verb not in src.replace("requests.post(f\"https://ntfy.sh", ""), verb
    assert "requests.post" in src   # only the ntfy nudge
    assert src.count("requests.post(") == 1


def test_kite_token_expiry(tmp_path, monkeypatch):
    monkeypatch.setattr(kite, "TOKEN_FILE", tmp_path / "t.json")
    with pytest.raises(kite.NeedLogin, match="no Kite token"):
        kite.token()
    old = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=1)).isoformat(timespec="seconds")
    (tmp_path / "t.json").write_text(json.dumps({"api_key": "k", "access_token": "t", "expires_at": old}))
    with pytest.raises(kite.NeedLogin, match="expired"):
        kite.token()


def test_historical_windows_respect_limits(monkeypatch):
    monkeypatch.setattr(kite, "token", lambda: {"api_key": "k", "access_token": "t", "user_id": "U"})
    k = kite.Kite(rate_per_s=1e9)
    windows = []
    monkeypatch.setattr(k, "historical", lambda tok, iv, a, b: windows.append((a, b)) or [[f"{a}", 1, 1, 1, 1, 1]])
    k.historical_all(1, "5minute", dt.date(2026, 1, 1), dt.date(2026, 7, 1))
    assert all((b - a).days <= 89 for a, b in windows) and windows[0][0] == dt.date(2026, 1, 1) and windows[-1][1] == dt.date(2026, 7, 1)
