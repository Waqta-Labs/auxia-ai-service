"""Distribution recommendation among prioritized zones (US-11, TS-04)."""

from fastapi import APIRouter

from app.core.config import MODEL_VERSION
from app.schemas.distributions import (
    AllocatedItem,
    DistributionRecommendationResponse,
    RecommendDistributionRequest,
    ZoneAllocation,
)
from app.services.distribution import justify, recommend_distribution

router = APIRouter(prefix="/distribution-recommendations", tags=["distribution recommendations"])


@router.post(
    "",
    summary="Recommend how to split the inventory among prioritized zones",
    description="The quantities never exceed the available inventory. Responds 400 without zones.",
)
def recommend(request: RecommendDistributionRequest) -> DistributionRecommendationResponse:
    distributions = recommend_distribution(request.zones, request.inventory)
    return DistributionRecommendationResponse(
        allocations=[
            ZoneAllocation(
                zone_id=distribution.zone_id,
                items=[
                    AllocatedItem(resource_id=resource_id, quantity=quantity)
                    for resource_id, quantity in distribution.quantities.items()
                ],
                coverage=distribution.coverage,
            )
            for distribution in distributions
        ],
        justification=justify(distributions),
        model_version=MODEL_VERSION,
    )
