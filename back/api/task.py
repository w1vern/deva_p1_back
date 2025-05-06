
import asyncio
from uuid import UUID

from deva_p1_db.enums.file_type import FileCategory, resolve_file_type
from deva_p1_db.enums.task_type import TaskType
from deva_p1_db.models import Task, User
from deva_p1_db.repositories import (FileRepository, ProjectRepository,
                                     TaskRepository)
from deva_p1_db.schemas.task import TaskToAi
from fastapi import Depends, HTTPException, Request
from fastapi_controllers import Controller, get, post
from fastapi_sse import sse_handler
from faststream.rabbit import RabbitBroker
from redis.asyncio import Redis

from back.broker import get_broker, send_message_and_cache
from back.config import Config
from back.get_auth import get_user, get_user_db
from back.schemas.task import (ActiveTaskSchema,
                               TaskCreateSchema, TaskSchema)
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
            raise HTTPException(
                status_code=404,
                detail="project not found"
            )
        if project.holder_id != user.id:
            raise HTTPException(
                status_code=403,
                detail="permission denied"
            )
        if project.origin_file is None:
            raise HTTPException(
                status_code=400,
                detail="project has no origin file"
            )
        pattern = f"{RedisType.task_cache}:{project.id}:"
        keys = await redis.keys(f"{pattern}*")
        if len(keys) > 1:
            raise HTTPException(
                status_code=400,
                detail="project already has active tasks"
            )
        if len(keys) == 1:
            match keys[0]:
                case val if val == f"{pattern}{TaskType.transcribe.value}":
                    if new_task.task_type != TaskType.frames_extract.value:
                        raise HTTPException(
                            status_code=400,
                            detail="you can create only frames extract task after transcribe task"
                        )
                case val if val == f"{pattern}{TaskType.frames_extract.value}":
                    if new_task.task_type != TaskType.transcribe.value:
                        raise HTTPException(
                            status_code=400,
                            detail="you can create only transcribe task after frames extract task"
                        )
                case _:
                    raise HTTPException(
                        status_code=400,
                        detail="project already has active tasks"
                    )
        match new_task.task_type:
            case TaskType.transcribe.value:
                if project.transcription_id is not None:
                    raise HTTPException(
                        status_code=400,
                        detail="project already has transcription"
                    )
            case TaskType.frames_extract.value:
                if project.frames_extract_done:
                    raise HTTPException(
                        status_code=400,
                        detail="project already has frames extract"
                    )
                if resolve_file_type(project.origin_file.file_type).category == FileCategory.audio.value:
                    raise HTTPException(
                        status_code=400,
                        detail="project origin file is audio, can't extract frames"
                    )
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
                        raise HTTPException(
                            status_code=500,
                            detail="server error"
                        )
                    if project.transcription_id is None:
                        transcription_task = await self.tr.create(
                            task_type=TaskType.transcribe.value,
                            project=project, user=user,
                            prompt=new_task.prompt,
                            origin_task=origin_task)
                        if transcription_task is None:
                            raise HTTPException(
                                status_code=500,
                                detail="server error"
                            )
                        task_queue.append(transcription_task)
                    if project.frames_extract_done is False and \
                            resolve_file_type(project.origin_file.file_type).category == FileCategory.video.value:
                        frames_extract_task = await self.tr.create(
                            task_type=TaskType.frames_extract.value,
                            project=project, user=user,
                            prompt=new_task.prompt,
                            origin_task=origin_task)
                        if frames_extract_task is None:
                            raise HTTPException(
                                status_code=500,
                                detail="server error"
                            )
                        task_queue.append(frames_extract_task)
                    summary_task = await self.tr.create(
                        task_type=TaskType.summary.value,
                        project=project,
                        user=user,
                        prompt=new_task.prompt,
                        origin_task=origin_task)
                    if summary_task is None:
                        raise HTTPException(
                            status_code=500,
                            detail="server error"
                        )
                    await self.session.commit()
                    for task in task_queue:
                        await send_message_and_cache(broker, redis, task, project.id)
                    await self.tr.add_subtask_count(origin_task, len(task_queue) + 1)
                    return ActiveTaskSchema.from_db(origin_task)
            case _:
                raise HTTPException(
                    status_code=400,
                    detail="invalid task type"
                )
        task = await self.tr.create(
            task_type=new_task.task_type,
            project=project,
            user=user,
            prompt=new_task.prompt
        )
        if task is None:
            raise HTTPException(
                status_code=500,
                detail="server error"
            )
        await self.session.commit()
        await send_message_and_cache(broker, redis, task, project.id)
        return ActiveTaskSchema.from_db(task)

    @get("/sse/{task_id}")
    @sse_handler()
    async def sse_task_response(self,
                                task_id: UUID,
                                request: Request,
                                user: UserSchema = Depends(get_user),
                                redis: Redis = Depends(get_redis_client)
                                ):
        done_cache_key_template = f"{RedisType.task}:"
        status_cache_key = f"{RedisType.task_status}:"
        main_task = await self.tr.get_by_id(task_id)
        prev_state = {}
        prev_state_done = {}
        if main_task is None:
            raise HTTPException(status_code=404, detail="task not found")
        tasks = await self.tr.get_by_origin_task(main_task)
        if len(tasks) == 0:
            tasks.append(main_task)
        counter = 0
        iterations = 0
        while True:
            iterations += 1
            if await request.is_disconnected():
                break
            for task in tasks:
                cached = await redis.get(f"{RedisType.task_error}:{task.id}")
                if cached:
                    raise HTTPException(
                        status_code=500,
                        detail=cached
                    )
                cached = await redis.get(f"{status_cache_key}{task.id}")
                if cached:
                    if cached != prev_state.get(task.id):
                        prev_state[task.id] = cached
                        yield TaskSchema(id=task.id,
                                         done=False,
                                         status=cached,
                                         task_type=task.task_type)
                cached = await redis.get(f"{done_cache_key_template}{task.id}")
                if cached:
                    if cached != prev_state_done.get(task.id):
                        prev_state_done[task.id] = cached
                        yield TaskSchema(id=task.id, done=True, status=1, task_type=task.task_type)
                        counter += 1
            if counter >= len(tasks):
                break
            if iterations > Config.sse_max_iterations:
                raise HTTPException(
                    status_code=500,
                    detail="too long polling"
                )
            await asyncio.sleep(Config.sse_task_polling_interval)
        if len(tasks) > 1:
            yield TaskSchema(id=task_id, done=True, status=1, task_type=main_task.task_type)
        print("goodbye")
