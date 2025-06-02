

import shutil
from copy import deepcopy
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from deva_p1_db.models import Project, User
from deva_p1_db.repositories import (FileRepository, InvitedUserRepository,
                                     ProjectRepository, TaskRepository)
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from minio import Minio
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from back.depends import (get_file_repo, get_project, get_project_editor,
                          get_project_repo, get_project_viewer, get_task_repo,
                          get_user_db)
from back.exceptions import *
from back.schemas.file import FileSchema
from back.schemas.project import (CreateProjectSchema, EditProjectSchema,
                                  ProjectSchema)
from back.schemas.task import ActiveTaskSchema
from back.websocket.start_polling import start_polling
from config import settings
from database.database import session_manager
from database.minio import get_s3_client
from database.redis import get_redis_client

from .share import router as share_router

router = APIRouter(prefix="/project", tags=["project"])

router.include_router(share_router)


@router.post("")
async def create(create_data: CreateProjectSchema,
                 user: User = Depends(get_user_db),
                 pr: ProjectRepository = Depends(get_project_repo)
                 ) -> ProjectSchema:
    project = await pr.get_by_user_and_name(user, create_data.name)
    if project is not None:
        raise ProjectAlreadyExistsException()
    project = await pr.create(
        holder=user,
        name=create_data.name,
        description=create_data.description,
    )
    if project is None:
        raise SendFeedbackToAdminException()
    return ProjectSchema.from_db(project)


@router.get("")
async def list_projects(user: User = Depends(get_user_db),
                        pr: ProjectRepository = Depends(get_project_repo)
                        ) -> list[ProjectSchema]:
    projects = await pr.get_by_user(user)
    return [ProjectSchema.from_db(p) for p in projects]


@router.get("/{project_id}")
async def get_by_id(project: Project = Depends(get_project),
                    user: User = Depends(get_project_viewer)
                    ) -> ProjectSchema:
    return ProjectSchema.from_db(project)


@router.delete("/{project_id}")
async def delete(project: Project = Depends(get_project),
                 user: User = Depends(get_project_editor),
                 pr: ProjectRepository = Depends(get_project_repo)
                 ):
    await pr.delete(project)
    return {"message": "OK"}


@router.patch("/{project_id}")
async def update(update_data: EditProjectSchema,
                 project: Project = Depends(get_project),
                 user: User = Depends(get_project_editor),
                 pr: ProjectRepository = Depends(get_project_repo)
                 ):
    await pr.update(project,
                    update_data.name,
                    update_data.description)
    return {"message": "OK"}


@router.get("/get_all_files/{project_id}")
async def get_files_from_project(project: Project = Depends(get_project),
                                 user: User = Depends(get_project_viewer),
                                 fr: FileRepository = Depends(get_file_repo)
                                 ) -> list[FileSchema]:
    files = await fr.get_by_project(project)
    return [FileSchema.from_db(f) for f in files]


@router.get("/get_active_tasks/{project_id}")
async def get_active_tasks(project: Project = Depends(get_project),
                           user: User = Depends(get_project_viewer),
                           tr: TaskRepository = Depends(get_task_repo)
                           ) -> list[ActiveTaskSchema]:
    return [ActiveTaskSchema.from_db(task) for task in (await tr.get_by_project(project)) if task.done is False]


@router.get("/download/{project_id}")
async def download_project(project: Project = Depends(get_project),
                           user: User = Depends(get_project_viewer),
                           minio_client: Minio = Depends(get_s3_client),
                           fr: FileRepository = Depends(get_file_repo)
                           ):
    images = deepcopy(await fr.get_active_images(project))
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


@router.websocket("/ws/{project_id}")
async def websocket(websocket: WebSocket,
                    project: Project = Depends(get_project),
                    user: User = Depends(get_project_viewer),
                    redis: Redis = Depends(get_redis_client),
                    session: AsyncSession = Depends(session_manager.session)
                    ):
    print("websocket~~!!!!!!")
    await websocket.accept()
    try:
        await websocket.send_json({"message": "Connected"})
        async for item in start_polling(websocket,
                                        redis,
                                        project,
                                        user.id,
                                        session):
            await websocket.send_text(item)
    except WebSocketDisconnect:
        pass
    finally:
        await websocket.close()
