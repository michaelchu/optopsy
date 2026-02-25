# syntax=docker/dockerfile:1
# Multi-stage build for Railway / container deployments.
# Uses uv for fast, reproducible dependency resolution.

# ---------------------------------------------------------------------------
# Stage 1: Build
# ---------------------------------------------------------------------------
FROM python:3.13-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.10.6 /uv /usr/local/bin/uv

WORKDIR /app

# Install dependencies first (layer cache optimisation).
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --extra ui --no-dev --no-install-project

# Copy source and install the project itself.
COPY . .
RUN uv sync --frozen --extra ui --no-dev

# ---------------------------------------------------------------------------
# Stage 2: Runtime
# ---------------------------------------------------------------------------
FROM python:3.13-slim

WORKDIR /app

# Copy the entire virtualenv + project from the builder.
COPY --from=builder /app /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

# Railway injects PORT; default to 8000 for local Docker runs.
ENV PORT=8000

EXPOSE ${PORT}

CMD optopsy-chat run --host 0.0.0.0 --port ${PORT} --headless
