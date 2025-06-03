
from uuid import UUID

from deva_p1_db.models import Note, User
from deva_p1_db.repositories import InvitedUserRepository, NoteRepository
from fastapi import Depends

from back.exceptions import NoteNotFoundException

from .database import get_note_repo
from .get_project import (get_invited_user_repo, get_project_editor,
                          get_project_viewer)
from .get_user import get_user_db


async def get_note(note_id: UUID,
                   nr: NoteRepository = Depends(get_note_repo)
                   ) -> Note:
    note = await nr.get_by_id(note_id)
    if note is None:
        raise NoteNotFoundException(note_id)
    return note


async def get_note_viewer(note: Note = Depends(get_note),
                          user: User = Depends(get_user_db),
                          iur: InvitedUserRepository = Depends(
                              get_invited_user_repo)
                          ) -> User:
    return await get_project_viewer(note.file.project, user)


async def get_note_editor(note: Note = Depends(get_note),
                          user: User = Depends(get_user_db)
                          ) -> User:
    return await get_project_editor(note.file.project, user)
