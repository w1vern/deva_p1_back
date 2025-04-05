from datetime import datetime

from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import *

from uuid import UUID


class ProjectRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self,
                     name: str,
                     description: str,
                     holder_id: UUID,
                     created_date: datetime | None = None,
                     last_modified_date: datetime | None = None
                     ) -> Optional[Project]:
        if created_date is None:
            created_date = datetime.now()
        if last_modified_date is None:
            last_modified_date = datetime.now()
        project = Project(name=name,
                          description=description,
                          holder_id=holder_id,
                          created_date=created_date,
                          last_modified_date=last_modified_date)
        self.session.add(project)
        await self.session.flush()
        return await self.get_by_id(project.id)

    async def get_by_id(self, project_id: UUID) -> Optional[Project]:
        stmt = select(Project).where(Project.id == project_id)
        return await self.session.scalar(stmt)

    async def update(self,
                     project: Project,
                     name: str | None = None,
                     description: str | None = None,
                     last_modified_date: datetime | None = None
                     ) -> None:
        if name is not None:
            project.name = name
        if description is not None:
            project.description = description
        if last_modified_date is not None:
            project.last_modified_date = last_modified_date
        await self.session.flush()
