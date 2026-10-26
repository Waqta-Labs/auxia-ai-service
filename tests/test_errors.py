import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient
from pydantic import Field

from app.core.errors import field_path
from app.schemas.common import CamelModel


class SampleZone(CamelModel):
    zone_id: str
    people_affected: int = Field(ge=0)


class SampleRequest(CamelModel):
    zones: list[SampleZone] = Field(min_length=1)


@pytest.fixture
def sample_client(app: FastAPI, client: TestClient) -> TestClient:
    router = APIRouter(prefix="/samples")

    @router.post("")
    def create(request: SampleRequest) -> SampleRequest:
        return request

    @router.get("/failure")
    def fail() -> None:
        raise RuntimeError("secret connection detail")

    app.include_router(router)
    return client


def test_json_uses_camel_case(sample_client: TestClient) -> None:
    body = {"zones": [{"zoneId": "z-1", "peopleAffected": 120}]}

    response = sample_client.post("/samples", json=body)

    assert response.status_code == 200
    assert response.json() == body


def test_invalid_field_returns_bad_request_with_field_path(sample_client: TestClient) -> None:
    response = sample_client.post(
        "/samples", json={"zones": [{"zoneId": "z-1", "peopleAffected": -5}]}
    )

    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert body["message"] == "The request is not valid."
    assert [detail["field"] for detail in body["details"]] == ["zones[0].peopleAffected"]


def test_missing_field_is_reported_in_camel_case(sample_client: TestClient) -> None:
    response = sample_client.post("/samples", json={"zones": [{"peopleAffected": 1}]})

    assert response.status_code == 400
    assert [detail["field"] for detail in response.json()["details"]] == ["zones[0].zoneId"]


def test_empty_list_returns_bad_request(sample_client: TestClient) -> None:
    response = sample_client.post("/samples", json={"zones": []})

    assert response.status_code == 400
    assert response.json()["details"][0]["field"] == "zones"


def test_missing_body_returns_bad_request(sample_client: TestClient) -> None:
    response = sample_client.post("/samples")

    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_unknown_route_returns_not_found(client: TestClient) -> None:
    response = client.get("/api/v1/unknown")

    assert response.status_code == 404
    assert response.json() == {"code": "NOT_FOUND", "message": "Not Found", "details": []}


def test_unsupported_method_returns_method_not_allowed(client: TestClient) -> None:
    response = client.post("/health")

    assert response.status_code == 405
    assert response.json()["code"] == "METHOD_NOT_ALLOWED"
    assert response.headers["allow"] == "GET"


def test_unexpected_error_returns_internal_error_without_details(
    sample_client: TestClient,
) -> None:
    response = sample_client.get("/samples/failure")

    assert response.status_code == 500
    assert response.json() == {
        "code": "INTERNAL_ERROR",
        "message": "An unexpected error occurred.",
        "details": [],
    }


@pytest.mark.parametrize(
    ("location", "expected"),
    [
        (("body", "text"), "text"),
        (("body", "zones", 0, "score"), "zones[0].score"),
        (("body", "inventory", 2, "availableQuantity"), "inventory[2].availableQuantity"),
        (("query", "limit"), "limit"),
        (("body",), "body"),
    ],
)
def test_field_path(location: tuple[str | int, ...], expected: str) -> None:
    assert field_path(location) == expected
