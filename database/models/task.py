


from sqlalchemy import ForeignKey
from database.models.base import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid import UUID, uuid4

from database.models.file import File
from database.models.project import Project
from database.models.user import User


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    task_type: Mapped[str] = mapped_column()
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id"))
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    origin_file_id: Mapped[UUID] = mapped_column(ForeignKey("files.id"))

    origin_file: Mapped[File] = relationship(lazy="selectin", foreign_keys=[origin_file_id])
    project: Mapped[Project] = relationship(lazy="selectin", foreign_keys=[project_id])
    user: Mapped[User] = relationship(lazy="selectin", foreign_keys=[user_id])

    