
import random
from datetime import UTC, datetime

from fastapi import Cookie, Depends, HTTPException, Request, Response
from fastapi_controllers import Controller, get, post

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from back.config import Config
from back.get_auth import get_user
from back.schemas.user import CredsSchema, RegisterSchema, UserSchema
from back.token import AccessToken, RefreshToken
from back.db import Session
from deva_p1_db.models.user import User
from database.redis import RedisType, get_redis_client
from deva_p1_db.repositories.user_repository import UserRepository


def create_code() -> str:
    tmp_code = str(random.randrange(start=0, stop=1000000))
    return "0"*(6-len(tmp_code)) + tmp_code


class AuthController(Controller):
    prefix = "/auth"
    tags = ["auth"]

    def __init__(self, session: Session) -> None:
        self.session = session

    @post("/refresh")
    # TODO: refresh secret logic
    async def refresh(self, response: Response, session: Session, refresh_token: str = Cookie(None)):
        if refresh_token is None:
            raise HTTPException(
                status_code=401, detail="refresh token doesn't exist")
        refresh = RefreshToken.from_token(refresh_token)
        current_time = datetime.now(UTC).replace(tzinfo=None)
        if refresh.created_date > current_time or refresh.created_date + refresh.lifetime < current_time:
            raise HTTPException(
                status_code=401, detail="refresh token expired")
        ur = UserRepository(self.session)
        user = await ur.get_by_id(refresh.user_id)
        if user is None:
            raise HTTPException(
                status_code=401, detail="incorrect refresh token")
        if user.secret != refresh.secret:
            raise HTTPException(
                status_code=401, detail="incorrect refresh token")
        access = AccessToken(user, current_time)
        response.set_cookie(key="access_token", value=access.to_token(
        ), max_age=Config.access_token_lifetime, httponly=True)
        return {"message": "OK"}

    @post("/register")
    async def register(self, request: Request, response: Response, register_data: RegisterSchema, redis: Redis = Depends(get_redis_client)):
        lock_time = await redis.ttl(f"{RedisType.invalidated_access_token}:{register_data.login}")
        if lock_time > 0:
            raise HTTPException(
                status_code=401, detail=f"login locked for {lock_time} seconds")
        ip = request.client.host  # type: ignore
        ip_counter = await redis.get(f"{RedisType.incorrect_credentials_ip}:{ip}")
        if ip_counter is not None:
            if int(ip_counter) >= Config.ip_buffer:
                raise HTTPException(
                    status_code=401, detail=f"too many incorrect credentials for ip: {ip}")
        else:
            ip_counter = 0
        ur = UserRepository(self.session)
        if register_data.password != register_data.password_repeat:
            raise HTTPException(
                status_code=401, detail="passwords do not match")
        if not await ur.get_by_auth(register_data.login, register_data.password) is None:
            raise HTTPException(
                status_code=401, detail="user with this creds is already exists")
        user = await ur.create(register_data.login, register_data.password)
        if user is None:
            raise HTTPException(
                status_code=401, detail="undefined error, try again")
        return {"message": "OK"}

    @post("/login")
    async def login(self, request: Request, response: Response, credentials: CredsSchema, redis: Redis = Depends(get_redis_client)):
        lock_time = await redis.ttl(f"{RedisType.invalidated_access_token}:{credentials.login}")
        if lock_time > 0:
            raise HTTPException(
                status_code=401, detail=f"login locked for {lock_time} seconds")
        ip = request.client.host  # type: ignore
        ip_counter = await redis.get(f"{RedisType.incorrect_credentials_ip}:{ip}")
        if ip_counter is not None:
            if int(ip_counter) >= Config.ip_buffer:
                raise HTTPException(
                    status_code=401, detail=f"too many incorrect credentials for ip: {ip}")
        else:
            ip_counter = 0
        ur = UserRepository(self.session)
        user = await ur.get_by_auth(credentials.login, credentials.password)
        if user is None:
            await redis.set(f"{RedisType.incorrect_credentials_ip}:{ip}", int(ip_counter) + 1, ex=Config.ip_buffer_lifetime)
            raise HTTPException(status_code=401, detail="invalid credentials")
        refresh = RefreshToken(user_id=user.id, secret=user.secret)
        access = AccessToken(user)
        response.set_cookie(key="refresh_token", value=refresh.to_token(
        ), max_age=Config.refresh_token_lifetime, httponly=True)
        response.set_cookie(key="access_token", value=access.to_token(
        ), max_age=Config.access_token_lifetime, httponly=True)
        return {"message": "OK"}

    @post("/logout")
    async def logout(self, response: Response, refresh_token: str = Cookie(None)):
        if refresh_token is None:
            raise HTTPException(status_code=401, detail="unauthorized")
        response.delete_cookie(key="refresh_token")
        response.delete_cookie(key="access_token")
        return {"message": "OK"}

    @get("/user_info")
    async def get_user_info(self, user: UserSchema = Depends(get_user)) -> UserSchema:
        return user
