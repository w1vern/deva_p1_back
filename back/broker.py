
import stat

from deva_p1_db.enums.rabbit import RabbitQueuesToAi, RabbitQueuesToBack
from deva_p1_db.enums.task_type import TaskType
from deva_p1_db.repositories import TaskRepository
from deva_p1_db.schemas.task import TaskReadyToBack, TaskStatusToBack, TaskToAi
from fastapi import Depends
from faststream.rabbit import RabbitBroker, RabbitQueue, fastapi

from back.config import Config
from config import settings
from database.db import Session
from database.redis import RedisType, get_redis_client

RABBIT_URL = f"amqp://{settings.rabbit_user}:{settings.rabbit_password}@{settings.rabbit_ip}:{settings.rabbit_port}/"

router = fastapi.RabbitRouter(RABBIT_URL)


def get_broker() -> RabbitBroker:
    return router.broker


async def send_message(broker: RabbitBroker, queue: RabbitQueue | str, data: TaskToAi | dict):
    await broker.publish(data, queue)


@router.subscriber(RabbitQueuesToBack.done_task)
async def handle_done_task(msg: TaskReadyToBack, session: Session, broker: RabbitBroker = Depends(get_broker)):
    tr = TaskRepository(session)
    handled_task = await tr.get_by_id(msg.task_id)
    if handled_task is None:
        raise Exception("got incorrect task id from ai")
    if handled_task.origin_task_id is not None:
        if handled_task.task_type == TaskType.frames_extract or handled_task.task_type == TaskType.transcribe:
            tasks = await tr.get_by_origin_task(handled_task)
            tasks.remove(handled_task)
            second_process_task = [task for task in tasks if task.task_type == TaskType.frames_extract
                                   or task.task_type == TaskType.transcribe]
            if len(second_process_task) == 0:
                need_to_start = True
            elif second_process_task[0].done:
                need_to_start = True
                tasks.remove(second_process_task[0])
            else:
                need_to_start = False
            if need_to_start:
                await send_message(broker, RabbitQueuesToAi.summary_task, TaskToAi(task_id=tasks[0].id))

    redis = await get_redis_client()
    await redis.set(f"{RedisType.task}:{msg.task_id}", 1, ex=Config.redis_task_status_lifetime)


@router.subscriber(RabbitQueuesToBack.progress_task)
async def handle_progress_task(msg: TaskStatusToBack):
    redis = await get_redis_client()
    await redis.set(f"{RedisType.task_status}:{msg.task_id}", msg.progress, ex=Config.redis_task_status_lifetime)
