

from uuid import UUID
from deva_p1_db.enums.rabbit import RabbitQueuesToAi, RabbitQueuesToBack
from deva_p1_db.enums.task_type import TaskType
from deva_p1_db.repositories import TaskRepository
from deva_p1_db.schemas.task import TaskReadyToBack, TaskStatusToBack, TaskToAi
from deva_p1_db.models import Task
from fastapi import Depends
from faststream.rabbit import RabbitBroker, RabbitQueue, fastapi
from redis.asyncio import Redis

from back.config import Config
from back.schemas.task import RedisTaskCacheSchema
from config import settings
from database.db import Session
from database.redis import RedisType, get_redis_client

RABBIT_URL = f"amqp://{settings.rabbit_user}:{settings.rabbit_password}@{settings.rabbit_ip}:{settings.rabbit_port}/"

router = fastapi.RabbitRouter(RABBIT_URL)


async def send_message_and_cache(broker: RabbitBroker, redis: Redis, task: Task, project_id: UUID):
    await send_message(broker, f"{task.task_type}_task", TaskToAi(task_id=task.id))
    await redis.set(f"{RedisType.task_cache}:{project_id}:{task.task_type}", RedisTaskCacheSchema.from_db(
        task).model_dump_json(), ex=Config.redis_task_status_lifetime)


def get_broker() -> RabbitBroker:
    return router.broker


async def send_message(broker: RabbitBroker, queue: RabbitQueue | str, data: TaskToAi | dict):
    await broker.publish(data, queue)


@router.subscriber(RabbitQueuesToBack.done_task)
async def handle_done_task(msg: TaskReadyToBack, session: Session, broker: RabbitBroker = Depends(get_broker), redis: Redis = Depends(get_redis_client)):
    tr = TaskRepository(session)
    handled_task = await tr.get_by_id(msg.task_id)
    if handled_task is None:
        raise Exception("got incorrect task id from ai")
    if handled_task.origin_task_id is not None:
        if handled_task.task_type == TaskType.frames_extract or handled_task.task_type == TaskType.transcribe:
            tasks = list(filter(lambda task: not task.done, (await tr.get_by_origin_task(handled_task))))
            if len(tasks) == 1:
                await send_message_and_cache(broker, redis, tasks[0], handled_task.project_id)
    await redis.delete(f"{RedisType.task_cache}:{handled_task.project_id}:{handled_task.task_type}")
    await redis.set(f"{RedisType.task}:{msg.task_id}", 1, ex=Config.redis_task_status_lifetime)


@router.subscriber(RabbitQueuesToBack.progress_task)
async def handle_progress_task(msg: TaskStatusToBack, redis: Redis = Depends(get_redis_client)):
    await redis.set(f"{RedisType.task_status}:{msg.task_id}", msg.progress, ex=Config.redis_task_status_lifetime)
