
import inspect
import traceback

from .base import BaseCustomHTTPException


class InternalServerException(BaseCustomHTTPException):
    def __init__(self):
        super().__init__(500, "Internal server error")


class TooLongPollingException(BaseCustomHTTPException):
    def __init__(self):
        super().__init__(500, "Polling duration exceeded limit")


class AIException(BaseCustomHTTPException):
    def __init__(self, message: str):
        super().__init__(500, f"Redis error: {message}")


class MinioException(BaseCustomHTTPException):
    def __init__(self, message: str | None):
        if message is None:
            message = "Unknown error"
        super().__init__(500, f"MinIO error: {message}")


class SendFeedbackToAdminException(BaseCustomHTTPException):
    def __init__(self):
        current_frame = inspect.currentframe()
        message = ""
        if current_frame:
            outer_frame = current_frame.f_back
            if outer_frame:
                filename = outer_frame.f_code.co_filename
                lineno = outer_frame.f_lineno
                function = outer_frame.f_code.co_name
                message += f"File: {filename}\nLine: {lineno}\nFunction: {function}\n"
        stack_trace = "".join(traceback.format_stack())
        message += f"Stack Trace:\n{stack_trace}"

        super().__init__(500, "".join([
            "Interesting error occurred.",
            "Please contact the administrator for assistance.",
            "\n\nAdditional information:\n",
            message]))
