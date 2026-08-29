"""FastAPI application entry point."""

from fastapi import FastAPI

app = FastAPI()


@app.get("/api/health")
async def health() -> dict[str, str]:
    """Return the service health status."""
    return {"status": "ok", "service": "baby-english"}
