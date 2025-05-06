

from uuid import UUID

from deva_p1_db.repositories import FileRepository, NoteRepository
from fastapi import Depends, HTTPException
from fastapi_controllers import Controller, delete, get, patch, post

from back.get_auth import get_user
from back.schemas.note import CreateNoteSchema, NoteSchema, UpdateNoteSchema
from back.schemas.user import UserSchema
from database.db import Session


class NoteController(Controller):
    prefix = "/note"
    tags = ["note"]

    def __init__(self, session: Session) -> None:
        self.session = session
        self.nr = NoteRepository(self.session)
        self.fr = FileRepository(self.session)

    @post("")
    async def create_note(self,
                          new_note: CreateNoteSchema,
                          user: UserSchema = Depends(get_user)
                          ) -> NoteSchema:
        file = await self.fr.get_by_id(new_note.file_id)
        if file is None:
            raise HTTPException(status_code=404, detail="file not found")
        if file.user_id != user.id:
            raise HTTPException(status_code=403, detail="permission denied")
        note = await self.nr.create(file=file,
                                    text=new_note.text,
                                    start_time_code=new_note.start_time_code,
                                    end_time_code=new_note.end_time_code)
        if note is None:
            raise HTTPException(
                status_code=500, detail="internal server error")
        return NoteSchema.from_db(note)

    @get("/{file_id}")
    async def get_all_notes(self,
                            file_id: UUID,
                            user: UserSchema = Depends(get_user)
                            ) -> list[NoteSchema]:
        file = await self.fr.get_by_id(file_id)
        if file is None:
            raise HTTPException(status_code=404, detail="file not found")
        if file.user_id != user.id:
            raise HTTPException(status_code=403, detail="permission denied")
        return [NoteSchema.from_db(note) for note in (await self.nr.get_by_file(file))]

    @patch("/{note_id}")
    async def update_note(self,
                          note_id: UUID,
                          update_data: UpdateNoteSchema,
                          user: UserSchema = Depends(get_user)
                          ) -> NoteSchema:
        note = await self.nr.get_by_id(note_id)
        if note is None:
            raise HTTPException(status_code=404, detail="note not found")
        if note.file.user_id != user.id:
            raise HTTPException(status_code=403, detail="permission denied")
        await self.nr.update(note,
                             update_data.new_text,
                             update_data.new_start_time_code,
                             update_data.new_end_time_code)
        note = await self.nr.get_by_id(note_id)
        if note is None:
            raise HTTPException(
                status_code=500, detail="internal server error")
        return NoteSchema.from_db(note)

    @delete("/{note_id}")
    async def delete_note(self,
                          note_id: UUID,
                          user: UserSchema = Depends(get_user)
                          ) -> None:
        note = await self.nr.get_by_id(note_id)
        if note is None:
            raise HTTPException(status_code=404, detail="note not found")
        if note.file.user_id != user.id:
            raise HTTPException(status_code=403, detail="permission denied")
        await self.nr.delete(note)
