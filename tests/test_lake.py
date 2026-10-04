"""The research lake: Binance Data Vision files -> checked raw zips -> clean Parquet -> quality report (no network)."""
import hashlib
import io
import zipfile

import pytest

duckdb = pytest.importorskip("duckdb")


class R:
    def __init__(self, status=200, content=b"", text=""):
        self.status_code, self.content, self.text = status, content, text or content.decode(errors="ignore")


def _zip(name: str, rows: list[str]) -> bytes:
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr(name.replace(".zip", ".csv"), "\n".join(rows) + "\n")
    return b.getvalue()


def _fake_bucket(months: dict[str, bytes], bad: set = frozenset()):
    def get(url, params=None, timeout=60):
        if params is not None:
            body = "".join(f"<Contents><Key>{k}</Key><Size>{len(v)}</Size></Contents><Contents><Key>{k}.CHECKSUM</Key><Size>88</Size></Contents>"
                           for k, v in months.items())
            return R(text=f"<ListBucketResult><IsTruncated>false</IsTruncated>{body}</ListBucketResult>")
        key = url.split("data.binance.vision/")[1]
        if key.endswith(".CHECKSUM"):
            k = key[: -len(".CHECKSUM")]
            h = "0" * 64 if k in bad else hashlib.sha256(months[k]).hexdigest()
            return R(text=f"{h}  {k.split('/')[-1]}")
        return R(content=months[key])
    return get


def _rows(t0_ms: int, n: int, us: bool = False, skip: tuple = ()) -> list[str]:
    out = []
    for i in range(n):
        if i in skip:
            continue
        t = (t0_ms + 60_000 * i) * (1000 if us else 1)
        p = 100 + i * 0.01
        out.append(f"{t},{p},{p + 0.5},{p - 0.5},{p + 0.1},1.5,{t + 59_999},150,10,0.7,70,0")
    return out


def test_pull_build_and_check(tmp_path, monkeypatch):
    from src.lake import binance_vision as bv
    from src.lake import quality

    monkeypatch.setenv("ANANTA_LAKE", str(tmp_path))
    p = "data/spot/monthly/klines/TESTUSDT/1m/"
    jan = 1_704_067_200_000                                   # 2024-01-01 00:00 UTC, milliseconds
    jan25 = 1_735_689_600_000                                 # 2025-01-01: Binance writes microseconds from 2025
    months = {p + "TESTUSDT-1m-2024-01.zip": _zip("TESTUSDT-1m-2024-01.zip", ["open_time,open,high,low,close,volume,close_time,qv,n,tb,tq,ig"] + _rows(jan, 100, skip=(50, 51, 52))),
              p + "TESTUSDT-1m-2025-01.zip": _zip("TESTUSDT-1m-2025-01.zip", _rows(jan25, 60, us=True)),
              p + "TESTUSDT-1m-2025-02.zip": _zip("TESTUSDT-1m-2025-02.zip", _rows(jan25 + 3_600_000, 10, us=True))}
    get = _fake_bucket(months, bad={p + "TESTUSDT-1m-2025-02.zip"})
    r = bv.pull("TESTUSDT", get=get, log=lambda *_: None)
    assert r["months"] == 3 and r["downloaded"] == 2 and r["errors"] == 1          # the bad checksum is removed, never used
    assert bv.pull("TESTUSDT", get=_fake_bucket({k: v for k, v in months.items() if "02" not in k}), log=lambda *_: None)["already_held"] == 2
    b = bv.build("TESTUSDT")
    assert b["rows"] == 97 + 60 and b["first_t"] == jan // 1000 and b["last_t"] == jan25 // 1000 + 59 * 60   # header dropped, microseconds fixed
    q = quality.check("TESTUSDT")
    assert q["broken_candles"] == 0 and q["duplicates"] == 0 and q["gaps"] == 2                 # 3 minutes in 2024, then the year to 2025
    assert q["longest_gaps"][0]["from"].startswith("2024-01-01") and q["grade"] == "C"
    years = sorted(x.name for x in (tmp_path / "clean" / "binance" / "spot" / "1m" / "symbol=TESTUSDT").iterdir())
    assert years == ["year=2024", "year=2025"]
