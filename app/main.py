"""Creates the FastAPI application. Run it with `uvicorn app.main:app`."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import health
from app.core.config import VERSION, get_settings
from app.core.errors import register_error_handlers


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # Fail at startup, not on the first request, when the configuration is missing.
    get_settings()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="AuxIA AI Service",
        version=VERSION,
        description=(
            "Structures field reports, scores zone urgency, recommends aid distribution and"
            " suggests brigades for auxia-backend."
        ),
        lifespan=lifespan,
    )
    register_error_handlers(app)
    app.include_router(health.router)
    return app


app = create_app()
