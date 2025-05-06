

from datetime import datetime
from importlib import metadata
from uuid import UUID

from deva_p1_db.models import File
from pydantic import BaseModel


class FileSchema(BaseModel):
    id: UUID
    file_name: str
    file_type: str
    created_date: datetime
    last_modified_date: datetime

    metadata_is_hide: bool | None = None
    metadata_text: str | None = None
    metadata_timecode: float | None = None

    @classmethod
    def from_db(cls, file: File):
        return cls(**file.__dict__)


class FileDownloadURLSchema(BaseModel):
    id: UUID
    file_name: str
    file_type: str
    created_date: datetime
    last_modified_date: datetime
    download_url: str

    @classmethod
    def from_db(cls, file: File, download_url: str):
        return cls(**file.__dict__, download_url=download_url)
    
class FileEditSchema(BaseModel):
    file_name: str | None = None
    metadata_is_hide: bool | None = None
    metadata_text: str | None = None
    metadata_timecode: float | None = None
