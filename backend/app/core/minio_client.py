from datetime import timedelta
from typing import Optional

from app.config import get_settings

settings = get_settings()

_client = None


def get_minio_client():
    global _client
    if _client is None:
        from minio import Minio
        from minio.error import S3Error
        _client = Minio(
            endpoint=settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )
        bucket = settings.MINIO_BUCKET
        if not _client.bucket_exists(bucket):
            _client.make_bucket(bucket)
    return _client


async def presigned_upload_url(object_name: str, expiry_hours: int = 1) -> str:
    client = get_minio_client()
    url = client.presigned_put_object(
        settings.MINIO_BUCKET,
        object_name,
        expires=timedelta(hours=expiry_hours),
    )
    return url


async def presigned_download_url(object_name: str, expiry_hours: int = 24) -> str:
    client = get_minio_client()
    url = client.presigned_get_object(
        settings.MINIO_BUCKET,
        object_name,
        expires=timedelta(hours=expiry_hours),
    )
    return url


async def upload_file(object_name: str, file_path: str, content_type: str = "application/octet-stream"):
    client = get_minio_client()
    client.fput_object(
        settings.MINIO_BUCKET,
        object_name,
        file_path,
        content_type=content_type,
    )


async def remove_file(object_name: str):
    client = get_minio_client()
    from minio.error import S3Error
    try:
        client.remove_object(settings.MINIO_BUCKET, object_name)
    except S3Error:
        pass
