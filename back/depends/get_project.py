

from uuid import UUID

from deva_p1_db.models import Project, User
from deva_p1_db.repositories import InvitedUserRepository, ProjectRepository
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from back.exceptions import PermissionDeniedException, ProjectNotFoundException
from database.db import session_manager

from .get_user import get_user_db


async def get_project(project_id: UUID, session: AsyncSession = Depends(session_manager.session)) -> Project:
    pr = ProjectRepository(session)
    project = await pr.get_by_id(project_id)
    if project is None:
        raise ProjectNotFoundException(project_id)
    return project

async def get_project_viewer(session: AsyncSession = Depends(session_manager.session),
                             project: Project = Depends(get_project),
                             user: User = Depends(get_user_db)
                             ) -> User:
    iur = InvitedUserRepository(session)
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
