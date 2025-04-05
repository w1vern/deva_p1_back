

from .base import Base
from sqlalchemy.orm import Mapped, mapped_column
from uuid import UUID, uuid4


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    login: Mapped[str]
    hashed_password: Mapped[str]
    secret: Mapped[str]