"""Request and response of the distribution recommendation endpoint."""

from enum import StrEnum
from uuid import UUID

from pydantic import Field, field_validator

from app.schemas.common import CamelModel
from app.schemas.indicators import Need


class UnitOfMeasure(StrEnum):
    """Same values as UnitOfMeasure in auxia-backend."""

    UNIT = "UNIT"
    KG = "KG"
    LITER = "LITER"
    KIT = "KIT"


class Coverage(StrEnum):
    """How much of the demand of a zone the recommendation covers."""

    FULL = "FULL"
    PARTIAL = "PARTIAL"
    NONE = "NONE"


class AllocatedCategory(CamelModel):
    category: Need
    quantity: int = Field(ge=0)
    """Units of the category the zone already has from approved plans."""


class PrioritizedZone(CamelModel):
    zone_id: UUID
    score: float = Field(ge=0, le=100)
    """Urgency score of the zone."""
    people_affected: int = Field(ge=0)
    needs: list[Need] = Field(default_factory=list)
    already_allocated: list[AllocatedCategory] = Field(default_factory=list)
    """What earlier approved plans already give the zone; it is taken from its demand."""

    @field_validator("already_allocated")
    @classmethod
    def categories_are_unique(cls, allocated: list[AllocatedCategory]) -> list[AllocatedCategory]:
        if len({item.category for item in allocated}) != len(allocated):
            raise ValueError("each category appears only once")
        return allocated


class AvailableResource(CamelModel):
    resource_id: UUID
    category: Need
    """Resource category; the same values as the needs of a zone."""
    unit: UnitOfMeasure
    available_quantity: int = Field(ge=0)


class RecommendDistributionRequest(CamelModel):
    zones: list[PrioritizedZone] = Field(min_length=1)
    inventory: list[AvailableResource] = Field(default_factory=list)

    @field_validator("zones")
    @classmethod
    def zones_are_unique(cls, zones: list[PrioritizedZone]) -> list[PrioritizedZone]:
        if len({zone.zone_id for zone in zones}) != len(zones):
            raise ValueError("each zone appears only once")
        return zones

    @field_validator("inventory")
    @classmethod
    def resources_are_unique(cls, inventory: list[AvailableResource]) -> list[AvailableResource]:
        if len({resource.resource_id for resource in inventory}) != len(inventory):
            raise ValueError("each resource appears only once")
        return inventory


class AllocatedItem(CamelModel):
    resource_id: UUID
    quantity: int = Field(gt=0)


class ZoneAllocation(CamelModel):
    zone_id: UUID
    items: list[AllocatedItem]
    """Resources for the zone; empty when it receives nothing."""
    coverage: Coverage


class DistributionRecommendationResponse(CamelModel):
    allocations: list[ZoneAllocation]
    """One per zone, in the order of the request."""
    justification: str
    model_version: str
