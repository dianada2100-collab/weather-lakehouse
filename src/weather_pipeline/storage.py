"""Storage abstraction: the same pipeline code runs on local disk and on S3."""
from __future__ import annotations

import io
import json
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import pandas as pd

from .config import Settings


class Storage(ABC):
    """Key-based object storage. Keys look like 'silver/hourly_weather/city=x/...'."""

    @abstractmethod
    def write_bytes(self, key: str, data: bytes) -> None: ...

    @abstractmethod
    def read_bytes(self, key: str) -> bytes: ...

    @abstractmethod
    def list_keys(self, prefix: str) -> list[str]: ...

    # --- convenience helpers built on the primitives -------------------------
    def write_json(self, key: str, obj: Any) -> None:
        self.write_bytes(key, json.dumps(obj).encode("utf-8"))

    def read_json(self, key: str) -> Any:
        return json.loads(self.read_bytes(key).decode("utf-8"))

    def write_parquet(self, key: str, df: pd.DataFrame) -> None:
        buf = io.BytesIO()
        df.to_parquet(buf, index=False)
        self.write_bytes(key, buf.getvalue())

    def read_parquet(self, key: str) -> pd.DataFrame:
        return pd.read_parquet(io.BytesIO(self.read_bytes(key)))


class LocalStorage(Storage):
    def __init__(self, root: str | Path):
        self.root = Path(root)

    def _path(self, key: str) -> Path:
        return self.root / key

    def write_bytes(self, key: str, data: bytes) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        # Write to a temp file, then rename: readers never see half-written files.
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_bytes(data)
        os.replace(tmp, path)

    def read_bytes(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def list_keys(self, prefix: str) -> list[str]:
        base = self._path(prefix)
        if not base.exists():
            return []
        return sorted(
            p.relative_to(self.root).as_posix() for p in base.rglob("*") if p.is_file()
        )


class S3Storage(Storage):
    def __init__(self, bucket: str, prefix: str = ""):
        import boto3  # imported lazily so local runs/tests don't need AWS setup

        if not bucket:
            raise ValueError("S3_BUCKET must be set when STORAGE_BACKEND=s3")
        self.client = boto3.client("s3")
        self.bucket = bucket
        self.prefix = prefix.strip("/")

    def _full(self, key: str) -> str:
        return f"{self.prefix}/{key}" if self.prefix else key

    def write_bytes(self, key: str, data: bytes) -> None:
        # put_object overwrites -> re-running a step is idempotent.
        self.client.put_object(Bucket=self.bucket, Key=self._full(key), Body=data)

    def read_bytes(self, key: str) -> bytes:
        return self.client.get_object(Bucket=self.bucket, Key=self._full(key))["Body"].read()

    def list_keys(self, prefix: str) -> list[str]:
        paginator = self.client.get_paginator("list_objects_v2")
        strip = len(self.prefix) + 1 if self.prefix else 0
        keys: list[str] = []
        for page in paginator.paginate(Bucket=self.bucket, Prefix=self._full(prefix)):
            keys.extend(obj["Key"][strip:] for obj in page.get("Contents", []))
        return sorted(keys)


def get_storage(settings: Settings) -> Storage:
    if settings.backend == "s3":
        return S3Storage(settings.s3_bucket, settings.s3_prefix)
    if settings.backend == "local":
        return LocalStorage(settings.local_root)
    raise ValueError(f"Unknown STORAGE_BACKEND: {settings.backend!r}")
