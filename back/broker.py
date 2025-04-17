
from faststream.rabbit import RabbitBroker, fastapi, RabbitQueue

from config import settings

RABBIT_URL = f"amqp://{settings.rabbit_user}:{settings.rabbit_password}@{settings.rabbit_ip}:{settings.rabbit_port}/"

router = fastapi.RabbitRouter(RABBIT_URL)

def get_broker() -> RabbitBroker:
    return router.broker

async def send_message(broker: RabbitBroker, data: dict, queue: RabbitQueue | str = "message"):
    await broker.publish(data, queue)