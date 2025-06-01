

from uuid import UUID

from deva_p1_db.models import File, User
from deva_p1_db.repositories import FileRepository
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from back.exceptions import FileNotFoundException
from database.db import session_manager

from .get_project import get_project_editor, get_project_viewer
from .get_user import get_user_db


async def get_file(file_id: UUID, session: AsyncSession = Depends(session_manager.session)) -> File:
    fr = FileRepository(session)
    file = await fr.get_by_id(file_id)
    if file is None:
        raise FileNotFoundException(file_id)
    return file


async def get_file_viewer(session: AsyncSession = Depends(session_manager.session),
                          file: File = Depends(get_file),
                          user: User = Depends(get_user_db)
                          ) -> User:
    return await get_project_viewer(session, file.project, user)


async def get_file_editor(file: File = Depends(get_file),
                          user: User = Depends(get_user_db)
                          ) -> User:
    return await get_project_editor(file.project, user)
