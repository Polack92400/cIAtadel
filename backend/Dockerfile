# syntax=docker/dockerfile:1
FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

FROM base AS dev
COPY requirements-dev.txt .
RUN pip install -r requirements-dev.txt

FROM base AS runtime
RUN useradd --system --uid 10001 --home /app ciatadel
COPY --chown=ciatadel . .
RUN chmod +x docker/*.sh
USER ciatadel
EXPOSE 8000
CMD ["docker/start-web.sh"]
