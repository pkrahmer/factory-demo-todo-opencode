"""The one place where errors become status codes and the `{"detail": ...}` body."""

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.domain.errors import InvalidTitle, TodoError, TodoNotFound

_STATUS_BY_ERROR: dict[type[TodoError], int] = {
    TodoNotFound: status.HTTP_404_NOT_FOUND,
    InvalidTitle: status.HTTP_422_UNPROCESSABLE_CONTENT,
}


def _error_response(status_code: int, detail: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"detail": detail})


async def _domain_error(_request: Request, error: TodoError) -> JSONResponse:
    return _error_response(_STATUS_BY_ERROR[type(error)], str(error))


async def _validation_error(_request: Request, error: RequestValidationError) -> JSONResponse:
    # One sentence instead of FastAPI's list: the first error, its location joined with dots.
    first = error.errors()[0]
    location = ".".join(str(part) for part in first["loc"])
    return _error_response(status.HTTP_422_UNPROCESSABLE_CONTENT, f"{location}: {first['msg']}")


def register_error_handlers(app: FastAPI) -> None:
    for error_type in _STATUS_BY_ERROR:
        app.exception_handler(error_type)(_domain_error)
    app.exception_handler(RequestValidationError)(_validation_error)
