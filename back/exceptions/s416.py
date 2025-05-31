
from .base import BaseCustomHTTPException


class RangeHeaderRequiredException(BaseCustomHTTPException):
    def __init__(self):
        super().__init__(416, "Range header is required")


class InvalidRangeHeaderException(BaseCustomHTTPException):
    def __init__(self):
        super().__init__(416, "Range header is invalid or unsatisfiable")
