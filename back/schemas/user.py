

from pydantic import BaseModel
from uuid import UUID

class UserSchema (BaseModel):
    id: UUID
    login: str

class CredsSchema (BaseModel):
    login: str
    password: str
    