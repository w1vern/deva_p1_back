

from uuid import UUID

from deva_p1_db.models import Project, User
from deva_p1_db.repositories import InvitedUserRepository, ProjectRepository
from fastapi import Depends

from back.exceptions import PermissionDeniedException, ProjectNotFoundException
from back.schemas import InvitedUserSchema

from .database import get_invited_user_repo, get_project_repo
from .get_user import get_user_db


async def get_project(project_id: UUID,
                      pr: ProjectRepository = Depends(get_project_repo)
                      ) -> Project:
    project = await pr.get_by_id(project_id)
    if project is None:
        raise ProjectNotFoundException(project_id)
    return project


async def get_project_viewer(project: Project = Depends(get_project),
                             user: User = Depends(get_user_db),
                             iur: InvitedUserRepository = Depends(
                                 get_invited_user_repo)
                             ) -> User:
    users = await iur.get_by_project(project)
    if user.id not in [_.user_id for _ in users] and user.id != project.holder_id:
        raise PermissionDeniedException()
    return user


async def get_project_editor(project: Project = Depends(get_project),
                             user: User = Depends(get_user_db)
                             ) -> User:
    if user.id != project.holder_id:
        raise PermissionDeniedException()
    return user

async def get_project_by_invited_user(invited_user_schema: InvitedUserSchema,
                                     pr: ProjectRepository = Depends(get_project_repo)
                                     ) -> Project:
    project = await pr.get_by_id(invited_user_schema.project_id)
    if project is None:
        raise ProjectNotFoundException(invited_user_schema.project_id)
    return project
