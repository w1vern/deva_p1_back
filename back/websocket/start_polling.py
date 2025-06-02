

import asyncio
from typing import AsyncGenerator
from uuid import UUID

from deva_p1_db.models import Project
from fastapi import WebSocket
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from back.config import Config
from back.schemas import WebsocketMessage

from .payload import (project_payload, redis_to_websocket, task_payload,
                      websocket_to_redis)


async def start_polling(websocket: WebSocket,
                        redis: Redis,
                        project: Project,
                        user_id: UUID,
                        session: AsyncSession
                        ) -> AsyncGenerator[WebsocketMessage, None]:

    generators = [gen(redis, project, user_id, session)
                  for gen in [project_payload, task_payload, redis_to_websocket]]
    queue = asyncio.Queue()

    async def consume(gen: AsyncGenerator) -> None:
        async for item in gen:
            if item is None:
                await asyncio.sleep(Config.websocket_polling_interval)
                continue
            await queue.put(item)

    tasks = [asyncio.create_task(consume(g))
             for g in generators]
    tasks.append(asyncio.create_task(websocket_to_redis(
        websocket, redis, project, user_id)))

    try:
        while True:
            item = await queue.get()
            yield item
    finally:
        for task in tasks:
            task.cancel()
