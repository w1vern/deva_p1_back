

import asyncio
from typing import Any, AsyncGenerator
from uuid import UUID

from deva_p1_db.models import Project, Task
from deva_p1_db.repositories import ProjectRepository, TaskRepository
from fastapi import WebSocket, WebSocketDisconnect
from redis.asyncio import Redis

from back.config import Config
from back.exceptions import *
from back.schemas import ProjectSchema, TaskSchema, WebsocketMessage
from database.redis import RedisType
from database.database import session_manager


async def redis_get_unique(redis: Redis, key: str, my_dict: dict[str, Any]) -> Any | None:
    value = await redis.get(key)
    if value and (key not in my_dict or my_dict[key] != value):
        my_dict[key] = value
        return value
    return None


def websocket_package(data: Any, package_type: str) -> WebsocketMessage:
    return WebsocketMessage(message_type=package_type, data=data)


async def task_payload(redis: Redis,
                       project: Project,
                       user_id: UUID,
                       ) -> AsyncGenerator[WebsocketMessage | None, None]:

    async def get_active_tasks(project: Project) -> list[Task]:
        async with session_manager.context_session() as session:
            tr = TaskRepository(session)
            tasks = await tr.get_by_project(project)
        return [task for task in tasks if task.done is False]

    my_dict = {}

    tasks = await get_active_tasks(project)

    while True:
        flag = True
        if task_update := await redis_get_unique(redis, f"{RedisType.project_task_update}:{project.id}", my_dict):
            tasks = await get_active_tasks(project)
        for task in tasks:
            if cached := await redis_get_unique(redis, f"{RedisType.task_error}:{task.id}", my_dict):
                tasks.pop(tasks.index(task))
                flag = False
                yield websocket_package(cached, RedisType.task_error)
                continue

            if cached := await redis_get_unique(redis, f"{RedisType.task_status}:{task.id}", my_dict):
                flag = False
                yield websocket_package(TaskSchema(id=task.id,
                                                   done=False,
                                                   status=cached,
                                                   task_type=task.task_type
                                                   ).model_dump(), RedisType.task_status)

            if cached := await redis_get_unique(redis, f"{RedisType.task_done}:{task.id}", my_dict):
                flag = False
                yield websocket_package(TaskSchema(id=task.id,
                                                   done=True,
                                                   status=1,
                                                   task_type=task.task_type
                                                   ).model_dump(), RedisType.task_done)
                if task.origin_task_id:
                    if task.origin_task_id not in [_.origin_task_id for _ in tasks if task.id != _.id]:
                        for _ in tasks:
                            if _.id == task.origin_task_id:
                                yield websocket_package(TaskSchema(id=_.id,
                                                                   done=True,
                                                                   status=1,
                                                                   task_type=_.task_type
                                                                   ).model_dump(), RedisType.task_done)
                                tasks.pop(tasks.index(_))
                tasks.pop(tasks.index(task))
                continue
        if flag:
            yield None


async def project_payload(redis: Redis,
                          project: Project,
                          user_id: UUID,
                          ) -> AsyncGenerator[WebsocketMessage | None, None]:
    my_dict = {}
    key = f"{RedisType.project_update}:{project.id}"
    while True:
        flag = True
        data = await redis_get_unique(redis, key, my_dict)
        if data:
            redis_user_id = UUID(data["user_id"])
            if redis_user_id != user_id:
                async with session_manager.context_session() as session:
                    pr = ProjectRepository(session)
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
                             ) -> AsyncGenerator[WebsocketMessage | None, None]:
    my_dict = {}
    while True:
        if data := await redis_get_unique(redis, f"{RedisType.project_doc_bytes}:{project.id}:{user_id}", my_dict):
            yield websocket_package(data, "project_doc_bytes")
        else:
            yield None
