
from .base import BaseCustomHTTPException


class PasswordsDoNotMatchException(BaseCustomHTTPException):
    def __init__(self):
        super().__init__(400, "Passwords do not match")


class UserAlreadyExistsException(BaseCustomHTTPException):
    def __init__(self):
        super().__init__(400, "A user with this login already exists")


class UndefinedRegistrationException(BaseCustomHTTPException):
    def __init__(self):
        super().__init__(400, "An unknown error occurred during registration")


class UndefinedFileTypeException(BaseCustomHTTPException):
    def __init__(self):
        super().__init__(400, f"File type is undefined")


class InvalidFileTypeException(BaseCustomHTTPException):
    def __init__(self):
        super().__init__(400, "File type is not supported")


class ProjectAlreadyHasOriginFileException(BaseCustomHTTPException):
    def __init__(self):
        super().__init__(400, "Project already contains an origin file")


class ProjectAlreadyExistsException(BaseCustomHTTPException):
    def __init__(self):
        super().__init__(400, "A project with this name already exists")


class ProjectHasNoOriginFileException(BaseCustomHTTPException):
    def __init__(self):
        super().__init__(400, "Project does not contain an origin file")


class ProjectAlreadyHasActiveTasksException(BaseCustomHTTPException):
    def __init__(self):
        super().__init__(400, "Project already has active tasks")


class OnlyFramesAfterTranscribeAllowedException(BaseCustomHTTPException):
    def __init__(self):
        super().__init__(
            400, "You can only create a frames extraction task after a transcription task")


class OnlyTranscribeAfterFramesAllowedException(BaseCustomHTTPException):
    def __init__(self):
        super().__init__(
            400, "You can only create a transcription task after a frames extraction task")


class ProjectAlreadyHasTranscriptionException(BaseCustomHTTPException):
    def __init__(self):
        super().__init__(400, "Project already contains a transcription")


class ProjectAlreadyHasFramesExtractException(BaseCustomHTTPException):
    def __init__(self):
        super().__init__(400, "Project already contains frames extract data")


class OriginFileIsAudioException(BaseCustomHTTPException):
    def __init__(self):
        super().__init__(400, "The origin file is audio, frame extraction is not possible")


class InvalidTaskTypeException(BaseCustomHTTPException):
    def __init__(self):
        super().__init__(400, "Task type is invalid")
