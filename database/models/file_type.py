




from uuid import UUID, uuid4
from database.models.base import Base
from sqlalchemy.orm import Mapped, mapped_column


class FileType(Base):
    __tablename__ = "file_types"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(unique=True)