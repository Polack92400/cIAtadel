"""Base settings shared by every environment.

Every value that differs between environments, or that is a secret, comes
from environment variables (see ../../../.env.example). Cloud-specific
choices (S3 vs MinIO, Ollama vs Bedrock, ...) are expressed as endpoints and
provider names so business code never imports a vendor SDK directly.
"""

from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()

# --- Core ---------------------------------------------------------------------
SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])

DJANGO_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]
THIRD_PARTY_APPS = [
    "rest_framework",
]
LOCAL_APPS = [
    "apps.core",
    "apps.tenants",
    "apps.accounts",
    "apps.matters",
    "apps.documents",
    "apps.rag",
    "apps.ai_engine",
    "apps.conversations",
    "apps.audit",
]
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.core.middleware.RequestIdMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# --- Database -----------------------------------------------------------------
# ATOMIC_REQUESTS gives every request a transaction, which is what lets us use
# `SET LOCAL app.current_tenant` for PostgreSQL Row-Level Security safely
# (transaction-scoped, never leaks across pooled connections). See
# docs/architecture/security-design.md.
DATABASES = {"default": env.db("DATABASE_URL")}
DATABASES["default"]["ATOMIC_REQUESTS"] = True
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DATABASE_CONN_MAX_AGE", default=60)
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Auth ---------------------------------------------------------------------
# A custom user model is declared from day one (swapping it later is painful).
AUTH_USER_MODEL = "accounts.User"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        # Phase 3 adds the HttpOnly-cookie JWT authenticator here.
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    # Deny by default: every view must opt *out* explicitly (e.g. health).
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {"anon": "30/min", "user": "300/min"},
    "EXCEPTION_HANDLER": "apps.core.exceptions.api_exception_handler",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env.int("JWT_ACCESS_MINUTES", default=15)),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env.int("JWT_REFRESH_DAYS", default=1)),
    "ROTATE_REFRESH_TOKENS": True,
    "SIGNING_KEY": env("JWT_SIGNING_KEY", default=SECRET_KEY),
    "AUTH_HEADER_TYPES": ("Bearer",),
}
AUTH_COOKIE_ACCESS = "ciatadel_access"
AUTH_COOKIE_REFRESH = "ciatadel_refresh"
AUTH_COOKIE_SECURE = env.bool("AUTH_COOKIE_SECURE", default=True)
AUTH_COOKIE_SAMESITE = "Lax"

# Header carrying the *requested* active tenant. It is only ever a hint: the
# server resolves it against the user's memberships on every request.
TENANT_HEADER = "HTTP_X_TENANT_ID"

# --- Security headers ---------------------------------------------------------
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False  # the SPA must read it for the double-submit pattern
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

# --- I18N ---------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# --- Object storage (MinIO locally, S3 on AWS) ----------------------------------
STORAGE = {
    "ENDPOINT_URL": env("S3_ENDPOINT_URL", default=None),  # None => real AWS S3
    "BUCKET": env("S3_BUCKET", default="ciatadel-documents"),
    "ACCESS_KEY_ID": env("S3_ACCESS_KEY_ID", default=None),
    "SECRET_ACCESS_KEY": env("S3_SECRET_ACCESS_KEY", default=None),
    "REGION": env("S3_REGION", default="us-east-1"),
}
DOCUMENT_MAX_UPLOAD_BYTES = env.int("DOCUMENT_MAX_UPLOAD_MB", default=25) * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024

# --- AI providers (Ollama locally, Bedrock/vLLM later) -------------------------
AI = {
    "LLM_PROVIDER": env("LLM_PROVIDER", default="ollama"),
    "LLM_MODEL": env("LLM_MODEL", default="llama3.2:3b"),
    "LLM_BASE_URL": env("LLM_BASE_URL", default="http://ollama:11434"),
    "LLM_TIMEOUT_SECONDS": env.int("LLM_TIMEOUT_SECONDS", default=120),
    "EMBEDDING_PROVIDER": env("EMBEDDING_PROVIDER", default="ollama"),
    "EMBEDDING_MODEL": env("EMBEDDING_MODEL", default="nomic-embed-text"),
    "EMBEDDING_BASE_URL": env("EMBEDDING_BASE_URL", default="http://ollama:11434"),
    # Must match the pgvector column dimension; changing it requires a re-index.
    "EMBEDDING_DIM": env.int("EMBEDDING_DIM", default=768),
    "RAG_TOP_K": env.int("RAG_TOP_K", default=6),
    "RAG_CHUNK_SIZE": env.int("RAG_CHUNK_SIZE", default=1200),
    "RAG_CHUNK_OVERLAP": env.int("RAG_CHUNK_OVERLAP", default=200),
}

# --- Celery -------------------------------------------------------------------
CELERY_BROKER_URL = env("REDIS_URL", default="redis://redis:6379/0")
CELERY_RESULT_BACKEND = None  # status is tracked on the Document row, not in Redis
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_TIME_LIMIT = env.int("CELERY_TASK_TIME_LIMIT", default=600)
CELERY_TASK_SOFT_TIME_LIMIT = env.int("CELERY_TASK_SOFT_TIME_LIMIT", default=540)
CELERY_TASK_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]

# --- Logging ------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {"request_id": {"()": "apps.core.logging.RequestIdFilter"}},
    "formatters": {
        "plain": {"format": "%(asctime)s %(levelname)s [%(request_id)s] %(name)s: %(message)s"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "plain",
            "filters": ["request_id"],
        },
    },
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", default="INFO")},
}
