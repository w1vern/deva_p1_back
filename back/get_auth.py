from datetime import UTC, datetime

from deva_p1_db.models.user import User
from deva_p1_db.repositories.user_repository import UserRepository
from fastapi import Cookie, Depends
from redis.asyncio import Redis

from back.schemas.user import UserSchema
from back.token import AccessToken
from database.db import Session
from database.redis import RedisType, get_redis_client
from back.exceptions import *


async def get_user(access_token: str = Cookie(default=None),
                   redis: Redis = Depends(get_redis_client)
                   ) -> UserSchema:
    if access_token is None:
        raise AccessTokenDoesNotExistException()
    access = AccessToken.from_token(access_token)
    current_time = datetime.now(UTC).replace(tzinfo=None)
    if access.created_date > current_time or access.created_date + access.lifetime < current_time:
        raise AccessTokenExpiredException()
    if await redis.exists(f"{RedisType.invalidated_access_token}:{access.user.id}"):
        raise AccessTokenInvalidatedException()
    if access.user is None:
        raise AccessTokenDamagedException()
    return access.user


async def get_user_db(session: Session,
                      user: UserSchema = Depends(get_user)
                      ) -> User:
    ur = UserRepository(session)
    user_db = await ur.get_by_id(user.id)
    if user_db is None:
        raise SendFeedbackToAdminException()
    return user_db
