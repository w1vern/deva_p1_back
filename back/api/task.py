

from uuid import uuid4
from deva_p1_db.enums.file_type import FileCategory, resolve_file_type
from deva_p1_db.enums.task_type import TaskType
from deva_p1_db.models import Project, User
from deva_p1_db.repositories import TaskRepository
from fastapi import APIRouter, Depends
from faststream.rabbit import RabbitBroker
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from back.broker import get_broker, send_message_and_cache
from back.config import Config
from back.depends import get_project, get_project_editor, get_task_repo
from back.exceptions import *
from back.schemas.task import ActiveTaskSchema, TaskCreateSchema
from database.database import session_manager
from database.redis import RedisType, get_redis_client

router = APIRouter(prefix="/task", tags=["task"])


@router.post("/{project_id}")
async def create_task(new_task: TaskCreateSchema,
                      project: Project = Depends(get_project),
                      user: User = Depends(get_project_editor),
                      broker: RabbitBroker = Depends(get_broker),
                      redis: Redis = Depends(get_redis_client),
                      tr: TaskRepository = Depends(get_task_repo),
                      session: AsyncSession = Depends(session_manager.session)
                      ) -> ActiveTaskSchema:
    if project.origin_file is None:
        raise ProjectHasNoOriginFileException()
    if new_task.task_type == TaskType.summary.value:
        if len([task for task in await tr.get_by_project(project) if task.done is False]) > 0:
            raise SummaryInTimeWithOtherTasksException()
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
                origin_task = await tr.create(
                    task_type=TaskType.summary.value,
                    project=project,
                    user=user,
                    prompt=new_task.prompt)
                if origin_task is None:
                    raise SendFeedbackToAdminException()
                if project.transcription_id is None:
                    transcription_task = await tr.create(
                        task_type=TaskType.transcribe.value,
                        project=project, user=user,
                        prompt=new_task.prompt,
                        origin_task=origin_task)
                    if transcription_task is None:
                        raise SendFeedbackToAdminException()
                    task_queue.append(transcription_task)
                if project.frames_extract_done is False and \
                        resolve_file_type(project.origin_file.file_type).category == FileCategory.video.value:
                    frames_extract_task = await tr.create(
                        task_type=TaskType.frames_extract.value,
                        project=project, user=user,
                        prompt=new_task.prompt,
                        origin_task=origin_task)
                    if frames_extract_task is None:
                        raise SendFeedbackToAdminException()
                    task_queue.append(frames_extract_task)
                summary_task = await tr.create(
                    task_type=TaskType.summary.value,
                    project=project,
                    user=user,
                    prompt=new_task.prompt,
                    origin_task=origin_task)
                if summary_task is None:
                    raise SendFeedbackToAdminException()
                await session.commit()
                for task in task_queue:
                    await send_message_and_cache(broker, redis, task, project.id)
                await tr.add_subtask_count(origin_task, len(task_queue) + 1)
                await redis.set(f"{RedisType.project_task_update}:{project.id}", str(uuid4()), ex=Config.redis_task_status_lifetime)
                return ActiveTaskSchema.from_db(origin_task)
        case _:
            raise InvalidTaskTypeException()
    task_type = new_task.task_type
    if task_type == TaskType.summary_edit.value:
        task_type = TaskType.summary.value
    task = await tr.create(
        task_type=task_type,
        project=project,
        user=user,
        prompt=new_task.prompt
    )
    if task is None:
        raise SendFeedbackToAdminException()
    await session.commit()
    await send_message_and_cache(broker, redis, task, project.id)
    await redis.set(f"{RedisType.project_task_update}:{project.id}", str(uuid4()), ex=Config.redis_task_status_lifetime)
    return ActiveTaskSchema.from_db(task)
