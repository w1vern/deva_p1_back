

from pydantic import BaseModel
from uuid import UUID

class UserSchema (BaseModel):
    id: UUID
    login: str

class CredsSchema (BaseModel):
    login: str
    password: str

class RegisterSchema (BaseModel):
    login: str
    password: str
    password_repeat: str
    