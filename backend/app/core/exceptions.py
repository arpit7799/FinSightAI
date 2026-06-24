from fastapi import HTTPException


class FinSightException(Exception):
    def __init__(self, detail: str):
        self.detail = detail


class UnauthorizedAccess(FinSightException):
    pass


class FilingNotFound(FinSightException):
    pass


class ProcessingError(FinSightException):
    pass


class UserAlreadyExists(FinSightException):
    pass