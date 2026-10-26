"""Shared fixtures: an application with a known API key and a client for it."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import create_app

TEST_API_KEY = "test-api-key-0123456789"


@pytest.fixture
def app() -> FastAPI:
    application = create_app()
    application.dependency_overrides[get_settings] = lambda: Settings(api_key=TEST_API_KEY)
    return application


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    # Unexpected errors must reach the error handler instead of failing the test.
    return TestClient(app, raise_server_exceptions=False)
