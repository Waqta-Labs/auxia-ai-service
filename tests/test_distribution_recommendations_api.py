from fastapi.testclient import TestClient

from app.core.security import API_KEY_HEADER
from tests.conftest import TEST_API_KEY

URL = "/api/v1/distribution-recommendations"
HEADERS = {API_KEY_HEADER: TEST_API_KEY}

ZONE_A = "5b0c2f6e-8a1d-4c47-9f3e-2d6a1b7c9e01"
ZONE_B = "a3e9d4c2-1f6b-4e8a-b5d7-0c2e4f6a8b02"
WATER = "c7f1e2d3-4b5a-4c6d-8e9f-0a1b2c3d4e03"
FOOD = "d8a2f3e4-5c6b-4d7e-9f0a-1b2c3d4e5f04"

README_REQUEST = {
    "zones": [
        {"zoneId": ZONE_A, "score": 78.4, "peopleAffected": 140, "needs": ["WATER", "FOOD"]},
        {"zoneId": ZONE_B, "score": 41.0, "peopleAffected": 90, "needs": ["WATER"]},
    ],
    "inventory": [
        {"resourceId": WATER, "category": "WATER", "unit": "LITER", "availableQuantity": 500},
        {"resourceId": FOOD, "category": "FOOD", "unit": "KG", "availableQuantity": 300},
    ],
}


def test_recommendation_returns_the_readme_example(client: TestClient) -> None:
    response = client.post(URL, json=README_REQUEST, headers=HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert body["allocations"] == [
        {
            "zoneId": ZONE_A,
            "items": [
                {"resourceId": WATER, "quantity": 329},
                {"resourceId": FOOD, "quantity": 140},
            ],
            "coverage": "PARTIAL",
        },
        {
            "zoneId": ZONE_B,
            "items": [{"resourceId": WATER, "quantity": 171}],
            "coverage": "PARTIAL",
        },
    ]
    assert "0 of 2 zones are fully covered" in body["justification"]
    assert body["modelVersion"] == "rules-v1"


def test_recommendation_never_exceeds_the_inventory_received(client: TestClient) -> None:
    allocations = client.post(URL, json=README_REQUEST, headers=HEADERS).json()["allocations"]

    given = {}
    for allocation in allocations:
        for item in allocation["items"]:
            given[item["resourceId"]] = given.get(item["resourceId"], 0) + item["quantity"]
    assert given[WATER] <= 500
    assert given[FOOD] <= 300


def test_request_without_zones_returns_bad_request(client: TestClient) -> None:
    response = client.post(URL, json={"zones": [], "inventory": []}, headers=HEADERS)

    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert response.json()["details"][0]["field"] == "zones"


def test_repeated_zone_returns_bad_request(client: TestClient) -> None:
    zones = [README_REQUEST["zones"][0], README_REQUEST["zones"][0]]

    response = client.post(URL, json={"zones": zones}, headers=HEADERS)

    assert response.status_code == 400
    assert response.json()["details"][0]["field"] == "zones"


def test_zone_receives_only_what_it_still_lacks(client: TestClient) -> None:
    zone_a = {
        **README_REQUEST["zones"][0],
        "alreadyAllocated": [{"category": "FOOD", "quantity": 140}],
    }
    request = {**README_REQUEST, "zones": [zone_a, README_REQUEST["zones"][1]]}

    response = client.post(URL, json=request, headers=HEADERS)

    assert response.status_code == 200
    allocations = {item["zoneId"]: item for item in response.json()["allocations"]}
    assert {item["resourceId"] for item in allocations[ZONE_A]["items"]} == {WATER}


def test_repeated_allocated_category_returns_bad_request(client: TestClient) -> None:
    repeated = [{"category": "FOOD", "quantity": 1}, {"category": "FOOD", "quantity": 2}]
    zone_a = {**README_REQUEST["zones"][0], "alreadyAllocated": repeated}

    response = client.post(URL, json={"zones": [zone_a]}, headers=HEADERS)

    assert response.status_code == 400
    assert response.json()["details"][0]["field"] == "zones[0].alreadyAllocated"


def test_negative_quantity_returns_bad_request(client: TestClient) -> None:
    inventory = [{**README_REQUEST["inventory"][0], "availableQuantity": -1}]

    response = client.post(
        URL, json={"zones": README_REQUEST["zones"], "inventory": inventory}, headers=HEADERS
    )

    assert response.status_code == 400
    assert response.json()["details"][0]["field"] == "inventory[0].availableQuantity"


def test_request_without_api_key_is_rejected(client: TestClient) -> None:
    response = client.post(URL, json=README_REQUEST)

    assert response.status_code == 401
