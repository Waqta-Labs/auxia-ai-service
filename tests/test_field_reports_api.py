from fastapi.testclient import TestClient

from app.core.security import API_KEY_HEADER
from tests.conftest import TEST_API_KEY

URL = "/api/v1/field-reports/structure"
HEADERS = {API_KEY_HEADER: TEST_API_KEY}


def test_structure_returns_the_readme_example(client: TestClient) -> None:
    text = (
        "Derrumbe de viviendas en el sector Alto Perú. Hay 35 familias afectadas, unas 140"
        " personas, entre ellas 40 niños y 15 adultos mayores. Urge agua potable, alimentos"
        " y carpas."
    )

    response = client.post(URL, json={"text": text}, headers=HEADERS)

    assert response.status_code == 200
    assert response.json() == {
        "indicators": {
            "damageLevel": "SEVERE",
            "familiesAffected": 35,
            "peopleAffected": 140,
            "children": 40,
            "elderlyPeople": 15,
            "disabledPeople": None,
            "needs": ["WATER", "FOOD", "SHELTER"],
        },
        "missingVariables": ["disabledPeople"],
        "modelVersion": "rules-v1",
    }


def test_missing_text_returns_bad_request(client: TestClient) -> None:
    response = client.post(URL, json={}, headers=HEADERS)

    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert [detail["field"] for detail in body["details"]] == ["text"]


def test_blank_text_returns_bad_request(client: TestClient) -> None:
    response = client.post(URL, json={"text": "   "}, headers=HEADERS)

    assert response.status_code == 400
    assert response.json()["details"][0]["field"] == "text"


def test_text_longer_than_5000_characters_returns_bad_request(client: TestClient) -> None:
    response = client.post(URL, json={"text": "a" * 5001}, headers=HEADERS)

    assert response.status_code == 400
    assert response.json()["details"][0]["field"] == "text"


def test_request_without_api_key_is_rejected(client: TestClient) -> None:
    response = client.post(URL, json={"text": "Viviendas colapsadas"})

    assert response.status_code == 401
    assert response.json()["code"] == "INVALID_API_KEY"
