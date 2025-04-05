

from datetime import datetime
from sqlalchemy import ForeignKey
from database.models.user import User
from .base import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid import UUID, uuid4


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str]
    description: Mapped[str]
    holder_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    created_date: Mapped[datetime]
    last_modified_date: Mapped[datetime]


    holder: Mapped[User] = relationship(lazy="selectin", foreign_keys=[holder_id]) 
