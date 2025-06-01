from datetime import UTC, datetime

from deva_p1_db.models import User
from deva_p1_db.repositories import UserRepository
from fastapi import Cookie, Depends
from redis.asyncio import Redis

from back.exceptions import *
from back.schemas.user import UserSchema
from back.token import AccessToken
from database.redis import RedisType, get_redis_client

from .database import get_user_repo


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


async def get_user_db(user: UserSchema = Depends(get_user),
                      ur: UserRepository = Depends(get_user_repo)
                      ) -> User:
    user_db = await ur.get_by_id(user.id)
    if user_db is None:
        raise SendFeedbackToAdminException()
    return user_db



