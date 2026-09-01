"""Alembic environment for the baby-english metadata."""

from logging.config import fileConfig
import os

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import make_url

from server.app.persistence.database import Base, DEFAULT_DATABASE_URL
from server.app.student_profile import model as student_profile_model  # noqa: F401
from server.app.pronunciation import model as pronunciation_model  # noqa: F401
from server.app.scenario import model as scenario_model  # noqa: F401
from server.app.photo import model as photo_model  # noqa: F401
from server.app.textbook import model as textbook_model  # noqa: F401


config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def migration_url() -> str:
    url = make_url(os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL))
    if "+" in url.drivername:
        url = url.set(drivername=url.drivername.split("+", 1)[0])
    return url.render_as_string(hide_password=False)


def run_migrations_offline() -> None:
    context.configure(
        url=migration_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = migration_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
