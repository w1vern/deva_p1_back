

from uuid import UUID

from deva_p1_db.models import File, User
from deva_p1_db.repositories import FileRepository
from fastapi import Depends


from back.exceptions import FileNotFoundException

from .database import get_file_repo
from .get_project import get_project_editor, get_project_viewer
from .get_user import get_user_db


async def get_file(file_id: UUID,
                   fr: FileRepository = Depends(get_file_repo)
                   ) -> File:
    file = await fr.get_by_id(file_id)
    if file is None:
        raise FileNotFoundException(file_id)
    return file


async def get_file_viewer(file: File = Depends(get_file),
                          user: User = Depends(get_user_db)
                          ) -> User:
    return await get_project_viewer(file.project, user)


async def get_file_editor(file: File = Depends(get_file),
                          user: User = Depends(get_user_db)
                          ) -> User:
    return await get_project_editor(file.project, user)
