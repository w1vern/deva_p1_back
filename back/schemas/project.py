
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

    @classmethod
    def from_db(cls, project: Project) -> "ProjectSchema":
        return cls(
            id=str(project.id),
            name=project.name,
            description=project.description,
            created_date=project.created_date.isoformat(),
            last_modified_date=project.last_modified_date.isoformat())
    
