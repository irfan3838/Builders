"""Private object storage: local directory for development, S3 in AWS. Never public."""

from __future__ import annotations

import asyncio
from pathlib import Path

from app.config import get_settings


async def put(key: str, data: bytes, content_type: str) -> None:
    st = get_settings()
    if st.storage_backend == "s3":
        import boto3

        def _put():
            boto3.client("s3", region_name=st.aws_region).put_object(
                Bucket=st.s3_bucket, Key=key, Body=data, ContentType=content_type, ServerSideEncryption="AES256"
            )

        await asyncio.to_thread(_put)
        return
    path = Path(st.storage_local_dir) / key
    path.parent.mkdir(parents=True, exist_ok=True)
    await asyncio.to_thread(path.write_bytes, data)


async def get(key: str) -> bytes:
    st = get_settings()
    if st.storage_backend == "s3":
        import boto3

        def _get():
            return boto3.client("s3", region_name=st.aws_region).get_object(Bucket=st.s3_bucket, Key=key)["Body"].read()

        return await asyncio.to_thread(_get)
    return await asyncio.to_thread((Path(st.storage_local_dir) / key).read_bytes)
