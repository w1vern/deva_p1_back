from datetime import datetime
from typing import Optional, Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import *
from uuid import UUID

from database.models.task import Task


class FileRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self,
                     user_file_name: str,
                     file_type: str,
                     project: Project,
                     task: Task | None = None, 
                     created_date: datetime | None = None,
                     last_modified_date: datetime | None = None
                     ) -> Optional[File]:
        if created_date is None:
            created_date = datetime.now()
        if last_modified_date is None:
            last_modified_date = datetime.now()
        if task is None:
            task_id = UUID(int=0)
        else:
            task_id = task.id
        file = File(user_file_name=user_file_name,
                    created_date=created_date,
                    last_modified_date=last_modified_date,
                    file_type=file_type,
                    project_id=project.id,
                    task_id = task_id)
        self.session.add(file)
        await self.session.flush()
        return await self.get_by_id(file.id)
    
    async def get_by_id(self, file_id: UUID) -> Optional[File]:
        stmt = select(File).where(File.id == file_id)
        return await self.session.scalar(stmt)
    
    async def get_by_project(self, project: Project) -> Sequence[File]:
        stmt = select(File).where(File.project_id == project.id)
        return (await self.session.scalars(stmt)).all()
    
    async def get_by_file_type(self, file_type: FileType) -> Sequence[File]:
        stmt = select(File).where(File.file_type_id == file_type.id)
        return (await self.session.scalars(stmt)).all()
    
    async def get_by_user_file_name(self, user_file_name: str) -> Sequence[File]:
        stmt = select(File).where(File.user_file_name == user_file_name)
        return (await self.session.scalars(stmt)).all()