
from .base import BaseCustomHTTPException


class AccessTokenDoesNotExistException(BaseCustomHTTPException):
    def __init__(self):
        super().__init__(401, "Access token doesn't exist")


class AccessTokenExpiredException(BaseCustomHTTPException):
    def __init__(self):
        super().__init__(401, "Access token has expired")


class AccessTokenInvalidatedException(BaseCustomHTTPException):
    def __init__(self):
        super().__init__(401, "Access token has been invalidated")


class AccessTokenDamagedException(BaseCustomHTTPException):
    def __init__(self):
        super().__init__(401, "Access token is corrupted")


class RefreshTokenDoesNotExistException(BaseCustomHTTPException):
    def __init__(self):
        super().__init__(401, "Refresh token doesn't exist")


class RefreshTokenExpiredException(BaseCustomHTTPException):
    def __init__(self):
        super().__init__(401, "Refresh token has expired")


class InvalidRefreshTokenException(BaseCustomHTTPException):
    def __init__(self):
        super().__init__(401, "Refresh token is invalid")


class UnauthorizedException(BaseCustomHTTPException):
    def __init__(self):
        super().__init__(401, "Unauthorized access")


class InvalidCredentialsException(BaseCustomHTTPException):
    def __init__(self):
        super().__init__(401, "Invalid username or password")


class LoginLockedException(BaseCustomHTTPException):
    def __init__(self, seconds: int):
        super().__init__(
            401, f"Too many attempts. Try again in {seconds} seconds")


class TooManyIncorrectCredentialsException(BaseCustomHTTPException):
    def __init__(self, ip: str):
        super().__init__(401, f"Too many failed login attempts from IP: {ip}")



