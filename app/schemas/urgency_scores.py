"""Request and response of the urgency score endpoint."""

from enum import StrEnum

from pydantic import Field

from app.schemas.common import CamelModel
from app.schemas.indicators import FieldIndicators


class PriorityLevel(StrEnum):
    """Same values as PriorityLevel in auxia-backend."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ScoreFeature(StrEnum):
    """Variables that add points to the score, named as in the JSON of the indicators."""

    DAMAGE_LEVEL = "damageLevel"
    PEOPLE_AFFECTED = "peopleAffected"
    VULNERABLE_POPULATION = "vulnerablePopulation"
    """children + elderlyPeople + disabledPeople."""
    NEEDS = "needs"


class CalculateUrgencyScoreRequest(CamelModel):
    indicators: FieldIndicators
    """The same indicators returned by the structuring endpoint."""
    zone_population: int = Field(gt=0)
    """Total number of people living in the zone."""


class FeatureContribution(CamelModel):
    feature: ScoreFeature
    contribution: float = Field(ge=0, le=100)
    """Score points that the variable added, with one decimal."""


class UrgencyScoreResponse(CamelModel):
    score: float = Field(ge=0, le=100)
    """From 0 to 100, with one decimal."""
    priority_level: PriorityLevel
    top_features: list[FeatureContribution]
    """The variables that weighed the most, from highest to lowest."""
    model_version: str
