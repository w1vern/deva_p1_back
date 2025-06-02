

import asyncio
from typing import Any, AsyncGenerator
from uuid import UUID

from deva_p1_db.models import Project, Task
from deva_p1_db.repositories import ProjectRepository, TaskRepository
from fastapi import WebSocket, WebSocketDisconnect
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from back.config import Config
from back.exceptions import *
from back.schemas import ProjectSchema, TaskSchema, WebsocketMessage
from database.redis import RedisType


async def redis_get_and_delete(redis: Redis, key: str) -> Any | None:
    value = await redis.get(key)
    if value:
        await redis.delete(key)
        return value
    return None


def websocket_package(data: Any, package_type: str) -> WebsocketMessage:
    return WebsocketMessage(message_type=package_type, data=data)


async def task_payload(redis: Redis,
                       project: Project,
                       user_id: UUID,
                       session: AsyncSession,
                       ) -> AsyncGenerator[WebsocketMessage | None, None]:

    async def get_active_tasks(tr: TaskRepository, project: Project) -> list[Task]:
        tasks = await tr.get_by_project(project)
        return [task for task in tasks if task.done is False]

    tr = TaskRepository(session)

    tasks = await get_active_tasks(tr, project)

    while True:
        flag = True
        task_update = await redis_get_and_delete(redis, (f"{RedisType.project_task_update}:{project.id}"))
        if task_update:
            tasks = await get_active_tasks(tr, project)
            """main_task = None
            for task in tasks:
                if not task.origin_task_id:
                    main_task = task
            assert isinstance(main_task, Task)
            if main_task.user_id != user_id:
                flag = False
                yield websocket_package(TaskSchema(id=main_task.id,
                                                   done=True,
                                                   status=1,
                                                   task_type=main_task.task_type
                                                   ).model_dump(), "task_done") """
        for task in tasks:
            if not task.origin_task_id and \
                    task.id not in [_.id for _ in tasks if _.id != task.id]:
                flag = False
                yield websocket_package(TaskSchema(id=task.id,
                                                   done=True,
                                                   status=1,
                                                   task_type=task.task_type
                                                   ).model_dump(), "task_done")

            if cached := await redis_get_and_delete(redis, f"{RedisType.task_error}:{task.id}"):
                tasks.pop(tasks.index(task))
                flag = False
                yield websocket_package(cached, "task_error")

            if cached := await redis_get_and_delete(redis, f"{RedisType.task_status}:{task.id}"):
                flag = False
                yield websocket_package(TaskSchema(id=task.id,
                                                   done=False,
                                                   status=cached,
                                                   task_type=task.task_type
                                                   ).model_dump(), "task_status")

            if cached := await redis_get_and_delete(redis, f"{RedisType.task}:{task.id}"):
                tasks.pop(tasks.index(task))
                flag = False
                yield websocket_package(TaskSchema(id=task.id,
                                                   done=True,
                                                   status=1,
                                                   task_type=task.task_type
                                                   ).model_dump(), "task_done")
        if flag:
            yield None


async def project_payload(redis: Redis,
                          project: Project,
                          user_id: UUID,
                          session: AsyncSession,
                          ) -> AsyncGenerator[WebsocketMessage | None, None]:
    key = f"{RedisType.project_update}:{project.id}"
    pr = ProjectRepository(session)
    while True:
        flag = True
        data = await redis_get_and_delete(redis, key)
        if data:
            redis_user_id = UUID(data["user_id"])
            if redis_user_id != user_id:
                updated_project = await pr.get_by_id(project.id)
                if updated_project is None:
                    raise SendFeedbackToAdminException()
                flag = False
                yield websocket_package(ProjectSchema.from_db(updated_project).model_dump(), "project_update")
        if flag:
            yield None


async def websocket_to_redis(websocket: WebSocket,
                             redis: Redis,
                             project: Project,
                             user_id: UUID,
                             ) -> None:
    while True:
        try:
            data = await asyncio.wait_for(websocket.receive_bytes(), timeout=0.1)
            await redis.set(f"{RedisType.project_doc_bytes}:{project.id}:{user_id}", str(data), ex=Config.websocket_redis_message_lifetime)
        except asyncio.TimeoutError:
            await asyncio.sleep(Config.websocket_polling_interval)
        except WebSocketDisconnect:
            break


async def redis_to_websocket(redis: Redis,
                             project: Project,
                             user_id: UUID,
                             session: AsyncSession
                             ) -> AsyncGenerator[WebsocketMessage | None, None]:

    while True:
        data = await redis_get_and_delete(redis, f"{RedisType.project_doc_bytes}:{project.id}:{user_id}")
        if data:
            yield websocket_package(data, "project_doc_bytes")
        else:
            yield None
