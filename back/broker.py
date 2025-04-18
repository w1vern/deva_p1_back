
from faststream.rabbit import RabbitBroker, fastapi, RabbitQueue, RabbitMessage

from config import settings

from deva_p1_db.schemas.task import TaskToAi, TaskToBack
from deva_p1_db.enums.rabbit import RabbitQueuesToBack

from database.redis import RedisType, get_redis_client

RABBIT_URL = f"amqp://{settings.rabbit_user}:{settings.rabbit_password}@{settings.rabbit_ip}:{settings.rabbit_port}/"

router = fastapi.RabbitRouter(RABBIT_URL)


def get_broker() -> RabbitBroker:
    return router.broker


async def send_message(broker: RabbitBroker, queue: RabbitQueue | str, data: TaskToAi | dict):
    await broker.publish(data, queue)


@router.subscriber(RabbitQueuesToBack.done_task)
async def handle_done_task(msg: TaskToBack):
    redis = await get_redis_client()
    await redis.set(f"{RedisType.task}:{msg.task_id}", msg.done, ex=300)
