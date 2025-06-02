

from uuid import UUID

from deva_p1_db.models import File, Note, User
from deva_p1_db.repositories import NoteRepository
from fastapi import APIRouter, Depends

from back.config import Config
from back.depends import (get_file, get_file_editor, get_file_viewer, get_note,
                          get_note_editor, get_note_repo, get_user)
from back.exceptions import *
from back.schemas.note import CreateNoteSchema, NoteSchema, UpdateNoteSchema
from back.schemas.user import UserSchema
from redis.asyncio import Redis

from database.redis import RedisType, get_redis_client

router = APIRouter(prefix="/note", tags=["note"])


@router.post("/{file_id}")
async def create_note(new_note: CreateNoteSchema,
                      file: File = Depends(get_file),
                      user: User = Depends(get_file_editor),
                      redis: Redis = Depends(get_redis_client),
                      nr: NoteRepository = Depends(get_note_repo)
                      ) -> NoteSchema:
    await redis.set(f"{RedisType.project_update}:{file.project.id}", 1, ex=Config.websocket_redis_message_lifetime)
    note = await nr.create(file=file,
                           text=new_note.text,
                           start_time_code=new_note.start_time_code,
                           end_time_code=new_note.end_time_code)
    if note is None:
        raise SendFeedbackToAdminException()
    return NoteSchema.from_db(note)


@router.get("/{file_id}")
async def get_all_notes(file: File = Depends(get_file),
                        user: User = Depends(get_file_viewer),
                        nr: NoteRepository = Depends(get_note_repo)
                        ) -> list[NoteSchema]:
    return [NoteSchema.from_db(note) for note in (await nr.get_by_file(file))]


@router.patch("/{note_id}")
async def update_note(update_data: UpdateNoteSchema,
                      note: Note = Depends(get_note),
                      user: UserSchema = Depends(get_user),
                      redis: Redis = Depends(get_redis_client),
                      nr: NoteRepository = Depends(get_note_repo)
                      ) -> NoteSchema:
    await redis.set(f"{RedisType.project_update}:{note.file.project.id}", 1, ex=Config.websocket_redis_message_lifetime)
    await nr.update(note,
                    update_data.new_text,
                    update_data.new_start_time_code,
                    update_data.new_end_time_code)
    updated_note = await nr.get_by_id(note.id)
    if updated_note is None:
        raise SendFeedbackToAdminException()
    return NoteSchema.from_db(updated_note)


@router.delete("/{note_id}")
async def delete_note(note: Note = Depends(get_note),
                      user: User = Depends(get_note_editor),
                      redis: Redis = Depends(get_redis_client),
                      nr: NoteRepository = Depends(get_note_repo)
                      ):
    await redis.set(f"{RedisType.project_update}:{note.file.project.id}", 1, ex=Config.websocket_redis_message_lifetime)
    await nr.delete(note)
    return {"message": "OK"}
