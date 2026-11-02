"""Brigade suggestion for the zone of an approved distribution plan."""

from fastapi import APIRouter

from app.core.config import MODEL_VERSION
from app.schemas.brigades import BrigadeSuggestionResponse, SuggestBrigadeRequest
from app.services.staffing import suggest_brigade

router = APIRouter(prefix="/brigade-assignments", tags=["brigade assignments"])


@router.post(
    "/suggestions",
    summary="Suggest the available brigade closest to a zone",
    description="Uses the haversine distance. Responds 400 without brigades.",
)
def suggest(request: SuggestBrigadeRequest) -> BrigadeSuggestionResponse:
    suggestion = suggest_brigade(request.zone_location, request.brigades)
    return BrigadeSuggestionResponse(
        brigade_id=suggestion.brigade_id,
        distance_km=suggestion.distance_km,
        model_version=MODEL_VERSION,
    )
