
from typing import Optional
from pydantic import BaseModel

class TaskSchema(BaseModel):
    id: str
    done: bool
    status: Optional[str] = None
