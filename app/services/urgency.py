"""Urgency score of a zone (rules-v1).

The score is a weighted sum of four variables, each normalized from 0 to 1.
The weights add up to 100, so each contribution is already in score points:

| Variable | Weight | Normalized value |
|---|---|---|
| damageLevel | 40 | LOW 0.25, MODERATE 0.5, SEVERE 0.75, CRITICAL 1 |
| peopleAffected | 25 | peopleAffected / zonePopulation, at most 1 |
| vulnerablePopulation | 20 | vulnerable people / peopleAffected, at most 1 |
| needs | 15 | distinct needs / 4, at most 1 |

Vulnerable people are children + elderlyPeople + disabledPeople; a group that
was not identified counts as 0. The priority level comes from the rounded
score: 75 or more is CRITICAL, 50 HIGH, 25 MEDIUM and anything lower LOW.
topFeatures are the three largest contributions that are not zero.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.schemas.indicators import DamageLevel, FieldIndicators
from app.schemas.urgency_scores import FeatureContribution, PriorityLevel, ScoreFeature

_WEIGHTS: dict[ScoreFeature, float] = {
    ScoreFeature.DAMAGE_LEVEL: 40.0,
    ScoreFeature.PEOPLE_AFFECTED: 25.0,
    ScoreFeature.VULNERABLE_POPULATION: 20.0,
    ScoreFeature.NEEDS: 15.0,
}

_DAMAGE_FACTORS: dict[DamageLevel, float] = {
    DamageLevel.LOW: 0.25,
    DamageLevel.MODERATE: 0.5,
    DamageLevel.SEVERE: 0.75,
    DamageLevel.CRITICAL: 1.0,
}

# Number of distinct needs that gives the highest value of the needs variable.
_NEEDS_FOR_FULL_WEIGHT = 4

# From the highest level to the lowest: the first threshold reached wins.
_PRIORITY_THRESHOLDS: list[tuple[float, PriorityLevel]] = [
    (75.0, PriorityLevel.CRITICAL),
    (50.0, PriorityLevel.HIGH),
    (25.0, PriorityLevel.MEDIUM),
]

_TOP_FEATURES = 3

# Indicators without which the score is not available (US-04, scenario 2).
_REQUIRED_INDICATORS = ("damage_level", "people_affected")


class InsufficientVariablesError(Exception):
    """The indicators do not include every variable that the score requires."""

    def __init__(self, missing_variables: list[str]) -> None:
        super().__init__(f"Missing variables: {', '.join(missing_variables)}")
        self.missing_variables = missing_variables
        """camelCase names of the missing indicators."""


@dataclass(frozen=True)
class UrgencyScore:
    score: float
    priority_level: PriorityLevel
    top_features: list[FeatureContribution]


def calculate_urgency_score(indicators: FieldIndicators, zone_population: int) -> UrgencyScore:
    """Calculates the score of a zone, or raises InsufficientVariablesError."""
    missing = [
        FieldIndicators.model_fields[name].alias or name
        for name in _REQUIRED_INDICATORS
        if getattr(indicators, name) is None
    ]
    if missing:
        raise InsufficientVariablesError(missing)

    contributions = {
        feature: _WEIGHTS[feature] * value
        for feature, value in _normalized_variables(indicators, zone_population).items()
    }
    score = _round(sum(contributions.values()))
    return UrgencyScore(
        score=score,
        priority_level=_priority_level(score),
        top_features=_top_features(contributions),
    )


def _normalized_variables(
    indicators: FieldIndicators, zone_population: int
) -> dict[ScoreFeature, float]:
    people = indicators.people_affected
    vulnerable = sum(
        count or 0
        for count in (indicators.children, indicators.elderly_people, indicators.disabled_people)
    )
    return {
        ScoreFeature.DAMAGE_LEVEL: _DAMAGE_FACTORS[indicators.damage_level],
        ScoreFeature.PEOPLE_AFFECTED: min(1.0, people / zone_population),
        ScoreFeature.VULNERABLE_POPULATION: min(1.0, vulnerable / people) if people else 0.0,
        ScoreFeature.NEEDS: min(1.0, len(set(indicators.needs)) / _NEEDS_FOR_FULL_WEIGHT),
    }


def _priority_level(score: float) -> PriorityLevel:
    for threshold, level in _PRIORITY_THRESHOLDS:
        if score >= threshold:
            return level
    return PriorityLevel.LOW


def _top_features(contributions: dict[ScoreFeature, float]) -> list[FeatureContribution]:
    # sorted is stable: equal contributions keep the order of ScoreFeature.
    largest = sorted(contributions.items(), key=lambda item: item[1], reverse=True)
    top = [
        FeatureContribution(feature=feature, contribution=_round(contribution))
        for feature, contribution in largest
    ]
    return [feature for feature in top if feature.contribution > 0][:_TOP_FEATURES]


def _round(value: float) -> float:
    """Rounds to one decimal, with halves away from zero (11.25 gives 11.3)."""
    return float(Decimal(str(value)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))
