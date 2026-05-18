"""S3-compatible file storage with local filesystem fallback.

Uses boto3 for S3-compatible providers (Cloudflare R2, AWS S3, MinIO, etc.).
Falls back to local filesystem when no S3 config is set (dev mode).
"""

import asyncio
import logging
import os
from functools import lru_cache

try:
    import boto3
    from botocore.exceptions import ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    boto3 = None
    ClientError = Exception
    BOTO3_AVAILABLE = False

from core.config import get_settings

logger = logging.getLogger(__name__)


class FileStorage:
    """Unified file storage — S3 in production, local filesystem in dev."""

    def __init__(self):
        settings = get_settings()
        self.is_s3 = bool(settings.s3_bucket_name) and BOTO3_AVAILABLE

        if self.is_s3:
            if not BOTO3_AVAILABLE:
                raise RuntimeError("boto3 is required for S3 storage. Install it with: pip install boto3")
            self.bucket = settings.s3_bucket_name
            self.client = boto3.client(
                "s3",
                endpoint_url=settings.s3_endpoint_url or None,
                aws_access_key_id=settings.s3_access_key_id,
                aws_secret_access_key=settings.s3_secret_access_key,
                region_name=settings.s3_region or "auto",
            )
            logger.info(
                "FileStorage: S3 mode — bucket=%s endpoint=%s",
                self.bucket,
                settings.s3_endpoint_url,
            )
        else:
            self.bucket = None
            self.client = None
            self.local_dir = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "generated_files"
            )
            os.makedirs(self.local_dir, exist_ok=True)
            logger.info("FileStorage: local mode — dir=%s", self.local_dir)

    async def upload(self, filepath: str, key: str) -> str:
        """Upload a local file to S3. Returns the S3 key.

        In local mode, this is a no-op (file already on disk).
        """
        if not self.is_s3:
            return filepath

        # Determine Content-Type from file extension
        import mimetypes
        content_type, _ = mimetypes.guess_type(filepath)
        extra_args = {}
        if content_type:
            extra_args["ContentType"] = content_type

        def _upload():
            self.client.upload_file(
                filepath, self.bucket, key,
                ExtraArgs=extra_args,
            )

        await asyncio.to_thread(_upload)
        logger.info("Uploaded %s -> s3://%s/%s (type=%s)", filepath, self.bucket, key, content_type)
        return key

    async def upload_from_bytes(self, data: bytes, key: str) -> str:
        """Upload raw bytes to storage. Returns the storage key/path."""
        if not self.is_s3:
            local_path = os.path.join(self.local_dir, key)
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            with open(local_path, "wb") as f:
                f.write(data)
            return local_path

        from io import BytesIO
        import mimetypes

        content_type, _ = mimetypes.guess_type(key)
        extra_args = {}
        if content_type:
            extra_args["ContentType"] = content_type

        def _upload():
            self.client.upload_fileobj(BytesIO(data), self.bucket, key, ExtraArgs=extra_args)

        await asyncio.to_thread(_upload)
        logger.info("Uploaded bytes -> s3://%s/%s (%d bytes, type=%s)", self.bucket, key, len(data), content_type)
        return key

    def get_download_url(self, key: str, expires: int = 3600, filename: str = None) -> str:
        """Generate a presigned download URL (default 1hr expiry).

        In local mode, returns None (caller should use FileResponse).
        """
        if not self.is_s3:
            return None

        params = {"Bucket": self.bucket, "Key": key}
        if filename:
            params["ResponseContentDisposition"] = f'attachment; filename="{filename}"'

        url = self.client.generate_presigned_url(
            "get_object",
            Params=params,
            ExpiresIn=expires,
        )
        return url

    async def delete(self, key: str) -> None:
        """Delete a file from S3.

        In local mode, deletes the local file.
        """
        if not self.is_s3:
            if os.path.exists(key):
                os.remove(key)
            return

        def _delete():
            try:
                self.client.delete_object(Bucket=self.bucket, Key=key)
            except ClientError as e:
                logger.warning("Failed to delete s3://%s/%s: %s", self.bucket, key, e)

        await asyncio.to_thread(_delete)
        logger.info("Deleted s3://%s/%s", self.bucket, key)

    async def exists(self, key: str) -> bool:
        """Check if a file exists in storage."""
        if not self.is_s3:
            return os.path.exists(key)

        def _exists():
            try:
                self.client.head_object(Bucket=self.bucket, Key=key)
                return True
            except ClientError:
                return False

        return await asyncio.to_thread(_exists)


@lru_cache()
def get_storage() -> FileStorage:
    """Get the singleton FileStorage instance."""
    return FileStorage()
