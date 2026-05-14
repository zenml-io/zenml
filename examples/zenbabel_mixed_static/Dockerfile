FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        git \
        nodejs \
        npm \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /work/zenml
COPY pyproject.toml README.md ./
COPY src ./src
RUN python -m pip install --no-cache-dir uv \
    && uv pip install --system -e .

WORKDIR /app
COPY examples/zenbabel_mixed_static/package.json ./package.json
COPY examples/zenbabel_mixed_static/package-lock.json ./package-lock.json
COPY examples/zenbabel_mixed_static/tsconfig.json ./tsconfig.json
COPY examples/zenbabel_mixed_static/ts ./ts
RUN npm ci && npm run build
