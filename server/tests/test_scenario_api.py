from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import func, select

from server.app.api.scenarios import get_assessor_factory, get_scenario_llm
from server.app.api.voice import get_media_store, get_stt_gateway, get_tts_gateway
from server.app.main import app
from server.app.persistence.database import SessionFactory
from server.app.scenario.assessment import FakeSceneGoalAssessor, SceneAssessmentError
from server.app.scenario.model import ScenarioSessionRecord, ScenarioTurnRecord, SceneGoalProgressRecord
from server.app.tutor.llm import LLMError
from server.app.voice.media import TemporaryMediaStore
from server.app.voice.stt import STTError, Transcript
from server.app.voice.tts import SynthesizedAudio, TTSError


PROFILE = {"age": 8, "grade": 3, "english_level": "beginner"}


def headers(label: str) -> dict[str, str]:
    return {"X-Client-Id": f"scenario_{label}_{uuid4().hex}"[:64]}


class RecordingLLM:
    def __init__(self, reply: str = "Great choice! Would you like some water?") -> None:
        self.reply = reply
        self.calls = []

    async def generate(self, *, system_prompt, message, history=()):
        self.calls.append((system_prompt, message, tuple(history)))
        return self.reply


class FailingLLM(RecordingLLM):
    async def generate(self, *, system_prompt, message, history=()):
        self.calls.append((system_prompt, message, tuple(history)))
        raise LLMError("provider raw scene failure")


class RecordingSTT:
    def __init__(self, fail: bool = False) -> None:
        self.path: Path | None = None
        self.fail = fail

    async def transcribe(self, path: Path) -> Transcript:
        self.path = path
        assert path.exists()
        if self.fail:
            raise STTError("provider raw stt")
        return Transcript("Can I have some water, please?", 900)


class RecordingTTS:
    def __init__(self, fail: bool = False) -> None:
        self.text = ""
        self.fail = fail

    async def synthesize(self, text: str) -> SynthesizedAudio:
        self.text = text
        if self.fail:
            raise TTSError("provider raw tts")
        return SynthesizedAudio(b"RIFFscene", "audio/wav", ".wav")


async def setup_profile(client: httpx.AsyncClient, owner: dict[str, str]) -> None:
    response = await client.put("/api/student/profile", headers=owner, json=PROFILE)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_catalogue_public_shape_profile_requirement_and_unknown_scene() -> None:
    owner = headers("catalogue")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        assert (await client.get("/api/scenarios", headers=owner)).status_code == 409
        await setup_profile(client, owner)
        response = await client.get("/api/scenarios", headers=owner)
        missing = await client.get("/api/scenarios/not-real", headers=owner)
    assert response.status_code == 200
    assert [scene["id"] for scene in response.json()] == ["restaurant", "school", "shopping", "travel"]
    assert missing.status_code == 404
    for scene in response.json():
        assert "persona" not in scene
        assert all("success_criteria" not in goal for goal in scene["goals"])
        assert scene["progress"]["completed_count"] == 0


@pytest.mark.asyncio
async def test_start_is_deterministic_and_cleans_stale_active_transcript() -> None:
    owner = headers("stale")
    llm = RecordingLLM()
    app.dependency_overrides[get_scenario_llm] = lambda: llm
    transport = httpx.ASGITransport(app=app)
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            await setup_profile(client, owner)
            first = await client.post("/api/scenarios/restaurant/sessions", headers=owner)
            sid = first.json()["session_id"]
            turn = await client.post(
                f"/api/scenarios/sessions/{sid}/turn",
                headers=owner,
                json={"message": "A sandwich, please."},
            )
            second = await client.post("/api/scenarios/restaurant/sessions", headers=owner)
    finally:
        app.dependency_overrides.clear()
    assert first.status_code == 201 and turn.status_code == 200 and second.status_code == 201
    assert first.json()["opening_message"] == first.json()["scene"]["opening_line"]
    assert len(llm.calls) == 1
    async with SessionFactory() as session:
        assert await session.get(ScenarioSessionRecord, sid) is None
        old_turns = await session.scalar(select(func.count()).select_from(ScenarioTurnRecord).where(ScenarioTurnRecord.session_id == sid))
    assert old_turns == 0


@pytest.mark.asyncio
async def test_text_turn_uses_server_history_and_persists_pair_only_on_success() -> None:
    owner = headers("history")
    llm = RecordingLLM()
    app.dependency_overrides[get_scenario_llm] = lambda: llm
    transport = httpx.ASGITransport(app=app)
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            await setup_profile(client, owner)
            start = await client.post("/api/scenarios/restaurant/sessions", headers=owner)
            sid = start.json()["session_id"]
            first = await client.post(f"/api/scenarios/sessions/{sid}/turn", headers=owner, json={"message": "A sandwich, please."})
            second = await client.post(f"/api/scenarios/sessions/{sid}/turn", headers=owner, json={"message": "Water too, please."})
    finally:
        app.dependency_overrides.clear()
    assert first.status_code == second.status_code == 200
    assert [item.role for item in llm.calls[1][2]] == ["assistant", "user", "assistant"]
    assert llm.calls[1][2][1].content == "A sandwich, please."

    failing = FailingLLM()
    app.dependency_overrides[get_scenario_llm] = lambda: failing
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            failed = await client.post(f"/api/scenarios/sessions/{sid}/turn", headers=owner, json={"message": "Thank you."})
    finally:
        app.dependency_overrides.clear()
    assert failed.status_code == 503 and "provider raw" not in failed.text
    async with SessionFactory() as session:
        count = await session.scalar(select(func.count()).select_from(ScenarioTurnRecord).where(ScenarioTurnRecord.session_id == sid))
    assert count == 5


@pytest.mark.asyncio
async def test_session_ownership_isolated() -> None:
    owner_a, owner_b = headers("owner_a"), headers("owner_b")
    app.dependency_overrides[get_scenario_llm] = lambda: RecordingLLM()
    transport = httpx.ASGITransport(app=app)
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            await setup_profile(client, owner_a)
            await setup_profile(client, owner_b)
            start = await client.post("/api/scenarios/school/sessions", headers=owner_a)
            response = await client.post(
                f"/api/scenarios/sessions/{start.json()['session_id']}/turn",
                headers=owner_b,
                json={"message": "Hi"},
            )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_turn_limit_rejects_before_llm_call() -> None:
    owner = headers("turn_limit")
    llm = RecordingLLM()
    app.dependency_overrides[get_scenario_llm] = lambda: llm
    transport = httpx.ASGITransport(app=app)
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            await setup_profile(client, owner)
            start = await client.post("/api/scenarios/school/sessions", headers=owner)
            sid = start.json()["session_id"]
            async with SessionFactory() as session:
                session.add_all([
                    ScenarioTurnRecord(
                        session_id=sid,
                        idx=idx,
                        role="user" if idx % 2 else "assistant",
                        content=f"bounded turn {idx}",
                    )
                    for idx in range(1, 39)
                ])
                await session.commit()
            response = await client.post(
                f"/api/scenarios/sessions/{sid}/turn",
                headers=owner,
                json={"message": "one more"},
            )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 409
    assert llm.calls == []


@pytest.mark.asyncio
async def test_voice_turn_reuses_stt_llm_tts_media_and_cleans_upload(tmp_path: Path) -> None:
    owner = headers("voice")
    stt, llm, tts = RecordingSTT(), RecordingLLM(), RecordingTTS()
    store = TemporaryMediaStore(base_dir=tmp_path)
    app.dependency_overrides.update({
        get_scenario_llm: lambda: llm,
        get_stt_gateway: lambda: stt,
        get_tts_gateway: lambda: tts,
        get_media_store: lambda: store,
    })
    transport = httpx.ASGITransport(app=app)
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            await setup_profile(client, owner)
            start = await client.post("/api/scenarios/restaurant/sessions", headers=owner)
            response = await client.post(
                f"/api/scenarios/sessions/{start.json()['session_id']}/voice-turn",
                headers=owner,
                files={"file": ("scene.mp3", b"mock audio", "audio/mpeg")},
            )
            audio = await client.get(response.json()["audio_url"])
    finally:
        app.dependency_overrides.clear()
        store.cleanup()
    assert response.status_code == 200 and audio.content == b"RIFFscene"
    assert response.json()["transcript"] == "Can I have some water, please?"
    assert stt.path is not None and not stt.path.exists()
    assert tts.text == llm.reply


@pytest.mark.asyncio
async def test_voice_provider_failure_is_safe_cleans_upload_and_leaves_no_pair(tmp_path: Path) -> None:
    owner = headers("voice_failure")
    stt, llm, tts = RecordingSTT(), RecordingLLM(), RecordingTTS(fail=True)
    store = TemporaryMediaStore(base_dir=tmp_path)
    app.dependency_overrides.update({
        get_scenario_llm: lambda: llm,
        get_stt_gateway: lambda: stt,
        get_tts_gateway: lambda: tts,
        get_media_store: lambda: store,
    })
    transport = httpx.ASGITransport(app=app)
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            await setup_profile(client, owner)
            start = await client.post("/api/scenarios/restaurant/sessions", headers=owner)
            sid = start.json()["session_id"]
            response = await client.post(
                f"/api/scenarios/sessions/{sid}/voice-turn",
                headers=owner,
                files={"file": ("scene.mp3", b"mock audio", "audio/mpeg")},
            )
    finally:
        app.dependency_overrides.clear()
        store.cleanup()
    assert response.status_code == 503 and "provider raw" not in response.text
    assert stt.path is not None and not stt.path.exists()
    async with SessionFactory() as session:
        turns = await session.scalar(select(func.count()).select_from(ScenarioTurnRecord).where(ScenarioTurnRecord.session_id == sid))
    assert turns == 1


@pytest.mark.asyncio
async def test_completion_is_atomic_private_idempotent_and_repeatable() -> None:
    owner = headers("complete")
    llm = RecordingLLM()
    assessor = FakeSceneGoalAssessor(("say_thank_you", "order_food", "say_thank_you"))
    app.dependency_overrides[get_scenario_llm] = lambda: llm
    app.dependency_overrides[get_assessor_factory] = lambda: (lambda: assessor)
    transport = httpx.ASGITransport(app=app)
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            await setup_profile(client, owner)
            start = await client.post("/api/scenarios/restaurant/sessions", headers=owner)
            sid = start.json()["session_id"]
            no_turn = await client.post(f"/api/scenarios/sessions/{sid}/complete", headers=owner)
            await client.post(f"/api/scenarios/sessions/{sid}/turn", headers=owner, json={"message": "A sandwich, please. Thank you!"})
            completed = await client.post(f"/api/scenarios/sessions/{sid}/complete", headers=owner)
            retried = await client.post(f"/api/scenarios/sessions/{sid}/complete", headers=owner)
            next_start = await client.post("/api/scenarios/restaurant/sessions", headers=owner)
            next_sid = next_start.json()["session_id"]
            await client.post(f"/api/scenarios/sessions/{next_sid}/turn", headers=owner, json={"message": "A sandwich, please."})
            later = await client.post(f"/api/scenarios/sessions/{next_sid}/complete", headers=owner)
    finally:
        app.dependency_overrides.clear()
    assert no_turn.status_code == 400
    assert completed.status_code == retried.status_code == later.status_code == 200
    assert completed.json() == retried.json()
    assert completed.json()["completed_goal_ids"] == ["order_food", "say_thank_you"]
    assert completed.json()["progress"] == {
        "completed_goal_ids": ["order_food", "say_thank_you"],
        "missing_goal_ids": ["ask_for_drink"],
        "completed_count": 2,
        "total_count": 3,
    }
    assert assessor.calls == 2
    async with SessionFactory() as session:
        turns = await session.scalar(select(func.count()).select_from(ScenarioTurnRecord).where(ScenarioTurnRecord.session_id.in_([sid, next_sid])))
        progress = await session.scalar(select(SceneGoalProgressRecord).where(
            SceneGoalProgressRecord.client_id == owner["X-Client-Id"],
            SceneGoalProgressRecord.scene_id == "restaurant",
            SceneGoalProgressRecord.goal_id == "order_food",
        ))
    assert turns == 0
    assert progress is not None and progress.completion_count == 2


@pytest.mark.asyncio
async def test_malformed_assessment_leaves_active_transcript_and_progress_unchanged() -> None:
    owner = headers("bad_assessment")
    class BrokenAssessor:
        async def assess(self, scene, transcript):
            raise SceneAssessmentError("malformed provider JSON")
    app.dependency_overrides[get_scenario_llm] = lambda: RecordingLLM()
    app.dependency_overrides[get_assessor_factory] = lambda: (lambda: BrokenAssessor())
    transport = httpx.ASGITransport(app=app)
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            await setup_profile(client, owner)
            start = await client.post("/api/scenarios/travel/sessions", headers=owner)
            sid = start.json()["session_id"]
            await client.post(f"/api/scenarios/sessions/{sid}/turn", headers=owner, json={"message": "Where is the museum?"})
            response = await client.post(f"/api/scenarios/sessions/{sid}/complete", headers=owner)
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 503 and "malformed" not in response.text
    async with SessionFactory() as session:
        record = await session.get(ScenarioSessionRecord, sid)
        turns = await session.scalar(select(func.count()).select_from(ScenarioTurnRecord).where(ScenarioTurnRecord.session_id == sid))
        progress = await session.scalar(select(func.count()).select_from(SceneGoalProgressRecord).where(SceneGoalProgressRecord.client_id == owner["X-Client-Id"]))
    assert record is not None and record.status == "active"
    assert turns == 3 and progress == 0
