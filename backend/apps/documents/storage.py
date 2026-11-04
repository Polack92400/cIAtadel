"""Object storage behind a tiny interface.

`S3Storage` talks to MinIO locally and to Amazon S3 on AWS (leave
S3_ENDPOINT_URL empty and use an IAM task role). `MemoryStorage` is for tests.
Keys are generated server-side only: tenants/<tenant>/documents/<doc>.pdf.
"""

from collections.abc import Iterator
from functools import lru_cache
from typing import Protocol

from django.conf import settings


class ObjectStorage(Protocol):
    def put(self, key: str, data: bytes, content_type: str) -> None: ...
    def get(self, key: str) -> bytes: ...
    def stream(self, key: str, chunk_size: int = 64 * 1024) -> Iterator[bytes]: ...
    def delete(self, key: str) -> None: ...
    def ensure_bucket(self) -> None: ...


def document_key(tenant_id, document_id) -> str:
    return f"tenants/{tenant_id}/documents/{document_id}.pdf"


class S3Storage:
    def __init__(self, cfg: dict):
        import boto3
        from botocore.config import Config

        self.bucket = cfg["BUCKET"]
        self.sse = cfg.get("SSE") or ""
        self.client = boto3.client(
            "s3",
            endpoint_url=cfg["ENDPOINT_URL"] or None,
            aws_access_key_id=cfg["ACCESS_KEY_ID"] or None,
            aws_secret_access_key=cfg["SECRET_ACCESS_KEY"] or None,
            region_name=cfg["REGION"],
            config=Config(
                signature_version="s3v4",
                s3={"addressing_style": "path"},
                retries={"max_attempts": 3},
            ),
        )

    def put(self, key, data, content_type):
        extra = {"ServerSideEncryption": self.sse} if self.sse else {}
        self.client.put_object(
            Bucket=self.bucket, Key=key, Body=data, ContentType=content_type, **extra
        )

    def get(self, key):
        return self.client.get_object(Bucket=self.bucket, Key=key)["Body"].read()

    def stream(self, key, chunk_size=64 * 1024):
        body = self.client.get_object(Bucket=self.bucket, Key=key)["Body"]
        yield from body.iter_chunks(chunk_size)

    def delete(self, key):
        self.client.delete_object(Bucket=self.bucket, Key=key)

    def ensure_bucket(self):
        from botocore.exceptions import ClientError

        try:
            self.client.head_bucket(Bucket=self.bucket)
        except ClientError:
            self.client.create_bucket(Bucket=self.bucket)


class MemoryStorage:
    def __init__(self):
        self.objects: dict[str, bytes] = {}

    def put(self, key, data, content_type):
        self.objects[key] = bytes(data)

    def get(self, key):
        return self.objects[key]

    def stream(self, key, chunk_size=64 * 1024):
        data = self.objects[key]
        for i in range(0, len(data), chunk_size):
            yield data[i : i + chunk_size]

    def delete(self, key):
        self.objects.pop(key, None)

    def ensure_bucket(self):
        return None


@lru_cache(maxsize=1)
def get_storage() -> ObjectStorage:
    cfg = settings.STORAGE
    if cfg["BACKEND"] == "memory":
        return MemoryStorage()
    if cfg["BACKEND"] == "s3":
        return S3Storage(cfg)
    raise ValueError(f"Unknown STORAGE_BACKEND {cfg['BACKEND']!r}")
