

from typing import Optional, Sequence
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import *


class TaskRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self,
                     task_type: str,
                     project: Project,
                     user: User,
                     origin_file: File
                     ) -> Optional[Task]:
        task = Task(task_type=task_type,
                    project_id=project.id,
                    user_id=user.id,
                    origin_file_id=origin_file.id)
        self.session.add(task)
        await self.session.flush()
        return await self.get_by_id(task.id)

    async def get_by_id(self, task_id: UUID) -> Optional[Task]:
        stmt = select(Task).where(Task.id == task_id)
        return await self.session.scalar(stmt)

    async def get_by_project(self, project: Project) -> Sequence[Task]:
        stmt = select(Task).where(Task.project_id == project.id)
        return (await self.session.scalars(stmt)).all()

    async def get_by_user(self, user: User) -> Sequence[Task]:
        stmt = select(Task).where(Task.user_id == user.id)
        return (await self.session.scalars(stmt)).all()

    async def get_by_origin_file(self, origin_file: File) -> Sequence[Task]:
        stmt = select(Task).where(Task.origin_file_id == origin_file.id)
        return (await self.session.scalars(stmt)).all()

    async def get_by_project_and_user(self, project: Project, user: User) -> Sequence[Task]:
        stmt = select(Task).where(Task.project_id ==
                                  project.id).where(Task.user_id == user.id)
        return (await self.session.scalars(stmt)).all()
