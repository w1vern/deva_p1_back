

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey
from database.models.base import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models.file_type import FileType
from database.models.project import Project


class File(Base):
    __tablename__ = "files"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_file_name: Mapped[str]
    created_date: Mapped[datetime]
    last_modified_date: Mapped[datetime]
    file_type_id: Mapped[FileType] = mapped_column(ForeignKey("file_types.id"))
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id"))

    project: Mapped[Project] = relationship(lazy="selectin", foreign_keys=[project_id])
    file_type: Mapped[FileType] = relationship(lazy="selectin", foreign_keys=[file_type_id])