"""Base model and error format shared by every endpoint."""

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """Base of every request and response: camelCase in JSON, snake_case in Python."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        validate_by_alias=True,
        validate_by_name=True,
        serialize_by_alias=True,
    )


class ErrorDetail(CamelModel):
    """One problem found in the request, such as an invalid field."""

    field: str
    message: str


class ErrorResponse(CamelModel):
    """Single error format of the service."""

    code: str
    message: str
    details: list[ErrorDetail] = Field(default_factory=list)
