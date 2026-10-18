"""Uploads-only backup of the India lake to Cloudflare R2 (bucket ananta-india-lake). Never deletes, never overwrites a file whose size matches.

  python -m india.r2sync            silver/, sealed/silver/ and manifests/
  python -m india.r2sync restore-check <dir>   download a few objects to <dir> and compare sizes (the restore test)
R2 keys come from ~/code/ananta-decision-agent/.env (R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY); the bucket name is fixed here
so the crypto bucket named in that file is never touched. Nothing secret is printed.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import boto3
from botocore.config import Config

from india import paths

BUCKET = "ananta-india-lake"
ENV = Path("~/code/ananta-decision-agent/.env").expanduser()
PARTS = ("silver", "sealed/silver", "manifests")


def _env() -> dict:
    out = {}
    for line in ENV.read_text().splitlines():
        if line.startswith("R2_") and "=" in line:
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def client():
    e = _env()
    return boto3.client("s3", endpoint_url=f"https://{e['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
                        aws_access_key_id=e["R2_ACCESS_KEY_ID"], aws_secret_access_key=e["R2_SECRET_ACCESS_KEY"],
                        region_name="auto", config=Config(retries={"max_attempts": 5}))


def _existing(c) -> dict[str, int]:
    out = {}
    for page in c.get_paginator("list_objects_v2").paginate(Bucket=BUCKET):
        for o in page.get("Contents", []):
            out[o["Key"]] = o["Size"]
    return out


def sync() -> dict:
    c = client()
    have = _existing(c)
    root = paths.data_dir()
    up = skipped = nbytes = 0
    for part in PARTS:
        base = root / part
        if not base.exists():
            continue
        for p in sorted(base.rglob("*")):
            if not p.is_file() or p.name.startswith("."):
                continue
            key = str(p.relative_to(root))
            size = p.stat().st_size
            if have.get(key) == size:
                skipped += 1
                continue
            c.upload_file(str(p), BUCKET, key)
            up += 1
            nbytes += size
    return {"uploaded": up, "skipped_same_size": skipped, "bytes_uploaded": nbytes, "objects_in_bucket_before": len(have)}


def restore_check(dest: str, n: int = 5) -> dict:
    c = client()
    have = _existing(c)
    keys = sorted(k for k in have if k.endswith(".parquet"))[:: max(1, len(have) // n)][:n]
    ok = 0
    for k in keys:
        t = Path(dest) / k
        t.parent.mkdir(parents=True, exist_ok=True)
        c.download_file(BUCKET, k, str(t))
        ok += t.stat().st_size == have[k]
    return {"checked": len(keys), "size_match": ok, "objects": len(have)}


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "restore-check":
        print(restore_check(sys.argv[2]))
    else:
        print(sync())
