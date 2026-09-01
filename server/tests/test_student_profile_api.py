from uuid import uuid4

import httpx
import pytest

from server.app.main import app


def headers(label: str = "profile") -> dict[str, str]:
    return {"X-Client-Id": f"test_{label}_{uuid4().hex}"}


@pytest.mark.asyncio
async def test_profile_get_missing_put_create_get_update_without_internal_ids() -> None:
    owner = headers()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        missing = await client.get("/api/student/profile", headers=owner)
        created = await client.put(
            "/api/student/profile",
            headers=owner,
            json={"age": 8, "grade": 3, "english_level": "beginner"},
        )
        fetched = await client.get("/api/student/profile", headers=owner)
        updated = await client.put(
            "/api/student/profile",
            headers=owner,
            json={"age": 10, "grade": 5, "english_level": "elementary"},
        )

    assert missing.status_code == 404
    assert created.status_code == 200
    assert fetched.json() == {"age": 8, "grade": 3, "english_level": "beginner"}
    assert updated.json() == {"age": 10, "grade": 5, "english_level": "elementary"}
    assert set(created.json()) == {"age", "grade", "english_level"}
    assert "client_id" not in created.text
    assert "\"id\"" not in created.text


@pytest.mark.asyncio
async def test_profile_isolated_by_client_and_invalid_payload_does_not_write() -> None:
    owner_a = headers("a")
    owner_b = headers("b")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        assert (
            await client.put(
                "/api/student/profile",
                headers=owner_a,
                json={"age": 7, "grade": 2, "english_level": "starter"},
            )
        ).status_code == 200
        assert (await client.get("/api/student/profile", headers=owner_b)).status_code == 404
        invalid = await client.put(
            "/api/student/profile",
            headers=owner_b,
            json={"age": 5, "grade": 7, "english_level": "advanced"},
        )
        still_missing = await client.get("/api/student/profile", headers=owner_b)

    assert invalid.status_code == 422
    assert still_missing.status_code == 404


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "client_id",
    [None, "", "anon", "x" * 65, "invalid client id"],
)
async def test_profile_rejects_missing_or_invalid_client_id(client_id: str | None) -> None:
    request_headers = {"X-Client-Id": client_id} if client_id else {}
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/student/profile", headers=request_headers)

    assert response.status_code == 400
    assert "anon" not in response.text
