

from pydantic import BaseModel


class WebsocketMessage(BaseModel):
    message_type: str
    data: str