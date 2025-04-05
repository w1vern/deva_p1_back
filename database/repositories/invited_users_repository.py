

from typing import Optional, Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import *


class InvitedUsersRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self,
                     user: User,
                     project: Project,
                     accepted: bool = False,
                     rights_level: int = 0
                     ) -> Optional[InvitedUsers]:
        invited_user = InvitedUsers(user_id=user.id,
                                    project_id=project.id,
                                    accepted=accepted,
                                    rights_level=rights_level)
        self.session.add(invited_user)
        await self.session.flush()
        return await self.get_by_id(user, project)

    async def get_by_id(self, user: User, project: Project) -> Optional[InvitedUsers]:
        stmt = select(InvitedUsers).where(InvitedUsers.user_id == user.id).where(
            InvitedUsers.project_id == project.id)
        return await self.session.scalar(stmt)

    async def get_by_user(self, user: User) -> Sequence[InvitedUsers]:
        stmt = select(InvitedUsers).where(
            InvitedUsers.user_id == user.id)
        return (await self.session.scalars(stmt)).all()

    async def get_by_project(self, project: Project) -> Sequence[InvitedUsers]:
        stmt = select(InvitedUsers).where(
            InvitedUsers.project_id == project.id)
        return (await self.session.scalars(stmt)).all()
