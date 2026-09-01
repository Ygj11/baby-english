"""FastAPI application entry point."""

from fastapi import FastAPI

from server.app.api.photo import router as photo_router
from server.app.api.pronunciation import router as pronunciation_router
from server.app.api.scenarios import router as scenarios_router
from server.app.api.student_profile import router as student_profile_router
from server.app.api.textbooks import router as textbooks_router
from server.app.api.tutor import router as tutor_router
from server.app.api.voice import router as voice_router

app = FastAPI()
app.include_router(photo_router)
app.include_router(pronunciation_router)
app.include_router(scenarios_router)
app.include_router(student_profile_router)
app.include_router(textbooks_router)
app.include_router(tutor_router)
app.include_router(voice_router)


@app.get("/api/health")
async def health() -> dict[str, str]:
    """Return the service health status."""
    return {"status": "ok", "service": "baby-english"}
