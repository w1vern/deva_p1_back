


from datetime import datetime, UTC
from uuid import UUID
from fastapi import Depends, HTTPException
from fastapi_controllers import Controller, get, post

from back.db import Session
from deva_p1_db.models import User, Project
from deva_p1_db.repositories import ProjectRepository

from back.get_auth import get_user_db
from back.schemas.project import CreateProjectSchema, ProjectSchema, EditProjectSchema


class ProjectController(Controller):
    __prefix__ = "/project"
    __tags__ = ["project"]

    def __init__(self, session: Session) -> None:
        self.session = session
        self.pr = ProjectRepository(self.session)

    @post("/create")
    async def create(self, create_data: CreateProjectSchema, user: User = Depends(get_user_db)) -> ProjectSchema:
        project = await self.pr.create(create_data.name, create_data.description, user)
        if project is None:
            raise HTTPException(status_code=500, detail="project creation error")
        return ProjectSchema.from_db(project)

    @post("/delete")
    async def delete(self, project_id: str, user: User = Depends(get_user_db)):
        project = await self.pr.get_by_id(UUID(project_id))
        if project is None:
            raise HTTPException(status_code=404, detail="project not found")
        await self.pr.delete(project)
        return {"message": "OK"}

    @get("/list")
    async def list(self, user: User = Depends(get_user_db)) -> list[ProjectSchema]:
        projects = await self.pr.get_by_user(user)
        return [ProjectSchema.from_db(p) for p in projects]

    @post("/update")
    async def update(self, update_data: EditProjectSchema, user: User = Depends(get_user_db)):
        project = await self.pr.get_by_id(UUID(update_data.id))
        if project is None:
            raise HTTPException(status_code=404, detail="project not found")
        if project.holder_id != user.id:
            raise HTTPException(status_code=403, detail="permission denied")
        await self.pr.update(project, 
                             update_data.name, 
                             update_data.description, 
                             datetime.now(UTC).replace(tzinfo=UTC))
        return {"message": "OK"}



