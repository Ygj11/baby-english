"""Domain schemas for child tutor requests."""

from dataclasses import dataclass
from typing import Literal

EnglishLevel = Literal["starter", "beginner", "elementary"]


@dataclass(frozen=True, slots=True)
class StudentProfile:
    age: int
    grade: int
    english_level: EnglishLevel
