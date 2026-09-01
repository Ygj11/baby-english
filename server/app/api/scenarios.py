"""Child-safe scenario catalogue and role-play endpoints."""

import logging
from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.api.dependencies import get_client_id, require_student_profile
from server.app.api.voice import get_media_store, get_stt_gateway, get_tts_gateway
from server.app.persistence.database import get_session
from server.app.scenario.assessment import (
    SceneAssessmentError,
    SceneGoalAssessor,
    create_scene_goal_assessor,
)
from server.app.scenario.catalog import SCENES, get_scene
from server.app.scenario.repository import (
    SQLAlchemyScenarioRepository,
    ScenarioCompletionRequiresLearnerError,
    ScenarioSessionInactiveError,
    ScenarioSessionNotFoundError,
    ScenarioTurnLimitError,
)
from server.app.scenario.schemas import (
    SceneResponse,
    ScenarioCompletionResponse,
    ScenarioTurnRequest,
    ScenarioTurnResponse,
    ScenarioVoiceTurnResponse,
    StartSessionResponse,
    progress_response,
    scene_response,
)
from server.app.scenario.service import ScenarioService
from server.app.tutor.llm import LLMConfigurationError, LLMError, LLMGateway, create_llm
from server.app.tutor.schemas import StudentProfile
from server.app.voice.audio import AudioTooLargeError, EmptyAudioError, UnsupportedAudioError, temporary_audio
from server.app.voice.media import TemporaryMediaStore
from server.app.voice.stt import STTError, STTGateway
from server.app.voice.tts import TTSError, TTSGateway


router = APIRouter(prefix="/api/scenarios", tags=["scenarios"])
logger = logging.getLogger("uvicorn.error.baby_english.scenarios")


def get_scenario_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ScenarioService:
    return ScenarioService(SQLAlchemyScenarioRepository(session))


def get_scenario_llm() -> LLMGateway:
    try:
        return create_llm()
    except LLMConfigurationError as error:
        _log_failure("llm", "configuration", error)
        raise HTTPException(status_code=503, detail="Scenario practice is temporarily unavailable.") from None


def get_assessor_factory() -> Callable[[], SceneGoalAssessor]:
    return create_scene_goal_assessor


@router.get("", response_model=list[SceneResponse])
async def list_scenes(
    client_id: Annotated[str, Depends(get_client_id)],
    _student: Annotated[StudentProfile, Depends(require_student_profile)],
    service: Annotated[ScenarioService, Depends(get_scenario_service)],
) -> list[SceneResponse]:
    return [
        scene_response(scene, await service.repository.progress(client_id, scene))
        for scene in SCENES
    ]


@router.get("/{scene_id}", response_model=SceneResponse)
async def get_scene_detail(
    scene_id: str,
    client_id: Annotated[str, Depends(get_client_id)],
    _student: Annotated[StudentProfile, Depends(require_student_profile)],
    service: Annotated[ScenarioService, Depends(get_scenario_service)],
) -> SceneResponse:
    scene = get_scene(scene_id)
    if scene is None:
        raise HTTPException(status_code=404, detail="Scene not found.")
    return scene_response(scene, await service.repository.progress(client_id, scene))


@router.post("/{scene_id}/sessions", response_model=StartSessionResponse, status_code=201)
async def start_scene_session(
    scene_id: str,
    client_id: Annotated[str, Depends(get_client_id)],
    _student: Annotated[StudentProfile, Depends(require_student_profile)],
    service: Annotated[ScenarioService, Depends(get_scenario_service)],
) -> StartSessionResponse:
    scene = get_scene(scene_id)
    if scene is None:
        raise HTTPException(status_code=404, detail="Scene not found.")
    session = await service.repository.start(client_id, scene)
    progress = await service.repository.progress(client_id, scene)
    return StartSessionResponse(
        session_id=session.id,
        scene=scene_response(scene, progress),
        opening_message=scene.opening_line,
        progress=progress_response(progress),
    )


@router.post("/sessions/{session_id}/turn", response_model=ScenarioTurnResponse)
async def scenario_text_turn(
    session_id: int,
    request: ScenarioTurnRequest,
    client_id: Annotated[str, Depends(get_client_id)],
    student: Annotated[StudentProfile, Depends(require_student_profile)],
    service: Annotated[ScenarioService, Depends(get_scenario_service)],
    llm: Annotated[LLMGateway, Depends(get_scenario_llm)],
) -> ScenarioTurnResponse:
    try:
        prepared = await service.prepare_turn(
            client_id=client_id, session_id=session_id, student=student,
            message=request.message, llm=llm,
        )
        await service.save_turn(client_id, prepared)
        return ScenarioTurnResponse(session_id=session_id, reply=prepared.reply)
    except LLMError as error:
        _log_failure("llm", "request", error)
        raise HTTPException(status_code=503, detail="Scenario practice is temporarily unavailable.") from None
    except (ScenarioSessionNotFoundError, ScenarioSessionInactiveError, ScenarioTurnLimitError) as error:
        raise _session_http_error(error) from None


@router.post("/sessions/{session_id}/voice-turn", response_model=ScenarioVoiceTurnResponse)
async def scenario_voice_turn(
    session_id: int,
    file: Annotated[UploadFile, File()],
    client_id: Annotated[str, Depends(get_client_id)],
    student: Annotated[StudentProfile, Depends(require_student_profile)],
    service: Annotated[ScenarioService, Depends(get_scenario_service)],
    llm: Annotated[LLMGateway, Depends(get_scenario_llm)],
    stt: Annotated[STTGateway, Depends(get_stt_gateway)],
    tts: Annotated[TTSGateway, Depends(get_tts_gateway)],
    store: Annotated[TemporaryMediaStore, Depends(get_media_store)],
) -> ScenarioVoiceTurnResponse:
    stage = "stt"
    try:
        existing = await service.repository.get(client_id, session_id)
        await service.repository.require_turn_capacity(existing)
        async with temporary_audio(file) as audio:
            transcript = await stt.transcribe(audio.path)
            stage = "llm"
            prepared = await service.prepare_turn(
                client_id=client_id, session_id=session_id, student=student,
                message=transcript.text, llm=llm,
            )
            stage = "tts"
            synthesized = await tts.synthesize(prepared.reply)
            media_id = store.save(synthesized)
            await service.save_turn(client_id, prepared)
    except EmptyAudioError:
        raise HTTPException(status_code=400, detail="The audio file is empty.") from None
    except UnsupportedAudioError:
        raise HTTPException(status_code=400, detail="The audio format is unsupported.") from None
    except AudioTooLargeError:
        raise HTTPException(status_code=413, detail="The audio file is too large.") from None
    except (STTError, LLMError, TTSError) as error:
        _log_failure(stage, "request", error)
        raise HTTPException(status_code=503, detail="Scenario voice is temporarily unavailable.") from None
    except (ScenarioSessionNotFoundError, ScenarioSessionInactiveError, ScenarioTurnLimitError) as error:
        raise _session_http_error(error) from None
    return ScenarioVoiceTurnResponse(
        session_id=session_id,
        transcript=transcript.text,
        reply=prepared.reply,
        audio_url=f"/api/voice/media/{media_id}",
    )


@router.post("/sessions/{session_id}/complete", response_model=ScenarioCompletionResponse)
async def complete_scene_session(
    session_id: int,
    client_id: Annotated[str, Depends(get_client_id)],
    _student: Annotated[StudentProfile, Depends(require_student_profile)],
    service: Annotated[ScenarioService, Depends(get_scenario_service)],
    assessor_factory: Annotated[Callable[[], SceneGoalAssessor], Depends(get_assessor_factory)],
) -> ScenarioCompletionResponse:
    try:
        completion = await service.complete(
            client_id=client_id,
            session_id=session_id,
            assessor_factory=assessor_factory,
        )
    except ScenarioSessionNotFoundError:
        raise HTTPException(status_code=404, detail="Scenario session not found.") from None
    except ScenarioCompletionRequiresLearnerError:
        raise HTTPException(status_code=400, detail="At least one learner turn is required.") from None
    except (SceneAssessmentError, LLMError, LLMConfigurationError) as error:
        _log_failure("assessment", "request", error)
        raise HTTPException(status_code=503, detail="Scene assessment is temporarily unavailable.") from None
    return ScenarioCompletionResponse(
        session_id=completion.session_id,
        scene_id=completion.scene_id,
        completed_goal_ids=list(completion.completed_goal_ids),
        summary=completion.summary,
        tip=completion.tip,
        progress=progress_response(completion.progress),
    )


def _session_http_error(error: Exception) -> HTTPException:
    if isinstance(error, ScenarioSessionNotFoundError):
        return HTTPException(status_code=404, detail="Scenario session not found.")
    if isinstance(error, ScenarioTurnLimitError):
        return HTTPException(status_code=409, detail="This scene is full. Complete it or start again.")
    return HTTPException(status_code=409, detail="This scenario session is no longer active.")


def _log_failure(stage: str, category: str, error: Exception) -> None:
    logger.warning(
        "provider_failure stage=scenario_%s category=%s exception=%s",
        stage, category, type(error).__name__,
    )
