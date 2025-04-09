


from sqlalchemy import ForeignKey
from database.models.base import Base
from sqlalchemy.orm import Mapped, mapped_column
from uuid import UUID, uuid4


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id"))
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))