"""OpenAPI document of the service, shown in /docs."""

from typing import Any

from fastapi import FastAPI

# FastAPI documents a 422 response with these schemas for every endpoint with a body,
# but validation errors answer 400 with ErrorResponse (see app/core/errors.py).
_VALIDATION_STATUS = "422"
_VALIDATION_SCHEMAS = ("HTTPValidationError", "ValidationError")


def remove_default_validation_response(app: FastAPI) -> None:
    """Makes the OpenAPI document leave out the 422 response that the service never sends."""

    def openapi() -> dict[str, Any]:
        if app.openapi_schema is None:
            schema = FastAPI.openapi(app)
            for path in schema["paths"].values():
                for operation in path.values():
                    operation.get("responses", {}).pop(_VALIDATION_STATUS, None)
            schemas = schema.get("components", {}).get("schemas", {})
            for name in _VALIDATION_SCHEMAS:
                schemas.pop(name, None)
        return app.openapi_schema

    app.openapi = openapi
