ARG PYTHON_VERSION=3.9
FROM python:${PYTHON_VERSION}-slim AS base

ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    ZENML_DEBUG=1 \
    ZENML_LOGGING_VERBOSITY=INFO \
    ZENML_CONTAINER=1 \
    ZENML_SERVER_RATE_LIMIT_ENABLED=1 \
    ZENML_SERVER_LOGIN_RATE_LIMIT_MINUTE=100

ARG USERNAME=zenml
ARG USER_UID=1000
ARG USER_GID=$USER_UID

# Create the user
RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME \
    # Add sudo support.
    && apt-get update \
    && apt-get install -y sudo \
    && echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME


WORKDIR /zenml

COPY README.md pyproject.toml ./
# The existence of this __init__.py file allows the pip install before actually 
# copying our source files which would invalidate caching
COPY src/zenml/__init__.py ./src/zenml/

# Upgrade pip to the latest version
RUN pip install --upgrade pip
RUN pip install -e .[server,secrets-aws,secrets-gcp,secrets-azure,secrets-hashicorp,s3fs,gcsfs,adlfs,connectors-aws,connectors-gcp,connectors-azure]

COPY src src

RUN mkdir -p /zenml/.zenconfig/local_stores/default_zen_store && chown -R $USER_UID:$USER_GID /zenml
ENV PATH="$PATH:/home/$USERNAME/.local/bin"

ENV ZENML_CONFIG_PATH=/zenml/.zenconfig \
    ZENML_DEBUG=true \
    ZENML_ANALYTICS_OPT_IN=false

ENTRYPOINT ["uvicorn", "zenml.zen_server.zen_server_api:app",  "--log-level", "debug"]
CMD ["--port", "8080", "--host",  "0.0.0.0"]
