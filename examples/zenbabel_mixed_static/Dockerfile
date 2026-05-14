ARG ZENBABEL_IMAGE_PLATFORM=linux/amd64
FROM --platform=${ZENBABEL_IMAGE_PLATFORM} node:20-bookworm-slim AS node
FROM --platform=${ZENBABEL_IMAGE_PLATFORM} python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1 \
    HOME=/app \
    XDG_CONFIG_HOME=/app/.config \
    ZENML_CONFIG_PATH=/app/.zenconfig

COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && ln -s /usr/local/lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx

WORKDIR /work/zenml
COPY pyproject.toml README.md ./
COPY src ./src
RUN python -m pip install --no-cache-dir uv \
    && uv pip install --system -e ".[local,s3fs,connectors-aws]"

WORKDIR /app
RUN mkdir -p /app/.config /app/.zenconfig && chmod -R a+rw /app
COPY examples/zenbabel_mixed_static/package.json ./package.json
COPY examples/zenbabel_mixed_static/package-lock.json ./package-lock.json
COPY examples/zenbabel_mixed_static/tsconfig.json ./tsconfig.json
COPY examples/zenbabel_mixed_static/ts ./ts
RUN npm ci && npm run build
