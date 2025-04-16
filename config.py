import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=f"{os.getenv('TARGET', 'dev')}.env")
    
    db_user: str = "postgres"
    db_password: str = "1234"
    db_ip: str = "postgres"
    db_port: int = 5432
    db_name: str = "vpn_db"
    redis_ip: str = "redis"
    redis_port: int = 6379
    rabbit_user: str = "guest"
    rabbit_password: str = "guest"
    rabbit_ip: str = "rabbitmq"
    rabbit_port: int = 5672
    secret: str = "YOUR_SECRET"
    minio_ip: str = "minio"
    minio_port: int = 9000
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "my-bucket"
    minio_secure: bool = False
    

settings = Settings()
