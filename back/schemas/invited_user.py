

from uuid import UUID

from pydantic import BaseModel


class InvitedUserSchema(BaseModel):
    login: str
    project_id: UUID