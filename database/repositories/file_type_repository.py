
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import *
from uuid import UUID


class FileTypeRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, name: str) -> Optional[FileType]:
        file_type = FileType(name=name)
        self.session.add(file_type)
        await self.session.flush()
        return await self.get_by_id(file_type.id)

    async def get_by_id(self, file_type_id: UUID) -> Optional[FileType]:
        stmt = select(FileType).where(FileType.id == file_type_id)
        return await self.session.scalar(stmt)
    
    async def get_by_name(self, name: str) -> Optional[FileType]:
        stmt = select(FileType).where(FileType.name == name)
        return await self.session.scalar(stmt)
