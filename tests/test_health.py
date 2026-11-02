import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import MODEL_VERSION, VERSION, get_settings
from app.main import create_app


def test_health_is_open_and_reports_versions(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "UP", "version": VERSION, "modelVersion": MODEL_VERSION}


def test_model_version_is_rules_v1() -> None:
    assert MODEL_VERSION == "rules-v1"


def test_startup_fails_without_api_key(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.delenv("AI_SERVICE_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)  # no local .env file
    get_settings.cache_clear()

    with pytest.raises(ValidationError), TestClient(create_app()):
        pass

    get_settings.cache_clear()
