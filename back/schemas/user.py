

from uuid import UUID

from deva_p1_db.models.user import User
from pydantic import BaseModel, ConfigDict


class UserSchema (BaseModel):
    id: UUID
    login: str

    model_config = ConfigDict(
        json_encoders={
            UUID: lambda v: str(v),
        },
        from_attributes = True
    )

    @classmethod
    def from_db(cls, user: User) -> "UserSchema":
        return UserSchema(
			id=user.id,
			login=user.login,
		)

class CredsSchema (BaseModel):
    login: str
    password: str

class RegisterSchema (BaseModel):
    login: str
    password: str
    password_repeat: str
    