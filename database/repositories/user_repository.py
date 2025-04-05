

from secrets import token_urlsafe

from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import *
from werkzeug.security import generate_password_hash, check_password_hash
from uuid import UUID


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, login: str, password: str) -> Optional[User]:
        user = User(login=login,
                    hashed_password=generate_password_hash(password),
                    secret=token_urlsafe(32))
        self.session.add(user)
        await self.session.flush()
        return await self.get_by_id(user.id)

    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        stmt = select(User).where(User.id == user_id)
        return await self.session.scalar(stmt)

    async def get_by_auth(self, login: str, password: str) -> Optional[User]:
        stmt = select(User).where(User.login == login).limit(1)
        user = await self.session.scalar(stmt)
        if user is None:
            return None
        if not check_password_hash(user.hashed_password, password):
            return None
        return user

    async def update_secret(self, user: User) -> None:
        user.secret = token_urlsafe(32)
        await self.session.flush()
