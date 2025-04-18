
from enum import Enum

from redis.asyncio import Redis

from config import settings


class RedisType(str, Enum):
    incorrect_credentials = "incorrect_credentials",
    invalidated_access_token = "invalidated_access_token"
    incorrect_credentials_ip = "incorrect_credentials_ip"
    task = "task"
    task_status = "task_status"


def get_redis_client() -> Redis:
    return Redis(host=settings.redis_ip,
                 port=settings.redis_port,
                 db=0,
                 decode_responses=True)
