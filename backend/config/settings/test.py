"""Test settings.

Tests need PostgreSQL + pgvector (vector search and Row-Level Security are
part of what is being tested). CI provides a service container; locally run
`make test-db` (or `docker compose run --rm backend-test`).
"""

import os

os.environ.setdefault("DJANGO_SECRET_KEY", "test-only-not-a-secret-but-long-enough-for-hs256")
os.environ.setdefault("DATABASE_URL", "postgres://ciatadel:testpw@localhost:55432/ciatadel_test")

from .base import *  # noqa: E402, F403
from .base import AI, REST_FRAMEWORK, STORAGE  # noqa: E402

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
STORAGE["BACKEND"] = "memory"
AI["EMBEDDING_DIM"] = 768
AI["EMBEDDING_QUERY_PREFIX"] = ""
AI["EMBEDDING_DOCUMENT_PREFIX"] = ""
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["login"] = "10000/min"
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["ask"] = "10000/min"
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
