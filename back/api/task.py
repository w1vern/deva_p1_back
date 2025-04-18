
from uuid import UUID
from fastapi_controllers import Controller, post
from fastapi import Depends
from minio import Minio

from back.broker import get_broker, send_message
from back.get_auth import get_user_db
from back.db import Session

from fastapi import HTTPException
from minio.error import S3Error
from deva_p1_db.models.user import User
from deva_p1_db.repositories.file_repository import FileRepository
from deva_p1_db.repositories.project_repository import ProjectRepository
from deva_p1_db.repositories.task_repository import TaskRepository
from database.s3 import get_s3_client
from config import settings
from faststream.rabbit import RabbitBroker
from deva_p1_db.enums.task_type import TaskType


class TaskController(Controller):
    prefix = "/task"
    tags = ["task"]

    def __init__(self, session: Session) -> None:
        self.session = session
        self.tr = TaskRepository(self.session)
        self.fr = FileRepository(self.session)

    @post("/create")
    async def create_task(self,
                          project_id: str,
                          task_type: TaskType,
                          file_id: UUID,
                          user: User = Depends(get_user_db),
                          broker: RabbitBroker = Depends(get_broker)):
        pass
        # pr = ProjectRepository(self.session)
        # project = await pr.get_by_id(UUID(project_id))
        # if project is None:
        #     raise HTTPException(
        #         status_code=404,
        #         detail="project not found"
        #     )
        

        # task = await self.tr.create(
        #     task_type=task_type,
        #     project=project,
        #     user=user,
        #     origin_file=db_file
        # )
        # if task is None:
        #     raise HTTPException(
        #         status_code=500,
        #         detail="server error"
        #     )

        # await send_message(broker, {"task_id": str(task.id)}, "task")

        # return {"task_id": str(task.id)}

        

    @post("/get/{task_id}")
    async def get_file(self, task_id: str, user: User = Depends(get_user_db), minio_client: Minio = Depends(get_s3_client)):
        task = await self.tr.get_by_id(UUID(task_id))
        if task is None:
            raise HTTPException(
                status_code=404,
                detail="task not found"
            )
        if task.user_id != user.id:
            raise HTTPException(
                status_code=403,
                detail="permission denied"
            )
        if task.origin_file is None:
            raise HTTPException(
                status_code=404,
                detail="file not found"
            )
        
        pass