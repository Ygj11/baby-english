"""Student profile API."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from server.app.api.dependencies import get_client_id, get_profile_service
from server.app.student_profile.service import StudentProfileService
from server.app.tutor.schemas import EnglishLevel, StudentProfile


router = APIRouter(prefix="/api/student", tags=["student-profile"])


class StudentProfilePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    age: int = Field(ge=6, le=12)
    grade: int = Field(ge=1, le=6)
    english_level: EnglishLevel


@router.get("/profile", response_model=StudentProfilePayload)
async def get_profile(
    client_id: Annotated[str, Depends(get_client_id)],
    service: Annotated[StudentProfileService, Depends(get_profile_service)],
) -> StudentProfilePayload:
    profile = await service.get(client_id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student profile has not been set up.",
        )
    return StudentProfilePayload.model_validate(profile, from_attributes=True)


@router.put("/profile", response_model=StudentProfilePayload)
async def put_profile(
    payload: StudentProfilePayload,
    client_id: Annotated[str, Depends(get_client_id)],
    service: Annotated[StudentProfileService, Depends(get_profile_service)],
) -> StudentProfilePayload:
    profile = await service.save(
        client_id,
        StudentProfile(
            age=payload.age,
            grade=payload.grade,
            english_level=payload.english_level,
        ),
    )
    return StudentProfilePayload.model_validate(profile, from_attributes=True)
