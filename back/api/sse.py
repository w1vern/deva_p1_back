import asyncio
import json
from typing import AsyncGenerator
from fastapi.responses import StreamingResponse
from fastapi_controllers import Controller, get
from fastapi import Depends, Request

from redis.asyncio import Redis

from back.config import Config
from back.db import Session
from database.redis import get_redis_client, RedisType

class SseController(Controller):
    prefix = "/sse"
    tags = ["sse"]

    def __init__(self, session: Session) -> None:
        self.session = session

    @get("/{task_id}")
    async def sse_task_response(
        self,
        task_id: str,
        request: Request,
        redis: Redis = Depends(get_redis_client)
    ):
        cache_key = f"{RedisType.task}:{task_id}"

        async def event_stream() -> AsyncGenerator[str, None]:
            while True:
                if await request.is_disconnected():
                    break
                cached = await redis.get(cache_key)
                if cached:
                    yield f"data: {cached}\n\n"
                    break
                await asyncio.sleep(Config.redis_task_polling_time)


        response = StreamingResponse(event_stream(), media_type="text/event-stream")
        response.headers["X-Accel-Buffering"] = "no"
        return response
