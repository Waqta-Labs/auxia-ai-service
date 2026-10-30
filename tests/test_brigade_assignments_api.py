from fastapi.testclient import TestClient

from app.core.security import API_KEY_HEADER
from tests.conftest import TEST_API_KEY

URL = "/api/v1/brigade-assignments/suggestions"
HEADERS = {API_KEY_HEADER: TEST_API_KEY}

NEAR = "e9b3a4f5-6d7c-4e8f-a0b1-2c3d4e5f6a05"
FAR = "f0c4b5a6-7e8d-4f9a-b1c2-3d4e5f6a7b06"

README_REQUEST = {
    "zoneLocation": {"latitude": -12.0464, "longitude": -77.0428},
    "brigades": [
        {"brigadeId": NEAR, "location": {"latitude": -12.0560, "longitude": -77.0844}},
        {"brigadeId": FAR, "location": {"latitude": -12.1210, "longitude": -77.0300}},
    ],
}


def test_suggestion_returns_the_readme_example(client: TestClient) -> None:
    response = client.post(URL, json=README_REQUEST, headers=HEADERS)

    assert response.status_code == 200
    assert response.json() == {"brigadeId": NEAR, "distanceKm": 4.6, "modelVersion": "rules-v1"}


def test_request_without_brigades_returns_bad_request(client: TestClient) -> None:
    request = {**README_REQUEST, "brigades": []}

    response = client.post(URL, json=request, headers=HEADERS)

    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert response.json()["details"][0]["field"] == "brigades"


def test_repeated_brigade_returns_bad_request(client: TestClient) -> None:
    brigades = [README_REQUEST["brigades"][0], README_REQUEST["brigades"][0]]

    response = client.post(URL, json={**README_REQUEST, "brigades": brigades}, headers=HEADERS)

    assert response.status_code == 400
    assert response.json()["details"][0]["field"] == "brigades"


def test_latitude_out_of_range_returns_bad_request(client: TestClient) -> None:
    request = {**README_REQUEST, "zoneLocation": {"latitude": -91, "longitude": -77.0428}}

    response = client.post(URL, json=request, headers=HEADERS)

    assert response.status_code == 400
    assert response.json()["details"][0]["field"] == "zoneLocation.latitude"


def test_request_without_zone_location_returns_bad_request(client: TestClient) -> None:
    response = client.post(URL, json={"brigades": README_REQUEST["brigades"]}, headers=HEADERS)

    assert response.status_code == 400
    assert response.json()["details"][0]["field"] == "zoneLocation"


def test_openapi_documents_400_for_the_suggestion(client: TestClient) -> None:
    document = client.get("/openapi.json").json()

    responses = document["paths"][URL]["post"]["responses"]
    assert "400" in responses
    assert "422" not in responses


def test_request_without_api_key_is_rejected(client: TestClient) -> None:
    response = client.post(URL, json=README_REQUEST)

    assert response.status_code == 401
