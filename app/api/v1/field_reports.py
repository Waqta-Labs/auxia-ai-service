"""Structuring of field reports (US-02)."""

from fastapi import APIRouter

from app.core.config import MODEL_VERSION
from app.schemas.field_reports import StructureFieldReportRequest, StructureFieldReportResponse
from app.services.nlp import structure_field_report

router = APIRouter(prefix="/field-reports", tags=["field reports"])


@router.post("/structure", summary="Extract the indicators of a field report")
def structure(request: StructureFieldReportRequest) -> StructureFieldReportResponse:
    report = structure_field_report(request.text)
    return StructureFieldReportResponse(
        indicators=report.indicators,
        missing_variables=report.missing_variables,
        model_version=MODEL_VERSION,
    )
