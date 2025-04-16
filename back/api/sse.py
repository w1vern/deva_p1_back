import asyncio
import json
from typing import AsyncGenerator
from fastapi.responses import StreamingResponse
from fastapi_controllers import Controller, get
from fastapi import Depends, Request

from redis.asyncio import Redis
from redis.asyncio.client import PubSub

from back.config import Config
from database.database import get_db_session
from sqlalchemy.ext.asyncio import AsyncSession
from database.redis import get_redis_client, RedisType


class SseController(Controller):
    prefix = "/sse"
    tags = ["sse"]

    def __init__(self, session: AsyncSession = Depends(get_db_session)) -> None:
        self.session = session

    @get("/{task_id}")
    async def sse_task_response(
        self,
        task_id: str,
        request: Request,
        redis: Redis = Depends(get_redis_client)
    ):
        cache_key = f"{RedisType.task}:{task_id}"
        channel = RedisType.task.value

        async def event_stream() -> AsyncGenerator[str, None]:
            cached = await redis.get(cache_key)
            if cached:
                yield f"data: {cached.decode()}\n\n"
                return

            pubsub: PubSub = redis.pubsub()
            await pubsub.subscribe(channel)

            try:
                while True:
                    if await request.is_disconnected():
                        break

                    message = await pubsub.get_message(
                        ignore_subscribe_messages=True, timeout=Config.redis_pubsub_check_time
                    )
                    if message:
                        try:
                            data = json.loads(message["data"])
                            if data.get("task_id") == str(task_id):
                                await redis.set(cache_key, json.dumps(data), ex=300)
                                yield f"data: {json.dumps(data)}\n\n"
                                break
                        except (json.JSONDecodeError, TypeError):
                            continue

                    await asyncio.sleep(Config.redis_pubsub_check_timeout)

            finally:
                await pubsub.unsubscribe(channel)
                await pubsub.close()

        response = StreamingResponse(event_stream(), media_type="text/event-stream")
        response.headers["X-Accel-Buffering"] = "no"
        return response
