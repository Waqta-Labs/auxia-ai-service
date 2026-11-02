"""Brigade suggestion for a zone (rules-v1).

The suggested brigade is the one whose base is closest to the zone, measured
as the great-circle (haversine) distance on a sphere of 6371 km. Between two
brigades at the same distance, the first one of the request wins, so the same
request always gets the same answer.
"""

import math
from dataclasses import dataclass
from uuid import UUID

from app.schemas.brigades import CandidateBrigade, GeoLocation

EARTH_RADIUS_KM = 6371.0


@dataclass(frozen=True)
class BrigadeSuggestion:
    brigade_id: UUID
    distance_km: float


def haversine_km(origin: GeoLocation, destination: GeoLocation) -> float:
    lat1, lat2 = math.radians(origin.latitude), math.radians(destination.latitude)
    delta_lat = lat2 - lat1
    delta_lon = math.radians(destination.longitude - origin.longitude)
    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def suggest_brigade(zone: GeoLocation, brigades: list[CandidateBrigade]) -> BrigadeSuggestion:
    """The brigade closest to the zone; brigades must not be empty."""
    closest = min(brigades, key=lambda brigade: haversine_km(brigade.location, zone))
    return BrigadeSuggestion(
        brigade_id=closest.brigade_id,
        distance_km=round(haversine_km(closest.location, zone), 1),
    )
