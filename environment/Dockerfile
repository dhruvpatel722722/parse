FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir uv && uv pip install --system pytest

COPY src/ /app/environment/src/
COPY fixtures/ /app/environment/fixtures/

WORKDIR /app
