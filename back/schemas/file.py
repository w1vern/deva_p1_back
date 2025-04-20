

from typing import Optional
from pydantic import BaseModel
from deva_p1_db.models import File

class FileSchema(BaseModel):
    id: str
    name: str
    download_url: Optional[str] = None

    @classmethod
    def from_db(cls, file: File):
        return cls(id=str(file.id), name=file.user_file_name)
    
class FileDownloadURLSchema(BaseModel):
    id: str
    name: str
    download_url: str

    @classmethod
    def from_db(cls, file: File, url: str):
        return cls(id=str(file.id), name=file.user_file_name, download_url=url)