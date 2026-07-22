"""Shared, isolated environment for the unittest suite."""
from __future__ import annotations

import os
from pathlib import Path


def configure_test_environment() -> None:
    root = Path(__file__).resolve().parents[1]
    database = root / "test.db"
    if os.environ.get("ECLASS_TEST_ENV_READY") != "1":
        database.unlink(missing_ok=True)
        os.environ["ECLASS_TEST_ENV_READY"] = "1"
    os.environ["ENV"] = "test"
    os.environ["DATABASE_URL"] = f"sqlite:///{database.as_posix()}"
    os.environ["DATABASE_URL_SYNC"] = f"sqlite:///{database.as_posix()}"
    # Vector integration has its own opt-in test. Unit/API tests must never
    # depend on, or mutate, the developer's Docker database.
    os.environ["VECTOR_DATABASE_URL"] = ""
    os.environ.setdefault("JWT_SECRET_KEY", "test-only-secret-key-with-at-least-32-characters")
