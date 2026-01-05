from __future__ import annotations

from datetime import timedelta
from urllib.parse import quote

from django.conf import settings


def _require_minio_config() -> None:
    missing = []
    if not getattr(settings, "MINIO_ENDPOINT", ""):
        missing.append("MINIO_ENDPOINT")
    if not getattr(settings, "MINIO_ACCESS_KEY", ""):
        missing.append("MINIO_ACCESS_KEY")
    if not getattr(settings, "MINIO_SECRET_KEY", ""):
        missing.append("MINIO_SECRET_KEY")
    if missing:
        raise RuntimeError(f"MinIO 未配置：缺少 {', '.join(missing)}")


def get_minio_client():
    _require_minio_config()
    from minio import Minio

    endpoint = settings.MINIO_PUBLIC_ENDPOINT or settings.MINIO_ENDPOINT
    return Minio(
        endpoint,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=bool(getattr(settings, "MINIO_SECURE", False)),
    )


def ensure_bucket(client) -> None:
    bucket = settings.MINIO_BUCKET
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)


def put_object(*, object_name: str, data, length: int, content_type: str | None = None) -> str:
    client = get_minio_client()
    ensure_bucket(client)
    client.put_object(
        settings.MINIO_BUCKET,
        object_name,
        data,
        length,
        content_type=content_type or "application/octet-stream",
    )
    return object_name


def presigned_download_url(*, object_name: str, filename: str, expires_seconds: int = 600) -> str:
    client = get_minio_client()
    ensure_bucket(client)
    # 让浏览器直接下载，尽量保留文件名
    quoted = quote(filename)
    disposition = f"attachment; filename*=UTF-8''{quoted}"
    return client.presigned_get_object(
        settings.MINIO_BUCKET,
        object_name,
        expires=timedelta(seconds=expires_seconds),
        response_headers={"response-content-disposition": disposition},
    )


def presigned_preview_url(
    *,
    object_name: str,
    filename: str,
    content_type: str | None = None,
    expires_seconds: int = 600,
) -> str:
    client = get_minio_client()
    ensure_bucket(client)
    quoted = quote(filename)
    disposition = f"inline; filename*=UTF-8''{quoted}"
    headers: dict[str, str] = {"response-content-disposition": disposition}
    if content_type:
        headers["response-content-type"] = content_type
    return client.presigned_get_object(
        settings.MINIO_BUCKET,
        object_name,
        expires=timedelta(seconds=expires_seconds),
        response_headers=headers,
    )
