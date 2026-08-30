"""Shared environment guard for no-key Fake providers."""

import os
from typing import Literal, cast

AppEnvironment = Literal["development", "test", "production"]


class ProviderEnvironmentError(RuntimeError):
    """Raised when provider selection is unsafe for the app environment."""


def get_app_environment(value: str | None = None) -> AppEnvironment:
    """Resolve and validate APP_ENV, defaulting local runs to development."""
    raw_value = value if value is not None else os.getenv("APP_ENV", "development")
    environment = (raw_value or "development").strip().lower()
    if environment not in {"development", "test", "production"}:
        raise ProviderEnvironmentError(
            "APP_ENV must be development, test, or production."
        )
    return cast(AppEnvironment, environment)


def ensure_fake_provider_allowed(
    provider: str,
    *,
    app_env: str | None = None,
) -> None:
    """Reject an empty/Fake provider when the application is in production."""
    environment = get_app_environment(app_env)
    if environment == "production" and provider.strip().lower() in {"", "fake"}:
        raise ProviderEnvironmentError(
            "Fake providers are forbidden when APP_ENV=production."
        )
