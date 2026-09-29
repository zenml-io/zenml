# syntax=docker/dockerfile:1
FROM novaskyai/skyrl-train-ray-2.57.0-py3.12-cu13.0@sha256:609b7df001fa41a657d1d6a3607cb78af9290208d2f3397e4c7ce7182ec1d622

USER root
ENV SKYRL_COMMIT=0b286bacba2bb51dfe50186b6b5d6b1e0b5f5518 \
    UV_PROJECT_ENVIRONMENT=/opt/skyrl-venv \
    PATH=/opt/skyrl-venv/bin:/home/ray/.local/bin:$PATH \
    HF_HOME=/models/huggingface \
    HF_HUB_DISABLE_TELEMETRY=1 \
    DO_NOT_TRACK=1 \
    WANDB_MODE=disabled \
    SKYRL_RAY_NUM_CPUS=4

RUN mkdir -p /opt/skyrl /opt/terminal-training /models /checkpoints \
    && curl -fL --retry 0 "https://codeload.github.com/NovaSky-AI/SkyRL/tar.gz/${SKYRL_COMMIT}" -o /tmp/skyrl.tar.gz \
    && echo "2ce7e93a5631f0f8d08adb14d9a237f1d73df421484e57f5ddbffea8d8e0a731  /tmp/skyrl.tar.gz" | sha256sum -c - \
    && tar -xzf /tmp/skyrl.tar.gz --strip-components=1 -C /opt/skyrl \
    && rm /tmp/skyrl.tar.gz
WORKDIR /opt/skyrl
# Keep the upstream lock and its prebuilt Astral CUDA13/Torch2.11 wheels.
# Fail rather than silently compile GPU extensions under AMD64 emulation.
RUN uv sync --frozen --no-dev --extra fsdp --extra tinker \
    --no-build-package flash-attn --no-build-package causal-conv1d \
    && uv run --frozen --no-sync --extra fsdp --extra tinker -m skyrl.tinker.api --help > /dev/null \
    && uv cache clean
COPY entrypoint.py backend_config.json diagnostics.py /opt/terminal-training/
RUN chown -R ray: /models /checkpoints
USER ray
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=15m --retries=4 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/healthz', timeout=3)"
ENTRYPOINT ["python", "/opt/terminal-training/entrypoint.py"]
