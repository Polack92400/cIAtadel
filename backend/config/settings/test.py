"""Test settings.

Defaults to SQLite so unit tests run anywhere. Security/RLS/pgvector tests
need PostgreSQL: CI and `make test` set DATABASE_URL to the compose database.
"""

import os

os.environ.setdefault("DJANGO_SECRET_KEY", "test-only-not-a-secret")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from .base import *  # noqa: E402, F403
from .base import AI, REST_FRAMEWORK  # noqa: E402

DEBUG = False
ALLOWED_HOSTS = ["testserver", "localhost"]
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]  # speed only
AUTH_COOKIE_SECURE = False
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = []

# Deterministic, offline providers: tests never need Ollama or a paid API.
AI["LLM_PROVIDER"] = "fake"
AI["EMBEDDING_PROVIDER"] = "fake"
