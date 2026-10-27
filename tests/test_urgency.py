import pytest

from app.schemas.indicators import DamageLevel, FieldIndicators, Need
from app.schemas.urgency_scores import PriorityLevel, ScoreFeature
from app.services.urgency import InsufficientVariablesError, calculate_urgency_score

README_INDICATORS = FieldIndicators(
    damage_level=DamageLevel.SEVERE,
    families_affected=35,
    people_affected=140,
    children=40,
    elderly_people=15,
    needs=[Need.WATER, Need.FOOD, Need.SHELTER],
)
VULNERABLE = ScoreFeature.VULNERABLE_POPULATION


def contributions(indicators: FieldIndicators, zone_population: int) -> dict[ScoreFeature, float]:
    urgency = calculate_urgency_score(indicators, zone_population)
    return {feature.feature: feature.contribution for feature in urgency.top_features}


def test_readme_example_adds_the_weighted_contributions() -> None:
    urgency = calculate_urgency_score(README_INDICATORS, zone_population=600)

    # 30 (SEVERE) + 5.83 (140 / 600) + 7.86 (55 / 140) + 11.25 (3 of 4 needs) = 54.94
    assert urgency.score == 54.9
    assert urgency.priority_level == PriorityLevel.HIGH
    assert [(f.feature, f.contribution) for f in urgency.top_features] == [
        (ScoreFeature.DAMAGE_LEVEL, 30.0),
        (ScoreFeature.NEEDS, 11.3),
        (ScoreFeature.VULNERABLE_POPULATION, 7.9),
    ]


def test_every_variable_at_its_highest_value_gives_100() -> None:
    indicators = FieldIndicators(
        damage_level=DamageLevel.CRITICAL,
        people_affected=200,
        children=120,
        elderly_people=60,
        disabled_people=20,
        needs=[Need.WATER, Need.FOOD, Need.SHELTER, Need.MEDICINE],
    )

    urgency = calculate_urgency_score(indicators, zone_population=200)

    assert urgency.score == 100.0
    assert urgency.priority_level == PriorityLevel.CRITICAL


@pytest.mark.parametrize(
    ("damage_level", "contribution"),
    [
        (DamageLevel.LOW, 10.0),
        (DamageLevel.MODERATE, 20.0),
        (DamageLevel.SEVERE, 30.0),
        (DamageLevel.CRITICAL, 40.0),
    ],
)
def test_damage_level_adds_its_share_of_40_points(
    damage_level: DamageLevel, contribution: float
) -> None:
    indicators = FieldIndicators(damage_level=damage_level, people_affected=0)

    assert contributions(indicators, zone_population=100) == {
        ScoreFeature.DAMAGE_LEVEL: contribution
    }


def test_people_affected_beyond_the_zone_population_count_as_the_whole_zone() -> None:
    indicators = FieldIndicators(damage_level=DamageLevel.LOW, people_affected=500)

    assert contributions(indicators, zone_population=100)[ScoreFeature.PEOPLE_AFFECTED] == 25.0


def test_vulnerable_groups_not_identified_count_as_zero() -> None:
    indicators = FieldIndicators(damage_level=DamageLevel.LOW, people_affected=100, children=10)

    # 10 / 100 * 20
    vulnerable = contributions(indicators, zone_population=1000)[VULNERABLE]
    assert vulnerable == 2.0


def test_vulnerable_people_beyond_the_people_affected_count_as_all_of_them() -> None:
    indicators = FieldIndicators(
        damage_level=DamageLevel.LOW, people_affected=10, children=8, elderly_people=8
    )

    vulnerable = contributions(indicators, zone_population=1000)[VULNERABLE]
    assert vulnerable == 20.0


def test_zero_people_affected_adds_no_vulnerable_population() -> None:
    indicators = FieldIndicators(damage_level=DamageLevel.LOW, people_affected=0, children=5)

    assert VULNERABLE not in contributions(indicators, zone_population=100)


def test_needs_count_once_and_stop_adding_after_four() -> None:
    repeated = FieldIndicators(
        damage_level=DamageLevel.LOW, people_affected=0, needs=[Need.WATER, Need.WATER]
    )
    all_needs = FieldIndicators(damage_level=DamageLevel.LOW, people_affected=0, needs=list(Need))

    # 1 of 4 needs, then the six categories capped at 4 of 4.
    assert contributions(repeated, zone_population=100)[ScoreFeature.NEEDS] == 3.8
    assert contributions(all_needs, zone_population=100)[ScoreFeature.NEEDS] == 15.0


@pytest.mark.parametrize(
    ("people_affected", "score", "priority_level"),
    [
        # Each case adds 10 points of LOW damage to people_affected / 100 * 25.
        (0, 10.0, PriorityLevel.LOW),
        (59, 24.8, PriorityLevel.LOW),
        (60, 25.0, PriorityLevel.MEDIUM),
        (100, 35.0, PriorityLevel.MEDIUM),
    ],
)
def test_priority_level_comes_from_the_score_thresholds(
    people_affected: int, score: float, priority_level: PriorityLevel
) -> None:
    indicators = FieldIndicators(damage_level=DamageLevel.LOW, people_affected=people_affected)

    urgency = calculate_urgency_score(indicators, zone_population=100)

    assert urgency.score == score
    assert urgency.priority_level == priority_level


@pytest.mark.parametrize(
    ("indicators", "score", "priority_level"),
    [
        # 10 (LOW) + 24.75 (99 of 100) + 15 (every need) = 49.75
        (
            FieldIndicators(damage_level=DamageLevel.LOW, people_affected=99, needs=list(Need)),
            49.8,
            PriorityLevel.MEDIUM,
        ),
        # 10 (LOW) + 25 (the whole zone) + 15 (every need)
        (
            FieldIndicators(damage_level=DamageLevel.LOW, people_affected=100, needs=list(Need)),
            50.0,
            PriorityLevel.HIGH,
        ),
        # 30 (SEVERE) + 25 (the whole zone) + 20 (every person is vulnerable)
        (
            FieldIndicators(damage_level=DamageLevel.SEVERE, people_affected=100, children=100),
            75.0,
            PriorityLevel.CRITICAL,
        ),
    ],
)
def test_high_and_critical_levels_start_at_50_and_75(
    indicators: FieldIndicators, score: float, priority_level: PriorityLevel
) -> None:
    urgency = calculate_urgency_score(indicators, zone_population=100)

    assert urgency.score == score
    assert urgency.priority_level == priority_level


def test_the_rounded_score_decides_the_priority_level() -> None:
    indicators = FieldIndicators(
        damage_level=DamageLevel.SEVERE, people_affected=3984, children=3984, needs=list(Need)
    )

    # 30 + 9.96 (3984 of 10000) + 20 + 15 = 74.96, shown as 75.0
    urgency = calculate_urgency_score(indicators, zone_population=10000)

    assert urgency.score == 75.0
    assert urgency.priority_level == PriorityLevel.CRITICAL


def test_top_features_keep_the_three_largest_and_skip_zero_contributions() -> None:
    complete = FieldIndicators(
        damage_level=DamageLevel.LOW,
        people_affected=100,
        children=100,
        needs=[Need.WATER],
    )
    only_damage = FieldIndicators(damage_level=DamageLevel.CRITICAL, people_affected=0)

    # 10 (damage), 25 (people), 20 (vulnerable), 3.75 (needs): the needs are left out.
    assert list(contributions(complete, zone_population=100)) == [
        ScoreFeature.PEOPLE_AFFECTED,
        ScoreFeature.VULNERABLE_POPULATION,
        ScoreFeature.DAMAGE_LEVEL,
    ]
    assert list(contributions(only_damage, zone_population=100)) == [ScoreFeature.DAMAGE_LEVEL]


@pytest.mark.parametrize(
    ("indicators", "missing_variables"),
    [
        (FieldIndicators(people_affected=10), ["damageLevel"]),
        (FieldIndicators(damage_level=DamageLevel.LOW), ["peopleAffected"]),
        (FieldIndicators(), ["damageLevel", "peopleAffected"]),
    ],
)
def test_score_is_not_available_without_damage_level_or_people_affected(
    indicators: FieldIndicators, missing_variables: list[str]
) -> None:
    with pytest.raises(InsufficientVariablesError) as error:
        calculate_urgency_score(indicators, zone_population=100)

    assert error.value.missing_variables == missing_variables
