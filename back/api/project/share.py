

from deva_p1_db.models import Project, User
from deva_p1_db.repositories import InvitedUserRepository
from fastapi import APIRouter, Depends

from back.depends import (get_invited_user, get_invited_user_repo,
                          get_not_invited_user, get_project,
                          get_project_editor)
from back.exceptions import *
from back.schemas import UserSchema

router = APIRouter(prefix="/share", tags=["share"])


@router.post("")
async def share_project(project: Project = Depends(get_project),
                        user: User = Depends(get_project_editor),
                        invited_user: User = Depends(get_not_invited_user),
                        iur: InvitedUserRepository = Depends(
                            get_invited_user_repo)
                        ):
    await iur.create(invited_user, project)
    return {"message": "OK"}


@router.delete("/{project_id}&{invited_user_id}")
async def unshare_project(project: Project = Depends(get_project),
                          user: User = Depends(get_project_editor),
                          invited_user: User = Depends(get_invited_user),
                          iur: InvitedUserRepository = Depends(
                              get_invited_user_repo)
                          ):
    iu = await iur.get_by_id(invited_user, project)
    if iu is None:
        raise UserNotInvitedException()
    await iur.delete(iu)
    return {"message": "OK"}


@router.get("")
async def get_invited_users_list(project: Project = Depends(get_project),
                                 user: User = Depends(get_project_editor),
                                 iur: InvitedUserRepository = Depends(
                                     get_invited_user_repo)
                                 ) -> list[UserSchema]:
    return [UserSchema.from_db(_.user) for _ in await iur.get_by_project(project)]
