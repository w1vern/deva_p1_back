

from uuid import UUID

from deva_p1_db.models import Note
from pydantic import BaseModel


class CreateNoteSchema(BaseModel):
    file_id: UUID
    text: str
    start_time_code: float
    end_time_code: float | None = None

class NoteSchema(BaseModel):
    id: UUID
    text: str
    start_time_code: float
    end_time_code: float

    @classmethod
    def from_db(cls, note: Note):
        return cls(**note.__dict__)
    
class UpdateNoteSchema(BaseModel):
    new_text: str | None = None
    new_start_time_code: float | None = None
    new_end_time_code: float | None = None

class DeleteNoteSchema(BaseModel):
    id: UUID