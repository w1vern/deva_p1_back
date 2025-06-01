

from uuid import UUID

from deva_p1_db.models import File, Note, User
from deva_p1_db.repositories import FileRepository, NoteRepository
from fastapi import Depends
from fastapi_controllers import Controller, delete, get, patch, post
from sqlalchemy.ext.asyncio import AsyncSession

from back.depends import (get_file, get_file_editor, get_file_viewer, get_note,
                          get_note_editor, get_user)
from back.exceptions import *
from back.schemas.note import CreateNoteSchema, NoteSchema, UpdateNoteSchema
from back.schemas.user import UserSchema
from database.db import session_manager


class NoteController(Controller):
    prefix = "/note"
    tags = ["note"]

    def __init__(self, session: AsyncSession = Depends(session_manager.session)) -> None:
        self.session = session
        self.nr = NoteRepository(self.session)
        self.fr = FileRepository(self.session)

    @post("")
    async def create_note(self,
                          new_note: CreateNoteSchema,
                          file: File = Depends(get_file),
                          user: User = Depends(get_file_editor)
                          ) -> NoteSchema:
        note = await self.nr.create(file=file,
                                    text=new_note.text,
                                    start_time_code=new_note.start_time_code,
                                    end_time_code=new_note.end_time_code)
        if note is None:
            raise SendFeedbackToAdminException()
        return NoteSchema.from_db(note)

    @get("/{file_id}")
    async def get_all_notes(self,
                            file: File = Depends(get_file),
                            user: User = Depends(get_file_viewer)
                            ) -> list[NoteSchema]:
        return [NoteSchema.from_db(note) for note in (await self.nr.get_by_file(file))]

    @patch("/{note_id}")
    async def update_note(self,
                          update_data: UpdateNoteSchema,
                          note: Note = Depends(get_note),
                          user: UserSchema = Depends(get_user)
                          ) -> NoteSchema:
        await self.nr.update(note,
                             update_data.new_text,
                             update_data.new_start_time_code,
                             update_data.new_end_time_code)
        updated_note = await self.nr.get_by_id(note.id)
        if updated_note is None:
            raise SendFeedbackToAdminException()
        return NoteSchema.from_db(updated_note)

    @delete("/{note_id}")
    async def delete_note(self,
                          note: Note = Depends(get_note),
                          user: User = Depends(get_note_editor)
                          ):
        await self.nr.delete(note)
        return {"message": "OK"}
