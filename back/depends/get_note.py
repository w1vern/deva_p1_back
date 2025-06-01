
from uuid import UUID

from deva_p1_db.models import Note, User
from deva_p1_db.repositories import NoteRepository
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from back.exceptions import NoteNotFoundException
from database.db import session_manager

from .get_file import get_file
from .get_project import get_project_editor, get_project_viewer
from .get_user import get_user_db


async def get_note(note_id: UUID, session: AsyncSession = Depends(session_manager.session)) -> Note:
    nr = NoteRepository(session)
    note = await nr.get_by_id(note_id)
    if note is None:
        raise NoteNotFoundException(note_id)
    return note


async def get_note_viewer(session: AsyncSession = Depends(session_manager.session),
                          note: Note = Depends(get_file),
                          user: User = Depends(get_user_db)
                          ) -> User:
    return await get_project_viewer(session, note.file.project, user)


async def get_note_editor(note: Note = Depends(get_file),
                          user: User = Depends(get_user_db)
                          ) -> User:
    return await get_project_editor(note.file.project, user)
