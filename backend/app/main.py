"""FastAPI application entry point."""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.v1.weather import router as weather_router
from app.database import init_db


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Initialize local database tables when the application starts."""
    await init_db()
    yield


app = FastAPI(
    title="Sports Weather Tracker API",
    description="運動天氣追蹤系統 API",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(weather_router)


@app.get("/health", tags=["系統"])
async def health_check() -> dict[str, str]:
    """Return the service health status."""
    return {"status": "ok"}
