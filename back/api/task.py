
from uuid import UUID
from fastapi_controllers import Controller, get, post
from fastapi import Depends

from back.broker import get_broker, send_message
from back.get_auth import get_user_db
from back.db import Session

from fastapi import HTTPException
from deva_p1_db.models.user import User
from deva_p1_db.repositories.file_repository import FileRepository
from deva_p1_db.repositories.task_repository import TaskRepository
from back.schemas.file import FileSchema
from faststream.rabbit import RabbitBroker
from deva_p1_db.enums.task_type import TaskType
from deva_p1_db.schemas.task import TaskToAi
from deva_p1_db.enums.file_type import FileType


class TaskController(Controller):
    prefix = "/task"
    tags = ["task"]

    def __init__(self, session: Session) -> None:
        self.session = session
        self.tr = TaskRepository(self.session)
        self.fr = FileRepository(self.session)

    @post("/create")
    async def create_task(self,
                          task_type: TaskType,
                          file_id: UUID,
                          user: User = Depends(get_user_db),
                          broker: RabbitBroker = Depends(get_broker)):
        file = await self.fr.get_by_id(file_id)
        if file is None:
            raise HTTPException(
                status_code=404,
                detail="file not found"
            )
        project = file.project

        task = await self.tr.create(
            task_type=task_type,
            project=project,
            user=user,
            origin_file=file
        )
        if task is None:
            raise HTTPException(
                status_code=500,
                detail="server error"
            )
        await self.session.commit()



        if task_type == TaskType.summary and not "image_" in file.file_type:
            raise HTTPException(
                status_code=400,
                detail="file must be image"
            )
        
        if task_type == TaskType.transcribe and not "audio_" in file.file_type or "video_" in file.file_type:
            raise HTTPException(
                status_code=400,
                detail="file must be audio or video"
        )
        if task_type == TaskType.summary and file.file_type != FileType.text_json.value:
            raise HTTPException(
                status_code=400,
                detail="file must be json"
            )

        await send_message(broker, task_type.value + "_task", TaskToAi(task_id=task.id))

        return {"task_id": str(task.id)}

    @get("/get/{task_id}")
    async def get_files_from_task(self, 
                                  task_id: str, 
                                  user: User = Depends(get_user_db), 
                                  ) -> list[FileSchema]:
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
        files = await self.fr.get_by_task(task)
        return [FileSchema.from_db(f) for f in files]
        
