from datetime import UTC, datetime

from fastapi import Cookie, Depends, HTTPException
from redis.asyncio import Redis

from back.token import AccessToken
from back.schemas.user import UserSchema
from back.db import Session 
from deva_p1_db.models.user import User
from database.redis import RedisType, get_redis_client
from deva_p1_db.repositories.user_repository import UserRepository


async def get_user(access_token: str = Cookie(default=None), redis: Redis = Depends(get_redis_client)) -> UserSchema:
    if access_token is None:
        raise HTTPException(
            status_code=401, detail="access token doesn't exist")
    access = AccessToken.from_token(access_token)
    current_time = datetime.now(UTC).replace(tzinfo=None)
    if access.created_date > current_time or access.created_date + access.lifetime < current_time:
        raise HTTPException(status_code=401, detail="access token expired")
    if await redis.exists(f"{RedisType.invalidated_access_token}:{access.user.id}"):
        raise HTTPException(status_code=401, detail="access token invalidated")
    if access.user is None:
        raise HTTPException(status_code=401, detail="access token damaged")
    return access.user


async def get_user_db(session: Session, user: UserSchema = Depends(get_user)) -> User:
    ur = UserRepository(session)
    user_db = await ur.get_by_id(user.id)
    if user_db is None:
        raise HTTPException(status_code=401, detail="send feedback to admin")
    return user_db
