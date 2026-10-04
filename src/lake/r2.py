"""The off-site copy of the lake in Cloudflare R2 (bucket from R2_BUCKET_NAME; keys R2_ACCOUNT_ID, R2_ACCESS_KEY_ID,
R2_SECRET_ACCESS_KEY from the .env, never printed).

  sync()        upload clean/ and reports/ files that R2 does not have or holds in an older version (compared by MD5, which is
                R2's ETag for single-part uploads); raw/ is not uploaded: it can always be downloaded again from Binance
  status()      how many files and bytes R2 holds
  duck(con)     let DuckDB read the lake straight from R2 (a cloud machine can then run research without copying anything)

Uploads only; nothing here ever deletes from R2.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

from src.lake import root

PARTS = ("clean", "reports")
SINGLE_PART_LIMIT = 1 << 30                       # files under 1 GB go up in one part, so R2's ETag is their MD5


def _env(k: str) -> str:
    v = os.getenv(k, "").strip().strip('"')
    if not v:
        raise RuntimeError(f"{k} is not set in the .env")
    return v


def endpoint() -> str:
    return f"https://{_env('R2_ACCOUNT_ID')}.r2.cloudflarestorage.com"


def client():
    import boto3
    from botocore.config import Config

    return boto3.client("s3", endpoint_url=endpoint(), aws_access_key_id=_env("R2_ACCESS_KEY_ID"),
                        aws_secret_access_key=_env("R2_SECRET_ACCESS_KEY"), region_name="auto",
                        config=Config(retries={"max_attempts": 5, "mode": "standard"}))


def bucket() -> str:
    return _env("R2_BUCKET_NAME")


def _md5(p: Path) -> str:
    h = hashlib.md5()  # noqa: S324  (a content fingerprint, not security)
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def remote(s3=None, prefix: str = "") -> dict[str, tuple[int, str]]:
    s3 = s3 or client()
    out = {}
    for page in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket(), Prefix=prefix):
        for o in page.get("Contents", []):
            out[o["Key"]] = (o["Size"], o["ETag"].strip('"'))
    return out


def sync(parts: tuple = PARTS, s3=None, log=print, workers: int = 8) -> dict:
    from concurrent.futures import ThreadPoolExecutor

    from boto3.s3.transfer import TransferConfig

    s3 = s3 or client()
    have = remote(s3)
    base = root()
    todo = []
    n_files = same = 0
    for part in parts:
        for p in (base / part).rglob("*"):
            if not p.is_file() or p.name.startswith("."):
                continue
            n_files += 1
            key = p.relative_to(base).as_posix()
            size = p.stat().st_size
            r = have.get(key)
            if r and r[0] == size and r[1] == _md5(p):
                same += 1
                continue
            todo.append((p, key, size))
    cfg = TransferConfig(multipart_threshold=SINGLE_PART_LIMIT)

    def up(item) -> int:
        p, key, size = item
        s3.upload_file(str(p), bucket(), key, Config=cfg)
        return size

    sent = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for size in pool.map(up, todo):
            sent += size
    log(f"R2: {len(todo)} uploaded ({sent / 1e6:.0f} MB), {same} already there")
    return {"files": n_files, "uploaded": len(todo), "uploaded_mb": round(sent / 1e6, 1), "unchanged": same}


def status(s3=None) -> dict:
    have = remote(s3)
    return {"bucket": bucket(), "files": len(have), "gb": round(sum(v[0] for v in have.values()) / 1e9, 3)}


def duck(con) -> None:
    """DuckDB reads r2://<bucket>/clean/... directly after this."""
    con.execute("INSTALL httpfs; LOAD httpfs;")
    con.execute(f"""CREATE OR REPLACE SECRET r2 (TYPE r2, KEY_ID '{_env("R2_ACCESS_KEY_ID")}', SECRET '{_env("R2_SECRET_ACCESS_KEY")}',
                    ACCOUNT_ID '{_env("R2_ACCOUNT_ID")}')""")
