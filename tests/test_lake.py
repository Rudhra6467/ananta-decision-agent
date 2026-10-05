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
    assert bv.pull("TESTUSDT", get=_fake_bucket({k: v for k, v in months.items() if "2025-02" not in k}), log=lambda *_: None)["already_held"] == 2
    b = bv.build("TESTUSDT")
    assert b["rows"] == 97 + 60 and b["first_t"] == jan // 1000 and b["last_t"] == jan25 // 1000 + 59 * 60   # header dropped, microseconds fixed
    q = quality.check("TESTUSDT")
    assert q["broken_candles"] == 0 and q["duplicates"] == 0 and q["gaps"] == 2                 # 3 minutes in 2024, then the year to 2025
    assert q["longest_gaps"][0]["from"].startswith("2024-01-01") and q["grade"] == "C"
    years = sorted(x.name for x in (tmp_path / "clean" / "binance" / "spot" / "1m" / "symbol=TESTUSDT").iterdir())
    assert years == ["year=2024", "year=2025"]


def test_bars_from_the_one_minute_base(tmp_path, monkeypatch):
    from src.lake import bars
    from src.lake import binance_vision as bv

    monkeypatch.setenv("ANANTA_LAKE", str(tmp_path))
    jan = 1_704_067_200_000
    months = {"data/spot/monthly/klines/TESTUSDT/1m/TESTUSDT-1m-2024-01.zip": _zip("x.zip", _rows(jan, 600, skip=(1, 2)))}
    bv.pull("TESTUSDT", get=_fake_bucket(months), log=lambda *_: None)
    bv.build("TESTUSDT")
    r = bars.build("TESTUSDT", frames=("5m", "1h"))
    assert r["candles"] == {"5m": 119, "1h": 10}               # the first 5 minutes miss 2 of 5: under 80%, dropped
    import duckdb

    o, h, l, c, share = duckdb.connect().execute(
        f"SELECT o, h, l, c, share FROM read_parquet('{tmp_path}/clean/binance/spot/1h/symbol=TESTUSDT/**/*.parquet') ORDER BY t LIMIT 1").fetchone()
    assert o == 100 and c == 100 + 59 * 0.01 + 0.1 and abs(share - 58 / 60) < 1e-9


def test_universe_rule_excludes_stables_and_leveraged():
    from src.lake import universe

    xml = ("<ListBucketResult><IsTruncated>false</IsTruncated>" + "".join(
        f"<CommonPrefixes><Prefix>data/spot/monthly/klines/{s}/</Prefix></CommonPrefixes>"
        for s in ("BTCUSDT", "ETHBTC", "USDCUSDT", "BTCUPUSDT", "WBTCUSDT", "SOLUSDT", "FDUSDUSDT")) + "</ListBucketResult>")
    got = universe.candidates(get=lambda url, params=None, timeout=60: R(text=xml))
    assert got == ["BTCUSDT", "SOLUSDT"]


def test_r2_sync_uploads_only_what_changed(tmp_path, monkeypatch):
    from src.lake import r2

    monkeypatch.setenv("ANANTA_LAKE", str(tmp_path))
    monkeypatch.setenv("R2_BUCKET_NAME", "b")
    (tmp_path / "clean" / "x").mkdir(parents=True)
    (tmp_path / "clean" / "x" / "a.parquet").write_bytes(b"aaa")
    (tmp_path / "reports").mkdir()
    (tmp_path / "reports" / "q.json").write_text("{}")
    (tmp_path / "raw").mkdir()
    (tmp_path / "raw" / "z.zip").write_bytes(b"zzz")                # raw is never uploaded
    store = {}

    class S3:
        def get_paginator(self, _):
            class P:
                def paginate(self, **kw):
                    return [{"Contents": [{"Key": k, "Size": len(v), "ETag": '"' + hashlib.md5(v).hexdigest() + '"'} for k, v in store.items()]}]
            return P()

        def upload_file(self, path, b, key, Config=None):
            store[key] = open(path, "rb").read()

    pytest.importorskip("boto3")
    r = r2.sync(s3=S3(), log=lambda *_: None)
    assert r["uploaded"] == 2 and set(store) == {"clean/x/a.parquet", "reports/q.json"}
    assert r2.sync(s3=S3(), log=lambda *_: None)["uploaded"] == 0
    (tmp_path / "reports" / "q.json").write_text('{"v": 2}')
    assert r2.sync(s3=S3(), log=lambda *_: None)["uploaded"] == 1


def test_quality_flags_a_token_swap_and_research_refuses_it(tmp_path, monkeypatch):
    """A x100 jump in one candle (a redenomination Binance did not back-adjust) grades C and blocks research (2026-10-05)."""
    import pytest

    from src.lake import binance_vision as bv
    from src.lake import quality
    from src.lake import research as L

    monkeypatch.setenv("ANANTA_LAKE", str(tmp_path))
    p = "data/spot/monthly/klines/SWAPUSDT/1m/"
    jan = 1_704_067_200_000
    rows = []
    for i in range(100):
        t, k = jan + 60_000 * i, (100 if i >= 60 else 1)              # from minute 60 every price is 100x: the swap
        p0 = (100 + i * 0.01) * k
        rows.append(f"{t},{p0},{p0 * 1.005},{p0 * 0.995},{p0 * 1.001},1.5,{t + 59_999},150,10,0.7,70,0")
    bv.pull("SWAPUSDT", get=_fake_bucket({p + "SWAPUSDT-1m-2024-01.zip": _zip("SWAPUSDT-1m-2024-01.zip", rows)}), log=lambda *_: None)
    bv.build("SWAPUSDT")
    q = quality.check("SWAPUSDT")
    assert q["grade"] == "C" and len(q["suspect_redenominations"]) == 1 and q["suspect_redenominations"][0]["ratio"] > 90
    with pytest.raises(ValueError, match="token swap"):
        L.load(["SWAPUSDT"])
    monkeypatch.setitem(L.BREAKS, "SWAPUSDT", q["suspect_redenominations"][0]["t"] + 60)
    assert L.unhandled_suspects("SWAPUSDT") == []
