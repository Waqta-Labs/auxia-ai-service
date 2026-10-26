"""Response of the health check."""

from app.schemas.common import CamelModel


class HealthResponse(CamelModel):
    status: str
    version: str
    model_version: str
