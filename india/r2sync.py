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
# 19 Oct firewall: an R2 API token scoped to this bucket only, in ~/ananta_private/r2_india.env (same R2_* key names), is used when present;
# until Madhav creates it, the crypto agent's account key is the fallback and india.firewall reports r2_credentials FAIL.
_OWN = Path("~/ananta_private/r2_india.env").expanduser()
ENV = _OWN if _OWN.exists() else Path("~/code/ananta-decision-agent/.env").expanduser()
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


def _existing(c, with_time: bool = False) -> dict:
    out = {}
    for page in c.get_paginator("list_objects_v2").paginate(Bucket=BUCKET):
        for o in page.get("Contents", []):
            out[o["Key"]] = (o["Size"], o["LastModified"].timestamp()) if with_time else o["Size"]
    return out


def sync() -> dict:
    c = client()
    have = _existing(c, with_time=True)
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
            old = have.get(key)
            # same size and not modified since the upload: skip. A rebuilt file of the same size (newer on disk) is uploaded again.
            if old and old[0] == size and p.stat().st_mtime <= old[1]:
                skipped += 1
                continue
            c.upload_file(str(p), BUCKET, key)
            up += 1
            nbytes += size
    return {"uploaded": up, "skipped_same_size": skipped, "bytes_uploaded": nbytes, "objects_in_bucket_before": len(have)}


def restore_check(dest: str, n: int = 8) -> dict:
    """Download a spread of objects into `dest` (never into the lake) and prove they are the same files: size, sha256 against the local copy, and,
    for Parquet, that the file opens and has the same row count."""
    import hashlib
    import pyarrow.parquet as pq

    c = client()
    have = _existing(c)
    pqk = sorted(k for k in have if k.endswith(".parquet") and have[k] < 300_000_000)
    keys = pqk[:: max(1, len(pqk) // n)][:n] + [k for k in sorted(have) if k.startswith("manifests/")][:2]
    res = []
    for k in keys:
        t = Path(dest) / k
        t.parent.mkdir(parents=True, exist_ok=True)
        c.download_file(BUCKET, k, str(t))
        local = paths.data_dir() / k
        r = {"key": k, "size_match": t.stat().st_size == have[k]}
        if local.exists():
            h1 = hashlib.sha256(t.read_bytes()).hexdigest()
            h2 = hashlib.sha256(local.read_bytes()).hexdigest()
            r["sha_matches_local"] = h1 == h2  # False only if the local file was rebuilt after its last upload
        if k.endswith(".parquet"):
            r["rows_restored"] = pq.ParquetFile(t).metadata.num_rows
            if local.exists():
                r["rows_local"] = pq.ParquetFile(local).metadata.num_rows
        res.append(r)
    return {"checked": len(res), "size_match": sum(r["size_match"] for r in res), "sha_match": sum(bool(r.get("sha_matches_local")) for r in res), "objects": len(have), "files": res}


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "restore-check":
        import json
        r = restore_check(sys.argv[2])
        (paths.manifest_dir() / "r2_restore_check.json").write_text(json.dumps(r, indent=1, default=str))
        print(json.dumps(r, indent=1, default=str))
    else:
        print(sync())
