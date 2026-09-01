"""Shared API dependencies."""

import re
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.persistence.database import get_session
from server.app.student_profile.repository import SQLAlchemyStudentProfileRepository
from server.app.student_profile.service import StudentProfileService
from server.app.tutor.schemas import StudentProfile


CLIENT_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{16,64}$")


def get_client_id(
    x_client_id: Annotated[str | None, Header(alias="X-Client-Id")] = None,
) -> str:
    client_id = (x_client_id or "").strip()
    if not CLIENT_ID_PATTERN.fullmatch(client_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A valid client identifier is required.",
        )
    return client_id


def get_profile_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> StudentProfileService:
    return StudentProfileService(SQLAlchemyStudentProfileRepository(session))


async def require_student_profile(
    client_id: Annotated[str, Depends(get_client_id)],
    service: Annotated[StudentProfileService, Depends(get_profile_service)],
) -> StudentProfile:
    profile = await service.get(client_id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Student profile setup is required.",
        )
    return profile
