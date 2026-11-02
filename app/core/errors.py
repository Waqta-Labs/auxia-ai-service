"""Error handling: every error is answered with the ErrorResponse format."""

import logging
from collections.abc import Iterable, Mapping
from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.schemas.common import ErrorDetail, ErrorResponse

logger = logging.getLogger(__name__)

# First element of a validation error location; it is not part of the field path.
_REQUEST_PARTS = {"body", "query", "path", "header", "cookie"}


class ApiError(Exception):
    """Error raised by the service with its HTTP status and error code."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: Iterable[ErrorDetail] = (),
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = list(details)


def register_error_handlers(app: FastAPI) -> None:
    """Registers the handlers that turn every error into an ErrorResponse."""
    app.add_exception_handler(ApiError, _handle_api_error)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.add_exception_handler(StarletteHTTPException, _handle_http_exception)
    app.add_exception_handler(Exception, _handle_unexpected_error)


def field_path(location: Iterable[str | int]) -> str:
    """Turns a location such as ("body", "zones", 0, "score") into "zones[0].score"."""
    parts = list(location)
    if len(parts) > 1 and parts[0] in _REQUEST_PARTS:
        parts = parts[1:]
    path = ""
    for part in parts:
        if isinstance(part, int):
            path += f"[{part}]"
        else:
            path += f".{part}" if path else str(part)
    return path


async def _handle_api_error(_: Request, exc: ApiError) -> JSONResponse:
    return _error_response(exc.status_code, exc.code, exc.message, exc.details)


async def _handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    details = [
        ErrorDetail(field=field_path(error["loc"]), message=error["msg"]) for error in exc.errors()
    ]
    return _error_response(
        HTTPStatus.BAD_REQUEST, "VALIDATION_ERROR", "The request is not valid.", details
    )


async def _handle_http_exception(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    status = HTTPStatus(exc.status_code)
    message = exc.detail if isinstance(exc.detail, str) else status.phrase
    return _error_response(status, status.name, message, headers=exc.headers)


async def _handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "Unexpected error while processing %s %s",
        request.method,
        request.url.path,
        exc_info=exc,
    )
    return _error_response(
        HTTPStatus.INTERNAL_SERVER_ERROR, "INTERNAL_ERROR", "An unexpected error occurred."
    )


def _error_response(
    status_code: int,
    code: str,
    message: str,
    details: Iterable[ErrorDetail] = (),
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    body = ErrorResponse(code=code, message=message, details=list(details))
    return JSONResponse(
        status_code=status_code, content=body.model_dump(mode="json"), headers=headers
    )
