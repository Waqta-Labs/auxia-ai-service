import random
from uuid import UUID, uuid4

from app.schemas.distributions import (
    AllocatedCategory,
    AvailableResource,
    Coverage,
    PrioritizedZone,
    UnitOfMeasure,
)
from app.schemas.indicators import Need
from app.services.distribution import demand_of, justify, recommend_distribution

ZONE_A = UUID("5b0c2f6e-8a1d-4c47-9f3e-2d6a1b7c9e01")
ZONE_B = UUID("a3e9d4c2-1f6b-4e8a-b5d7-0c2e4f6a8b02")
WATER = UUID("c7f1e2d3-4b5a-4c6d-8e9f-0a1b2c3d4e03")
FOOD = UUID("d8a2f3e4-5c6b-4d7e-9f0a-1b2c3d4e5f04")


def zone(zone_id: UUID, score: float, people: int, *needs: Need) -> PrioritizedZone:
    return PrioritizedZone(zone_id=zone_id, score=score, people_affected=people, needs=list(needs))


def resource(resource_id: UUID, category: Need, quantity: int) -> AvailableResource:
    return AvailableResource(
        resource_id=resource_id,
        category=category,
        unit=UnitOfMeasure.UNIT,
        available_quantity=quantity,
    )


def by_zone(zones, inventory):
    return {d.zone_id: d for d in recommend_distribution(zones, inventory)}


def test_readme_example_splits_by_score_and_caps_by_demand() -> None:
    result = by_zone(
        [zone(ZONE_A, 78.4, 140, Need.WATER, Need.FOOD), zone(ZONE_B, 41.0, 90, Need.WATER)],
        [resource(WATER, Need.WATER, 500), resource(FOOD, Need.FOOD, 300)],
    )

    # Water: 500 × 78.4 / 119.4 = 328.3 and 500 × 41 / 119.4 = 171.7, plus the last liter to A.
    # Food: only A needs it, and its demand is 140 × 1.
    assert result[ZONE_A].quantities == {WATER: 329, FOOD: 140}
    assert result[ZONE_B].quantities == {WATER: 171}
    assert result[ZONE_A].coverage == Coverage.PARTIAL
    assert result[ZONE_B].coverage == Coverage.PARTIAL


def test_demand_is_people_affected_times_the_ration_rounded_up() -> None:
    needs = (Need.WATER, Need.FOOD, Need.SHELTER, Need.HYGIENE, Need.MEDICINE, Need.OTHER)

    demand = demand_of(zone(ZONE_A, 50, 91, *needs))

    assert demand == {
        Need.WATER: 1365,
        Need.FOOD: 91,
        Need.SHELTER: 19,
        Need.HYGIENE: 19,
        Need.MEDICINE: 10,
        Need.OTHER: 91,
    }
    # 90 × 0.2 is 18.000000000000004 in floating point: still 18 tents.
    assert demand_of(zone(ZONE_A, 50, 90, Need.SHELTER)) == {Need.SHELTER: 18}


def test_enough_inventory_covers_every_zone_and_keeps_the_rest() -> None:
    result = by_zone(
        [zone(ZONE_A, 80, 10, Need.FOOD), zone(ZONE_B, 20, 30, Need.FOOD)],
        [resource(FOOD, Need.FOOD, 100)],
    )

    assert result[ZONE_A].quantities == {FOOD: 10}
    assert result[ZONE_B].quantities == {FOOD: 30}
    assert {d.coverage for d in result.values()} == {Coverage.FULL}


def test_what_a_zone_cannot_take_goes_to_the_others() -> None:
    result = by_zone(
        [zone(ZONE_A, 90, 5, Need.FOOD), zone(ZONE_B, 10, 100, Need.FOOD)],
        [resource(FOOD, Need.FOOD, 50)],
    )

    # A would get 45 by score but needs only 5; the other 40 go to B.
    assert result[ZONE_A].quantities == {FOOD: 5}
    assert result[ZONE_B].quantities == {FOOD: 45}
    assert result[ZONE_A].coverage == Coverage.FULL
    assert result[ZONE_B].coverage == Coverage.PARTIAL


def test_fewer_units_than_zones_go_to_the_most_urgent() -> None:
    result = by_zone(
        [zone(ZONE_A, 30, 10, Need.SHELTER), zone(ZONE_B, 70, 10, Need.SHELTER)],
        [resource(FOOD, Need.SHELTER, 1)],
    )

    assert result[ZONE_B].quantities == {FOOD: 1}
    assert result[ZONE_A].quantities == {}
    assert result[ZONE_A].coverage == Coverage.NONE


def test_zones_without_score_share_equally() -> None:
    result = by_zone(
        [zone(ZONE_A, 0, 100, Need.FOOD), zone(ZONE_B, 0, 100, Need.FOOD)],
        [resource(FOOD, Need.FOOD, 60)],
    )

    assert result[ZONE_A].quantities == {FOOD: 30}
    assert result[ZONE_B].quantities == {FOOD: 30}


def test_second_resource_of_a_category_covers_what_the_first_left() -> None:
    other_water = uuid4()
    result = by_zone(
        [zone(ZONE_A, 50, 10, Need.WATER)],
        [resource(WATER, Need.WATER, 100), resource(other_water, Need.WATER, 100)],
    )

    # Demand of 150 liters: 100 from the first resource and 50 from the second.
    assert result[ZONE_A].quantities == {WATER: 100, other_water: 50}
    assert result[ZONE_A].coverage == Coverage.FULL


def test_need_without_inventory_leaves_the_zone_partial_or_unserved() -> None:
    result = by_zone(
        [zone(ZONE_A, 60, 10, Need.FOOD, Need.MEDICINE), zone(ZONE_B, 40, 10, Need.MEDICINE)],
        [resource(FOOD, Need.FOOD, 100)],
    )

    assert result[ZONE_A].coverage == Coverage.PARTIAL
    assert result[ZONE_B].coverage == Coverage.NONE
    assert result[ZONE_B].quantities == {}


def test_zone_without_needs_is_covered_and_receives_nothing() -> None:
    result = by_zone([zone(ZONE_A, 90, 100)], [resource(FOOD, Need.FOOD, 100)])

    assert result[ZONE_A].quantities == {}
    assert result[ZONE_A].coverage == Coverage.FULL


def allocated(zone_with_needs: PrioritizedZone, **quantities: int) -> PrioritizedZone:
    return zone_with_needs.model_copy(
        update={
            "already_allocated": [
                AllocatedCategory(category=Need(category), quantity=quantity)
                for category, quantity in quantities.items()
            ]
        }
    )


def test_what_a_zone_already_has_is_taken_from_its_demand() -> None:
    base = zone(ZONE_A, 78.4, 140, Need.WATER, Need.FOOD)

    assert demand_of(allocated(base, WATER=100)) == {Need.WATER: 2000, Need.FOOD: 140}
    assert demand_of(allocated(base, WATER=2100, FOOD=500)) == {Need.WATER: 0, Need.FOOD: 0}


def test_zone_whose_needs_are_already_covered_is_full_and_receives_nothing() -> None:
    covered = allocated(zone(ZONE_A, 78.4, 140, Need.WATER, Need.FOOD), WATER=2100, FOOD=140)

    result = by_zone(
        [covered, zone(ZONE_B, 41.0, 90, Need.WATER)],
        [resource(WATER, Need.WATER, 500), resource(FOOD, Need.FOOD, 300)],
    )

    assert result[ZONE_A].quantities == {}
    assert result[ZONE_A].coverage == Coverage.FULL
    assert result[ZONE_B].quantities == {WATER: 500}


def test_zone_partly_covered_only_receives_what_it_still_lacks() -> None:
    partly = allocated(zone(ZONE_A, 78.4, 140, Need.WATER, Need.FOOD), FOOD=100)

    result = by_zone([partly], [resource(WATER, Need.WATER, 5000), resource(FOOD, Need.FOOD, 300)])

    assert result[ZONE_A].quantities == {WATER: 2100, FOOD: 40}
    assert result[ZONE_A].coverage == Coverage.FULL


def test_allocations_never_exceed_the_inventory_or_the_demand() -> None:
    rng = random.Random(2026)
    categories = list(Need)
    for _ in range(200):
        zones = [
            zone(uuid4(), rng.uniform(0, 100), rng.randint(0, 500), *rng.sample(categories, 3))
            for _ in range(rng.randint(1, 6))
        ]
        inventory = [
            resource(uuid4(), rng.choice(categories), rng.randint(0, 3000))
            for _ in range(rng.randint(0, 6))
        ]

        distributions = recommend_distribution(zones, inventory)

        for item in inventory:
            given = sum(d.quantities.get(item.resource_id, 0) for d in distributions)
            assert given <= item.available_quantity
        for current, distribution in zip(zones, distributions, strict=True):
            demand = demand_of(current)
            for category, needed in demand.items():
                received = sum(
                    quantity
                    for resource_id, quantity in distribution.quantities.items()
                    if next(r for r in inventory if r.resource_id == resource_id).category
                    == category
                )
                assert received <= needed


def test_justification_counts_the_covered_zones() -> None:
    covered = recommend_distribution(
        [zone(ZONE_A, 50, 10, Need.FOOD)], [resource(FOOD, Need.FOOD, 10)]
    )
    short = recommend_distribution(
        [zone(ZONE_A, 50, 10, Need.FOOD), zone(ZONE_B, 50, 10, Need.FOOD)],
        [resource(FOOD, Need.FOOD, 10)],
    )

    assert "1 of 1 zones are fully covered." in justify(covered)
    assert "unserved" not in justify(covered)
    assert "0 of 2 zones are fully covered." in justify(short)
    assert "partially or totally unserved" in justify(short)
