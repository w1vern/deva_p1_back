
from datetime import datetime
from uuid import UUID

from deva_p1_db.models import Project
from pydantic import BaseModel


class CreateProjectSchema(BaseModel):
    name: str
    description: str


class EditProjectSchema(BaseModel):
    name: str | None = None
    description: str | None = None


class ProjectSchema(BaseModel):
    id: UUID
    name: str
    description: str
    created_date: datetime
    last_modified_date: datetime
    origin_file_id: UUID | None = None
    transcription_id: UUID | None = None
    summary_id: UUID | None = None
    frames_extract_done: bool

    @classmethod
    def from_db(cls, project: Project) -> "ProjectSchema":
        return cls(**project.__dict__)
