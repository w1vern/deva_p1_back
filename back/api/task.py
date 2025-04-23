
from hmac import new
from uuid import UUID

from deva_p1_db.enums.file_type import FileTypes, resolve_file_type, FileCategory
from deva_p1_db.enums.task_type import TaskType
from deva_p1_db.models import User
from deva_p1_db.repositories import FileRepository, TaskRepository, ProjectRepository
from deva_p1_db.schemas.task import TaskToAi
from fastapi import Depends, HTTPException
from fastapi_controllers import Controller, get, post
from faststream.rabbit import RabbitBroker

from back.broker import get_broker, send_message
from back.get_auth import get_user_db
from back.schemas.file import FileSchema
from back.schemas.task import TaskCreateSchema
from database.db import Session


class TaskController(Controller):
    prefix = "/task"
    tags = ["task"]

    def __init__(self, session: Session) -> None:
        self.session = session
        self.tr = TaskRepository(self.session)
        self.fr = FileRepository(self.session)
        self.pr = ProjectRepository(self.session)

    @post("/create")
    async def create_task(self,
                          new_task: TaskCreateSchema,
                          user: User = Depends(get_user_db),
                          broker: RabbitBroker = Depends(get_broker)):
        if new_task.task_type not in [TaskType.transcribe.value, TaskType.frames_extract.value, TaskType.summary.value, TaskType.summary_edit.value]:
            raise HTTPException(
                status_code=400,
                detail="invalid task type"
            )

        project = await self.pr.get_by_id(UUID(new_task.project_id))
        if project is None:
            raise HTTPException(
                status_code=404,
                detail="project not found"
            )
        if project.holder_id != user.id:
            raise HTTPException(
                status_code=403,
                detail="permission denied"
            )
        if project.origin_file_id is None:
            raise HTTPException(
                status_code=400,
                detail="project has no origin file"
            )
        transcription_done = project.transcription_id is not None
        frames_extract_done = project.frames_extract_done
        summary_done = project.summary_id is not None
        if new_task.task_type is TaskType.transcribe and transcription_done:
            raise HTTPException(
                status_code=400,
                detail="project already has transcription"
            )
        if new_task.task_type is TaskType.frames_extract and frames_extract_done:
            raise HTTPException(
                status_code=400,
                detail="project already has frames extract"
            )
        if new_task.task_type is TaskType.summary_edit and not summary_done:
            raise HTTPException(
                status_code=400,
                detail="project has no summary"
            )

        if resolve_file_type(project.origin_file.file_type).category is FileCategory.audio.value \
                and new_task.task_type is TaskType.frames_extract:
            raise HTTPException(
                status_code=400,
                detail="project origin file is audio, can't extract frames"
            )
        origin_task = await self.tr.create(
            task_type=new_task.task_type,
            project=project,
            user=user,
            prompt=new_task.prompt if new_task.prompt is not None else ""
        )
        if origin_task is None:
            raise HTTPException(
                status_code=500,
                detail="server error"
            )
        if new_task.task_type is TaskType.summary.value:
            if not transcription_done:
                transcription_task = await self.tr.create(
                    task_type=TaskType.transcribe.value,
                    project=project,
                    user=user,
                    prompt=new_task.prompt if new_task.prompt is not None else ""
                    origin_task=origin_task
                )
        else:
            await self.session.commit()
            await send_message(broker, new_task.task_type + "_task", TaskToAi(task_id=origin_task.id))

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
