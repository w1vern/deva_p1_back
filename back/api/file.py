

from datetime import timedelta
from io import BytesIO
import mimetypes
from typing import Annotated
from uuid import UUID
from fastapi_controllers import Controller, get, post
from fastapi import Depends, File, HTTPException, UploadFile
from minio import Minio, S3Error

from back.db import Session

from deva_p1_db.repositories import FileRepository, ProjectRepository
from deva_p1_db.models import User

from back.get_auth import get_user_db
from back.schemas.file import FileSchema
from deva_p1_db.enums.file_type import FileType

from config import settings
from database.s3 import get_s3_client


async def download_files(files_id: list[UUID],
                         session: Session,
                         user: User = Depends(get_user_db),
                         minio_client: Minio = Depends(get_s3_client)
                         ) -> list[FileSchema]:
    files: list[FileSchema] = []
    fr = FileRepository(session)
    for file_id in files_id:
        file = await fr.get_by_id(file_id)
        if file is None:
            raise HTTPException(
                status_code=404,
                detail=f"file {file_id} not found"
            )
        if file.user_id != user.id:
            raise HTTPException(
                status_code=403,
                detail="permission denied"
            )
        files.append(FileSchema.from_db(file))
        files[-1].download_url = minio_client.presigned_get_object(
            bucket_name=settings.minio_bucket,
            object_name=str(file_id),
            expires=timedelta(seconds=10*60)
        )
    return files


class FileController(Controller):
    __prefix__ = "/file"
    __tags__ = ["file"]

    def __init__(self, session: Session) -> None:
        self.session = session
        self.fr = FileRepository(self.session)
        self.pr = ProjectRepository(self.session)

    @post("/upload")
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

            content_type = mimetypes.guess_type(file.filename)[0]
            match content_type:
                case "image/jpeg":
                    content_type = FileType.image_jpg.value
                case "image/png":
                    content_type = FileType.image_png.value
                case "image/webp":
                    content_type = FileType.image_webp.value
                case "audio/mpeg":
                    content_type = FileType.audio_mp3.value
                case "audio/wav":
                    content_type = FileType.audio_wav.value
                case "audio/ogg":
                    content_type = FileType.audio_ogg.value
                case "audio/flac":
                    content_type = FileType.audio_flac.value
                case "audio/aac":
                    content_type = FileType.audio_aac.value
                case "audio/mp4":
                    content_type = FileType.audio_m4a.value
                case "audio/opus":
                    content_type = FileType.audio_opus.value
                case "audio/webm":
                    content_type = FileType.audio_webm.value
                case "video/mp4":
                    content_type = FileType.video_mp4.value
                case "video/x-matroska":
                    content_type = FileType.video_mkv.value
                case "video/x-msvideo":
                    content_type = FileType.video_avi.value
                case "video/quicktime":
                    content_type = FileType.video_mov.value
                case "video/webm":
                    content_type = FileType.video_webm.value
                case None:
                    content_type = FileType.undefined.value
                case _:
                    content_type = FileType.undefined.value

            file_data = await file.read()
            file_size = len(file_data)

            db_file = await self.fr.create(
                user_file_name=file.filename,
                file_type=content_type,
                user=user,
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

    @get("/download_files")
    async def download_files(self, files: list[FileSchema] = Depends(download_files)) -> list[FileSchema]:
        return files
