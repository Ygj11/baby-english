from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def test_empty_sqlite_upgrade_downgrade_upgrade(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = tmp_path / "migration.sqlite3"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{database_path}")
    config = Config("alembic.ini")

    command.upgrade(config, "head")
    engine = create_engine(f"sqlite:///{database_path}")
    assert "student_profiles" in inspect(engine).get_table_names()
    assert "pronunciation_attempts" in inspect(engine).get_table_names()
    assert "scenario_sessions" in inspect(engine).get_table_names()
    assert "scenario_turns" in inspect(engine).get_table_names()
    assert "scene_goal_progress" in inspect(engine).get_table_names()
    assert "photo_learning_records" in inspect(engine).get_table_names()
    assert "textbooks" in inspect(engine).get_table_names()
    assert "textbook_units" in inspect(engine).get_table_names()
    assert "student_textbooks" in inspect(engine).get_table_names()
    unique_names = {
        item["name"] for item in inspect(engine).get_unique_constraints("scene_goal_progress")
    }
    assert "uq_scene_goal_progress_owner_goal" in unique_names

    command.downgrade(config, "base")
    assert "student_profiles" not in inspect(engine).get_table_names()
    assert "pronunciation_attempts" not in inspect(engine).get_table_names()
    assert "scenario_sessions" not in inspect(engine).get_table_names()
    assert "scenario_turns" not in inspect(engine).get_table_names()
    assert "scene_goal_progress" not in inspect(engine).get_table_names()
    assert "photo_learning_records" not in inspect(engine).get_table_names()
    assert "textbooks" not in inspect(engine).get_table_names()
    assert "textbook_units" not in inspect(engine).get_table_names()
    assert "student_textbooks" not in inspect(engine).get_table_names()

    command.upgrade(config, "head")
    columns = {column["name"] for column in inspect(engine).get_columns("student_profiles")}
    engine.dispose()

    assert columns == {
        "id",
        "client_id",
        "age",
        "grade",
        "english_level",
        "created_at",
        "updated_at",
    }
    photo_columns = {
        column["name"] for column in inspect(engine).get_columns("photo_learning_records")
    }
    assert photo_columns == {
        "id",
        "client_id",
        "primary_word_en",
        "primary_meaning_zh",
        "simple_sentence_en",
        "simple_sentence_zh",
        "practice_phrase",
        "related_words_json",
        "question_en",
        "created_at",
    }
    textbook_columns = {
        column["name"] for column in inspect(engine).get_columns("textbooks")
    }
    assert textbook_columns == {
        "id",
        "slug",
        "publisher",
        "series",
        "grade",
        "semester",
        "title",
        "version",
        "source_sha256",
        "embedding_model",
        "embedding_dimensions",
        "index_schema_version",
        "indexed_at",
        "created_at",
        "updated_at",
    }
