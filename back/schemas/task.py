
from typing import Optional

from deva_p1_db.models import Task
from pydantic import BaseModel


class TaskSchema(BaseModel):
    id: str
    done: bool
    status: Optional[str] = None

class ActiveTaskSchema(BaseModel):
    id: str
    type: str
    @classmethod
    def from_db(cls, task: Task) -> "ActiveTaskSchema":
        return cls(id=str(task.id), type=task.task_type)
