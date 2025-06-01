

import shutil
from copy import deepcopy
from io import BytesIO
from typing import AsyncGenerator
from uuid import UUID
from zipfile import ZIP_DEFLATED, ZipFile

from deva_p1_db.models import User
from deva_p1_db.repositories import (FileRepository, ProjectRepository,
                                     TaskRepository)
from fastapi import Depends, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from fastapi_controllers import Controller, delete, get, patch, post, websocket
from minio import Minio

from back.exceptions import *
from back.get_auth import get_user, get_user_db
from back.schemas.file import FileSchema
from back.schemas.project import (CreateProjectSchema, EditProjectSchema,
                                  ProjectSchema)
from back.schemas.task import ActiveTaskSchema
from back.schemas.user import UserSchema
from back.websocket.start_polling import start_polling
from config import settings
from database.db import Session
from database.redis import get_redis_client
from database.s3 import get_s3_client
from redis.asyncio import Redis


class ProjectController(Controller):
    prefix = "/project"
    tags = ["project"]

    def __init__(self, session: Session) -> None:
        self.session = session
        self.pr = ProjectRepository(self.session)
        self.fr = FileRepository(self.session)
        self.tr = TaskRepository(self.session)

    @post("")
    async def create(self,
                     create_data: CreateProjectSchema,
                     user: User = Depends(get_user_db)
                     ) -> ProjectSchema:
        project = await self.pr.get_by_user_and_name(user, create_data.name)
        if project is not None:
            raise ProjectAlreadyExistsException()
        project = await self.pr.create(
            holder=user,
            name=create_data.name,
            description=create_data.description,
        )
        if project is None:
            raise SendFeedbackToAdminException()
        return ProjectSchema.from_db(project)

    @get("")
    async def list_projects(self,
                            user: User = Depends(get_user_db)
                            ) -> list[ProjectSchema]:
        projects = await self.pr.get_by_user(user)
        return [ProjectSchema.from_db(p) for p in projects]

    @get("/{project_id}")
    async def get_by_id(self,
                        project_id: UUID,
                        user: UserSchema = Depends(get_user)
                        ) -> ProjectSchema:
        project = await self.pr.get_by_id(project_id)
        if project is None:
            raise ProjectNotFoundException(project_id)
        return ProjectSchema.from_db(project)

    @delete("/{project_id}")
    async def delete(self,
                     project_id: UUID,
                     user: UserSchema = Depends(get_user)
                     ):
        project = await self.pr.get_by_id(project_id)
        if project is None:
            raise ProjectNotFoundException(project_id)
        await self.pr.delete(project)
        return {"message": "OK"}

    @patch("/{project_id}")
    async def update(self,
                     project_id: UUID,
                     update_data: EditProjectSchema,
                     user: User = Depends(get_user_db)
                     ):
        project = await self.pr.get_by_id(project_id)
        if project is None:
            raise ProjectNotFoundException(project_id)
        if project.holder_id != user.id:
            raise PermissionDeniedException()
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
            raise ProjectNotFoundException(project_id)
        if project.holder_id != user.id:
            raise PermissionDeniedException()
        files = await self.fr.get_by_project(project)
        return [FileSchema.from_db(f) for f in files]

    @get("/get_active_tasks/{project_id}")
    async def get_active_tasks(self,
                               project_id: UUID,
                               user: UserSchema = Depends(get_user)
                               ) -> list[ActiveTaskSchema]:
        project = await self.pr.get_by_id(project_id)
        if project is None:
            raise ProjectNotFoundException(project_id)
        if project.holder_id != user.id:
            raise PermissionDeniedException()
        return [ActiveTaskSchema.from_db(task) for task in (await self.tr.get_by_project(project)) if task.done is False]

    @get("/download/{project_id}")
    async def download_project(self,
                               project_id: UUID,
                               user: UserSchema = Depends(get_user),
                               minio_client: Minio = Depends(get_s3_client)
                               ):
        project = await self.pr.get_by_id(project_id)
        if project is None:
            raise ProjectNotFoundException(project_id)
        if project.holder_id != user.id:
            raise PermissionDeniedException()

        images = deepcopy(await self.fr.get_active_images(project))
        for image in images:
            image.file_name = f"images/{image.file_name}"
        if project.summary is not None:
            images.append(project.summary)
        if project.transcription is not None:
            images.append(project.transcription)

        zip_stream = BytesIO()
        with ZipFile(zip_stream, "w", ZIP_DEFLATED) as zip_file:
            for image in images:
                obj = minio_client.get_object(
                    bucket_name=settings.minio_bucket,
                    object_name=str(image.id),
                )
                with zip_file.open(image.file_name, "w") as dest_file:
                    shutil.copyfileobj(obj, dest_file, length=1024*64)
                obj.close()
                obj.release_conn()

        zip_stream.seek(0)
        return StreamingResponse(
            zip_stream,
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="{user.login}.zip"'}
        )

    @websocket("/ws/{project_id}")
    async def websocket(self,
                        websocket: WebSocket,
                        project_id: UUID,
                        user: UserSchema = Depends(get_user),
                        redis: Redis = Depends(get_redis_client),
                        ):
        project = await self.pr.get_by_id(project_id)
        if project is None:
            raise ProjectNotFoundException(project_id)
        await websocket.accept()
        try:
            async for item in start_polling(websocket,
                                            redis,
                                            project,
                                            user.id,
                                            self.session):
                await websocket.send_text(item)
        except WebSocketDisconnect:
            pass
        finally:
            await websocket.close()
