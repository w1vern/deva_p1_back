
from datetime import UTC, datetime

from deva_p1_db.models.user import User
from deva_p1_db.repositories.user_repository import UserRepository
from fastapi import APIRouter, Cookie, Depends, Request, Response
from redis.asyncio import Redis

from back.config import Config
from back.depends import get_user, get_user_db, get_user_repo
from back.exceptions import *
from back.schemas.user import (CredsSchema, RegisterSchema, UserSchema,
                               UserUpdateSchema)
from back.token import AccessToken, RefreshToken
from database.redis import RedisType, get_redis_client

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/refresh")
async def refresh(response: Response,
                  refresh_token: str = Cookie(None),
                  ur: UserRepository = Depends(get_user_repo)
                  ):
    if refresh_token is None:
        raise RefreshTokenDoesNotExistException()
    refresh = RefreshToken.from_token(refresh_token)
    current_time = datetime.now(UTC).replace(tzinfo=None)
    if refresh.created_date > current_time or refresh.created_date + refresh.lifetime < current_time:
        raise RefreshTokenExpiredException()
    user = await ur.get_by_id(refresh.user_id)
    if user is None:
        raise InvalidRefreshTokenException()
    if user.secret != refresh.secret:
        raise InvalidRefreshTokenException()
    access = AccessToken(user, current_time)
    response.set_cookie(key="access_token", value=access.to_token(
    ), max_age=Config.access_token_lifetime, httponly=True)
    return {"message": "OK"}


@router.post("/register")
async def register(request: Request,
                   register_data: RegisterSchema,
                   redis: Redis = Depends(get_redis_client),
                   ur: UserRepository = Depends(get_user_repo)
                   ):
    lock_time = await redis.ttl(f"{RedisType.invalidated_access_token}:{register_data.login}")
    if lock_time > 0:
        raise LoginLockedException(lock_time)
    ip = request.client.host  # type: ignore
    ip_counter = await redis.get(f"{RedisType.incorrect_credentials_ip}:{ip}")
    if ip_counter is not None:
        if int(ip_counter) >= Config.ip_buffer:
            raise TooManyIncorrectCredentialsException(ip)
    else:
        ip_counter = 0
    if register_data.password != register_data.password_repeat:
        raise PasswordsDoNotMatchException()
    if await ur.get_by_login(register_data.login) is not None:
        raise UserAlreadyExistsException()
    user = await ur.create(register_data.login, register_data.password)
    if user is None:
        raise SendFeedbackToAdminException()
    return {"message": "OK"}


@router.post("/login")
async def login(request: Request,
                response: Response,
                credentials: CredsSchema,
                redis: Redis = Depends(get_redis_client),
                ur: UserRepository = Depends(get_user_repo)
                ):
    lock_time = await redis.ttl(f"{RedisType.invalidated_access_token}:{credentials.login}")
    if lock_time > 0:
        raise LoginLockedException(lock_time)
    ip = request.client.host  # type: ignore
    ip_counter = await redis.get(f"{RedisType.incorrect_credentials_ip}:{ip}")
    if ip_counter is not None:
        if int(ip_counter) >= Config.ip_buffer:
            raise TooManyIncorrectCredentialsException(ip)
    else:
        ip_counter = 0
    user = await ur.get_by_auth(credentials.login, credentials.password)
    if user is None:
        await redis.set(f"{RedisType.incorrect_credentials_ip}:{ip}", int(ip_counter) + 1, ex=Config.ip_buffer_lifetime)
        raise InvalidCredentialsException()
    refresh = RefreshToken(user_id=user.id, secret=user.secret)
    access = AccessToken(user)
    response.set_cookie(key="refresh_token", value=refresh.to_token(
    ), max_age=Config.refresh_token_lifetime, httponly=True)
    response.set_cookie(key="access_token", value=access.to_token(
    ), max_age=Config.access_token_lifetime, httponly=True)
    return {"message": "OK"}


@router.post("/logout")
async def logout(response: Response,
                 refresh_token: str = Cookie(None)
                 ):
    if refresh_token is None:
        raise UnauthorizedException()
    response.delete_cookie(key="refresh_token")
    response.delete_cookie(key="access_token")
    return {"message": "OK"}


@router.post("/logout_all")
async def logout_all(response: Response,
                     user: User = Depends(get_user_db),
                     ur: UserRepository = Depends(get_user_repo)
                     ):
    await ur.update_secret(user)
    response.delete_cookie(key="refresh_token")
    response.delete_cookie(key="access_token")
    return {"message": "OK"}


@router.patch("/update_credentials")
async def update_creds(user_update: UserUpdateSchema,
                       user: User = Depends(get_user_db),
                       ur: UserRepository = Depends(get_user_repo)
                       ):
    if user_update.new_password != user_update.new_password_repeat:
        raise PasswordsDoNotMatchException()
    await ur.update_credentials(user, user_update.new_login, user_update.new_password)
    return {"message": "OK"}


@router.get("/user_info")
async def get_user_info(self, user: UserSchema = Depends(get_user)) -> UserSchema:
    return user
