from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from prometheus_client import make_asgi_app

from lofin.api.routes import router
from lofin.core.config import get_settings
from lofin.core.logging import configure_logging
from lofin.db.init_db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[no-untyped-def]
    settings = get_settings()
    configure_logging(settings.log_level)
    await init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="LoFin", version="0.1.0", lifespan=lifespan)
    app.include_router(router)
    app.mount("/metrics", make_asgi_app())
    return app


app = create_app()
