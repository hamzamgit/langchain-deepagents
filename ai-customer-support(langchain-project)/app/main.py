"""FastAPI application entrypoint."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from app.api.routes import approvals, conversations, customers, tickets
from app.config import get_settings
from app.database.session import init_db
from app.llm import configure_langsmith


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


@asynccontextmanager
async def lifespan(_app: FastAPI):
    _configure_logging()
    settings = get_settings()
    configure_langsmith(settings)
    Path("./data").mkdir(parents=True, exist_ok=True)
    # For SQLite / local bootstrap create tables. Postgres uses Alembic migrations.
    if settings.is_sqlite or settings.app_env in {"development", "test"}:
        await init_db()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="AI Customer Support Agent — LangChain / LangGraph / FastAPI",
        lifespan=lifespan,
    )

    prefix = settings.api_prefix
    application.include_router(customers.router, prefix=prefix)
    application.include_router(conversations.router, prefix=prefix)
    application.include_router(tickets.router, prefix=prefix)
    application.include_router(approvals.router, prefix=prefix)

    @application.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "app": settings.app_name}

    return application


app = create_app()
