

import mimetypes
import re
from io import BytesIO
from typing import Annotated
from uuid import UUID
from zipfile import ZIP_DEFLATED, ZipFile

from deva_p1_db.enums.file_type import (FileCategory, FileTypes,
                                        resolve_file_type)
from deva_p1_db.models import File as FileDb
from deva_p1_db.models import User
from deva_p1_db.repositories import FileRepository, ProjectRepository
from fastapi import Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from fastapi_controllers import Controller, get, post
from minio import Minio, S3Error

from back.get_auth import get_user, get_user_db
from back.schemas.file import FileDownloadURLSchema, FileSchema
from back.schemas.user import UserSchema
from config import settings
from database.db import Session
from database.s3 import get_s3_client


class FileController(Controller):
    prefix = "/file"
    tags = ["file"]

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
            project = await self.pr.get_by_id(project_id)
            if project is None:
                raise HTTPException(
                    status_code=404,
                    detail="project not found"
                )
            if file.filename is None:
                file.filename = ""

            content_type = mimetypes.guess_type(file.filename)[0]
            if content_type is None:
                raise HTTPException(
                    status_code=400,
                    detail="undefined file type"
                )
            file_category = resolve_file_type(content_type).category
            if not file_category in [FileCategory.audio.value, FileCategory.video.value, FileCategory.image.value]:
                raise HTTPException(
                    status_code=400,
                    detail="unsupported file type to upload"
                )
            if file_category in [FileCategory.audio.value, FileCategory.video.value] and project.origin_file_id is not None:
                raise HTTPException(
                    status_code=400,
                    detail="project already has origin file"
                )

            file_data = await file.read()
            file_size = len(file_data)

            db_file = await self.fr.create(
                user_file_name=file.filename,
                file_type=content_type,
                user=user,
                file_size=file_size,
                project=project
            )

            if db_file is None:
                raise HTTPException(
                    status_code=500,
                    detail="server error"
                )

            minio_client.put_object(
                bucket_name=settings.minio_bucket,
                object_name=db_file.minio_name,
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

    @get("/download/{file_id}")
    async def download_file(self,
                            file_id: str,
                            user: User = Depends(get_user_db),
                            minio_client: Minio = Depends(get_s3_client)
                            ):
        file = await self.fr.get_by_id(UUID(file_id))
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
        response = minio_client.get_object(
            bucket_name=settings.minio_bucket,
            object_name=file.minio_name,
        )
        return StreamingResponse(
            response,
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{file.file_name}"'})

    # @post("/download_files")
    # async def download_files(self, files_id: list[str], user: User = Depends(get_user_db), minio_client: Minio = Depends(get_s3_client)):
    #     files: list[FileDb] = []
    #     for file_id in files_id:
    #         file = await self.fr.get_by_id(UUID(file_id))
    #         if file is None:
    #             raise HTTPException(
    #                 status_code=404,
    #                 detail=f"file {file_id} not found"
    #             )
    #         if file.user_id != user.id:
    #             raise HTTPException(
    #                 status_code=403,
    #                 detail="permission denied"
    #             )
    #         files.append(file)
    #     if len(files) == 0:
    #         raise HTTPException(
    #             status_code=404,
    #             detail="files not found"
    #         )

    #     zip_stream = BytesIO()
    #     with ZipFile(zip_stream, "w", ZIP_DEFLATED) as zip_file:
    #         for file in files:
    #             obj = minio_client.get_object(
    #                 bucket_name=settings.minio_bucket,
    #                 object_name=str(file.id),
    #             )
    #             with zip_file.open(file.user_file_name, "w") as dest_file:
    #                 shutil.copyfileobj(obj, dest_file, length=1024*64)
    #             obj.close()
    #             obj.release_conn()

    #     zip_stream.seek(0)
    #     return StreamingResponse(
    #         zip_stream,
    #         media_type="application/zip",
    #         headers={
    #             "Content-Disposition": f'attachment; filename="{user.login}.zip"'}
    #     )

    # @post("/get_download_urls")
    # async def get_download_urls(self, files_id: list[str], user: User = Depends(get_user_db), minio_client: Minio = Depends(get_s3_client)) -> list[FileDownloadURLSchema]:
    #     files: list[FileDownloadURLSchema] = []
    #     for file_id in files_id:
    #         file = await self.fr.get_by_id(UUID(file_id))
    #         if file is None:
    #             raise HTTPException(
    #                 status_code=404,
    #                 detail=f"file {file_id} not found"
    #             )
    #         if file.user_id != user.id:
    #             raise HTTPException(
    #                 status_code=403,
    #                 detail="permission denied"
    #             )
    #         files.append(FileDownloadURLSchema.from_db(file, minio_client.presigned_get_object(
    #             bucket_name=settings.minio_bucket,
    #             object_name=file.minio_name,
    #             expires=timedelta(seconds=Config.minio_url_live_time),
    #             response_headers={
    #                 "response-content-disposition": f'attachment; filename="{file.file_name}"'
    #             })))
    #     return files

    @get("/video/{file_id}")
    async def stream_video(self,
                           file_id: str,
                           request: Request,
                           user: UserSchema = Depends(get_user),
                           minio_client: Minio = Depends(get_s3_client)
                           ):
        range_header = request.headers.get("range")
        if range_header is None:
            raise HTTPException(
                status_code=416, detail="Range header required")

        match = re.match(r"bytes=(\d+)-(\d*)", range_header)
        if not match:
            raise HTTPException(status_code=416, detail="Invalid Range header")

        start = int(match.group(1))
        end = int(match.group(2)) if match.group(2) else None

        stat = minio_client.stat_object(settings.minio_bucket, file_id)
        file_size = stat.size
        if file_size is None:
            raise HTTPException(status_code=404, detail="File not found")

        if end is None or end >= file_size:
            end = file_size - 1

        content_length = end - start + 1

        response = minio_client.get_object(
            settings.minio_bucket,
            file_id,
            offset=start,
            length=content_length
        )

        headers = {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(content_length),
            "Content-Type": "video/mp4",
        }

        return StreamingResponse(response, status_code=206, headers=headers)
