

from io import BytesIO
import mimetypes
from typing import Annotated
from uuid import UUID
from fastapi_controllers import Controller
from fastapi import Depends, File, HTTPException, UploadFile
from minio import Minio, S3Error

from back.db import Session

from deva_p1_db.repositories import FileRepository, ProjectRepository
from deva_p1_db.models import User

from back.get_auth import get_user_db
from back.schemas.file import FileSchema
from deva_p1_db.enums.s3_type import S3Type

from config import settings
from database.s3 import get_s3_client


class FileController(Controller):
    __prefix__ = "/file"
    __tags__ = ["file"]

    def __init__(self, session: Session) -> None:
        self.session = session
        self.fr = FileRepository(self.session)
        self.pr = ProjectRepository(self.session)

    async def upload_file(self,
                          project_id: UUID,
                          file: Annotated[UploadFile, File(...)],
                          user: User = Depends(get_user_db),
                          minio_client: Minio = Depends(get_s3_client),
                          ) -> FileSchema:

        try:
            if not minio_client.bucket_exists(settings.minio_bucket):
                try:
                    minio_client.make_bucket(settings.minio_bucket)
                except S3Error as e:
                    raise HTTPException(
                        status_code=500,
                        detail=f"bucket creation error: {e.message}"
                    )

            project = await self.pr.get_by_id(project_id)
            if project is None:
                raise HTTPException(
                    status_code=404,
                    detail="project not found"
                )
            if file.filename is None:
                file.filename = ""

            content_type = (
                mimetypes.guess_type(file.filename)[0]
                or S3Type.undefined.value
            )

            file_data = await file.read()
            file_size = len(file_data)

            db_file = await self.fr.create(
                user_file_name=file.filename,
                file_type=content_type,
                project=project
            )

            if db_file is None:
                raise HTTPException(
                    status_code=500,
                    detail="server error"
                )

            owr = minio_client.put_object(
                bucket_name=settings.minio_bucket,
                object_name=str(db_file.id),
                data=BytesIO(file_data),
                length=file_size,
                content_type=content_type
            )
            return FileSchema.from_db(db_file)
        except S3Error as e:
            raise HTTPException(
                status_code=500,
                detail=f"MinIO error: {e.message}"
            )
        finally:
            await file.close()
