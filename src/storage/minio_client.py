"MinIO 异步客户端封装"

from __future__ import annotations
from datetime import timedelta

from miniopy_async import Minio
from miniopy_async.error import S3Error

from src.config import config
from src.observability import logger


class MinioClient:
    _instance: Minio | None = None

    def __init__(self):
        if MinioClient._instance is None:
            MinioClient._instance = Minio(
                endpoint=config.minio.endpoint,
                access_key=config.minio.access_key,
                secret_key=config.minio.secret_key,
                secure=config.minio.secure,
                region=config.minio.region,
            )
        self._client = MinioClient._instance
        self._bucket = config.minio.bucket

    async def _ensure_bucket(self):
        try:
            exists = await self._client.bucket_exists(self._bucket)
            if not exists:
                await self._client.make_bucket(self._bucket)
                logger.info("MinIO bucket created", bucket=self._bucket)
        except Exception as e:
            logger.error("MinIO bucket init failed", error=str(e))
            raise

    async def upload_file(self, file_path: str, object_name: str) -> dict:
        await self._ensure_bucket()
        result = await self._client.fput_object(
            bucket_name=self._bucket,
            object_name=object_name,
            file_path=file_path,
        )
        return {
            "bucket": result.bucket_name,
            "object": result.object_name,
            "etag": result.etag,
        }

    async def download_file(self, object_name: str, file_path: str) -> str:
        await self._client.fget_object(
            bucket_name=self._bucket,
            object_name=object_name,
            file_path=file_path,
        )
        return file_path

    async def delete_file(self, object_name: str) -> bool:
        try:
            await self._client.remove_object(
                bucket_name=self._bucket,
                object_name=object_name,
            )
            return True
        except S3Error:
            return False

    async def get_presigned_url(self, object_name: str, expiry_seconds: int | None = None) -> str:
        if expiry_seconds is None:
            expiry_seconds = config.minio.presigned_expiry_seconds
        return await self._client.presigned_get_object(
            bucket_name=self._bucket,
            object_name=object_name,
            expires=timedelta(seconds=expiry_seconds),
        )

    async def health_check(self) -> bool:
        try:
            await self._client.bucket_exists(self._bucket)
            return True
        except Exception:
            return False
