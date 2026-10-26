"""API key validation for the endpoints that auxia-backend calls."""

import secrets
from http import HTTPStatus
from typing import Annotated

from fastapi import Depends, Security
from fastapi.security import APIKeyHeader

from app.core.config import Settings, get_settings
from app.core.errors import ApiError

API_KEY_HEADER = "X-API-Key"

_api_key_header = APIKeyHeader(name=API_KEY_HEADER, auto_error=False)


def require_api_key(
    api_key: Annotated[str | None, Security(_api_key_header)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    """Rejects the request with 401 unless it carries the shared API key."""
    if api_key is None or not secrets.compare_digest(api_key.encode(), settings.api_key.encode()):
        raise ApiError(HTTPStatus.UNAUTHORIZED, "INVALID_API_KEY", "Missing or invalid API key.")
