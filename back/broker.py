
import stat

from deva_p1_db.enums.rabbit import RabbitQueuesToBack
from deva_p1_db.schemas.task import TaskToAi, TaskReadyToBack, TaskStatusToBack
from faststream.rabbit import RabbitBroker, RabbitMessage, RabbitQueue, fastapi

from back.config import Config
from config import settings
from database.redis import RedisType, get_redis_client

RABBIT_URL = f"amqp://{settings.rabbit_user}:{settings.rabbit_password}@{settings.rabbit_ip}:{settings.rabbit_port}/"

router = fastapi.RabbitRouter(RABBIT_URL)


def get_broker() -> RabbitBroker:
    return router.broker


async def send_message(broker: RabbitBroker, queue: RabbitQueue | str, data: TaskToAi | dict):
    await broker.publish(data, queue)


@router.subscriber(RabbitQueuesToBack.done_task)
async def handle_done_task(msg: TaskReadyToBack):
    redis = await get_redis_client()
    await redis.set(f"{RedisType.task}:{msg.task_id}", 1, ex=Config.redis_task_status_lifetime)

@router.subscriber(RabbitQueuesToBack.progress_task)
async def handle_progress_task(msg: TaskStatusToBack):
    redis = await get_redis_client()
    await redis.set(f"{RedisType.task_status}:{msg.task_id}", msg.progress, ex=Config.redis_task_status_lifetime)
