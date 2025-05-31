
from .base import BaseCustomHTTPException


class PermissionDeniedException(BaseCustomHTTPException):
    def __init__(self):
        super().__init__(403, "You do not have permission to perform this action")
