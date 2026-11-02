import pytest
from fastapi import APIRouter, Depends, FastAPI
from fastapi.testclient import TestClient

from app.core.security import API_KEY_HEADER, require_api_key
from tests.conftest import TEST_API_KEY

INVALID_API_KEY_RESPONSE = {
    "code": "INVALID_API_KEY",
    "message": "Missing or invalid API key.",
    "details": [],
}


@pytest.fixture
def protected_client(app: FastAPI) -> TestClient:
    router = APIRouter(dependencies=[Depends(require_api_key)])

    @router.get("/protected")
    def protected() -> dict[str, str]:
        return {"result": "ok"}

    app.include_router(router)
    return TestClient(app)


def test_request_without_api_key_is_rejected(protected_client: TestClient) -> None:
    response = protected_client.get("/protected")

    assert response.status_code == 401
    assert response.json() == INVALID_API_KEY_RESPONSE


def test_request_with_wrong_api_key_is_rejected(protected_client: TestClient) -> None:
    response = protected_client.get("/protected", headers={API_KEY_HEADER: "wrong-key"})

    assert response.status_code == 401
    assert response.json() == INVALID_API_KEY_RESPONSE


def test_request_with_valid_api_key_is_accepted(protected_client: TestClient) -> None:
    response = protected_client.get("/protected", headers={API_KEY_HEADER: TEST_API_KEY})

    assert response.status_code == 200
    assert response.json() == {"result": "ok"}
