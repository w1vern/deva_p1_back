
from typing import Optional

from deva_p1_db.models import Task
from pydantic import BaseModel


class TaskSchema(BaseModel):
    id: str
    task_type: str
    done: bool
    status: Optional[float]


class TaskCreateSchema(BaseModel):
    project_id: str
    task_type: str
    prompt: str = ""


class RedisTaskCacheSchema(BaseModel):
    id: str
    project_id: str
    task_type: str

    @classmethod
    def from_db(cls, task: Task) -> "RedisTaskCacheSchema":
        return cls(id=str(task.id), task_type=task.task_type, project_id=str(task.project_id))


class ActiveTaskSchema(BaseModel):
    id: str
    type: str

    @classmethod
    def from_db(cls, task: Task) -> "ActiveTaskSchema":
        return cls(id=str(task.id), type=task.task_type)
