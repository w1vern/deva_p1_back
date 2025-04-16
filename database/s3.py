
from enum import Enum
from minio import Minio

from config import settings

class S3Type(str, Enum):
    undefined = "undefined"


async def get_s3_client() -> Minio:
    return Minio(
        endpoint=settings.minio_ip,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure
    )
