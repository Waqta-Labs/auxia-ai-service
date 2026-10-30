from uuid import UUID

import pytest

from app.schemas.brigades import CandidateBrigade, GeoLocation
from app.services.staffing import haversine_km, suggest_brigade

LIMA = GeoLocation(latitude=-12.0464, longitude=-77.0428)
CALLAO = GeoLocation(latitude=-12.0560, longitude=-77.0844)
MIRAFLORES = GeoLocation(latitude=-12.1210, longitude=-77.0300)
NEAR = UUID("e9b3a4f5-6d7c-4e8f-a0b1-2c3d4e5f6a05")
FAR = UUID("f0c4b5a6-7e8d-4f9a-b1c2-3d4e5f6a7b06")


def brigade(brigade_id: UUID, location: GeoLocation) -> CandidateBrigade:
    return CandidateBrigade(brigade_id=brigade_id, location=location)


def test_distance_to_the_same_point_is_zero() -> None:
    assert haversine_km(LIMA, LIMA) == 0


def test_distance_is_symmetric() -> None:
    assert haversine_km(LIMA, CALLAO) == pytest.approx(haversine_km(CALLAO, LIMA))


def test_one_degree_of_latitude_is_about_111_km() -> None:
    north = GeoLocation(latitude=1, longitude=0)
    south = GeoLocation(latitude=0, longitude=0)

    assert haversine_km(north, south) == pytest.approx(111.19, abs=0.01)


def test_closest_brigade_is_suggested_whatever_the_order() -> None:
    near, far = brigade(NEAR, CALLAO), brigade(FAR, MIRAFLORES)

    assert suggest_brigade(LIMA, [far, near]).brigade_id == NEAR
    assert suggest_brigade(LIMA, [near, far]).brigade_id == NEAR


def test_distance_is_rounded_to_one_decimal() -> None:
    suggestion = suggest_brigade(LIMA, [brigade(NEAR, CALLAO)])

    assert suggestion.distance_km == 4.6


def test_first_brigade_wins_a_tie() -> None:
    suggestion = suggest_brigade(LIMA, [brigade(FAR, CALLAO), brigade(NEAR, CALLAO)])

    assert suggestion.brigade_id == FAR


def test_brigade_at_the_zone_is_at_zero_km() -> None:
    suggestion = suggest_brigade(LIMA, [brigade(FAR, MIRAFLORES), brigade(NEAR, LIMA)])

    assert suggestion.brigade_id == NEAR
    assert suggestion.distance_km == 0
