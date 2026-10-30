"""Request and response of the brigade suggestion endpoint."""

from uuid import UUID

from pydantic import Field, field_validator

from app.schemas.common import CamelModel


class GeoLocation(CamelModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class CandidateBrigade(CamelModel):
    brigade_id: UUID
    location: GeoLocation
    """Base location of the brigade."""


class SuggestBrigadeRequest(CamelModel):
    zone_location: GeoLocation
    brigades: list[CandidateBrigade] = Field(min_length=1)
    """Available brigades of the organization."""

    @field_validator("brigades")
    @classmethod
    def brigades_are_unique(cls, brigades: list[CandidateBrigade]) -> list[CandidateBrigade]:
        if len({brigade.brigade_id for brigade in brigades}) != len(brigades):
            raise ValueError("each brigade appears only once")
        return brigades


class BrigadeSuggestionResponse(CamelModel):
    brigade_id: UUID
    distance_km: float
    """Distance from the base of the brigade to the zone, with one decimal."""
    model_version: str
