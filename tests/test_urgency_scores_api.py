from fastapi.testclient import TestClient

from app.core.security import API_KEY_HEADER
from tests.conftest import TEST_API_KEY

URL = "/api/v1/urgency-scores"
HEADERS = {API_KEY_HEADER: TEST_API_KEY}

README_INDICATORS = {
    "damageLevel": "SEVERE",
    "familiesAffected": 35,
    "peopleAffected": 140,
    "children": 40,
    "elderlyPeople": 15,
    "disabledPeople": None,
    "needs": ["WATER", "FOOD", "SHELTER"],
}


def test_score_returns_the_readme_example(client: TestClient) -> None:
    response = client.post(
        URL, json={"indicators": README_INDICATORS, "zonePopulation": 600}, headers=HEADERS
    )

    assert response.status_code == 200
    assert response.json() == {
        "score": 54.9,
        "priorityLevel": "HIGH",
        "topFeatures": [
            {"feature": "damageLevel", "contribution": 30.0},
            {"feature": "needs", "contribution": 11.3},
            {"feature": "vulnerablePopulation", "contribution": 7.9},
        ],
        "modelVersion": "rules-v1",
    }


def test_structured_report_can_be_scored_as_it_is(client: TestClient) -> None:
    structured = client.post(
        "/api/v1/field-reports/structure",
        json={"text": "Colapso total de viviendas, 80 personas afectadas y 20 niños."},
        headers=HEADERS,
    ).json()

    response = client.post(
        URL, json={"indicators": structured["indicators"], "zonePopulation": 80}, headers=HEADERS
    )

    # 40 (CRITICAL) + 25 (the whole zone) + 5 (20 of 80 are children)
    assert response.status_code == 200
    assert response.json()["score"] == 70.0


def test_missing_damage_level_returns_insufficient_variables(client: TestClient) -> None:
    indicators = {**README_INDICATORS, "damageLevel": None}

    response = client.post(
        URL, json={"indicators": indicators, "zonePopulation": 600}, headers=HEADERS
    )

    assert response.status_code == 400
    assert response.json() == {
        "code": "INSUFFICIENT_VARIABLES",
        "message": "The urgency score cannot be calculated with the variables received.",
        "details": [
            {"field": "indicators.damageLevel", "message": "Required to calculate the score"}
        ],
    }


def test_empty_indicators_list_both_required_variables(client: TestClient) -> None:
    response = client.post(URL, json={"indicators": {}, "zonePopulation": 600}, headers=HEADERS)

    assert response.status_code == 400
    assert [detail["field"] for detail in response.json()["details"]] == [
        "indicators.damageLevel",
        "indicators.peopleAffected",
    ]


def test_zone_population_must_be_greater_than_zero(client: TestClient) -> None:
    response = client.post(
        URL, json={"indicators": README_INDICATORS, "zonePopulation": 0}, headers=HEADERS
    )

    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert [detail["field"] for detail in response.json()["details"]] == ["zonePopulation"]


def test_missing_zone_population_returns_bad_request(client: TestClient) -> None:
    response = client.post(URL, json={"indicators": README_INDICATORS}, headers=HEADERS)

    assert response.status_code == 400
    assert response.json()["details"][0]["field"] == "zonePopulation"


def test_negative_count_returns_bad_request(client: TestClient) -> None:
    indicators = {**README_INDICATORS, "children": -1}

    response = client.post(
        URL, json={"indicators": indicators, "zonePopulation": 600}, headers=HEADERS
    )

    assert response.status_code == 400
    assert response.json()["details"][0]["field"] == "indicators.children"


def test_request_without_api_key_is_rejected(client: TestClient) -> None:
    response = client.post(URL, json={"indicators": README_INDICATORS, "zonePopulation": 600})

    assert response.status_code == 401
    assert response.json()["code"] == "INVALID_API_KEY"
