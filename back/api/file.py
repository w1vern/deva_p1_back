

from database.s3 import get_s3_client
from database.db import Session
from config import settings
from back.schemas.user import UserSchema
from back.schemas.file import FileEditSchema, FileSchema
from back.get_auth import get_user, get_user_db
from minio import Minio, S3Error
from fastapi_controllers import Controller, get, patch, post, delete
from fastapi.responses import StreamingResponse
from fastapi import Depends, File, HTTPException, Request, UploadFile
from deva_p1_db.repositories import FileRepository, ProjectRepository
from deva_p1_db.models import User
import mimetypes
import re
from io import BytesIO
from typing import Annotated
from uuid import UUID

from deva_p1_db.enums.file_type import FileCategory, resolve_file_type


class FileController(Controller):
    prefix = "/file"
    tags = ["file"]

    def __init__(self, session: Session) -> None:
        self.session = session
        self.fr = FileRepository(self.session)
        self.pr = ProjectRepository(self.session)

    @post("")
    async def upload_file(self,
                          project_id: UUID,
                          file: Annotated[UploadFile, File(...)],
                          user: UserSchema = Depends(get_user),
                          minio_client: Minio = Depends(get_s3_client)
                          ) -> FileSchema:

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
        file_type = resolve_file_type(content_type)
        file_category = file_type.category

        if file_category not in [FileCategory.audio.value, FileCategory.video.value, FileCategory.image.value, FileCategory.summary, FileCategory.transcribe]:
            raise HTTPException(
                status_code=400,
                detail="invalid file type"
            )

        if file_category in [FileCategory.audio.value, FileCategory.video.value] and project.origin_file_id is not None:
            raise HTTPException(
                status_code=400,
                detail="project already has origin file"
            )

        file_data = await file.read()
        file_size = len(file_data)

        db_file = await self.fr.create(
            file_name=file.filename,
            file_type=file_type.internal,
            user=project.holder,
            file_size=file_size,
            project=project
        )

        if db_file is None:
            raise HTTPException(
                status_code=500,
                detail="server error"
            )

        try:
            minio_client.put_object(
                bucket_name=settings.minio_bucket,
                object_name=str(db_file.id),
                data=BytesIO(file_data),
                length=file_size,
                content_type=content_type
            )
        except S3Error as e:
            await self.session.rollback()
            raise HTTPException(
                status_code=404,
                detail=f"MinIO error: {e.message}"
            )
        finally:
            await file.close()

        go_down = False
        match file_category:
            case FileCategory.audio.value:
                go_down = True
            case value if value is FileCategory.video.value or go_down:
                await self.pr.add_origin_file(project, db_file)
            case FileCategory.transcribe.value:
                await self.pr.add_transcription_file(project, db_file)
            case FileCategory.summary.value:
                await self.pr.add_summary_file(project, db_file)

        return FileSchema.from_db(db_file)

    @patch("/{file_id}")
    async def update_file(self,
                          file_id: UUID,
                          edited_fields: FileEditSchema,
                          user: UserSchema = Depends(get_user),
                          ) -> FileSchema:
        file = await self.fr.get_by_id(file_id)
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
        await self.fr.update_metadata(
            file=file,
            is_hide=edited_fields.metadata_is_hide,
            timecode=edited_fields.metadata_timecode,
            text=edited_fields.metadata_text,
            file_name=edited_fields.file_name)
        file = await self.fr.get_by_id(file_id)
        if file is None:
            raise HTTPException(
                status_code=500,
                detail=f"internal server error"
            )
        return FileSchema.from_db(file)
    
    @delete("/{file_id}")
    async def hide_file(self,
                          file_id: UUID,
                          user: UserSchema = Depends(get_user)
                          ) -> None:
        file = await self.fr.get_by_id(file_id)
        if file is None:
            raise HTTPException(
                status_code=404,
                detail=f"file {file_id} not found"
            )
        project = file.project
        if file.user_id != user.id:
            raise HTTPException(
                status_code=403,
                detail="permission denied"
            )
        category = resolve_file_type(file.file_type).category
        go_down = False
        match category:
            case FileCategory.audio.value:
                go_down = True
            case value if value is FileCategory.video.value or go_down:
                if project.origin_file_id != file_id:
                    await self.pr.delete_origin_file(project)
                    await self.pr.delete_transcription_file(project)
                    await self.pr.delete_summary_file(project)
            case FileCategory.transcribe.value:
                if project.transcription_id != file_id:
                    await self.pr.delete_transcription_file(project)
                    await self.pr.delete_summary_file(project)
            case FileCategory.summary.value:
                if project.summary_id != file_id:
                    await self.pr.delete_summary_file(project)

    @get("/download/{file_id}")
    async def download_file(self,
                            file_id: UUID,
                            user: User = Depends(get_user_db),
                            minio_client: Minio = Depends(get_s3_client)
                            ):
        file = await self.fr.get_by_id(file_id)
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
        try:
            response = minio_client.get_object(
                bucket_name=settings.minio_bucket,
                object_name=str(file.id),
            )
        except S3Error as e:
            raise HTTPException(
                status_code=404,
                detail=f"MinIO error: {e.message}"
            )
        return StreamingResponse(
            response,
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{file.file_name}"'})

    @get("/video/{file_id}")
    async def stream_video(self,
                           file_id: UUID,
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

        try:

            stat = minio_client.stat_object(
                settings.minio_bucket, str(file_id))
            file_size = stat.size
            if file_size is None:
                raise HTTPException(status_code=404, detail="File not found")

            if end is None or end >= file_size:
                end = file_size - 1

            content_length = end - start + 1

            response = minio_client.get_object(
                settings.minio_bucket,
                str(file_id),
                offset=start,
                length=content_length
            )

        except S3Error as e:
            raise HTTPException(
                status_code=404,
                detail=f"MinIO error: {e.message}"
            )

        headers = {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(content_length),
            "Content-Type": "video/mp4",
        }

        return StreamingResponse(response, status_code=206, headers=headers)
