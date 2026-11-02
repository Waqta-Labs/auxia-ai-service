"""Variables of a zone extracted from a field report, shared by structuring and scoring."""

from enum import StrEnum

from pydantic import Field

from app.schemas.common import CamelModel


class DamageLevel(StrEnum):
    """Same values as DamageLevel in auxia-backend."""

    LOW = "LOW"
    MODERATE = "MODERATE"
    SEVERE = "SEVERE"
    CRITICAL = "CRITICAL"


class Need(StrEnum):
    """Same values as the resource categories in auxia-backend."""

    WATER = "WATER"
    FOOD = "FOOD"
    SHELTER = "SHELTER"
    HYGIENE = "HYGIENE"
    MEDICINE = "MEDICINE"
    OTHER = "OTHER"


class FieldIndicators(CamelModel):
    """Output of the structuring endpoint and input of the urgency score.

    A variable that could not be identified is None, or an empty list for needs.
    """

    damage_level: DamageLevel | None = None
    families_affected: int | None = Field(default=None, ge=0)
    people_affected: int | None = Field(default=None, ge=0)
    children: int | None = Field(default=None, ge=0)
    elderly_people: int | None = Field(default=None, ge=0)
    disabled_people: int | None = Field(default=None, ge=0)
    needs: list[Need] = Field(default_factory=list)
