
from enum import Enum

from redis.asyncio import Redis

from config import settings


class RedisType(str, Enum):
    incorrect_credentials = "incorrect_credentials",
    invalidated_access_token = "invalidated_access_token"
    incorrect_credentials_ip = "incorrect_credentials_ip"
    project_task_update = "project_task_update"
    project_update = "project_update"
    project_doc_bytes = "project_doc_bytes"
    task_done = "task_done"
    task_status = "task_status"
    task_cache = "task_cache"
    task_error = "task_error"


def get_redis_client() -> Redis:
    return Redis(host=settings.redis_ip,
                 port=settings.redis_port,
                 db=0,
                 decode_responses=True)
