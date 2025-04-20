

from typing import Optional
from pydantic import BaseModel
from deva_p1_db.models import File


class FileSchema(BaseModel):
    id: str
    name: str
    file_type: str
    created_date: str
    last_modified_date: str
    download_url: Optional[str] = None

    @classmethod
    def from_db(cls, file: File):
        return cls(id=str(file.id), 
                   file_type=file.file_type, 
                   name=file.user_file_name,
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
                   name=file.user_file_name,
                   created_date=file.created_date.isoformat(),
                   last_modified_date=file.last_modified_date.isoformat(),
                   download_url=download_url
                   )
