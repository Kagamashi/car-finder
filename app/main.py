from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.routers import admin, filters, health, listings, notifications, users
from app.utils.logging import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Car Finder",
        description="Personal car listing aggregation system with email notifications",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.include_router(health.router, prefix="/health", tags=["health"])
    app.include_router(users.router, prefix="/users", tags=["users"])
    app.include_router(filters.router, prefix="", tags=["filters"])
    app.include_router(listings.router, prefix="/listings", tags=["listings"])
    app.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
    app.include_router(admin.router, prefix="/admin", tags=["admin"])

    return app


app = create_app()
