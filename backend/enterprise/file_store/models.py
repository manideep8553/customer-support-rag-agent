import enum
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class FileStoreBackend(str, enum.Enum):
    LOCAL = "local"
    S3 = "s3"


class StoredFile(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    original_filename: str
    stored_path: str
    content_type: str
    size_bytes: int
    bucket: Optional[str] = None
    backend: FileStoreBackend = FileStoreBackend.LOCAL
    uploaded_by: Optional[str] = None
    uploaded_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    is_public: bool = False
    metadata: dict = Field(default_factory=dict)
