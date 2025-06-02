

from typing import Any
from pydantic import BaseModel


class WebsocketMessage(BaseModel):
    message_type: str
    data: Any