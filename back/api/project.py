

from uuid import UUID

from deva_p1_db.models import User
from deva_p1_db.repositories import (FileRepository, ProjectRepository,
                                     TaskRepository)
from fastapi import Depends, HTTPException
from fastapi_controllers import Controller, delete, get, patch, post

from back.get_auth import get_user, get_user_db
from back.schemas.file import FileSchema
from back.schemas.project import (CreateProjectSchema, EditProjectSchema,
                                  ProjectSchema)
from back.schemas.task import ActiveTaskSchema
from back.schemas.user import UserSchema
from database.db import Session


class ProjectController(Controller):
    prefix = "/project"
    tags = ["project"]

    def __init__(self, session: Session) -> None:
        self.session = session
        self.pr = ProjectRepository(self.session)
        self.fr = FileRepository(self.session)
        self.tr = TaskRepository(self.session)

    @post("/")
    async def create(self,
                     create_data: CreateProjectSchema,
                     user: User = Depends(get_user_db)
                     ) -> ProjectSchema:
        project = await self.pr.get_by_user_and_name(user, create_data.name)
        if project is not None:
            raise HTTPException(status_code=400, detail="project already exists")
        project = await self.pr.create(
            holder=user,
            name=create_data.name,
            description=create_data.description,
        )
        if project is None:
            raise HTTPException(
                status_code=500, detail="project creation error")
        return ProjectSchema.from_db(project)
    
    @get("/{project_id}/")
    async def get_by_id(self,
                  project_id: UUID,
                  user: UserSchema = Depends(get_user)
                  ) -> ProjectSchema:
        project = await self.pr.get_by_id(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="project not found")
        return ProjectSchema.from_db(project)

    @delete("/{project_id}")
    async def delete(self,
                     project_id: UUID,
                     user: UserSchema = Depends(get_user)
                     ):
        project = await self.pr.get_by_id(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="project not found")
        await self.pr.delete(project)
        return {"message": "OK"}

    @get("/list")
    async def list_projects(self,
                            user: User = Depends(get_user_db)
                            ) -> list[ProjectSchema]:
        projects = await self.pr.get_by_user(user)
        return [ProjectSchema.from_db(p) for p in projects]

    @patch("/{project_id}")
    async def update(self,
                     project_id: UUID,
                     update_data: EditProjectSchema,
                     user: User = Depends(get_user_db)
                     ):
        project = await self.pr.get_by_id(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="project not found")
        if project.holder_id != user.id:
            raise HTTPException(status_code=403, detail="permission denied")
        await self.pr.update(project,
                             update_data.name,
                             update_data.description)
        return {"message": "OK"}

    @get("/get_all_files/{project_id}")
    async def get_files_from_project(self,
                                     project_id: UUID,
                                     user: UserSchema = Depends(get_user)
                                     ) -> list[FileSchema]:
        project = await self.pr.get_by_id(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="project not found")
        if project.holder_id != user.id:
            raise HTTPException(status_code=403, detail="permission denied")
        files = await self.fr.get_by_project(project)
        return [FileSchema.from_db(f) for f in files]

    @get("/get_active_tasks/{project_id}")
    async def get_active_tasks(self,
                               project_id: str,
                               user: UserSchema = Depends(get_user)
                               ) -> list[ActiveTaskSchema]:
        project = await self.pr.get_by_id(UUID(project_id))
        if project is None:
            raise HTTPException(status_code=404, detail="project not found")
        if project.holder_id != user.id:
            raise HTTPException(status_code=403, detail="permission denied")
        return [ActiveTaskSchema.from_db(task) for task in (await self.tr.get_by_project(project))]
