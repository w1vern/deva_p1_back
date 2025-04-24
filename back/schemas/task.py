
from uuid import UUID

from deva_p1_db.models import Task
from pydantic import BaseModel


class TaskSchema(BaseModel):
    id: UUID
    task_type: str
    done: bool
    status: float | None = None


class TaskCreateSchema(BaseModel):
    project_id: UUID
    task_type: str
    prompt: str = ""


class RedisTaskCacheSchema(BaseModel):
    id: UUID
    project_id: UUID
    task_type: str

    @classmethod
    def from_db(cls, task: Task) -> "RedisTaskCacheSchema":
        return cls(**task.__dict__)


class ActiveTaskSchema(BaseModel):
    id: UUID
    task_type: str

    @classmethod
    def from_db(cls, task: Task) -> "ActiveTaskSchema":
        return cls(**task.__dict__)
