
from uuid import UUID
from .base import BaseCustomHTTPException


class ProjectNotFoundException(BaseCustomHTTPException):
    def __init__(self, project_id: UUID):
        super().__init__(404, f"Project not found, project_id: {project_id}")


class FileNotFoundException(BaseCustomHTTPException):
    def __init__(self, file_id: UUID):
        super().__init__(
            404, f"File '{file_id}' not found")


class NoteNotFoundException(BaseCustomHTTPException):
    def __init__(self, note_id: UUID):
        super().__init__(404, f"Note not found, note_id: {note_id}")


class TaskNotFoundException(BaseCustomHTTPException):
    def __init__(self, task_id: UUID):
        super().__init__(404, f"Task not found, task_id: {task_id}")



