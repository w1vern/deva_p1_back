
from typing import Optional
from uuid import UUID

from deva_p1_db.models import Project
from pydantic import BaseModel


class CreateProjectSchema(BaseModel):
    name: str
    description: str


class EditProjectSchema(BaseModel):
    id: str
    name: str | None
    description: str | None


class ProjectSchema(BaseModel):
    id: str
    name: str
    description: str
    created_date: str
    last_modified_date: str
    origin_file_id: Optional[str]
    transcription_file_id: Optional[str]
    summary_file_id: Optional[str]
    frames_extract_done: bool

    @classmethod
    def from_db(cls, project: Project) -> "ProjectSchema":
        return cls(
            id=str(project.id),
            name=project.name,
            description=project.description,
            created_date=project.created_date.isoformat(),
            last_modified_date=project.last_modified_date.isoformat(),
            origin_file_id=str(project.origin_file_id) if project.origin_file_id is not None else None,
            transcription_file_id=str(project.transcription_id) if project.transcription_id is not None else None,
            summary_file_id=str(project.summary_id) if project.summary_id is not None else None,
            frames_extract_done=project.frames_extract_done
        )
    
