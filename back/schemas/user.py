

from uuid import UUID

from deva_p1_db.models.user import User
from pydantic import BaseModel


class UserSchema (BaseModel):
    id: UUID
    login: str

    @classmethod
    def from_db(cls, user: User) -> "UserSchema":
        return UserSchema(**user.__dict__)

class CredsSchema (BaseModel):
    login: str
    password: str

class RegisterSchema (BaseModel):
    login: str
    password: str
    password_repeat: str

class UserUpdateSchema (BaseModel):
    new_login: str | None = None
    new_password: str | None = None
    new_password_repeat: str | None = None
    