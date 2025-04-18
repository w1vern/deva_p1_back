import asyncio
from typing import AsyncGenerator
from fastapi.responses import StreamingResponse
from fastapi_sse import sse_handler
from fastapi_controllers import Controller, get
from fastapi import Depends, Request

from redis.asyncio import Redis

from back.config import Config
from back.db import Session
from back.schemas.task import TaskSchema
from database.redis import get_redis_client, RedisType


class SseController(Controller):
    prefix = "/sse"
    tags = ["sse"]

    def __init__(self, session: Session) -> None:
        self.session = session

    @get("/{task_id}")
    @sse_handler()
    async def sse_task_response(self,
                                task_id: str,
                                request: Request,
                                redis: Redis = Depends(get_redis_client)
                                ) -> AsyncGenerator[TaskSchema, None]:
        done_cache_key = f"{RedisType.task}:{task_id}"
        status_cache_key = f"{RedisType.task_status}:{task_id}"
        while True:
            if await request.is_disconnected():
                break
            cached = await redis.get(status_cache_key)
            if cached:
                yield TaskSchema(id=task_id, done=False, status=cached)
                continue
            cached = await redis.get(done_cache_key)
            if cached:
                yield TaskSchema(id=task_id, done=bool(cached))
                break
            await asyncio.sleep(Config.redis_task_polling_time)
