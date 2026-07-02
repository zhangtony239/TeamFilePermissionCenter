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


def _build_minio_client(endpoint: str):
    """根据 endpoint 构造 Minio 客户端。"""
    from minio import Minio

    secure = bool(getattr(settings, "MINIO_SECURE", False))
    # endpoint 形如 "host:port"；若带 scheme 则剥离，Minio 只需 host:port
    if "://" in endpoint:
        from urllib.parse import urlparse

        parsed = urlparse(endpoint)
        endpoint = f"{parsed.hostname}:{parsed.port}" if parsed.port else parsed.hostname
    return Minio(
        endpoint,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=secure,
    )


def get_minio_client():
    """服务端内部访问 MinIO 的客户端（容器间直连，使用 MINIO_ENDPOINT）。"""
    _require_minio_config()
    return _build_minio_client(settings.MINIO_ENDPOINT)


def get_minio_public_client():
    """生成给浏览器的预签名 URL 的客户端（使用 MINIO_PUBLIC_ENDPOINT）。

    该 endpoint 参与预签名签名，必须与浏览器最终访问 MinIO 的地址一致，
    否则签名校验失败。在仅暴露 5173 的 docker-compose 方案中，
    该值通常为 "127.0.0.1:5173"（经 nginx 反代到 MinIO）。
    """
    _require_minio_config()
    public_endpoint = settings.MINIO_PUBLIC_ENDPOINT or settings.MINIO_ENDPOINT
    return _build_minio_client(public_endpoint)


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
    client = get_minio_public_client()
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
    client = get_minio_public_client()
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
