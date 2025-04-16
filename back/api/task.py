
from io import BytesIO
from uuid import UUID
from fastapi_controllers import Controller, post
from fastapi import Depends
from minio import Minio

from back.broker import get_broker, send_message
from back.get_auth import get_user_db
from back.main import Session

from fastapi import File, UploadFile, HTTPException
from minio.error import S3Error
import mimetypes
from typing import Annotated
from deva_p1_db.models.user import User
from deva_p1_db.models.task import Task
from deva_p1_db.repositories.file_repository import FileRepository
from deva_p1_db.repositories.project_repository import ProjectRepository
from deva_p1_db.repositories.task_repository import TaskRepository
from database.s3 import S3Type, get_s3_client
from config import settings
from faststream.rabbit import RabbitBroker


class TaskController(Controller):
    prefix = "/task"
    tags = ["task"]

    def __init__(self, session: Session) -> None:
        self.session = session

    @post("/create")
    async def upload_file(self,
                          project_id: str,
                          task_type: str,
                          file: Annotated[UploadFile, File(...)],
                          user: User = Depends(get_user_db),
                          minio_client: Minio = Depends(get_s3_client),
                          broker: RabbitBroker = Depends(get_broker)):
        try:
            pr = ProjectRepository(self.session)
            project = await pr.get_by_id(UUID(project_id))
            if project is None:
                raise HTTPException(
                    status_code=404,
                    detail="project not found"
                )
            if not minio_client.bucket_exists(settings.minio_bucket):
                try:
                    minio_client.make_bucket(settings.minio_bucket)
                except S3Error as e:
                    raise HTTPException(
                        status_code=500,
                        detail=f"bucket creation error: {e.message}"
                    )
            if file.filename is None:
                file.filename = ""

            content_type = (
                mimetypes.guess_type(file.filename)[0]
                or S3Type.undefined.value
            )

            file_data = await file.read()
            file_size = len(file_data)

            fr = FileRepository(self.session)

            db_file = await fr.create(
                user_file_name=file.filename,
                file_type=content_type,
                project=project
            )

            if db_file is None:
                raise HTTPException(
                    status_code=500,
                    detail="server error"
                )

            owr = minio_client.put_object(
                bucket_name=settings.minio_bucket,
                object_name=str(db_file.id),
                data=BytesIO(file_data),
                length=file_size,
                content_type=content_type
            )

            tr = TaskRepository(self.session)
            task = await tr.create(
                task_type=task_type,
                project=project,
                user=user,
                origin_file=db_file
            )
            if task is None:
                raise HTTPException(
                    status_code=500,
                    detail="server error"
                )

            await send_message({"task_id": str(task.id)}, broker)

            return {"task_id": str(task.id)}

        except S3Error as e:
            raise HTTPException(
                status_code=500,
                detail=f"MinIO error: {e.message}"
            )
        finally:
            await file.close()
