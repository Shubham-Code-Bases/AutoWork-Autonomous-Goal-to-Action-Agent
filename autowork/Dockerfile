# syntax=docker/dockerfile:1
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8080

WORKDIR /app

# Install system dependencies and uv package manager
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

# Copy project specification and install production dependencies
COPY pyproject.toml README.md ./
RUN uv pip install --system -r pyproject.toml

# Copy application source code
COPY app/ ./app/
COPY api/ ./api/
COPY worker/ ./worker/

# Non-root security user
RUN useradd -m -u 1000 autoworkuser && chown -R autoworkuser /app
USER autoworkuser

EXPOSE 8080

# Default entrypoint starts the API service (override with "python worker/main.py" for worker)
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
