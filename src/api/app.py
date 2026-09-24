"""FastAPI application entry point."""

from fastapi import FastAPI

from api.routes.health import router as health_router


app = FastAPI(
    title="Smart Data Quality API",
    description="REST interface for the existing data quality pipeline.",
    version="0.1.0",
)
app.include_router(health_router)