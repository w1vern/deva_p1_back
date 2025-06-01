from datetime import UTC, datetime

from deva_p1_db.models import User, InvitedUser
from deva_p1_db.repositories import UserRepository, InvitedUserRepository, ProjectRepository
from fastapi import Cookie, Depends
from redis.asyncio import Redis


from back.exceptions import *
from back.schemas import UserSchema, InvitedUserSchema
from back.token import AccessToken
from database.redis import RedisType, get_redis_client

from .database import get_user_repo, get_invited_user_repo, get_project_repo


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


async def util(invited_user_schema: InvitedUserSchema,
               ur: UserRepository,
               pr: ProjectRepository,
               iur: InvitedUserRepository
               ) -> tuple[User, InvitedUser | None]:
    user = await ur.get_by_login(invited_user_schema.login)
    project = await pr.get_by_id(invited_user_schema.project_id)
    if not user:
        raise UserNotFoundException(invited_user_schema.login)
    if not project:
        raise ProjectNotFoundException(invited_user_schema.project_id)
    invited_user = await iur.get_by_id(user, project)
    return user, invited_user


async def get_not_invited_user(invited_user_schema: InvitedUserSchema,
                               ur: UserRepository = Depends(get_user_repo),
                               pr: ProjectRepository = Depends(
                                   get_project_repo),
                               iur: InvitedUserRepository = Depends(
                                   get_invited_user_repo)
                               ) -> User:
    user, invited_user = await util(invited_user_schema, ur, pr, iur)
    if invited_user:
        raise UserAlreadyInvitedException()
    return user


async def get_invited_user(invited_user_schema: InvitedUserSchema,
                           ur: UserRepository = Depends(get_user_repo),
                           pr: ProjectRepository = Depends(get_project_repo),
                           iur: InvitedUserRepository = Depends(
                               get_invited_user_repo)
                           ) -> InvitedUser:
    _, invited_user = await util(invited_user_schema, ur, pr, iur)
    if not invited_user:
        raise UserNotInvitedException()
    return invited_user
