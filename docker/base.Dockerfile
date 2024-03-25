ARG PYTHON_VERSION=3.9
FROM python:${PYTHON_VERSION}-slim AS base

ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    ZENML_CONTAINER=1

ARG ZENML_VERSION

# Upgrade pip to the latest version
RUN pip install --upgrade pip

# install the given zenml version (default to latest)
RUN pip install zenml${ZENML_VERSION:+==$ZENML_VERSION}

FROM base AS server

RUN pip install zenml${ZENML_VERSION:+==$ZENML_VERSION}[server,secrets-aws,secrets-gcp,secrets-azure,secrets-hashicorp,s3fs,gcsfs,adlfs,connectors-aws,connectors-gcp,connectors-azure]

WORKDIR /zenml

ENV ZENML_CONFIG_PATH=/zenml/.zenconfig \
    ZENML_DEBUG=false \
    ZENML_ANALYTICS_OPT_IN=true

ARG USERNAME=zenml
ARG USER_UID=1000
ARG USER_GID=$USER_UID

# Create the user
RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME

RUN mkdir -p /zenml/.zenconfig/local_stores/default_zen_store && chown -R $USER_UID:$USER_GID /zenml
ENV PATH="$PATH:/home/$USERNAME/.local/bin"

ENTRYPOINT ["uvicorn", "zenml.zen_server.zen_server_api:app",  "--log-level", "debug"]
CMD ["--port", "8080", "--host",  "0.0.0.0"]
