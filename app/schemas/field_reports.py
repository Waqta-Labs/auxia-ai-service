"""Request and response of the field report structuring endpoint."""

from typing import Annotated

from pydantic import StringConstraints

from app.schemas.common import CamelModel
from app.schemas.indicators import FieldIndicators

MAX_REPORT_LENGTH = 5000


class StructureFieldReportRequest(CamelModel):
    text: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_REPORT_LENGTH)
    ]
    """Free text of the field report, written in Spanish."""


class StructureFieldReportResponse(CamelModel):
    indicators: FieldIndicators
    missing_variables: list[str]
    """camelCase names of the indicators that could not be identified."""
    model_version: str
