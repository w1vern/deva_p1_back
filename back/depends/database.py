
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from deva_p1_db.repositories import (UserRepository, FileRepository,
                                     ProjectRepository, InvitedUserRepository,
                                     TaskRepository, NoteRepository)

from database.database import session_manager


async def get_user_repo(session: AsyncSession = Depends(session_manager.session)
                        ) -> UserRepository:
    return UserRepository(session)


async def get_file_repo(session: AsyncSession = Depends(session_manager.session)
                        ) -> FileRepository:
    return FileRepository(session)


async def get_project_repo(session: AsyncSession = Depends(session_manager.session)
                           ) -> ProjectRepository:
    return ProjectRepository(session)


async def get_invited_user_repo(session: AsyncSession = Depends(session_manager.session)
                                ) -> InvitedUserRepository:
    return InvitedUserRepository(session)


async def get_task_repo(session: AsyncSession = Depends(session_manager.session)
                        ) -> TaskRepository:
    return TaskRepository(session)


async def get_note_repo(session: AsyncSession = Depends(session_manager.session)
                        ) -> NoteRepository:
    return NoteRepository(session)
