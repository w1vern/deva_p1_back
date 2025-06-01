

from datetime import timedelta
import mimetypes
import re
from io import BytesIO
from typing import Annotated

from deva_p1_db.enums.file_type import FileCategory, resolve_file_type
from deva_p1_db.models import File, Project, User
from deva_p1_db.repositories import FileRepository, ProjectRepository
from fastapi import APIRouter, Depends
from fastapi import File as fastapi_file
from fastapi import Request, UploadFile
from fastapi.responses import StreamingResponse
from minio import Minio, S3Error
from sqlalchemy.ext.asyncio import AsyncSession

from back.config import Config
from back.depends import (get_file, get_file_editor, get_file_repo,
                          get_file_viewer, get_project, get_project_editor,
                          get_project_repo)
from back.exceptions import *
from back.schemas.file import FileEditSchema, FileSchema
from back.schemas.user import UserSchema
from config import settings
from database.database import session_manager
from database.minio import get_s3_client

router = APIRouter(prefix="/file", tags=["file"])


@router.post("")
async def upload_file(file: Annotated[UploadFile, fastapi_file(...)],
                      project: Project = Depends(get_project),
                      user: UserSchema = Depends(get_project_editor),
                      minio_client: Minio = Depends(get_s3_client),
                      fr: FileRepository = Depends(get_file_repo),
                      pr: ProjectRepository = Depends(get_project_repo),
                      session: AsyncSession = Depends(session_manager.session)
                      ) -> FileSchema:
    if file.filename is None:
        file.filename = ""

    content_type = mimetypes.guess_type(file.filename)[0]
    if content_type is None:
        raise UndefinedFileTypeException()
    file_type = resolve_file_type(content_type)
    file_category = file_type.category

    if file_category not in [FileCategory.audio.value,
                             FileCategory.video.value,
                             FileCategory.image.value,
                             FileCategory.summary,
                             FileCategory.transcribe]:
        raise InvalidFileTypeException()

    if file_category in [FileCategory.audio.value,
                         FileCategory.video.value] \
            and project.origin_file_id is not None:
        raise ProjectAlreadyHasOriginFileException()

    file_data = await file.read()
    file_size = len(file_data)

    db_file = await fr.create(
        file_name=file.filename,
        file_type=file_type.internal,
        user=project.holder,
        file_size=file_size,
        project=project
    )

    if db_file is None:
        raise SendFeedbackToAdminException()

    try:
        minio_client.put_object(
            bucket_name=settings.minio_bucket,
            object_name=str(db_file.id),
            data=BytesIO(file_data),
            length=file_size,
            content_type=content_type
        )
    except S3Error as e:
        await session.rollback()
        raise MinioException(e.message)
    finally:
        await file.close()

    go_down = False
    match file_category:
        case FileCategory.audio.value:
            go_down = True
        case value if value is FileCategory.video.value or go_down:
            await pr.add_origin_file(project, db_file)
        case FileCategory.transcribe.value:
            await pr.add_transcription_file(project, db_file)
        case FileCategory.summary.value:
            await pr.add_summary_file(project, db_file)

    return FileSchema.from_db(db_file)


@router.patch("/{file_id}")
async def update_file(edited_fields: FileEditSchema,
                      file: File = Depends(get_file),
                      user: User = Depends(get_file_editor),
                      fr: FileRepository = Depends(get_file_repo)
                      ) -> FileSchema:
    await fr.update_metadata(
        file=file,
        is_hide=edited_fields.metadata_is_hide,
        timecode=edited_fields.metadata_timecode,
        text=edited_fields.metadata_text,
        file_name=edited_fields.file_name)
    updated_file = await fr.get_by_id(file.id)
    if updated_file is None:
        raise SendFeedbackToAdminException()
    return FileSchema.from_db(updated_file)


@router.delete("/{file_id}")
async def hide_file(file: File = Depends(get_file),
                    user: User = Depends(get_file_editor),
                    pr: ProjectRepository = Depends(get_file_repo)
                    ) -> None:
    project = file.project
    category = resolve_file_type(file.file_type).category
    go_down = False
    match category:
        case FileCategory.audio.value:
            go_down = True
        case value if value is FileCategory.video.value or go_down:
            if project.origin_file_id != file.id:
                await pr.delete_origin_file(project)
                await pr.delete_transcription_file(project)
                await pr.delete_summary_file(project)
        case FileCategory.transcribe.value:
            if project.transcription_id != file.id:
                await pr.delete_transcription_file(project)
                await pr.delete_summary_file(project)
        case FileCategory.summary.value:
            if project.summary_id != file.id:
                await pr.delete_summary_file(project)


@router.get("/download/{file_id}")
async def download_file(file: File = Depends(get_file),
                        user: User = Depends(get_file_viewer),
                        minio_client: Minio = Depends(get_s3_client)
                        ):
    try:
        response = minio_client.get_object(
            bucket_name=settings.minio_bucket,
            object_name=str(file.id),
        )
    except S3Error as e:
        raise MinioException(e.message)
    return StreamingResponse(
        response,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{file.file_name}"'})

@router.get("minio_url/{file_id}")
async def get_minio_url(file: File = Depends(get_file),
                        user: User = Depends(get_file_viewer),
                        minio_client: Minio = Depends(get_s3_client)
                        ) -> str:


    return minio_client.presigned_get_object(
        bucket_name=settings.minio_bucket,
        object_name=str(file.id),
        expires=timedelta(seconds=Config.minio_url_live_time)
    ).replace(f"{settings.minio_ip}:{settings.minio_port}", f"{settings.minio_url}")


@router.get("/video/{file_id}")
async def stream_video(request: Request,
                       file: File = Depends(get_file),
                       user: User = Depends(get_file_viewer),
                       minio_client: Minio = Depends(get_s3_client)
                       ):
    range_header = request.headers.get("range")
    if range_header is None:
        raise RangeHeaderRequiredException()

    match = re.match(r"bytes=(\d+)-(\d*)", range_header)
    if not match:
        raise InvalidRangeHeaderException()

    start = int(match.group(1))
    end = int(match.group(2)) if match.group(2) else None

    try:

        stat = minio_client.stat_object(
            settings.minio_bucket, str(file.id))
        file_size = stat.size
        if file_size is None:
            raise FileNotFoundException(file.id)

        if end is None or end >= file_size:
            end = file_size - 1

        content_length = end - start + 1

        response = minio_client.get_object(
            settings.minio_bucket,
            str(file.id),
            offset=start,
            length=content_length
        )

    except S3Error as e:
        raise MinioException(e.message)

    headers = {
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(content_length),
        "Content-Type": "video/mp4",
    }

    return StreamingResponse(response, status_code=206, headers=headers)
