

from deva_p1_db.models import Project, User, InvitedUser
from deva_p1_db.repositories import InvitedUserRepository
from fastapi import APIRouter, Depends

from back.depends import (get_invited_user, get_invited_user_repo,
                          get_not_invited_user, get_project,
                          get_project_editor, get_project_by_invited_user,
                          get_user_db)
from back.exceptions import *
from back.schemas import UserSchema

router = APIRouter(prefix="/share", tags=["share"])


@router.post("")
async def share_project(project: Project = Depends(get_project_by_invited_user),
                        user: User = Depends(get_user_db),
                        invited_user: User = Depends(get_not_invited_user),
                        iur: InvitedUserRepository = Depends(
                            get_invited_user_repo)
                        ):
    user = await get_project_editor(project, user)
    await iur.create(invited_user, project)
    return {"message": "OK"}


@router.delete("")
async def unshare_project(project: Project = Depends(get_project_by_invited_user),
                          user: User = Depends(get_user_db),
                          invited_user: InvitedUser = Depends(
                              get_invited_user),
                          iur: InvitedUserRepository = Depends(
                              get_invited_user_repo)
                          ):
    user = await get_project_editor(project, user)
    await iur.delete(invited_user)
    return {"message": "OK"}


@router.get("/{project_id}")
async def get_invited_users_list(project: Project = Depends(get_project),
                                 user: User = Depends(get_project_editor),
                                 iur: InvitedUserRepository = Depends(
                                     get_invited_user_repo)
                                 ) -> list[UserSchema]:
    return [UserSchema.from_db(_.user) for _ in await iur.get_by_project(project)]
