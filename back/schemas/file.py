

from typing import Optional
from uuid import UUID

from deva_p1_db.models import File
from pydantic import BaseModel


class FileSchema(BaseModel):
    id: str
    name: str
    file_type: str
    created_date: str
    last_modified_date: str

    @classmethod
    def from_db(cls, file: File):
        return cls(id=str(file.id), 
                   file_type=file.file_type, 
                   name=file.file_name,
                   created_date=file.created_date.isoformat(),
                   last_modified_date=file.last_modified_date.isoformat()
                   )


class FileDownloadURLSchema(BaseModel):
    id: str
    name: str
    file_type: str
    created_date: str
    last_modified_date: str
    download_url: str

    @classmethod
    def from_db(cls, file: File, download_url: str):
        return cls(id=str(file.id), 
                   file_type=file.file_type, 
                   name=file.file_name,
                   created_date=file.created_date.isoformat(),
                   last_modified_date=file.last_modified_date.isoformat(),
                   download_url=download_url
                   )
