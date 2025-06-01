

from uuid import UUID
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from deva_p1_db.models import Project
from deva_p1_db.repositories import TaskRepository


async def task_info(redis: Redis, project: Project, session: AsyncSession) -> str | None:
    tr = TaskRepository(session)
    tasks = await tr.get_by_project(project)