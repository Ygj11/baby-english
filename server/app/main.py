"""FastAPI application entry point."""

from fastapi import FastAPI

from server.app.api.tutor import router as tutor_router
from server.app.api.voice import router as voice_router

app = FastAPI()
app.include_router(tutor_router)
app.include_router(voice_router)


@app.get("/api/health")
async def health() -> dict[str, str]:
    """Return the service health status."""
    return {"status": "ok", "service": "baby-english"}
