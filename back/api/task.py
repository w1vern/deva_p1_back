
import asyncio
from uuid import UUID

from deva_p1_db.enums.file_type import FileCategory, resolve_file_type
from deva_p1_db.enums.task_type import TaskType
from deva_p1_db.models import User
from deva_p1_db.repositories import (FileRepository, ProjectRepository,
                                     TaskRepository)
from fastapi import Depends, Request
from fastapi_controllers import Controller, get, post
from fastapi_sse import sse_handler
from faststream.rabbit import RabbitBroker
from redis.asyncio import Redis

from back.broker import get_broker, send_message_and_cache
from back.config import Config
from back.exceptions import *
from back.get_auth import get_user, get_user_db
from back.schemas.task import ActiveTaskSchema, TaskCreateSchema, TaskSchema
from back.schemas.user import UserSchema
from database.db import Session
from database.redis import RedisType, get_redis_client


class TaskController(Controller):
    prefix = "/task"
    tags = ["task"]

    def __init__(self, session: Session) -> None:
        self.session = session
        self.tr = TaskRepository(self.session)
        self.fr = FileRepository(self.session)
        self.pr = ProjectRepository(self.session)

    @post("")
    async def create_task(self,
                          new_task: TaskCreateSchema,
                          user: User = Depends(get_user_db),
                          broker: RabbitBroker = Depends(get_broker),
                          redis: Redis = Depends(get_redis_client)
                          ) -> ActiveTaskSchema:
        project = await self.pr.get_by_id(new_task.project_id)
        if project is None:
            raise ProjectNotFoundException(new_task.project_id)
        if project.holder_id != user.id:
            raise PermissionDeniedException()
        if project.origin_file is None:
            raise ProjectHasNoOriginFileException()
        pattern = f"{RedisType.task_cache}:{project.id}:"
        keys = await redis.keys(f"{pattern}*")
        if len(keys) > 1:
            raise ProjectAlreadyHasActiveTasksException()
        if len(keys) == 1:
            match keys[0]:
                case val if val == f"{pattern}{TaskType.transcribe.value}":
                    if new_task.task_type != TaskType.frames_extract.value:
                        raise OnlyFramesAfterTranscribeAllowedException()
                case val if val == f"{pattern}{TaskType.frames_extract.value}":
                    if new_task.task_type != TaskType.transcribe.value:
                        raise OnlyTranscribeAfterFramesAllowedException()
                case _:
                    raise ProjectAlreadyHasActiveTasksException()
        match new_task.task_type:
            case TaskType.transcribe.value:
                if project.transcription_id:
                    raise ProjectAlreadyHasTranscriptionException()
            case TaskType.frames_extract.value:
                if project.frames_extract_done:
                    raise ProjectAlreadyHasFramesExtractException()
                if resolve_file_type(project.origin_file.file_type).category == FileCategory.audio.value:
                    raise OriginFileIsAudioException()
            case TaskType.summary_edit.value:
                pass  # no-op: nothing to do
            case TaskType.summary.value:
                if (project.transcription_id is None) \
                    or (
                    (project.frames_extract_done is False)
                    and
                    (resolve_file_type(project.origin_file.file_type).category ==
                     FileCategory.video.value)
                ):
                    task_queue = []
                    origin_task = await self.tr.create(
                        task_type=TaskType.summary.value,
                        project=project,
                        user=user,
                        prompt=new_task.prompt)
                    if origin_task is None:
                        raise SendFeedbackToAdminException()
                    if project.transcription_id is None:
                        transcription_task = await self.tr.create(
                            task_type=TaskType.transcribe.value,
                            project=project, user=user,
                            prompt=new_task.prompt,
                            origin_task=origin_task)
                        if transcription_task is None:
                            raise SendFeedbackToAdminException()
                        task_queue.append(transcription_task)
                    if project.frames_extract_done is False and \
                            resolve_file_type(project.origin_file.file_type).category == FileCategory.video.value:
                        frames_extract_task = await self.tr.create(
                            task_type=TaskType.frames_extract.value,
                            project=project, user=user,
                            prompt=new_task.prompt,
                            origin_task=origin_task)
                        if frames_extract_task is None:
                            raise SendFeedbackToAdminException()
                        task_queue.append(frames_extract_task)
                    summary_task = await self.tr.create(
                        task_type=TaskType.summary.value,
                        project=project,
                        user=user,
                        prompt=new_task.prompt,
                        origin_task=origin_task)
                    if summary_task is None:
                        raise SendFeedbackToAdminException()
                    await self.session.commit()
                    for task in task_queue:
                        await send_message_and_cache(broker, redis, task, project.id)
                    await self.tr.add_subtask_count(origin_task, len(task_queue) + 1)
                    return ActiveTaskSchema.from_db(origin_task)
            case _:
                raise InvalidTaskTypeException()
        task = await self.tr.create(
            task_type=new_task.task_type,
            project=project,
            user=user,
            prompt=new_task.prompt
        )
        if task is None:
            raise SendFeedbackToAdminException()
        await self.session.commit()
        await send_message_and_cache(broker, redis, task, project.id)
        await redis.set(f"{RedisType.project_task_update}:{project.id}", 1, ex=Config.redis_task_status_lifetime)
        return ActiveTaskSchema.from_db(task)


