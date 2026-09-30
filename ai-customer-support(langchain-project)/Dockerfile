"""Dockerfile for the AI Customer Support Agent API."""

FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY app ./app
COPY knowledge ./knowledge
COPY alembic ./alembic
COPY alembic.ini ./
COPY scripts ./scripts

RUN pip install --upgrade pip setuptools wheel \
    && pip install .

RUN mkdir -p /app/data

EXPOSE 8000

CMD ["sh", "-c", "python scripts/seed_database.py && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
