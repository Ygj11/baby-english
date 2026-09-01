"""Photo English application service."""

from dataclasses import dataclass
from pathlib import Path

from server.app.photo.domain import InvalidPhotoLearningResultError, PhotoLearningResult, validate_learning_result
from server.app.photo.gateway import VisionError, VisionGateway
from server.app.photo.prompt import build_photo_prompt
from server.app.tutor.schemas import StudentProfile


@dataclass(slots=True)
class PhotoLearningService:
    gateway: VisionGateway

    async def analyze(self, *, image_path: Path, student: StudentProfile) -> PhotoLearningResult:
        result = await self.gateway.analyze(
            image_path=image_path,
            system_prompt=build_photo_prompt(student),
        )
        try:
            return validate_learning_result(result)
        except InvalidPhotoLearningResultError as error:
            raise VisionError("The Vision provider returned an invalid lesson.") from error
