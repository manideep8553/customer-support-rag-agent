import os
import uuid
import logging
import aiofiles
from pathlib import Path
from typing import Optional, BinaryIO
from datetime import datetime

from backend.config import settings
from backend.enterprise.file_store.models import StoredFile, FileStoreBackend

logger = logging.getLogger("gigacorp.filestore")


class FileStore:
    def __init__(self):
        self._backend = FileStoreBackend(settings.file_storage_backend)
        self._local_path = settings.upload_dir
        self._local_path.mkdir(parents=True, exist_ok=True)
        self._s3_client = None

        if self._backend == FileStoreBackend.S3:
            self._init_s3()

    def _init_s3(self):
        try:
            import boto3
            session_kwargs = {
                "region_name": settings.s3_region,
            }
            if settings.s3_access_key_id:
                session_kwargs["aws_access_key_id"] = settings.s3_access_key_id
                session_kwargs["aws_secret_access_key"] = settings.s3_secret_access_key
            if settings.s3_endpoint_url:
                session_kwargs["endpoint_url"] = settings.s3_endpoint_url

            session = boto3.Session(**session_kwargs)
            self._s3_client = session.client("s3")
            logger.info("S3 file store initialized (bucket: %s)", settings.s3_bucket)
        except Exception as e:
            logger.warning("S3 initialization failed, falling back to local storage: %s", e)
            self._backend = FileStoreBackend.LOCAL

    def _get_ext(self, filename: str) -> str:
        parts = filename.rsplit(".", 1)
        return f".{parts[1].lower()}" if len(parts) > 1 else ""

    def _sanitize_filename(self, filename: str) -> str:
        safe = "".join(c for c in filename if c.isalnum() or c in "._- ")
        return safe.strip() or "unnamed"

    async def upload(
        self,
        content: bytes,
        original_filename: str,
        content_type: Optional[str] = None,
        uploaded_by: Optional[str] = None,
        is_public: bool = False,
        metadata: Optional[dict] = None,
    ) -> StoredFile:
        file_id = str(uuid.uuid4())
        ext = self._get_ext(original_filename)
        safe_name = self._sanitize_filename(original_filename)
        stored_name = f"{file_id}{ext}"
        size_bytes = len(content)

        if self._backend == FileStoreBackend.S3:
            stored_path = f"uploads/{stored_name}"
            try:
                extra_args = {}
                if content_type:
                    extra_args["ContentType"] = content_type
                if is_public:
                    extra_args["ACL"] = "public-read"

                self._s3_client.put_object(
                    Bucket=settings.s3_bucket,
                    Key=stored_path,
                    Body=content,
                    **extra_args,
                )
                logger.info("File uploaded to S3: %s/%s", settings.s3_bucket, stored_path)
            except Exception as e:
                logger.error("S3 upload failed: %s", e)
                raise
        else:
            date_path = datetime.utcnow().strftime("%Y/%m/%d")
            dir_path = self._local_path / date_path
            dir_path.mkdir(parents=True, exist_ok=True)
            stored_path = str(dir_path / stored_name)

            async with aiofiles.open(stored_path, "wb") as f:
                await f.write(content)

            logger.info("File saved locally: %s", stored_path)

        return StoredFile(
            id=file_id,
            original_filename=safe_name,
            stored_path=stored_path,
            content_type=content_type or "application/octet-stream",
            size_bytes=size_bytes,
            bucket=settings.s3_bucket if self._backend == FileStoreBackend.S3 else None,
            backend=self._backend,
            uploaded_by=uploaded_by,
            is_public=is_public,
            metadata=metadata or {},
        )

    async def get(self, stored_path: str) -> Optional[bytes]:
        try:
            if self._backend == FileStoreBackend.S3:
                response = self._s3_client.get_object(
                    Bucket=settings.s3_bucket,
                    Key=stored_path,
                )
                return response["Body"].read()
            else:
                async with aiofiles.open(stored_path, "rb") as f:
                    return await f.read()
        except Exception as e:
            logger.warning("Failed to read file %s: %s", stored_path, e)
            return None

    async def delete(self, stored_path: str) -> bool:
        try:
            if self._backend == FileStoreBackend.S3:
                self._s3_client.delete_object(
                    Bucket=settings.s3_bucket,
                    Key=stored_path,
                )
            else:
                os.remove(stored_path)
            logger.info("File deleted: %s", stored_path)
            return True
        except Exception as e:
            logger.warning("Failed to delete file %s: %s", stored_path, e)
            return False

    async def get_url(self, stored_path: str) -> str:
        if self._backend == FileStoreBackend.S3:
            from botocore.exceptions import ClientError
            try:
                url = self._s3_client.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": settings.s3_bucket, "Key": stored_path},
                    ExpiresIn=3600,
                )
                return url
            except Exception as e:
                logger.warning("Failed to generate presigned URL: %s", e)
                return ""
        else:
            return f"/api/v1/files/{stored_path}"


_file_store: Optional[FileStore] = None


def get_file_store() -> FileStore:
    global _file_store
    if _file_store is None:
        _file_store = FileStore()
    return _file_store
