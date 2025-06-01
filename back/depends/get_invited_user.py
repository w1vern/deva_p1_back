

from deva_p1_db.models import Project, User
from deva_p1_db.repositories import InvitedUserRepository, UserRepository
from fastapi import Depends

from back.exceptions import *

from .database import get_invited_user_repo, get_user_repo
from .get_project import get_project


async def get_invited_user(invited_user_id: UUID,
                           project: Project = Depends(get_project),
                           ur: UserRepository = Depends(get_user_repo),
                           iur: InvitedUserRepository = Depends(
                               get_invited_user_repo)
                           ) -> User:
    invited_user = await ur.get_by_id(invited_user_id)
    if invited_user is None:
        raise UserNotFoundException(invited_user_id)
    _ = await iur.get_by_id(invited_user, project)
    if _ is None or \
            _.project_id != project.id or \
            _.user_id != invited_user.id:
        raise UserNotInvitedException()
    return invited_user


async def get_not_invited_user(invited_user_id: UUID,
                               project: Project = Depends(get_project),
                               ur: UserRepository = Depends(get_user_repo),
                               iur: InvitedUserRepository = Depends(
                                   get_invited_user_repo)
                               ) -> User:
    invited_user = await ur.get_by_id(invited_user_id)
    if invited_user is None:
        raise UserNotFoundException(invited_user_id)
    _ = await iur.get_by_id(invited_user, project)
    if _:
        raise UserAlreadyInvitedException()
    return invited_user
