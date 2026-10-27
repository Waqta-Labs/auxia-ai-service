"""Distribution of the available inventory among prioritized zones (rules-v1).

The demand of a zone for each category it needs is its people affected times
a ration per person, in the unit of the resource, rounded up:

| Category | Ration per person | Basis |
|---|---|---|
| WATER | 15 | liters a day (Sphere standard) |
| FOOD | 1 | one ration or kit |
| SHELTER | 0.2 | one tent per family of 5 |
| HYGIENE | 0.2 | one kit per family of 5 |
| MEDICINE | 0.1 | one kit per 10 people |
| OTHER | 1 | one unit |

Each resource, in the order of the inventory, is split among the zones that
still need its category, in proportion to their urgency score and capped by
what they still need. What a zone cannot take goes to the others, until the
resource runs out or every zone is covered. Quantities are whole units and
never exceed the available quantity of the resource.

A zone is FULL when every category it needs is covered, NONE when it needs
something and receives nothing, and PARTIAL otherwise. A zone that needs
nothing is FULL.
"""

import math
from dataclasses import dataclass
from uuid import UUID

from app.schemas.distributions import AvailableResource, Coverage, PrioritizedZone
from app.schemas.indicators import Need

RATIONS: dict[Need, float] = {
    Need.WATER: 15,
    Need.FOOD: 1,
    Need.SHELTER: 0.2,
    Need.HYGIENE: 0.2,
    Need.MEDICINE: 0.1,
    Need.OTHER: 1,
}


@dataclass(frozen=True)
class ZoneDistribution:
    zone_id: UUID
    quantities: dict[UUID, int]
    """Quantity of each resource for the zone, only the ones above zero."""
    coverage: Coverage


def demand_of(zone: PrioritizedZone) -> dict[Need, int]:
    """What the zone needs of each category, in whole units."""
    # The tolerance keeps float noise, such as 90 × 0.2 = 18.000000000000004, from rounding up.
    return {
        need: math.ceil(zone.people_affected * RATIONS[need] - 1e-9) for need in set(zone.needs)
    }


def recommend_distribution(
    zones: list[PrioritizedZone], inventory: list[AvailableResource]
) -> list[ZoneDistribution]:
    """Splits the inventory among the zones. Returns one distribution per zone, in order."""
    pending = {zone.zone_id: demand_of(zone) for zone in zones}
    quantities: dict[UUID, dict[UUID, int]] = {zone.zone_id: {} for zone in zones}

    for resource in inventory:
        candidates = [zone for zone in zones if pending[zone.zone_id].get(resource.category, 0) > 0]
        shares = _split(resource.available_quantity, candidates, pending, resource.category)
        for zone_id, quantity in shares.items():
            pending[zone_id][resource.category] -= quantity
            quantities[zone_id][resource.resource_id] = quantity

    return [
        ZoneDistribution(
            zone_id=zone.zone_id,
            quantities=quantities[zone.zone_id],
            coverage=_coverage(pending[zone.zone_id], quantities[zone.zone_id]),
        )
        for zone in zones
    ]


def _split(
    available: int,
    candidates: list[PrioritizedZone],
    pending: dict[UUID, dict[Need, int]],
    category: Need,
) -> dict[UUID, int]:
    """Splits one resource in proportion to the score, capped by what each zone still needs."""
    shares = {zone.zone_id: 0 for zone in candidates}
    left = available
    active = list(candidates)
    while left > 0 and active:
        total_score = sum(zone.score for zone in active)
        given = 0
        for zone in active:
            weight = zone.score / total_score if total_score > 0 else 1 / len(active)
            missing = pending[zone.zone_id][category] - shares[zone.zone_id]
            share = min(missing, math.floor(left * weight))
            shares[zone.zone_id] += share
            given += share
        if given == 0:
            # Fewer units than zones: the next unit goes to the most urgent zone.
            most_urgent = max(active, key=lambda zone: zone.score)
            shares[most_urgent.zone_id] += 1
            given = 1
        left -= given
        active = [zone for zone in active if shares[zone.zone_id] < pending[zone.zone_id][category]]
    return {zone_id: quantity for zone_id, quantity in shares.items() if quantity > 0}


def _coverage(pending: dict[Need, int], received: dict[UUID, int]) -> Coverage:
    if all(missing == 0 for missing in pending.values()):
        return Coverage.FULL
    return Coverage.PARTIAL if received else Coverage.NONE


def justify(distributions: list[ZoneDistribution]) -> str:
    """Explains the recommendation to the authority that has to approve it."""
    covered = sum(1 for distribution in distributions if distribution.coverage == Coverage.FULL)
    text = (
        "Each resource was split among the zones that need it in proportion to their urgency"
        " score, capped by each zone's demand (people affected times a ration per person)."
        f" {covered} of {len(distributions)} zones are fully covered."
    )
    if covered < len(distributions):
        text += " The others are left partially or totally unserved for lack of inventory."
    return text
