#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.

import os
from typing import Optional

from zenml import __version__


def handle_bool_env_var(var: str, default: bool = False) -> bool:
    """Converts normal env var to boolean"""
    value = os.getenv(var)
    if value in ["1", "y", "yes", "True", "true"]:
        return True
    elif value in ["0", "n", "no", "False", "false"]:
        return False
    return default


def handle_int_env_var(var: str, default: int = 0) -> int:
    """Converts normal env var to int"""
    value = os.getenv(var, "")
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


# Global constants
APP_NAME = "zenml"
CONFIG_VERSION = "1"
GIT_REPO_URL = "https://github.com/zenml-io/zenml.git"

# Environment variables
ENV_ZENML_CONFIG_PATH = "ZENML_CONFIG_PATH"
ENV_ZENML_DEBUG = "ZENML_DEBUG"
ENV_ZENML_LOGGING_VERBOSITY = "ZENML_LOGGING_VERBOSITY"
ENV_ABSL_LOGGING_VERBOSITY = "ZENML_ABSL_LOGGING_VERBOSITY"
ENV_ZENML_REPOSITORY_PATH = "ZENML_REPOSITORY_PATH"
ENV_ZENML_PREVENT_PIPELINE_EXECUTION = "ZENML_PREVENT_PIPELINE_EXECUTION"
ENV_ZENML_ENABLE_RICH_TRACEBACK = "ZENML_ENABLE_RICH_TRACEBACK"
ENV_ZENML_DEFAULT_STORE_TYPE = "ZENML_DEFAULT_STORE_TYPE"
ENV_ZENML_ACTIVATED_STACK = "ZENML_ACTIVATED_STACK"
ENV_ZENML_PROFILE_NAME = "ZENML_PROFILE_NAME"
ENV_ZENML_SUPPRESS_LOGS = "ZENML_SUPPRESS_LOGS"

# Logging variables
IS_DEBUG_ENV: bool = handle_bool_env_var(ENV_ZENML_DEBUG, default=False)

ZENML_LOGGING_VERBOSITY: str = "INFO"

if IS_DEBUG_ENV:
    ZENML_LOGGING_VERBOSITY = os.getenv(
        ENV_ZENML_LOGGING_VERBOSITY, default="DEBUG"
    ).upper()
else:
    ZENML_LOGGING_VERBOSITY = os.getenv(
        ENV_ZENML_LOGGING_VERBOSITY, default="INFO"
    ).upper()

ABSL_LOGGING_VERBOSITY: int = handle_int_env_var(
    ENV_ABSL_LOGGING_VERBOSITY, -100
)

# Base images for zenml
ZENML_REGISTRY: str = "eu.gcr.io/maiot-zenml"
ZENML_BASE_IMAGE_NAME: str = f"{ZENML_REGISTRY}/zenml:base-{__version__}"
ZENML_TRAINER_IMAGE_NAME: str = f"{ZENML_REGISTRY}/zenml:cuda-{__version__}"
ZENML_DATAFLOW_IMAGE_NAME: str = (
    f"{ZENML_REGISTRY}/zenml:dataflow-{__version__}"
)

# Evaluation utils constants
COMPARISON_NOTEBOOK: str = "comparison_notebook.ipynb"
EVALUATION_NOTEBOOK: str = "evaluation_notebook.ipynb"

# Pipeline related constants
PREPROCESSING_FN: str = (
    "zenml.components.transform.transform_module" ".preprocessing_fn"
)
TRAINER_FN: str = "zenml.components.trainer.trainer_module.run_fn"

# GCP Orchestration
GCP_ENTRYPOINT: str = "zenml.backends.orchestrator.entrypoint"
AWS_ENTRYPOINT: str = "zenml.backends.orchestrator.entrypoint"
K8S_ENTRYPOINT: str = "zenml.backends.orchestrator.entrypoint"

# Analytics constants
VALID_OPERATING_SYSTEMS = ["Windows", "Darwin", "Linux"]

# Path utilities constants
REMOTE_FS_PREFIX = ["gs://", "hdfs://", "s3://", "az://", "abfs://"]

# Segment
SEGMENT_KEY_DEV = "mDBYI0m7GcCj59EZ4f9d016L1T3rh8J5"
SEGMENT_KEY_PROD = "sezE77zEoxHPFDXuyFfILx6fBnJFZ4p7"

# Container utils
SHOULD_PREVENT_PIPELINE_EXECUTION = handle_bool_env_var(
    ENV_ZENML_PREVENT_PIPELINE_EXECUTION
)

# Repository and local store directory paths:
REPOSITORY_DIRECTORY_NAME = ".zen"
LOCAL_STORES_DIRECTORY_NAME = "local_stores"

USER_MAIN_MODULE: Optional[str] = None

# Config file name
CONFIG_FILE_NAME = "config.yaml"

# Secrets Manager
ZENML_SCHEMA_NAME = "zenml_schema_name"
LOCAL_SECRETS_FILENAME = "secrets.yaml"

# Rich config
ENABLE_RICH_TRACEBACK = handle_bool_env_var(
    ENV_ZENML_ENABLE_RICH_TRACEBACK, True
)

# Services
DEFAULT_SERVICE_START_STOP_TIMEOUT = 10
DEFAULT_LOCAL_SERVICE_IP_ADDRESS = "127.0.0.1"
ZEN_SERVER_ENTRYPOINT = "zenml.zen_server.zen_server_api:app"


# API Endpoint paths:
STACKS_EMPTY = "/stacks-empty"
STACKS = "/stacks"
STACK_COMPONENTS = "/components"
STACK_CONFIGURATIONS = "/stack-configurations"
USERS = "/users"
TEAMS = "/teams"
PROJECTS = "/projects"
ROLES = "/roles"
FLAVORS = "/flavors"
ROLE_ASSIGNMENTS = "/role_assignments"
PIPELINE_RUNS = "/pipeline_runs"

# mandatory stack component attributes
MANDATORY_COMPONENT_ATTRIBUTES = ["name", "uuid"]
